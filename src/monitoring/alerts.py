#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
알림 매니저 (Alert Manager)
=============================================================================

다양한 채널(Slack, Discord, Email)로 알림을 전송합니다.

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import logging
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class AlertLevel(Enum):
    """알림 수준"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AlertConfig:
    """
    알림 설정

    Attributes:
        slack_webhook_url: Slack 웹훅 URL
        discord_webhook_url: Discord 웹훅 URL
        email_config: 이메일 설정 딕셔너리
        enabled_channels: 활성화된 채널 목록
        min_level: 최소 알림 수준
    """
    slack_webhook_url: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    email_config: Optional[Dict[str, str]] = None
    enabled_channels: List[str] = None
    min_level: AlertLevel = AlertLevel.WARNING

    def __post_init__(self):
        if self.enabled_channels is None:
            self.enabled_channels = []


class AlertManager:
    """
    알림 전송 매니저

    다양한 채널로 알림을 전송하고 관리합니다.

    Example:
        >>> config = AlertConfig(
        ...     slack_webhook_url="https://hooks.slack.com/...",
        ...     enabled_channels=["slack"]
        ... )
        >>> alert_manager = AlertManager(config)
        >>>
        >>> await alert_manager.send(
        ...     level=AlertLevel.ERROR,
        ...     title="크롤링 실패",
        ...     message="서민금융진흥원 크롤러 오류 발생",
        ...     details={"error": "Connection timeout"}
        ... )
    """

    def __init__(self, config: AlertConfig):
        """
        알림 매니저 초기화

        Args:
            config: 알림 설정
        """
        self._config = config
        self._logger = logging.getLogger(__name__)
        self._history: List[Dict[str, Any]] = []

    async def send(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        알림 전송

        Args:
            level: 알림 수준
            title: 알림 제목
            message: 알림 메시지
            details: 추가 세부 정보

        Returns:
            bool: 전송 성공 여부
        """
        # 최소 수준 확인
        if self._get_level_priority(level) < self._get_level_priority(self._config.min_level):
            return False

        # 알림 기록
        alert_record = {
            "level": level.value,
            "title": title,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self._history.append(alert_record)

        # 채널별 전송
        success = True

        if "slack" in self._config.enabled_channels and self._config.slack_webhook_url:
            if not await self._send_slack(level, title, message, details):
                success = False

        if "discord" in self._config.enabled_channels and self._config.discord_webhook_url:
            if not await self._send_discord(level, title, message, details):
                success = False

        return success

    async def _send_slack(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]]
    ) -> bool:
        """Slack으로 알림 전송"""
        try:
            # 색상 설정
            color_map = {
                AlertLevel.INFO: "#36a64f",
                AlertLevel.WARNING: "#ff9800",
                AlertLevel.ERROR: "#f44336",
                AlertLevel.CRITICAL: "#9c27b0"
            }

            payload = {
                "attachments": [{
                    "color": color_map.get(level, "#000000"),
                    "title": f"[{level.value.upper()}] {title}",
                    "text": message,
                    "fields": [
                        {"title": k, "value": str(v), "short": True}
                        for k, v in (details or {}).items()
                    ],
                    "footer": "Youth Policy System",
                    "ts": datetime.now().timestamp()
                }]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._config.slack_webhook_url,
                    json=payload
                ) as response:
                    return response.status == 200

        except Exception as e:
            self._logger.error(f"Slack 알림 전송 실패: {e}")
            return False

    async def _send_discord(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]]
    ) -> bool:
        """Discord로 알림 전송"""
        try:
            color_map = {
                AlertLevel.INFO: 3066993,
                AlertLevel.WARNING: 16776960,
                AlertLevel.ERROR: 15158332,
                AlertLevel.CRITICAL: 10181046
            }

            payload = {
                "embeds": [{
                    "title": f"[{level.value.upper()}] {title}",
                    "description": message,
                    "color": color_map.get(level, 0),
                    "fields": [
                        {"name": k, "value": str(v), "inline": True}
                        for k, v in (details or {}).items()
                    ],
                    "footer": {"text": "Youth Policy System"},
                    "timestamp": datetime.now().isoformat()
                }]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._config.discord_webhook_url,
                    json=payload
                ) as response:
                    return response.status == 204

        except Exception as e:
            self._logger.error(f"Discord 알림 전송 실패: {e}")
            return False

    def _get_level_priority(self, level: AlertLevel) -> int:
        """알림 수준 우선순위"""
        priorities = {
            AlertLevel.INFO: 0,
            AlertLevel.WARNING: 1,
            AlertLevel.ERROR: 2,
            AlertLevel.CRITICAL: 3
        }
        return priorities.get(level, 0)

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """알림 기록 조회"""
        return self._history[-limit:]
