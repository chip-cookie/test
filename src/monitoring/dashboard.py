#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
모니터링 대시보드 (Monitoring Dashboard)
=============================================================================

시스템 전체 상태를 통합하여 제공하는 대시보드 API입니다.

주요 기능:
    - 시스템 전체 상태 요약
    - 실시간 메트릭스 조회
    - 알림 히스토리
    - 성능 트렌드

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import psutil
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .health import HealthChecker, HealthStatus
from .metrics import MetricsCollector


class SystemStatus(Enum):
    """시스템 전체 상태"""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    OUTAGE = "outage"
    MAINTENANCE = "maintenance"


@dataclass
class DashboardConfig:
    """
    대시보드 설정

    Attributes:
        refresh_interval: 갱신 주기 (초)
        retention_hours: 데이터 보관 기간 (시간)
        alert_threshold: 알림 임계값
    """
    refresh_interval: int = 30
    retention_hours: int = 24
    alert_threshold: float = 0.8


@dataclass
class SystemMetrics:
    """시스템 리소스 메트릭스"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    timestamp: datetime = field(default_factory=datetime.now)


class MonitoringDashboard:
    """
    통합 모니터링 대시보드

    시스템의 모든 모니터링 정보를 통합하여 제공합니다.

    Example:
        >>> dashboard = MonitoringDashboard()
        >>> status = await dashboard.get_system_status()
        >>> print(f"시스템 상태: {status['status']}")
    """

    def __init__(
        self,
        config: Optional[DashboardConfig] = None,
        health_checker: Optional[HealthChecker] = None,
        metrics_collector: Optional[MetricsCollector] = None
    ):
        """
        대시보드 초기화

        Args:
            config: 대시보드 설정
            health_checker: 헬스 체커 인스턴스
            metrics_collector: 메트릭스 수집기 인스턴스
        """
        self.config = config or DashboardConfig()
        self.health_checker = health_checker or HealthChecker()
        self.metrics_collector = metrics_collector

        self._logger = logging.getLogger(__name__)
        self._alert_history: List[Dict[str, Any]] = []
        self._maintenance_mode = False

    async def get_system_status(self) -> Dict[str, Any]:
        """
        시스템 전체 상태 조회

        Returns:
            Dict: 시스템 상태 정보
        """
        # 유지보수 모드 체크
        if self._maintenance_mode:
            return {
                "status": SystemStatus.MAINTENANCE.value,
                "message": "시스템 유지보수 중입니다",
                "timestamp": datetime.now().isoformat()
            }

        # 컴포넌트 상태 확인
        health_result = await self.health_checker.check_all()

        # 시스템 리소스 메트릭스
        system_metrics = self._get_system_metrics()

        # 전체 상태 결정
        overall_status = self._determine_overall_status(
            health_result,
            system_metrics
        )

        # 최근 알림
        recent_alerts = self._get_recent_alerts(hours=1)

        return {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": self._get_uptime(),
            "health": health_result,
            "system": {
                "cpu_percent": system_metrics.cpu_percent,
                "memory_percent": system_metrics.memory_percent,
                "disk_percent": system_metrics.disk_percent
            },
            "alerts": {
                "recent_count": len(recent_alerts),
                "items": recent_alerts[:5]  # 최근 5개만
            },
            "metrics_summary": self._get_metrics_summary()
        }

    async def get_component_details(self, component: str) -> Dict[str, Any]:
        """
        특정 컴포넌트 상세 정보

        Args:
            component: 컴포넌트 이름

        Returns:
            Dict: 컴포넌트 상세 정보
        """
        health = await self.health_checker.check_component(component)

        return {
            "name": component,
            "status": health.status.value,
            "message": health.message,
            "latency_ms": health.latency_ms,
            "checked_at": health.checked_at.isoformat(),
            "metrics": self._get_component_metrics(component)
        }

    def get_metrics_history(
        self,
        metric_name: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        메트릭스 히스토리 조회

        Args:
            metric_name: 메트릭스 이름
            hours: 조회 기간 (시간)

        Returns:
            List: 시계열 데이터
        """
        if not self.metrics_collector:
            return []

        # 메트릭스 수집기에서 히스토리 조회
        # 실제 구현에서는 시계열 DB나 저장소에서 조회
        return []

    def add_alert(
        self,
        level: str,
        message: str,
        component: str = "system"
    ) -> None:
        """
        알림 추가

        Args:
            level: 알림 레벨 (info, warning, error, critical)
            message: 알림 메시지
            component: 관련 컴포넌트
        """
        alert = {
            "id": len(self._alert_history) + 1,
            "level": level,
            "message": message,
            "component": component,
            "timestamp": datetime.now().isoformat(),
            "acknowledged": False
        }

        self._alert_history.append(alert)

        # 보관 기간 초과 알림 정리
        self._cleanup_old_alerts()

        self._logger.info(f"알림 추가: [{level}] {message}")

    def acknowledge_alert(self, alert_id: int) -> bool:
        """
        알림 확인 처리

        Args:
            alert_id: 알림 ID

        Returns:
            bool: 성공 여부
        """
        for alert in self._alert_history:
            if alert["id"] == alert_id:
                alert["acknowledged"] = True
                alert["acknowledged_at"] = datetime.now().isoformat()
                return True
        return False

    def set_maintenance_mode(self, enabled: bool) -> None:
        """
        유지보수 모드 설정

        Args:
            enabled: 활성화 여부
        """
        self._maintenance_mode = enabled
        self._logger.info(f"유지보수 모드: {'활성화' if enabled else '비활성화'}")

    def get_api_stats(self) -> Dict[str, Any]:
        """
        API 통계 조회

        Returns:
            Dict: API 호출 통계
        """
        if not self.metrics_collector:
            return {}

        return {
            "total_requests": self.metrics_collector.get_counter("api_requests_total"),
            "error_rate": self._calculate_error_rate(),
            "avg_latency_ms": self._calculate_avg_latency(),
            "requests_per_minute": self._calculate_rpm()
        }

    # =========================================================================
    # Private 메서드
    # =========================================================================

    def _get_system_metrics(self) -> SystemMetrics:
        """시스템 리소스 메트릭스 수집"""
        net_io = psutil.net_io_counters()

        return SystemMetrics(
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_percent=psutil.virtual_memory().percent,
            disk_percent=psutil.disk_usage('/').percent,
            network_bytes_sent=net_io.bytes_sent,
            network_bytes_recv=net_io.bytes_recv
        )

    def _determine_overall_status(
        self,
        health_result: Dict[str, Any],
        system_metrics: SystemMetrics
    ) -> SystemStatus:
        """전체 시스템 상태 결정"""
        # 컴포넌트 상태 확인
        unhealthy_count = sum(
            1 for comp in health_result.get("components", [])
            if comp["status"] == HealthStatus.UNHEALTHY.value
        )

        if unhealthy_count > 0:
            return SystemStatus.OUTAGE

        # 리소스 임계값 확인
        threshold = self.config.alert_threshold * 100

        if (
            system_metrics.cpu_percent > threshold or
            system_metrics.memory_percent > threshold or
            system_metrics.disk_percent > threshold
        ):
            return SystemStatus.DEGRADED

        return SystemStatus.OPERATIONAL

    def _get_uptime(self) -> float:
        """시스템 가동 시간 (초)"""
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        return (datetime.now() - boot_time).total_seconds()

    def _get_recent_alerts(self, hours: int) -> List[Dict[str, Any]]:
        """최근 알림 조회"""
        cutoff = datetime.now() - timedelta(hours=hours)

        return [
            alert for alert in self._alert_history
            if datetime.fromisoformat(alert["timestamp"]) > cutoff
        ]

    def _get_metrics_summary(self) -> Dict[str, Any]:
        """메트릭스 요약"""
        if not self.metrics_collector:
            return {}

        return {
            "counters": self.metrics_collector.get_all_counters(),
            "gauges": self.metrics_collector.get_all_gauges()
        }

    def _get_component_metrics(self, component: str) -> Dict[str, Any]:
        """컴포넌트별 메트릭스"""
        # 컴포넌트별 메트릭스 조회
        return {}

    def _cleanup_old_alerts(self) -> None:
        """오래된 알림 정리"""
        cutoff = datetime.now() - timedelta(hours=self.config.retention_hours)

        self._alert_history = [
            alert for alert in self._alert_history
            if datetime.fromisoformat(alert["timestamp"]) > cutoff
        ]

    def _calculate_error_rate(self) -> float:
        """에러율 계산"""
        if not self.metrics_collector:
            return 0.0

        total = self.metrics_collector.get_counter("api_requests_total")
        errors = self.metrics_collector.get_counter("api_errors_total")

        if total == 0:
            return 0.0

        return round((errors / total) * 100, 2)

    def _calculate_avg_latency(self) -> float:
        """평균 지연시간 계산"""
        # 실제 구현에서는 히스토그램에서 계산
        return 0.0

    def _calculate_rpm(self) -> float:
        """분당 요청 수 계산"""
        # 실제 구현에서는 시계열 데이터에서 계산
        return 0.0


# =============================================================================
# 편의 함수
# =============================================================================

def create_default_dashboard() -> MonitoringDashboard:
    """
    기본 설정으로 대시보드 생성

    Returns:
        MonitoringDashboard: 대시보드 인스턴스
    """
    from .metrics import MetricsCollector

    config = DashboardConfig()
    health_checker = HealthChecker()
    metrics_collector = MetricsCollector()

    # 기본 헬스 체크 등록
    async def check_system():
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        return cpu < 90 and memory < 90

    health_checker.add_check("system", check_system)

    return MonitoringDashboard(
        config=config,
        health_checker=health_checker,
        metrics_collector=metrics_collector
    )
