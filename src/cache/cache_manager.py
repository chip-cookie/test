#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
캐시 매니저 (Cache Manager)
=============================================================================

Redis 기반 캐싱을 관리하는 싱글톤 클래스입니다.
Strategy 패턴을 사용하여 다양한 캐싱 전략을 지원합니다.

주요 기능:
    - 응답 캐싱 (API 응답 결과)
    - 임베딩 캐싱 (벡터 임베딩)
    - 정책 데이터 캐싱
    - TTL 기반 자동 만료
    - 캐시 무효화

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import json
import hashlib
import logging
from typing import Any, Optional, Dict, List, Union
from dataclasses import dataclass
from datetime import timedelta
from abc import ABC, abstractmethod


@dataclass(frozen=True)
class CacheConfig:
    """
    캐시 설정 불변 데이터 클래스

    실행 중 설정 변경을 방지하여 안정성을 보장합니다.

    Attributes:
        host (str): Redis 호스트
        port (int): Redis 포트
        db (int): Redis DB 번호
        password (Optional[str]): Redis 비밀번호
        default_ttl (int): 기본 TTL (초)
        prefix (str): 키 접두사
        max_connections (int): 최대 연결 수

    Note:
        frozen=True로 인해 생성 후 수정할 수 없습니다.
        설정 변경이 필요하면 새 인스턴스를 생성하세요.
    """
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    default_ttl: int = 3600  # 1시간
    prefix: str = "youth_policy"
    max_connections: int = 10


class CacheStrategy(ABC):
    """
    캐싱 전략 추상 클래스

    Strategy 패턴을 사용하여 다양한 캐싱 방식을 지원합니다.
    """

    @abstractmethod
    def generate_key(self, *args, **kwargs) -> str:
        """캐시 키 생성"""
        pass

    @abstractmethod
    def serialize(self, value: Any) -> str:
        """값 직렬화"""
        pass

    @abstractmethod
    def deserialize(self, data: str) -> Any:
        """값 역직렬화"""
        pass


class JSONCacheStrategy(CacheStrategy):
    """
    JSON 기반 캐싱 전략

    일반적인 데이터(딕셔너리, 리스트)를 JSON으로 직렬화합니다.
    """

    def generate_key(self, *args, **kwargs) -> str:
        """
        인자를 기반으로 캐시 키 생성

        Args:
            *args: 위치 인자
            **kwargs: 키워드 인자

        Returns:
            str: MD5 해시 기반 키
        """
        # 인자를 문자열로 변환
        key_data = json.dumps(
            {"args": args, "kwargs": kwargs},
            sort_keys=True,
            default=str
        )
        # MD5 해시 생성
        return hashlib.md5(key_data.encode()).hexdigest()

    def serialize(self, value: Any) -> str:
        """JSON 직렬화"""
        return json.dumps(value, default=str, ensure_ascii=False)

    def deserialize(self, data: str) -> Any:
        """JSON 역직렬화"""
        return json.loads(data)


class EmbeddingCacheStrategy(CacheStrategy):
    """
    임베딩 전용 캐싱 전략

    벡터 임베딩을 효율적으로 저장합니다.
    """

    def generate_key(self, text: str, model: str = "default") -> str:
        """
        텍스트와 모델명으로 키 생성

        Args:
            text: 임베딩 대상 텍스트
            model: 임베딩 모델명

        Returns:
            str: 캐시 키
        """
        content = f"{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()

    def serialize(self, value: List[float]) -> str:
        """임베딩 벡터 직렬화"""
        return json.dumps(value)

    def deserialize(self, data: str) -> List[float]:
        """임베딩 벡터 역직렬화"""
        return json.loads(data)


class CacheManager:
    """
    캐시 매니저 싱글톤 클래스

    Redis 연결을 관리하고 캐싱 작업을 수행합니다.

    디자인 패턴:
        - Singleton Pattern: 전역적으로 하나의 인스턴스만 사용
        - Strategy Pattern: 다양한 캐싱 전략 지원

    Attributes:
        _instance: 싱글톤 인스턴스
        _config: 캐시 설정
        _redis: Redis 클라이언트
        _strategies: 등록된 캐싱 전략

    Example:
        >>> config = CacheConfig(host='localhost', port=6379)
        >>> cache = CacheManager(config)
        >>>
        >>> # 값 저장
        >>> await cache.set('key', {'data': 'value'}, ttl=300)
        >>>
        >>> # 값 조회
        >>> value = await cache.get('key')
        >>>
        >>> # 임베딩 캐싱
        >>> embedding = await cache.get_embedding('text')
        >>> if not embedding:
        ...     embedding = generate_embedding('text')
        ...     await cache.set_embedding('text', embedding)
    """

    # 싱글톤 인스턴스
    _instance: Optional['CacheManager'] = None

    def __new__(cls, config: Optional[CacheConfig] = None):
        """
        싱글톤 인스턴스 생성

        Args:
            config: 캐시 설정 (첫 생성 시만 사용)

        Returns:
            CacheManager: 싱글톤 인스턴스
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        캐시 매니저 초기화

        Args:
            config: 캐시 설정
        """
        # 이미 초기화된 경우 스킵
        if self._initialized:
            return

        # 설정
        self._config = config or CacheConfig()
        self._redis = None
        self._logger = logging.getLogger(__name__)

        # 캐싱 전략 등록
        self._strategies: Dict[str, CacheStrategy] = {
            "json": JSONCacheStrategy(),
            "embedding": EmbeddingCacheStrategy()
        }

        self._initialized = True

    # =========================================================================
    # 연결 관리
    # =========================================================================

    async def connect(self) -> bool:
        """
        Redis 연결

        Returns:
            bool: 연결 성공 여부
        """
        try:
            import redis.asyncio as redis

            self._redis = redis.Redis(
                host=self._config.host,
                port=self._config.port,
                db=self._config.db,
                password=self._config.password,
                max_connections=self._config.max_connections,
                decode_responses=True
            )

            # 연결 테스트
            await self._redis.ping()
            self._logger.info(
                f"Redis 연결 성공: {self._config.host}:{self._config.port}"
            )
            return True

        except ImportError:
            self._logger.error("redis 라이브러리가 설치되지 않았습니다.")
            return False
        except Exception as e:
            self._logger.error(f"Redis 연결 실패: {e}")
            return False

    async def disconnect(self) -> None:
        """Redis 연결 종료"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._logger.info("Redis 연결 종료")

    @property
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._redis is not None

    # =========================================================================
    # 기본 캐시 작업
    # =========================================================================

    def _build_key(self, key: str, namespace: str = "default") -> str:
        """
        전체 캐시 키 생성 (private)

        Args:
            key: 기본 키
            namespace: 네임스페이스

        Returns:
            str: 접두사가 포함된 전체 키
        """
        return f"{self._config.prefix}:{namespace}:{key}"

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "default",
        strategy: str = "json"
    ) -> bool:
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: TTL (초), None이면 기본값 사용
            namespace: 네임스페이스
            strategy: 캐싱 전략 이름

        Returns:
            bool: 저장 성공 여부
        """
        if not self._redis:
            self._logger.warning("Redis가 연결되지 않았습니다.")
            return False

        try:
            full_key = self._build_key(key, namespace)
            cache_strategy = self._strategies.get(strategy, self._strategies["json"])

            # 직렬화
            serialized = cache_strategy.serialize(value)

            # TTL 설정
            expire_time = ttl or self._config.default_ttl

            # 저장
            await self._redis.setex(full_key, expire_time, serialized)

            self._logger.debug(f"캐시 저장: {full_key} (TTL: {expire_time}s)")
            return True

        except Exception as e:
            self._logger.error(f"캐시 저장 실패: {e}")
            return False

    async def get(
        self,
        key: str,
        namespace: str = "default",
        strategy: str = "json"
    ) -> Optional[Any]:
        """
        캐시에서 값 조회

        Args:
            key: 캐시 키
            namespace: 네임스페이스
            strategy: 캐싱 전략 이름

        Returns:
            Optional[Any]: 캐시된 값, 없으면 None
        """
        if not self._redis:
            return None

        try:
            full_key = self._build_key(key, namespace)
            cache_strategy = self._strategies.get(strategy, self._strategies["json"])

            # 조회
            data = await self._redis.get(full_key)

            if data:
                self._logger.debug(f"캐시 히트: {full_key}")
                return cache_strategy.deserialize(data)

            self._logger.debug(f"캐시 미스: {full_key}")
            return None

        except Exception as e:
            self._logger.error(f"캐시 조회 실패: {e}")
            return None

    async def delete(self, key: str, namespace: str = "default") -> bool:
        """
        캐시에서 값 삭제

        Args:
            key: 삭제할 키
            namespace: 네임스페이스

        Returns:
            bool: 삭제 성공 여부
        """
        if not self._redis:
            return False

        try:
            full_key = self._build_key(key, namespace)
            result = await self._redis.delete(full_key)
            self._logger.debug(f"캐시 삭제: {full_key}")
            return result > 0

        except Exception as e:
            self._logger.error(f"캐시 삭제 실패: {e}")
            return False

    async def exists(self, key: str, namespace: str = "default") -> bool:
        """키 존재 여부 확인"""
        if not self._redis:
            return False

        full_key = self._build_key(key, namespace)
        return await self._redis.exists(full_key) > 0

    async def clear_namespace(self, namespace: str) -> int:
        """
        네임스페이스의 모든 키 삭제

        Args:
            namespace: 삭제할 네임스페이스

        Returns:
            int: 삭제된 키 수
        """
        if not self._redis:
            return 0

        pattern = f"{self._config.prefix}:{namespace}:*"
        keys = []

        async for key in self._redis.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            deleted = await self._redis.delete(*keys)
            self._logger.info(f"네임스페이스 '{namespace}' 정리: {deleted}개 삭제")
            return deleted

        return 0

    # =========================================================================
    # 특수 캐싱 메서드
    # =========================================================================

    async def set_embedding(
        self,
        text: str,
        embedding: List[float],
        model: str = "default",
        ttl: Optional[int] = None
    ) -> bool:
        """
        임베딩 캐싱

        Args:
            text: 원본 텍스트
            embedding: 임베딩 벡터
            model: 모델명
            ttl: TTL

        Returns:
            bool: 저장 성공 여부
        """
        strategy = self._strategies["embedding"]
        key = strategy.generate_key(text, model)

        # 임베딩은 더 긴 TTL (기본 24시간)
        ttl = ttl or 86400

        return await self.set(
            key, embedding,
            ttl=ttl,
            namespace="embeddings",
            strategy="embedding"
        )

    async def get_embedding(
        self,
        text: str,
        model: str = "default"
    ) -> Optional[List[float]]:
        """
        임베딩 조회

        Args:
            text: 원본 텍스트
            model: 모델명

        Returns:
            Optional[List[float]]: 캐시된 임베딩
        """
        strategy = self._strategies["embedding"]
        key = strategy.generate_key(text, model)

        return await self.get(
            key,
            namespace="embeddings",
            strategy="embedding"
        )

    async def cache_response(
        self,
        user_input: str,
        response: str,
        ttl: int = 1800  # 30분
    ) -> bool:
        """
        API 응답 캐싱

        Args:
            user_input: 사용자 입력
            response: 생성된 응답
            ttl: TTL

        Returns:
            bool: 저장 성공 여부
        """
        strategy = self._strategies["json"]
        key = strategy.generate_key(user_input)

        return await self.set(
            key,
            {"input": user_input, "response": response},
            ttl=ttl,
            namespace="responses"
        )

    async def get_cached_response(self, user_input: str) -> Optional[str]:
        """
        캐시된 응답 조회

        Args:
            user_input: 사용자 입력

        Returns:
            Optional[str]: 캐시된 응답
        """
        strategy = self._strategies["json"]
        key = strategy.generate_key(user_input)

        data = await self.get(key, namespace="responses")

        if data:
            return data.get("response")
        return None

    # =========================================================================
    # 통계 및 관리
    # =========================================================================

    async def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회

        Returns:
            Dict: 통계 정보
        """
        if not self._redis:
            return {}

        info = await self._redis.info()

        return {
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory_human", "N/A"),
            "total_keys": await self._redis.dbsize(),
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0)
        }

    # =========================================================================
    # 컨텍스트 매니저
    # =========================================================================

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.disconnect()
        return False
