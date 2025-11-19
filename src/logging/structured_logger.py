#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
구조화된 로거 (Structured Logger)
=============================================================================

JSON 형식의 구조화된 로깅을 제공합니다.
ELK 스택, CloudWatch 등과 연동하기 쉬운 형태입니다.

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import logging
import json
import sys
from typing import Any, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class LogConfig:
    """
    로깅 설정

    Attributes:
        level (str): 로그 수준 (DEBUG, INFO, WARNING, ERROR)
        format_type (str): 형식 (json, text)
        output (str): 출력 대상 (console, file, both)
        file_path (Optional[str]): 로그 파일 경로
        max_file_size (int): 최대 파일 크기 (bytes)
        backup_count (int): 백업 파일 수
        include_trace (bool): 스택 트레이스 포함 여부
    """
    level: str = "INFO"
    format_type: str = "json"
    output: str = "console"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    include_trace: bool = True


class JSONFormatter(logging.Formatter):
    """
    JSON 형식 로그 포맷터

    로그를 JSON 형식으로 변환하여 구조화된 로깅을 지원합니다.
    """

    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 JSON으로 변환"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # 추가 필드 (extra)
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # 예외 정보
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False, default=str)


class StructuredLogger:
    """
    구조화된 로거 클래스

    JSON 형식의 로그를 생성하고 다양한 출력 대상을 지원합니다.

    Example:
        >>> config = LogConfig(level="DEBUG", format_type="json")
        >>> logger = StructuredLogger("my_app", config)
        >>>
        >>> logger.info("사용자 요청 처리", user_id="user123", action="search")
        >>> logger.error("API 호출 실패", endpoint="/api/policy", status=500)
    """

    def __init__(self, name: str, config: Optional[LogConfig] = None):
        """
        구조화된 로거 초기화

        Args:
            name: 로거 이름
            config: 로깅 설정
        """
        self._config = config or LogConfig()
        self._logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self) -> None:
        """로거 설정"""
        # 로그 수준 설정
        level = getattr(logging, self._config.level.upper(), logging.INFO)
        self._logger.setLevel(level)

        # 기존 핸들러 제거
        self._logger.handlers.clear()

        # 포맷터 생성
        if self._config.format_type == "json":
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        # 콘솔 핸들러
        if self._config.output in ["console", "both"]:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)

        # 파일 핸들러
        if self._config.output in ["file", "both"] and self._config.file_path:
            from logging.handlers import RotatingFileHandler

            # 디렉토리 생성
            Path(self._config.file_path).parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                self._config.file_path,
                maxBytes=self._config.max_file_size,
                backupCount=self._config.backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

    def _log(
        self,
        level: int,
        message: str,
        **kwargs: Any
    ) -> None:
        """
        로그 기록 (private)

        Args:
            level: 로그 수준
            message: 로그 메시지
            **kwargs: 추가 필드
        """
        # extra 필드로 추가 데이터 전달
        extra = {"extra_fields": kwargs} if kwargs else {}
        self._logger.log(level, message, extra=extra)

    # =========================================================================
    # 공개 메서드
    # =========================================================================

    def debug(self, message: str, **kwargs: Any) -> None:
        """DEBUG 수준 로그"""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """INFO 수준 로그"""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """WARNING 수준 로그"""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """ERROR 수준 로그"""
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """CRITICAL 수준 로그"""
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """예외와 함께 로그"""
        self._logger.exception(message, extra={"extra_fields": kwargs})

    # =========================================================================
    # 컨텍스트 매니저
    # =========================================================================

    def context(self, **kwargs: Any):
        """
        로그 컨텍스트 매니저

        with 블록 내의 모든 로그에 공통 필드를 추가합니다.

        Example:
            >>> with logger.context(request_id="req123", user_id="user456"):
            ...     logger.info("처리 시작")
            ...     logger.info("처리 완료")
        """
        return LogContext(self, kwargs)


class LogContext:
    """로그 컨텍스트 매니저"""

    def __init__(self, logger: StructuredLogger, context: Dict[str, Any]):
        self._logger = logger
        self._context = context
        self._original_log = None

    def __enter__(self):
        # 원본 _log 메서드 저장
        self._original_log = self._logger._log

        # 컨텍스트를 포함하는 새 _log 메서드
        def contextual_log(level, message, **kwargs):
            merged = {**self._context, **kwargs}
            self._original_log(level, message, **merged)

        self._logger._log = contextual_log
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 원본 복원
        self._logger._log = self._original_log
        return False
