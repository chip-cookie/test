#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
Repository 패턴 (Data Access Layer)
=============================================================================

데이터베이스 CRUD 작업을 캡슐화한 Repository 클래스입니다.
SQL 쿼리를 직접 작성하지 않고 ORM을 통해 데이터를 관리합니다.

Author: Youth Policy System Team
Version: 2.0.0 (MVP)
=============================================================================
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .models import Policy, SearchHistory, SearchResult, Statistics


# =============================================================================
# Policy Repository
# =============================================================================

class PolicyRepository:
    """
    정책 데이터 저장소

    정책 데이터의 CRUD 작업을 담당합니다.
    """

    def __init__(self, db: Session):
        """
        Args:
            db: SQLAlchemy 세션
        """
        self.db = db

    def create(self, policy_data: Dict[str, Any]) -> Policy:
        """
        새 정책 생성

        Args:
            policy_data: 정책 데이터 딕셔너리

        Returns:
            Policy: 생성된 정책 객체

        Example:
            >>> repo = PolicyRepository(db)
            >>> policy = repo.create({
            ...     "policy_id": "bokjiro_001",
            ...     "policy_name": "청년 월세 지원",
            ...     "category": "주거",
            ...     ...
            ... })
        """
        policy = Policy(**policy_data)
        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def bulk_create(self, policies_data: List[Dict[str, Any]]) -> int:
        """
        여러 정책 일괄 생성

        Args:
            policies_data: 정책 데이터 리스트

        Returns:
            int: 생성된 정책 수

        Example:
            >>> policies = [
            ...     {"policy_id": "p1", "policy_name": "정책1", ...},
            ...     {"policy_id": "p2", "policy_name": "정책2", ...},
            ... ]
            >>> count = repo.bulk_create(policies)
        """
        policies = [Policy(**data) for data in policies_data]
        self.db.bulk_save_objects(policies)
        self.db.commit()
        return len(policies)

    def get_by_id(self, policy_id: int) -> Optional[Policy]:
        """
        ID로 정책 조회

        Args:
            policy_id: 정책 ID

        Returns:
            Optional[Policy]: 정책 객체 또는 None
        """
        return self.db.query(Policy).filter(Policy.id == policy_id).first()

    def get_by_policy_id(self, policy_id: str) -> Optional[Policy]:
        """
        정책 고유 ID로 조회

        Args:
            policy_id: 정책 고유 ID (예: "bokjiro_001")

        Returns:
            Optional[Policy]: 정책 객체 또는 None
        """
        return self.db.query(Policy).filter(Policy.policy_id == policy_id).first()

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Policy]:
        """
        모든 정책 조회 (페이징)

        Args:
            limit: 최대 개수
            offset: 시작 위치

        Returns:
            List[Policy]: 정책 리스트
        """
        return (
            self.db.query(Policy)
            .filter(Policy.is_active == True)
            .order_by(Policy.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def search_by_keyword(
        self,
        keyword: str,
        limit: int = 20
    ) -> List[Policy]:
        """
        키워드로 정책 검색 (간단한 텍스트 검색)

        정책명, 요약, 내용에서 키워드를 검색합니다.

        Args:
            keyword: 검색 키워드
            limit: 최대 결과 수

        Returns:
            List[Policy]: 검색된 정책 리스트

        Example:
            >>> policies = repo.search_by_keyword("주거")
        """
        search_pattern = f"%{keyword}%"

        return (
            self.db.query(Policy)
            .filter(
                and_(
                    Policy.is_active == True,
                    or_(
                        Policy.policy_name.like(search_pattern),
                        Policy.summary.like(search_pattern),
                        Policy.content.like(search_pattern),
                    )
                )
            )
            .order_by(Policy.view_count.desc())
            .limit(limit)
            .all()
        )

    def filter_by_conditions(
        self,
        category: Optional[str] = None,
        age: Optional[int] = None,
        income: Optional[int] = None,
        location: Optional[str] = None,
        limit: int = 20
    ) -> List[Policy]:
        """
        조건으로 정책 필터링

        Args:
            category: 카테고리
            age: 사용자 연령
            income: 사용자 소득
            location: 사용자 지역
            limit: 최대 결과 수

        Returns:
            List[Policy]: 필터링된 정책 리스트

        Example:
            >>> policies = repo.filter_by_conditions(
            ...     category="주거",
            ...     age=25,
            ...     income=30000000
            ... )
        """
        query = self.db.query(Policy).filter(Policy.is_active == True)

        # 카테고리 필터
        if category:
            query = query.filter(Policy.category == category)

        # 연령 필터
        if age:
            query = query.filter(
                and_(
                    Policy.target_age_min <= age,
                    Policy.target_age_max >= age
                )
            )

        # 소득 필터
        if income:
            query = query.filter(
                or_(
                    Policy.income_limit.is_(None),
                    Policy.income_limit >= income
                )
            )

        # 지역 필터 (JSON 필드 검색)
        if location:
            # SQLite JSON 검색은 복잡하므로 Python에서 필터링
            # 또는 location을 별도 테이블로 정규화
            pass

        return query.order_by(Policy.view_count.desc()).limit(limit).all()

    def update(self, policy_id: int, update_data: Dict[str, Any]) -> Optional[Policy]:
        """
        정책 업데이트

        Args:
            policy_id: 정책 ID
            update_data: 업데이트할 데이터

        Returns:
            Optional[Policy]: 업데이트된 정책 객체 또는 None
        """
        policy = self.get_by_id(policy_id)
        if not policy:
            return None

        for key, value in update_data.items():
            setattr(policy, key, value)

        policy.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(policy)
        return policy

    def increment_view_count(self, policy_id: int) -> None:
        """
        조회수 증가

        Args:
            policy_id: 정책 ID
        """
        policy = self.get_by_id(policy_id)
        if policy:
            policy.view_count += 1
            self.db.commit()

    def delete(self, policy_id: int) -> bool:
        """
        정책 삭제 (소프트 삭제)

        실제로 삭제하지 않고 is_active를 False로 설정합니다.

        Args:
            policy_id: 정책 ID

        Returns:
            bool: 삭제 성공 여부
        """
        policy = self.get_by_id(policy_id)
        if not policy:
            return False

        policy.is_active = False
        self.db.commit()
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """
        정책 통계 조회

        Returns:
            Dict: 통계 정보
        """
        total = self.db.query(func.count(Policy.id)).scalar()
        active = self.db.query(func.count(Policy.id)).filter(Policy.is_active == True).scalar()

        # 카테고리별 통계
        category_stats = (
            self.db.query(Policy.category, func.count(Policy.id))
            .filter(Policy.is_active == True)
            .group_by(Policy.category)
            .all()
        )

        return {
            "total_policies": total,
            "active_policies": active,
            "categories": {cat: count for cat, count in category_stats}
        }


# =============================================================================
# Search History Repository
# =============================================================================

class SearchHistoryRepository:
    """
    검색 기록 저장소

    검색 기록을 저장하고 분석합니다.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        query: str,
        result_count: int,
        user_age: Optional[int] = None,
        user_income: Optional[int] = None,
        user_location: Optional[str] = None,
        response_time: Optional[float] = None,
        llm_provider: Optional[str] = None,
        llm_response: Optional[str] = None
    ) -> SearchHistory:
        """
        검색 기록 생성

        Args:
            query: 검색 쿼리
            result_count: 결과 수
            user_age: 사용자 연령
            user_income: 사용자 소득
            user_location: 사용자 지역
            response_time: 응답 시간
            llm_provider: LLM 제공자
            llm_response: LLM 응답

        Returns:
            SearchHistory: 생성된 검색 기록
        """
        search = SearchHistory(
            query=query,
            result_count=result_count,
            user_age=user_age,
            user_income=user_income,
            user_location=user_location,
            response_time=response_time,
            llm_provider=llm_provider,
            llm_response=llm_response
        )
        self.db.add(search)
        self.db.commit()
        self.db.refresh(search)
        return search

    def add_results(
        self,
        search_id: int,
        policy_ids: List[int],
        scores: Optional[List[float]] = None
    ) -> None:
        """
        검색 결과 추가

        Args:
            search_id: 검색 기록 ID
            policy_ids: 정책 ID 리스트
            scores: 관련성 점수 리스트
        """
        if scores is None:
            scores = [None] * len(policy_ids)

        results = [
            SearchResult(
                search_id=search_id,
                policy_id=policy_id,
                rank=rank + 1,
                score=score
            )
            for rank, (policy_id, score) in enumerate(zip(policy_ids, scores))
        ]

        self.db.bulk_save_objects(results)
        self.db.commit()

    def get_recent_searches(self, limit: int = 10) -> List[SearchHistory]:
        """
        최근 검색 기록 조회

        Args:
            limit: 최대 개수

        Returns:
            List[SearchHistory]: 검색 기록 리스트
        """
        return (
            self.db.query(SearchHistory)
            .order_by(SearchHistory.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_popular_queries(self, limit: int = 10) -> List[tuple]:
        """
        인기 검색어 조회

        Args:
            limit: 최대 개수

        Returns:
            List[tuple]: (검색어, 검색 횟수) 리스트
        """
        return (
            self.db.query(SearchHistory.query, func.count(SearchHistory.id))
            .group_by(SearchHistory.query)
            .order_by(func.count(SearchHistory.id).desc())
            .limit(limit)
            .all()
        )

    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        검색 통계 조회

        Args:
            days: 조회 기간 (일)

        Returns:
            Dict: 통계 정보
        """
        from_date = datetime.now() - timedelta(days=days)

        total = (
            self.db.query(func.count(SearchHistory.id))
            .filter(SearchHistory.created_at >= from_date)
            .scalar()
        )

        avg_response = (
            self.db.query(func.avg(SearchHistory.response_time))
            .filter(SearchHistory.created_at >= from_date)
            .scalar()
        )

        return {
            "total_searches": total,
            "avg_response_time": round(avg_response, 2) if avg_response else None,
            "period_days": days
        }


# =============================================================================
# Statistics Repository
# =============================================================================

class StatisticsRepository:
    """
    통계 저장소

    일별 통계를 관리합니다.
    """

    def __init__(self, db: Session):
        self.db = db

    def update_daily_stats(
        self,
        date: date,
        searches: int = 0,
        views: int = 0
    ) -> Statistics:
        """
        일별 통계 업데이트

        Args:
            date: 날짜
            searches: 검색 수
            views: 조회 수

        Returns:
            Statistics: 통계 객체
        """
        stats = (
            self.db.query(Statistics)
            .filter(func.date(Statistics.date) == date)
            .first()
        )

        if not stats:
            stats = Statistics(date=datetime.combine(date, datetime.min.time()))
            self.db.add(stats)

        stats.total_searches += searches
        stats.total_views += views

        self.db.commit()
        self.db.refresh(stats)
        return stats
