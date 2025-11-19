#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
캐시 데코레이터 (Cache Decorators)
=============================================================================

함수 결과를 자동으로 캐싱하는 데코레이터를 제공합니다.

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import functools
import hashlib
import json
from typing import Callable, Optional, Any
import logging

logger = logging.getLogger(__name__)


def cached(
    ttl: int = 3600,
    namespace: str = "function",
    key_prefix: Optional[str] = None
):
    """
    함수 결과 캐싱 데코레이터

    함수의 인자를 기반으로 캐시 키를 생성하고,
    결과를 Redis에 캐싱합니다.

    Args:
        ttl: 캐시 TTL (초)
        namespace: 캐시 네임스페이스
        key_prefix: 키 접두사 (기본값: 함수명)

    Example:
        >>> @cached(ttl=300, namespace="api")
        ... async def get_policy_data(policy_id: str):
        ...     # 데이터베이스 조회
        ...     return data
        >>>
        >>> # 첫 호출: DB 조회 후 캐싱
        >>> data = await get_policy_data("policy-001")
        >>>
        >>> # 두 번째 호출: 캐시에서 반환
        >>> data = await get_policy_data("policy-001")
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 캐시 매니저 임포트 (순환 임포트 방지)
            from .cache_manager import CacheManager

            cache = CacheManager()

            # 캐시가 연결되지 않은 경우 원본 함수 실행
            if not cache.is_connected:
                return await func(*args, **kwargs)

            # 캐시 키 생성
            prefix = key_prefix or func.__name__
            key_data = json.dumps(
                {"args": args[1:], "kwargs": kwargs},  # self 제외
                sort_keys=True,
                default=str
            )
            key = f"{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"

            # 캐시 조회
            cached_value = await cache.get(key, namespace=namespace)

            if cached_value is not None:
                logger.debug(f"캐시 히트: {func.__name__}")
                return cached_value

            # 원본 함수 실행
            result = await func(*args, **kwargs)

            # 결과 캐싱
            if result is not None:
                await cache.set(key, result, ttl=ttl, namespace=namespace)
                logger.debug(f"캐시 저장: {func.__name__}")

            return result

        return wrapper
    return decorator


def cache_invalidate(
    namespace: str = "function",
    pattern: Optional[str] = None
):
    """
    캐시 무효화 데코레이터

    함수 실행 후 지정된 캐시를 무효화합니다.
    데이터 수정 작업 시 사용합니다.

    Args:
        namespace: 무효화할 네임스페이스
        pattern: 무효화할 키 패턴 (None이면 전체)

    Example:
        >>> @cache_invalidate(namespace="policies")
        ... async def update_policy(policy_id: str, data: dict):
        ...     # 정책 업데이트
        ...     return updated_policy
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 원본 함수 실행
            result = await func(*args, **kwargs)

            # 캐시 무효화
            from .cache_manager import CacheManager
            cache = CacheManager()

            if cache.is_connected:
                await cache.clear_namespace(namespace)
                logger.info(f"캐시 무효화: {namespace}")

            return result

        return wrapper
    return decorator
