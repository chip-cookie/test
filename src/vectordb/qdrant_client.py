#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
Qdrant Vector Database 클라이언트
=============================================================================

Qdrant를 사용한 벡터 검색 및 데이터 관리 클라이언트입니다.

주요 기능:
    - 벡터 임베딩 저장/검색
    - 메타데이터 필터링
    - 유사도 검색 (RAG용)

Qdrant 선택 이유:
    - 무료 셀프호스팅
    - 강력한 메타데이터 필터링
    - Docker로 쉬운 배포
    - 높은 검색 정확도

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import logging
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import hashlib
import json


# =============================================================================
# 설정
# =============================================================================

@dataclass
class VectorDBConfig:
    """
    Vector DB 설정

    Attributes:
        url: Qdrant 서버 URL
        collection_name: 컬렉션 이름
        vector_size: 임베딩 벡터 차원 (OpenAI ada-002는 1536)
        distance: 유사도 측정 방식
        api_key: Qdrant Cloud API 키 (선택)
    """
    url: str = "http://localhost:6333"
    collection_name: str = "youth-policy-kb"
    vector_size: int = 1536
    distance: str = "Cosine"
    api_key: Optional[str] = None
    timeout: int = 30


# =============================================================================
# Qdrant 클라이언트
# =============================================================================

class QdrantVectorDB:
    """
    Qdrant Vector Database 클라이언트

    청년 정책 데이터를 벡터로 저장하고 검색합니다.

    Example:
        >>> db = QdrantVectorDB(url="http://localhost:6333")
        >>> await db.connect()
        >>>
        >>> # 데이터 저장
        >>> await db.upsert({
        ...     "id": "policy-001",
        ...     "content": "청년 대출 정책...",
        ...     "metadata": {"category": "대출"}
        ... })
        >>>
        >>> # 검색
        >>> results = await db.search(
        ...     query="청년 주거 지원",
        ...     filter={"target_age_max": {"$gte": 30}},
        ...     limit=5
        ... )
    """

    def __init__(self, config: VectorDBConfig = None, **kwargs):
        """
        클라이언트 초기화

        Args:
            config: VectorDBConfig 객체
            **kwargs: 개별 설정값
        """
        if config:
            self.config = config
        else:
            self.config = VectorDBConfig(
                url=kwargs.get("url", "http://localhost:6333"),
                collection_name=kwargs.get("collection_name", "youth-policy-kb"),
                vector_size=kwargs.get("vector_size", 1536),
                api_key=kwargs.get("api_key")
            )

        self._session: Optional[aiohttp.ClientSession] = None
        self._logger = logging.getLogger(__name__)
        self._embedding_client = None

    # =========================================================================
    # 연결 관리
    # =========================================================================

    async def connect(self) -> bool:
        """
        Qdrant 서버 연결

        Returns:
            bool: 연결 성공 여부
        """
        try:
            headers = {"Content-Type": "application/json"}

            if self.config.api_key:
                headers["api-key"] = self.config.api_key

            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout
            )

            # 컬렉션 존재 확인 및 생성
            await self._ensure_collection()

            self._logger.info(f"Qdrant 연결 성공: {self.config.url}")
            return True

        except Exception as e:
            self._logger.error(f"Qdrant 연결 실패: {e}")
            return False

    async def close(self):
        """연결 종료"""
        if self._session:
            await self._session.close()
            self._session = None

    async def _ensure_collection(self):
        """컬렉션 존재 확인 및 생성"""
        url = f"{self.config.url}/collections/{self.config.collection_name}"

        async with self._session.get(url) as resp:
            if resp.status == 404:
                # 컬렉션 생성
                await self._create_collection()
            elif resp.status != 200:
                error = await resp.text()
                raise Exception(f"컬렉션 확인 실패: {error}")

    async def _create_collection(self):
        """컬렉션 생성"""
        url = f"{self.config.url}/collections/{self.config.collection_name}"

        payload = {
            "vectors": {
                "size": self.config.vector_size,
                "distance": self.config.distance
            },
            "optimizers_config": {
                "default_segment_number": 2
            },
            "replication_factor": 1
        }

        async with self._session.put(url, json=payload) as resp:
            if resp.status not in [200, 201]:
                error = await resp.text()
                raise Exception(f"컬렉션 생성 실패: {error}")

            self._logger.info(f"컬렉션 생성: {self.config.collection_name}")

    # =========================================================================
    # 데이터 조작
    # =========================================================================

    async def upsert(
        self,
        document: Dict[str, Any],
        embedding: List[float] = None
    ) -> bool:
        """
        문서 추가/업데이트

        Args:
            document: 문서 데이터 (id, content, metadata)
            embedding: 임베딩 벡터 (없으면 자동 생성)

        Returns:
            bool: 성공 여부
        """
        try:
            doc_id = document["id"]
            content = document["content"]
            metadata = document.get("metadata", {})

            # 임베딩 생성 (없으면)
            if embedding is None:
                embedding = await self._get_embedding(content)

            # 포인트 ID 생성 (해시)
            point_id = self._generate_point_id(doc_id)

            # Qdrant 포인트 구성
            point = {
                "id": point_id,
                "vector": embedding,
                "payload": {
                    "doc_id": doc_id,
                    "content": content,
                    **metadata
                }
            }

            # Upsert 요청
            url = f"{self.config.url}/collections/{self.config.collection_name}/points"

            async with self._session.put(url, json={"points": [point]}) as resp:
                if resp.status not in [200, 201]:
                    error = await resp.text()
                    self._logger.error(f"Upsert 실패: {error}")
                    return False

            self._logger.debug(f"Upsert 성공: {doc_id}")
            return True

        except Exception as e:
            self._logger.error(f"Upsert 오류: {e}")
            return False

    async def upsert_batch(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """
        배치 문서 추가

        Args:
            documents: 문서 목록
            batch_size: 배치 크기

        Returns:
            int: 성공 건수
        """
        success_count = 0

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            points = []

            for doc in batch:
                try:
                    embedding = await self._get_embedding(doc["content"])
                    point_id = self._generate_point_id(doc["id"])

                    points.append({
                        "id": point_id,
                        "vector": embedding,
                        "payload": {
                            "doc_id": doc["id"],
                            "content": doc["content"],
                            **doc.get("metadata", {})
                        }
                    })
                except Exception as e:
                    self._logger.error(f"임베딩 실패 ({doc['id']}): {e}")

            if points:
                url = f"{self.config.url}/collections/{self.config.collection_name}/points"

                async with self._session.put(url, json={"points": points}) as resp:
                    if resp.status in [200, 201]:
                        success_count += len(points)

            self._logger.info(f"배치 처리: {i + len(batch)}/{len(documents)}")

        return success_count

    async def delete(self, doc_id: str) -> bool:
        """
        문서 삭제

        Args:
            doc_id: 문서 ID

        Returns:
            bool: 성공 여부
        """
        url = f"{self.config.url}/collections/{self.config.collection_name}/points/delete"

        payload = {
            "filter": {
                "must": [
                    {"key": "doc_id", "match": {"value": doc_id}}
                ]
            }
        }

        async with self._session.post(url, json=payload) as resp:
            return resp.status == 200

    # =========================================================================
    # 검색
    # =========================================================================

    async def search(
        self,
        query: str,
        filter: Dict[str, Any] = None,
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        유사도 검색

        Args:
            query: 검색 쿼리
            filter: 메타데이터 필터
            limit: 반환 결과 수
            score_threshold: 최소 유사도 점수

        Returns:
            List[Dict]: 검색 결과

        Example:
            >>> results = await db.search(
            ...     query="청년 주거 지원",
            ...     filter={
            ...         "target_age_max": {"$gte": 30},
            ...         "category": "주거"
            ...     },
            ...     limit=10
            ... )
        """
        try:
            # 쿼리 임베딩
            query_vector = await self._get_embedding(query)

            # 검색 요청 구성
            payload = {
                "vector": query_vector,
                "limit": limit,
                "with_payload": True,
                "score_threshold": score_threshold
            }

            # 필터 변환
            if filter:
                payload["filter"] = self._build_filter(filter)

            url = f"{self.config.url}/collections/{self.config.collection_name}/points/search"

            async with self._session.post(url, json=payload) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    self._logger.error(f"검색 실패: {error}")
                    return []

                data = await resp.json()
                results = data.get("result", [])

                # 결과 포맷팅
                formatted = []
                for r in results:
                    formatted.append({
                        "id": r["payload"].get("doc_id"),
                        "content": r["payload"].get("content"),
                        "score": r["score"],
                        "metadata": {
                            k: v for k, v in r["payload"].items()
                            if k not in ["doc_id", "content"]
                        }
                    })

                self._logger.debug(f"검색 결과: {len(formatted)}개")
                return formatted

        except Exception as e:
            self._logger.error(f"검색 오류: {e}")
            return []

    async def search_with_filter(
        self,
        query: str,
        age: int = None,
        income: int = None,
        location: str = None,
        category: str = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        조건부 검색 (편의 메서드)

        Args:
            query: 검색 쿼리
            age: 나이
            income: 소득
            location: 지역
            category: 카테고리
            limit: 결과 수

        Returns:
            List[Dict]: 검색 결과
        """
        filter_conditions = {}

        if age:
            filter_conditions["target_age_min"] = {"$lte": age}
            filter_conditions["target_age_max"] = {"$gte": age}

        if income:
            filter_conditions["income_limit"] = {"$gte": income}

        if location:
            filter_conditions["location"] = {"$in": [location, "전국"]}

        if category:
            filter_conditions["category"] = category

        return await self.search(
            query=query,
            filter=filter_conditions if filter_conditions else None,
            limit=limit
        )

    # =========================================================================
    # 헬퍼 메서드
    # =========================================================================

    def _build_filter(self, filter_dict: Dict[str, Any]) -> Dict:
        """
        필터 딕셔너리를 Qdrant 필터 형식으로 변환

        Args:
            filter_dict: 필터 조건

        Returns:
            Dict: Qdrant 필터
        """
        must = []

        for key, value in filter_dict.items():
            if isinstance(value, dict):
                # 연산자 처리
                for op, val in value.items():
                    if op == "$gte":
                        must.append({
                            "key": key,
                            "range": {"gte": val}
                        })
                    elif op == "$lte":
                        must.append({
                            "key": key,
                            "range": {"lte": val}
                        })
                    elif op == "$in":
                        must.append({
                            "key": key,
                            "match": {"any": val}
                        })
            else:
                # 정확한 매치
                must.append({
                    "key": key,
                    "match": {"value": value}
                })

        return {"must": must} if must else {}

    def _generate_point_id(self, doc_id: str) -> int:
        """
        문서 ID를 Qdrant 포인트 ID로 변환

        Args:
            doc_id: 문서 ID

        Returns:
            int: 포인트 ID
        """
        # MD5 해시의 일부를 정수로 변환
        hash_hex = hashlib.md5(doc_id.encode()).hexdigest()[:16]
        return int(hash_hex, 16) % (2**63)

    async def _get_embedding(self, text: str) -> List[float]:
        """
        텍스트 임베딩 생성

        실제 구현에서는 OpenAI API를 호출합니다.

        Args:
            text: 임베딩할 텍스트

        Returns:
            List[float]: 임베딩 벡터
        """
        # TODO: OpenAI Embedding API 연동
        # 현재는 더미 벡터 반환 (테스트용)

        import os

        openai_key = os.getenv("OPENAI_API_KEY")

        if openai_key and self._session:
            try:
                url = "https://api.openai.com/v1/embeddings"
                headers = {
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": "text-embedding-ada-002",
                    "input": text[:8000]  # 최대 토큰 제한
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data["data"][0]["embedding"]

            except Exception as e:
                self._logger.warning(f"OpenAI 임베딩 실패, 더미 사용: {e}")

        # 더미 임베딩 (테스트용)
        import random
        return [random.uniform(-1, 1) for _ in range(self.config.vector_size)]

    # =========================================================================
    # 유틸리티
    # =========================================================================

    async def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 정보 조회"""
        url = f"{self.config.url}/collections/{self.config.collection_name}"

        async with self._session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            return {}

    async def count_documents(self) -> int:
        """문서 수 조회"""
        info = await self.get_collection_info()
        return info.get("result", {}).get("points_count", 0)

    async def health_check(self) -> bool:
        """헬스 체크"""
        try:
            url = f"{self.config.url}/health"
            async with self._session.get(url) as resp:
                return resp.status == 200
        except:
            return False
