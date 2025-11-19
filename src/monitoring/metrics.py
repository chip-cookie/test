#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
메트릭 수집기 (Metrics Collector)
=============================================================================

Prometheus 형식의 메트릭을 수집하고 노출합니다.

주요 메트릭:
    - 요청 수, 응답 시간, 오류율
    - 크롤링 통계
    - 캐시 히트율
    - 시스템 리소스 사용량

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps


@dataclass
class MetricValue:
    """
    단일 메트릭 값

    Attributes:
        name (str): 메트릭 이름
        value (float): 현재 값
        labels (Dict): 레이블
        timestamp (datetime): 측정 시각
        metric_type (str): counter, gauge, histogram
    """
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    metric_type: str = "gauge"


class MetricsCollector:
    """
    메트릭 수집 및 관리 클래스

    싱글톤 패턴을 사용하여 전역적으로 메트릭을 관리합니다.

    Example:
        >>> from src.monitoring import metrics
        >>>
        >>> # 카운터 증가
        >>> metrics.increment('requests_total', labels={'endpoint': '/api'})
        >>>
        >>> # 게이지 설정
        >>> metrics.set_gauge('active_crawlers', 3)
        >>>
        >>> # 히스토그램 관측
        >>> metrics.observe('response_time', 0.234)
        >>>
        >>> # 타이머 데코레이터
        >>> @metrics.timer('function_duration')
        ... async def my_function():
        ...     pass
    """

    _instance: Optional['MetricsCollector'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 메트릭 저장소
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = {}

        # 로거
        self._logger = logging.getLogger(__name__)

        self._initialized = True

    # =========================================================================
    # 카운터 (Counter) - 단조 증가하는 값
    # =========================================================================

    def increment(
        self,
        name: str,
        value: float = 1,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        카운터 증가

        Args:
            name: 메트릭 이름
            value: 증가량
            labels: 레이블
        """
        key = self._build_key(name, labels)

        if key not in self._counters:
            self._counters[key] = 0

        self._counters[key] += value

    def get_counter(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> float:
        """카운터 값 조회"""
        key = self._build_key(name, labels)
        return self._counters.get(key, 0)

    # =========================================================================
    # 게이지 (Gauge) - 임의로 증감하는 값
    # =========================================================================

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        게이지 설정

        Args:
            name: 메트릭 이름
            value: 설정할 값
            labels: 레이블
        """
        key = self._build_key(name, labels)
        self._gauges[key] = value

    def inc_gauge(
        self,
        name: str,
        value: float = 1,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """게이지 증가"""
        key = self._build_key(name, labels)
        self._gauges[key] = self._gauges.get(key, 0) + value

    def dec_gauge(
        self,
        name: str,
        value: float = 1,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """게이지 감소"""
        key = self._build_key(name, labels)
        self._gauges[key] = self._gauges.get(key, 0) - value

    def get_gauge(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> float:
        """게이지 값 조회"""
        key = self._build_key(name, labels)
        return self._gauges.get(key, 0)

    # =========================================================================
    # 히스토그램 (Histogram) - 분포 측정
    # =========================================================================

    def observe(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        히스토그램 관측값 기록

        Args:
            name: 메트릭 이름
            value: 관측값
            labels: 레이블
        """
        key = self._build_key(name, labels)

        if key not in self._histograms:
            self._histograms[key] = []

        self._histograms[key].append(value)

        # 최대 1000개만 유지 (메모리 관리)
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-1000:]

    def get_histogram_stats(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, float]:
        """
        히스토그램 통계 조회

        Returns:
            Dict: count, sum, avg, min, max, p50, p90, p99
        """
        key = self._build_key(name, labels)
        values = self._histograms.get(key, [])

        if not values:
            return {}

        sorted_values = sorted(values)
        count = len(values)

        return {
            "count": count,
            "sum": sum(values),
            "avg": sum(values) / count,
            "min": min(values),
            "max": max(values),
            "p50": sorted_values[int(count * 0.5)],
            "p90": sorted_values[int(count * 0.9)],
            "p99": sorted_values[int(count * 0.99)] if count > 100 else sorted_values[-1]
        }

    # =========================================================================
    # 데코레이터
    # =========================================================================

    def timer(self, name: str, labels: Optional[Dict[str, str]] = None):
        """
        함수 실행 시간 측정 데코레이터

        Args:
            name: 메트릭 이름
            labels: 레이블

        Example:
            >>> @metrics.timer('api_response_time')
            ... async def handle_request():
            ...     pass
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self.observe(name, duration, labels)

            return wrapper
        return decorator

    def count_calls(self, name: str, labels: Optional[Dict[str, str]] = None):
        """
        함수 호출 횟수 카운팅 데코레이터

        Args:
            name: 메트릭 이름
            labels: 레이블
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                self.increment(name, labels=labels)
                return await func(*args, **kwargs)

            return wrapper
        return decorator

    # =========================================================================
    # 내보내기
    # =========================================================================

    def export_prometheus(self) -> str:
        """
        Prometheus 형식으로 메트릭 내보내기

        Returns:
            str: Prometheus exposition 형식 문자열
        """
        lines = []

        # 카운터
        for key, value in self._counters.items():
            name, labels = self._parse_key(key)
            label_str = self._format_labels(labels)
            lines.append(f"{name}{label_str} {value}")

        # 게이지
        for key, value in self._gauges.items():
            name, labels = self._parse_key(key)
            label_str = self._format_labels(labels)
            lines.append(f"{name}{label_str} {value}")

        # 히스토그램
        for key, values in self._histograms.items():
            name, labels = self._parse_key(key)
            label_str = self._format_labels(labels)
            stats = self.get_histogram_stats(name, labels)

            if stats:
                lines.append(f"{name}_count{label_str} {stats['count']}")
                lines.append(f"{name}_sum{label_str} {stats['sum']}")

        return "\n".join(lines)

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        모든 메트릭을 딕셔너리로 반환

        Returns:
            Dict: 전체 메트릭
        """
        return {
            "counters": self._counters.copy(),
            "gauges": self._gauges.copy(),
            "histograms": {
                k: self.get_histogram_stats(k)
                for k in self._histograms.keys()
            }
        }

    def reset(self) -> None:
        """모든 메트릭 초기화"""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()

    # =========================================================================
    # Private 메서드
    # =========================================================================

    def _build_key(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> str:
        """메트릭 키 생성"""
        if not labels:
            return name

        label_parts = [f"{k}={v}" for k, v in sorted(labels.items())]
        return f"{name}:{','.join(label_parts)}"

    def _parse_key(self, key: str) -> tuple:
        """메트릭 키 파싱"""
        if ":" not in key:
            return key, {}

        name, label_str = key.split(":", 1)
        labels = {}

        for part in label_str.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                labels[k] = v

        return name, labels

    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Prometheus 레이블 형식"""
        if not labels:
            return ""

        parts = [f'{k}="{v}"' for k, v in labels.items()]
        return "{" + ",".join(parts) + "}"


# 전역 인스턴스
metrics = MetricsCollector()
