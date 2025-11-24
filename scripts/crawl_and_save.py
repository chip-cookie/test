#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
크롤러 실행 및 SQLite 저장 스크립트
=============================================================================

크롤러를 실행하고 결과를 SQLite 데이터베이스에 저장합니다.
MVP 버전: 간단한 실행 스크립트

Author: Youth Policy System Team
Version: 2.0.0 (MVP)
=============================================================================
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.bokjiro_crawler import BokjiroCrawler
from src.crawlers.kinfa_crawler import KinfaCrawler
from src.database.database import init_db, SessionLocal, get_database_info
from src.database.crawler_adapter import CrawlerAdapter


async def crawl_and_save_source(crawler, db_session, source_name: str):
    """
    단일 소스 크롤링 및 저장

    Args:
        crawler: 크롤러 인스턴스
        db_session: DB 세션
        source_name: 소스명 (로깅용)
    """
    print(f"\n{'='*60}")
    print(f"[{source_name}] 크롤링 시작...")
    print(f"{'='*60}")

    try:
        # 크롤링 실행
        result = await crawler.crawl()

        print(f"\n✅ 크롤링 완료:")
        print(f"   - 총 정책: {result.total_policies}개")
        print(f"   - 성공: {result.success_count}개")
        print(f"   - 실패: {result.error_count}개")
        print(f"   - 소요 시간: {result.elapsed_time:.2f}초")

        # SQLite에 저장
        print(f"\n💾 데이터베이스에 저장 중...")
        adapter = CrawlerAdapter(db_session)
        stats = adapter.save_crawl_result(result, update_if_exists=True)

        print(f"\n✅ 저장 완료:")
        print(f"   - 생성: {stats['created']}개")
        print(f"   - 업데이트: {stats['updated']}개")
        print(f"   - 스킵: {stats['skipped']}개")
        print(f"   - 실패: {stats['failed']}개")

        return stats

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return {"created": 0, "updated": 0, "skipped": 0, "failed": 0}


async def main():
    """메인 함수"""

    print("=" * 60)
    print("청년 정책 크롤러 → SQLite 저장")
    print("=" * 60)

    # 1. 데이터베이스 초기화
    print("\n[1/3] 데이터베이스 초기화...")
    init_db(drop_existing=False)  # 테스트 시 True로 변경

    # DB 정보 출력
    db_info = get_database_info()
    print(f"   경로: {db_info['path']}")
    if db_info['exists']:
        print(f"   크기: {db_info['size_mb']} MB")

    # 2. 크롤러 실행 및 저장
    print("\n[2/3] 크롤링 시작...")

    db = SessionLocal()

    try:
        # 복지로 크롤러
        bokjiro_crawler = BokjiroCrawler()
        bokjiro_stats = await crawl_and_save_source(
            bokjiro_crawler,
            db,
            "복지로"
        )

        # 서민금융진흥원 크롤러
        kinfa_crawler = KinfaCrawler()
        kinfa_stats = await crawl_and_save_source(
            kinfa_crawler,
            db,
            "서민금융진흥원"
        )

        # 전체 통계
        total_created = bokjiro_stats['created'] + kinfa_stats['created']
        total_updated = bokjiro_stats['updated'] + kinfa_stats['updated']

        print(f"\n{'='*60}")
        print(f"[전체 결과]")
        print(f"{'='*60}")
        print(f"✅ 총 생성: {total_created}개")
        print(f"♻️  총 업데이트: {total_updated}개")

    finally:
        db.close()

    # 3. 최종 DB 정보 출력
    print("\n[3/3] 최종 데이터베이스 상태...")
    db_info = get_database_info()

    if db_info['exists']:
        print(f"   크기: {db_info['size_mb']} MB")
        print(f"   테이블 수: {db_info['table_count']}")
        print(f"\n   테이블별 레코드 수:")
        for table, count in db_info.get('table_counts', {}).items():
            print(f"      - {table}: {count:,}개")

    print(f"\n{'='*60}")
    print("✨ 완료!")
    print(f"{'='*60}")


if __name__ == "__main__":
    # Windows에서 asyncio 이벤트 루프 정책 설정
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 크롤러 실행
    asyncio.run(main())
