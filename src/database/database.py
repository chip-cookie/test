#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
데이터베이스 연결 및 세션 관리 (Database Connection & Session)
=============================================================================

SQLAlchemy를 사용한 SQLite 데이터베이스 연결 및 세션 관리입니다.

Author: Youth Policy System Team
Version: 2.0.0 (MVP)
=============================================================================
"""

import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base


# =============================================================================
# 데이터베이스 설정
# =============================================================================

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent.parent

# SQLite 데이터베이스 경로
# 환경 변수로 경로 지정 가능, 기본값은 프로젝트 루트의 data/ 폴더
DATABASE_DIR = Path(os.getenv("DATABASE_DIR", PROJECT_ROOT / "data"))
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATABASE_DIR / "youth_policy.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# SQLAlchemy 엔진 생성
# SQLite 특화 설정:
# - check_same_thread=False: FastAPI 비동기 환경에서 필요
# - StaticPool: 단일 연결 재사용 (개발/테스트용)
# - echo=False: SQL 쿼리 로깅 비활성화 (개발 시 True로 변경)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,  # 개발 시 True로 변경하여 SQL 로그 확인
)


# SQLite 최적화 설정
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """
    SQLite 연결 시 성능 최적화 설정

    - foreign_keys=ON: 외래 키 제약 조건 활성화
    - journal_mode=WAL: Write-Ahead Logging (동시성 향상)
    - synchronous=NORMAL: 적절한 안정성과 성능 균형
    - temp_store=MEMORY: 임시 테이블을 메모리에 저장
    - mmap_size=30000000000: 메모리 맵 I/O 사용 (약 30GB)
    - cache_size=10000: 캐시 크기 증가
    """
    cursor = dbapi_conn.cursor()

    # 외래 키 제약 조건 활성화
    cursor.execute("PRAGMA foreign_keys=ON")

    # Write-Ahead Logging 모드 (동시 읽기/쓰기 성능 향상)
    cursor.execute("PRAGMA journal_mode=WAL")

    # 동기화 수준 (FULL > NORMAL > OFF)
    cursor.execute("PRAGMA synchronous=NORMAL")

    # 임시 저장소를 메모리에
    cursor.execute("PRAGMA temp_store=MEMORY")

    # 메모리 맵 I/O 사용 (약 30GB)
    cursor.execute("PRAGMA mmap_size=30000000000")

    # 페이지 캐시 크기 증가 (10000 pages ≈ 40MB)
    cursor.execute("PRAGMA cache_size=10000")

    cursor.close()


# 세션 팩토리 생성
# autocommit=False: 명시적 커밋 필요
# autoflush=False: 자동 flush 비활성화 (성능 향상)
# bind=engine: 데이터베이스 엔진 연결
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# =============================================================================
# 데이터베이스 초기화
# =============================================================================

def init_db(drop_existing: bool = False) -> None:
    """
    데이터베이스 초기화

    모든 테이블을 생성합니다.
    개발 중에는 drop_existing=True로 기존 테이블을 삭제할 수 있습니다.

    Args:
        drop_existing (bool): True일 경우 기존 테이블 삭제 후 재생성

    Example:
        >>> from src.database import init_db
        >>> init_db()  # 테이블 생성
        >>> init_db(drop_existing=True)  # 기존 테이블 삭제 후 재생성

    Warning:
        drop_existing=True는 모든 데이터를 삭제합니다!
        프로덕션 환경에서는 절대 사용하지 마세요.
    """
    if drop_existing:
        print("⚠️  경고: 기존 테이블을 삭제합니다...")
        Base.metadata.drop_all(bind=engine)
        print("✅ 기존 테이블 삭제 완료")

    print("📦 데이터베이스 테이블 생성 중...")
    Base.metadata.create_all(bind=engine)
    print(f"✅ 데이터베이스 초기화 완료: {DATABASE_PATH}")


def get_db() -> Generator[Session, None, None]:
    """
    데이터베이스 세션 생성 (의존성 주입용)

    FastAPI의 Dependency Injection에서 사용합니다.
    자동으로 세션을 열고 닫아줍니다.

    Yields:
        Session: SQLAlchemy 세션

    Example:
        >>> from fastapi import Depends
        >>> from src.database import get_db
        >>>
        >>> @app.get("/policies")
        >>> def get_policies(db: Session = Depends(get_db)):
        >>>     return db.query(Policy).all()

    Note:
        - 세션은 자동으로 닫힙니다 (finally 블록)
        - 에러 발생 시 자동 롤백
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# 유틸리티 함수
# =============================================================================

def get_database_info() -> dict:
    """
    데이터베이스 정보 조회

    Returns:
        dict: 데이터베이스 경로, 크기 등 정보

    Example:
        >>> from src.database.database import get_database_info
        >>> info = get_database_info()
        >>> print(info)
        {'path': '/path/to/youth_policy.db', 'size_mb': 1.5, ...}
    """
    import sqlite3

    info = {
        "path": str(DATABASE_PATH),
        "url": DATABASE_URL,
        "exists": DATABASE_PATH.exists(),
    }

    if DATABASE_PATH.exists():
        # 파일 크기 (MB)
        size_bytes = DATABASE_PATH.stat().st_size
        info["size_mb"] = round(size_bytes / (1024 * 1024), 2)

        # 테이블 수 조회
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        )
        info["table_count"] = cursor.fetchone()[0]

        # 각 테이블의 레코드 수
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = cursor.fetchall()

        table_counts = {}
        for (table_name,) in tables:
            if table_name != 'sqlite_sequence':
                cursor.execute(f"SELECT count(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                table_counts[table_name] = count

        info["table_counts"] = table_counts
        conn.close()

    return info


def reset_database() -> None:
    """
    데이터베이스 완전 초기화

    데이터베이스 파일을 삭제하고 새로 생성합니다.

    Warning:
        모든 데이터가 삭제됩니다!
        개발/테스트 환경에서만 사용하세요.
    """
    print("⚠️  경고: 데이터베이스를 완전히 초기화합니다...")

    # 기존 파일 삭제
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
        print(f"🗑️  기존 데이터베이스 삭제: {DATABASE_PATH}")

    # 새로 생성
    init_db()
    print("✅ 데이터베이스 초기화 완료")


# =============================================================================
# 스크립트 실행 시 테스트
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("데이터베이스 초기화 스크립트")
    print("=" * 60)

    # 데이터베이스 초기화
    init_db(drop_existing=False)

    # 정보 출력
    info = get_database_info()
    print(f"\n📊 데이터베이스 정보:")
    print(f"   경로: {info['path']}")
    print(f"   존재: {info['exists']}")

    if info['exists']:
        print(f"   크기: {info['size_mb']} MB")
        print(f"   테이블 수: {info['table_count']}")
        print(f"\n📋 테이블별 레코드 수:")
        for table, count in info.get('table_counts', {}).items():
            print(f"   - {table}: {count}개")
