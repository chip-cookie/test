#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
FastAPI MVP 서버
=============================================================================

청년 정책 추천 시스템의 REST API 서버입니다.
SQLite + SQLAlchemy ORM을 사용한 간단한 MVP 버전입니다.

Author: Youth Policy System Team
Version: 2.0.0 (MVP)
=============================================================================
"""

import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db, Policy, SearchHistory
from ..database.repository import PolicyRepository, SearchHistoryRepository


# =============================================================================
# FastAPI 앱 생성
# =============================================================================

app = FastAPI(
    title="청년 정책 추천 API",
    description="청년을 위한 정책 추천 서비스 MVP",
    version="2.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
)

# CORS 설정 (프론트엔드 연동을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 구체적인 도메인 지정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Pydantic 스키마 (Request/Response 모델)
# =============================================================================

class PolicyResponse(BaseModel):
    """정책 응답 모델"""

    id: int
    policy_id: str
    policy_name: str
    category: str
    summary: Optional[str]
    eligibility: Optional[str]
    target_age_min: Optional[int]
    target_age_max: Optional[int]
    income_limit: Optional[int]
    benefits: Optional[str]
    required_documents: Optional[List[str]]
    application_url: Optional[str]
    official_link: str
    source_name: str
    keywords: Optional[List[str]]
    location: Optional[List[str]]
    view_count: int

    class Config:
        orm_mode = True


class SearchRequest(BaseModel):
    """검색 요청 모델"""

    query: str = Field(..., min_length=1, max_length=500, description="검색 쿼리")
    age: Optional[int] = Field(None, ge=0, le=150, description="사용자 연령")
    income: Optional[int] = Field(None, ge=0, description="사용자 소득 (원)")
    location: Optional[str] = Field(None, max_length=100, description="사용자 지역")
    category: Optional[str] = Field(None, max_length=50, description="카테고리 필터")
    limit: int = Field(20, ge=1, le=100, description="최대 결과 수")


class SearchResponse(BaseModel):
    """검색 응답 모델"""

    query: str
    total_results: int
    results: List[PolicyResponse]
    response_time: Optional[float]


# =============================================================================
# API 엔드포인트
# =============================================================================

@app.get("/")
async def root():
    """
    API 루트 엔드포인트

    서비스 상태 확인용
    """
    return {
        "service": "청년 정책 추천 API",
        "version": "2.0.0 (MVP)",
        "status": "healthy",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    헬스 체크

    데이터베이스 연결 상태 확인
    """
    try:
        # DB 쿼리 실행하여 연결 확인
        repo = PolicyRepository(db)
        stats = repo.get_statistics()

        return {
            "status": "healthy",
            "database": "connected",
            "total_policies": stats["total_policies"],
            "active_policies": stats["active_policies"],
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")


@app.get("/policies", response_model=List[PolicyResponse])
async def get_policies(
    limit: int = Query(20, ge=1, le=100, description="최대 개수"),
    offset: int = Query(0, ge=0, description="오프셋"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    db: Session = Depends(get_db)
):
    """
    정책 목록 조회

    페이징을 지원합니다.
    """
    repo = PolicyRepository(db)

    if category:
        # 카테고리 필터
        policies = repo.filter_by_conditions(category=category, limit=limit)
    else:
        # 전체 조회
        policies = repo.get_all(limit=limit, offset=offset)

    return policies


@app.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: int,
    db: Session = Depends(get_db)
):
    """
    정책 상세 조회

    조회수가 자동으로 증가합니다.
    """
    repo = PolicyRepository(db)

    policy = repo.get_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # 조회수 증가
    repo.increment_view_count(policy_id)

    return policy


@app.post("/search", response_model=SearchResponse)
async def search_policies(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    정책 검색

    키워드와 조건으로 정책을 검색합니다.
    검색 기록이 자동으로 저장됩니다.
    """
    import time
    start_time = time.time()

    repo = PolicyRepository(db)
    search_repo = SearchHistoryRepository(db)

    # 조건 필터링
    policies = repo.filter_by_conditions(
        category=request.category,
        age=request.age,
        income=request.income,
        location=request.location,
        limit=request.limit
    )

    # 키워드 검색 (추가 필터링)
    if request.query:
        keyword_results = repo.search_by_keyword(request.query, limit=request.limit * 2)

        # 두 결과를 병합 (중복 제거)
        policy_ids = {p.id for p in policies}
        for p in keyword_results:
            if p.id not in policy_ids:
                policies.append(p)
                if len(policies) >= request.limit:
                    break

    # 응답 시간 계산
    response_time = time.time() - start_time

    # 검색 기록 저장
    search_history = search_repo.create(
        query=request.query,
        result_count=len(policies),
        user_age=request.age,
        user_income=request.income,
        user_location=request.location,
        response_time=response_time
    )

    # 검색 결과 연결
    if policies:
        policy_ids = [p.id for p in policies]
        search_repo.add_results(search_history.id, policy_ids)

    return SearchResponse(
        query=request.query,
        total_results=len(policies),
        results=policies[:request.limit],
        response_time=round(response_time, 3)
    )


@app.get("/categories")
async def get_categories(db: Session = Depends(get_db)):
    """
    사용 가능한 카테고리 목록 조회
    """
    repo = PolicyRepository(db)
    stats = repo.get_statistics()

    return {
        "categories": list(stats["categories"].keys()),
        "category_counts": stats["categories"]
    }


@app.get("/statistics")
async def get_statistics(db: Session = Depends(get_db)):
    """
    시스템 통계 조회
    """
    policy_repo = PolicyRepository(db)
    search_repo = SearchHistoryRepository(db)

    policy_stats = policy_repo.get_statistics()
    search_stats = search_repo.get_statistics(days=7)
    popular_queries = search_repo.get_popular_queries(limit=10)

    return {
        "policies": policy_stats,
        "searches": search_stats,
        "popular_queries": [
            {"query": q, "count": c} for q, c in popular_queries
        ]
    }


@app.get("/search/recent")
async def get_recent_searches(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    최근 검색 기록 조회
    """
    repo = SearchHistoryRepository(db)
    searches = repo.get_recent_searches(limit=limit)

    return [
        {
            "query": s.query,
            "result_count": s.result_count,
            "created_at": s.created_at.isoformat()
        }
        for s in searches
    ]


# =============================================================================
# 앱 시작 이벤트
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """
    앱 시작 시 실행

    데이터베이스 초기화
    """
    from ..database.database import init_db, get_database_info

    print("=" * 60)
    print("청년 정책 추천 API 서버 시작")
    print("=" * 60)

    # DB 초기화 (테이블이 없으면 생성)
    init_db(drop_existing=False)

    # DB 정보 출력
    info = get_database_info()
    print(f"\n📊 데이터베이스 정보:")
    print(f"   경로: {info['path']}")

    if info['exists']:
        print(f"   크기: {info['size_mb']} MB")
        print(f"   테이블 수: {info['table_count']}")
        print(f"\n   테이블별 레코드 수:")
        for table, count in info.get('table_counts', {}).items():
            print(f"      - {table}: {count:,}개")

    print(f"\n✅ 서버 준비 완료")
    print(f"   Swagger UI: http://localhost:8000/docs")
    print(f"   ReDoc: http://localhost:8000/redoc")
    print("=" * 60)


if __name__ == "__main__":
    import uvicorn

    # 개발 서버 실행
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 코드 변경 시 자동 재시작
        log_level="info"
    )
