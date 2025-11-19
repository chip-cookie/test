#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
분석 트래커 (Analytics Tracker)
=============================================================================

사용자 쿼리 및 시스템 사용 패턴을 분석합니다.

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import Counter
from dataclasses import dataclass, field
import hashlib


@dataclass
class QueryAnalytics:
    """쿼리 분석 데이터"""
    query_hash: str
    query_type: str
    categories: List[str]
    response_time_ms: float
    policies_returned: int
    timestamp: datetime
    success: bool


class AnalyticsTracker:
    """
    사용 패턴 분석 트래커

    사용자 쿼리, 인기 정책, 응답 시간 등을 추적하고 분석합니다.

    Example:
        >>> tracker = AnalyticsTracker()
        >>>
        >>> # 쿼리 추적
        >>> tracker.track_query(
        ...     query="대출 갈아타기",
        ...     categories=["대출"],
        ...     response_time=234,
        ...     policies_count=3
        ... )
        >>>
        >>> # 통계 조회
        >>> stats = tracker.get_statistics()
        >>> popular = tracker.get_popular_categories()
    """

    def __init__(self, max_records: int = 10000):
        """
        분석 트래커 초기화

        Args:
            max_records: 최대 저장 레코드 수
        """
        self._max_records = max_records
        self._records: List[QueryAnalytics] = []
        self._logger = logging.getLogger(__name__)

    def track_query(
        self,
        query: str,
        categories: List[str],
        response_time: float,
        policies_count: int,
        success: bool = True,
        query_type: str = "search"
    ) -> None:
        """
        쿼리 추적

        Args:
            query: 사용자 쿼리 (해시화됨)
            categories: 관련 카테고리
            response_time: 응답 시간 (ms)
            policies_count: 반환된 정책 수
            success: 성공 여부
            query_type: 쿼리 유형
        """
        # 쿼리 해시화 (개인정보 보호)
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]

        record = QueryAnalytics(
            query_hash=query_hash,
            query_type=query_type,
            categories=categories,
            response_time_ms=response_time,
            policies_returned=policies_count,
            timestamp=datetime.now(),
            success=success
        )

        self._records.append(record)

        # 레코드 수 제한
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

    def get_statistics(
        self,
        period_hours: int = 24
    ) -> Dict[str, Any]:
        """
        통계 조회

        Args:
            period_hours: 통계 기간 (시간)

        Returns:
            Dict: 통계 정보
        """
        cutoff = datetime.now() - timedelta(hours=period_hours)
        recent = [r for r in self._records if r.timestamp >= cutoff]

        if not recent:
            return {"message": "데이터 없음"}

        response_times = [r.response_time_ms for r in recent]
        success_count = sum(1 for r in recent if r.success)

        return {
            "period_hours": period_hours,
            "total_queries": len(recent),
            "success_rate": round(success_count / len(recent) * 100, 2),
            "avg_response_time_ms": round(sum(response_times) / len(response_times), 2),
            "min_response_time_ms": round(min(response_times), 2),
            "max_response_time_ms": round(max(response_times), 2),
            "avg_policies_returned": round(
                sum(r.policies_returned for r in recent) / len(recent), 2
            )
        }

    def get_popular_categories(self, top_n: int = 10) -> List[tuple]:
        """
        인기 카테고리 조회

        Args:
            top_n: 상위 N개

        Returns:
            List[tuple]: (카테고리, 횟수) 리스트
        """
        all_categories = []
        for record in self._records:
            all_categories.extend(record.categories)

        return Counter(all_categories).most_common(top_n)

    def get_hourly_distribution(self) -> Dict[int, int]:
        """
        시간대별 쿼리 분포

        Returns:
            Dict: {시간: 쿼리 수}
        """
        distribution = Counter(r.timestamp.hour for r in self._records)
        return dict(sorted(distribution.items()))

    def export_report(self) -> Dict[str, Any]:
        """
        전체 분석 리포트 생성

        Returns:
            Dict: 분석 리포트
        """
        return {
            "generated_at": datetime.now().isoformat(),
            "total_records": len(self._records),
            "statistics_24h": self.get_statistics(24),
            "statistics_7d": self.get_statistics(168),
            "popular_categories": self.get_popular_categories(),
            "hourly_distribution": self.get_hourly_distribution()
        }
