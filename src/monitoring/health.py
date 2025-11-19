#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
헬스 체커 (Health Checker)
=============================================================================

시스템 컴포넌트의 상태를 확인합니다.

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import asyncio


class HealthStatus(Enum):
    """컴포넌트 상태"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """컴포넌트 상태 정보"""
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0
    checked_at: datetime = None

    def __post_init__(self):
        if self.checked_at is None:
            self.checked_at = datetime.now()


class HealthChecker:
    """
    시스템 헬스 체커

    Example:
        >>> checker = HealthChecker()
        >>> checker.add_check("redis", check_redis)
        >>> checker.add_check("pinecone", check_pinecone)
        >>>
        >>> status = await checker.check_all()
        >>> print(status)
    """

    def __init__(self):
        self._checks: Dict[str, callable] = {}
        self._logger = logging.getLogger(__name__)

    def add_check(self, name: str, check_func: callable) -> None:
        """
        헬스 체크 함수 등록

        Args:
            name: 컴포넌트 이름
            check_func: 체크 함수 (async, bool 반환)
        """
        self._checks[name] = check_func

    async def check_all(self) -> Dict[str, Any]:
        """
        모든 컴포넌트 상태 확인

        Returns:
            Dict: 전체 상태 정보
        """
        results: List[ComponentHealth] = []
        overall_status = HealthStatus.HEALTHY

        for name, check_func in self._checks.items():
            start_time = datetime.now()

            try:
                is_healthy = await asyncio.wait_for(
                    check_func(),
                    timeout=5.0
                )

                latency = (datetime.now() - start_time).total_seconds() * 1000

                if is_healthy:
                    status = HealthStatus.HEALTHY
                    message = "OK"
                else:
                    status = HealthStatus.UNHEALTHY
                    message = "Check failed"
                    overall_status = HealthStatus.UNHEALTHY

            except asyncio.TimeoutError:
                status = HealthStatus.UNHEALTHY
                message = "Timeout"
                latency = 5000
                overall_status = HealthStatus.UNHEALTHY

            except Exception as e:
                status = HealthStatus.UNHEALTHY
                message = str(e)
                latency = (datetime.now() - start_time).total_seconds() * 1000
                overall_status = HealthStatus.UNHEALTHY

            results.append(ComponentHealth(
                name=name,
                status=status,
                message=message,
                latency_ms=latency
            ))

        return {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "components": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "latency_ms": round(r.latency_ms, 2)
                }
                for r in results
            ]
        }

    async def check_component(self, name: str) -> ComponentHealth:
        """단일 컴포넌트 상태 확인"""
        if name not in self._checks:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message="Unknown component"
            )

        result = await self.check_all()
        for comp in result["components"]:
            if comp["name"] == name:
                return ComponentHealth(
                    name=comp["name"],
                    status=HealthStatus(comp["status"]),
                    message=comp["message"],
                    latency_ms=comp["latency_ms"]
                )

        return ComponentHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            message="Check not found"
        )
