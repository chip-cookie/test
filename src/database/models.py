#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
SQLAlchemy 데이터 모델 (Database Models)
=============================================================================

청년 정책 추천 시스템의 데이터베이스 모델입니다.
SQLite를 사용한 간단한 MVP 서비스용 설계입니다.

ORM을 사용하여 SQL 쿼리 없이 클래스 기반으로 데이터를 관리합니다.

Author: Youth Policy System Team
Version: 2.0.0 (MVP)
=============================================================================
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Boolean, JSON,
    ForeignKey, Index, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# SQLAlchemy Base 클래스
Base = declarative_base()


# =============================================================================
# 정책 모델 (Policy)
# =============================================================================

class Policy(Base):
    """
    청년 정책 정보 모델

    크롤링한 정책 데이터를 저장하는 핵심 테이블입니다.

    Attributes:
        id (int): 기본 키 (자동 증가)
        policy_id (str): 정책 고유 ID (크롤러 생성)
        policy_name (str): 정책명
        category (str): 카테고리 (주거, 취업, 교육 등)
        content (str): 정책 전체 내용
        summary (str): 정책 요약

        # 자격 조건
        eligibility (str): 자격 조건 설명
        target_age_min (int): 최소 연령
        target_age_max (int): 최대 연령
        income_limit (int): 소득 제한 (원)

        # 지원 내용
        benefits (str): 지원 내용
        required_documents (str): 필수 서류 (JSON 배열 문자열)

        # URL 및 메타데이터
        application_url (str): 신청 URL
        official_link (str): 공식 링크
        source_name (str): 데이터 소스명
        source_tier (str): 소스 신뢰도 (Tier 1/2)

        # 날짜 정보
        start_date (datetime): 신청 시작일
        end_date (datetime): 신청 종료일
        crawled_at (datetime): 크롤링 시각

        # 검색 최적화
        keywords (str): 검색 키워드 (JSON 배열)
        location (str): 대상 지역 (JSON 배열)

        # 상태
        is_active (bool): 활성 상태 (종료된 정책 필터링)
        view_count (int): 조회수

    Indexes:
        - policy_id (UNIQUE)
        - category
        - target_age_min, target_age_max
        - source_name
        - is_active
    """

    __tablename__ = "policies"

    # 기본 키
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 정책 기본 정보
    policy_id = Column(String(50), unique=True, nullable=False, index=True,
                       comment="정책 고유 ID")
    policy_name = Column(String(200), nullable=False,
                        comment="정책명")
    category = Column(String(50), nullable=False, index=True,
                     comment="카테고리")
    content = Column(Text, nullable=False,
                    comment="정책 전체 내용")
    summary = Column(Text, nullable=True,
                    comment="정책 요약")

    # 자격 조건
    eligibility = Column(Text, nullable=True,
                        comment="자격 조건 설명")
    target_age_min = Column(Integer, nullable=True, index=True,
                           comment="최소 연령")
    target_age_max = Column(Integer, nullable=True, index=True,
                           comment="최대 연령")
    income_limit = Column(Integer, nullable=True,
                         comment="소득 제한 (원)")

    # 지원 내용
    benefits = Column(Text, nullable=True,
                     comment="지원 내용")
    required_documents = Column(JSON, nullable=True,
                               comment="필수 서류 목록")

    # URL 및 소스 정보
    application_url = Column(String(500), nullable=True,
                            comment="신청 URL")
    official_link = Column(String(500), nullable=False,
                          comment="공식 링크")
    source_name = Column(String(100), nullable=False, index=True,
                        comment="데이터 소스명")
    source_tier = Column(String(10), nullable=False,
                        comment="소스 신뢰도")

    # 날짜 정보
    start_date = Column(DateTime, nullable=True,
                       comment="신청 시작일")
    end_date = Column(DateTime, nullable=True,
                     comment="신청 종료일")
    crawled_at = Column(DateTime, nullable=False, default=datetime.now,
                       comment="크롤링 시각")
    updated_at = Column(DateTime, nullable=False, default=datetime.now,
                       onupdate=datetime.now,
                       comment="마지막 업데이트 시각")

    # 검색 최적화
    keywords = Column(JSON, nullable=True,
                     comment="검색 키워드 배열")
    location = Column(JSON, nullable=True,
                     comment="대상 지역 배열")

    # 상태 및 통계
    is_active = Column(Boolean, default=True, nullable=False, index=True,
                      comment="활성 상태")
    view_count = Column(Integer, default=0, nullable=False,
                       comment="조회수")

    # 관계: 검색 기록과의 연결
    search_results = relationship("SearchResult", back_populates="policy")

    # 제약 조건
    __table_args__ = (
        CheckConstraint('target_age_min >= 0 AND target_age_min <= 150',
                       name='check_age_min_range'),
        CheckConstraint('target_age_max >= 0 AND target_age_max <= 150',
                       name='check_age_max_range'),
        CheckConstraint('target_age_min <= target_age_max',
                       name='check_age_range_valid'),
        CheckConstraint('income_limit >= 0',
                       name='check_income_positive'),
        CheckConstraint('view_count >= 0',
                       name='check_view_count_positive'),
        Index('idx_age_range', 'target_age_min', 'target_age_max'),
        Index('idx_active_category', 'is_active', 'category'),
    )

    def __repr__(self):
        return f"<Policy(id={self.id}, name='{self.policy_name}', category='{self.category}')>"

    def to_dict(self):
        """모델을 딕셔너리로 변환 (JSON 직렬화용)"""
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "policy_name": self.policy_name,
            "category": self.category,
            "summary": self.summary,
            "eligibility": self.eligibility,
            "target_age_min": self.target_age_min,
            "target_age_max": self.target_age_max,
            "income_limit": self.income_limit,
            "benefits": self.benefits,
            "required_documents": self.required_documents,
            "application_url": self.application_url,
            "official_link": self.official_link,
            "source_name": self.source_name,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "keywords": self.keywords,
            "location": self.location,
            "view_count": self.view_count,
        }


# =============================================================================
# 검색 기록 모델 (SearchHistory)
# =============================================================================

class SearchHistory(Base):
    """
    사용자 검색 기록 모델

    사용자의 검색 쿼리와 결과를 추적합니다.
    검색 패턴 분석 및 추천 개선에 활용됩니다.

    Attributes:
        id (int): 기본 키
        query (str): 검색 쿼리
        user_age (int): 사용자 연령 (선택)
        user_income (int): 사용자 소득 (선택)
        user_location (str): 사용자 지역 (선택)

        result_count (int): 검색 결과 수
        response_time (float): 응답 시간 (초)

        created_at (datetime): 검색 시각

    Indexes:
        - query
        - created_at
    """

    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 검색 쿼리
    query = Column(String(500), nullable=False, index=True,
                  comment="검색 쿼리")

    # 사용자 정보 (선택적)
    user_age = Column(Integer, nullable=True,
                     comment="사용자 연령")
    user_income = Column(Integer, nullable=True,
                        comment="사용자 소득")
    user_location = Column(String(100), nullable=True,
                          comment="사용자 지역")

    # 검색 메타데이터
    result_count = Column(Integer, default=0, nullable=False,
                         comment="검색 결과 수")
    response_time = Column(Float, nullable=True,
                          comment="응답 시간 (초)")

    # LLM 응답 정보 (MVP에서는 단일 LLM 사용)
    llm_provider = Column(String(50), nullable=True,
                         comment="사용된 LLM 제공자")
    llm_response = Column(Text, nullable=True,
                         comment="LLM 응답 내용")

    # 타임스탬프
    created_at = Column(DateTime, nullable=False, default=datetime.now,
                       index=True, comment="검색 시각")

    # 관계: 검색 결과
    results = relationship("SearchResult", back_populates="search")

    __table_args__ = (
        CheckConstraint('user_age >= 0 AND user_age <= 150 OR user_age IS NULL',
                       name='check_user_age_range'),
        CheckConstraint('user_income >= 0 OR user_income IS NULL',
                       name='check_user_income_positive'),
        CheckConstraint('result_count >= 0',
                       name='check_result_count_positive'),
        Index('idx_created_query', 'created_at', 'query'),
    )

    def __repr__(self):
        return f"<SearchHistory(id={self.id}, query='{self.query[:30]}...', results={self.result_count})>"


# =============================================================================
# 검색 결과 연결 모델 (SearchResult)
# =============================================================================

class SearchResult(Base):
    """
    검색 기록과 정책을 연결하는 중간 테이블

    어떤 검색에서 어떤 정책이 결과로 나왔는지 추적합니다.

    Attributes:
        id (int): 기본 키
        search_id (int): 검색 기록 ID (외래 키)
        policy_id (int): 정책 ID (외래 키)
        rank (int): 검색 결과 순위
        score (float): 관련성 점수
    """

    __tablename__ = "search_results"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 외래 키
    search_id = Column(Integer, ForeignKey('search_history.id'),
                      nullable=False, index=True)
    policy_id = Column(Integer, ForeignKey('policies.id'),
                      nullable=False, index=True)

    # 검색 결과 메타데이터
    rank = Column(Integer, nullable=False,
                 comment="검색 결과 순위")
    score = Column(Float, nullable=True,
                  comment="관련성 점수")

    # 관계
    search = relationship("SearchHistory", back_populates="results")
    policy = relationship("Policy", back_populates="search_results")

    __table_args__ = (
        CheckConstraint('rank > 0', name='check_rank_positive'),
        CheckConstraint('score >= 0 AND score <= 100 OR score IS NULL',
                       name='check_score_range'),
        Index('idx_search_rank', 'search_id', 'rank'),
    )

    def __repr__(self):
        return f"<SearchResult(search_id={self.search_id}, policy_id={self.policy_id}, rank={self.rank})>"


# =============================================================================
# 통계 모델 (Statistics) - 선택적
# =============================================================================

class Statistics(Base):
    """
    시스템 통계 정보

    일별 사용 통계를 저장합니다.

    Attributes:
        id (int): 기본 키
        date (datetime): 날짜
        total_searches (int): 총 검색 수
        total_views (int): 총 조회 수
        unique_queries (int): 고유 검색 쿼리 수
        avg_response_time (float): 평균 응답 시간
    """

    __tablename__ = "statistics"

    id = Column(Integer, primary_key=True, autoincrement=True)

    date = Column(DateTime, nullable=False, unique=True, index=True,
                 comment="통계 날짜")

    total_searches = Column(Integer, default=0, nullable=False,
                           comment="총 검색 수")
    total_views = Column(Integer, default=0, nullable=False,
                        comment="총 조회 수")
    unique_queries = Column(Integer, default=0, nullable=False,
                           comment="고유 검색 쿼리 수")
    avg_response_time = Column(Float, nullable=True,
                              comment="평균 응답 시간 (초)")

    created_at = Column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (
        CheckConstraint('total_searches >= 0', name='check_searches_positive'),
        CheckConstraint('total_views >= 0', name='check_views_positive'),
    )

    def __repr__(self):
        return f"<Statistics(date={self.date}, searches={self.total_searches})>"
