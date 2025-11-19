#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
데이터 파이프라인 (Data Pipeline)
=============================================================================

크롤링된 데이터를 처리하고 Vector DB에 저장하는 파이프라인입니다.
Chain of Responsibility 패턴을 사용하여 처리 단계를 모듈화합니다.

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import asyncio

from .base_crawler import CrawlResult, PolicyData, SourceTier


@dataclass
class PipelineContext:
    """
    파이프라인 처리 컨텍스트

    파이프라인 단계 간 데이터를 전달하는 컨테이너입니다.

    Attributes:
        crawl_result (CrawlResult): 원본 크롤링 결과
        processed_policies (List): 처리된 정책 데이터
        embeddings (Dict): 생성된 임베딩
        errors (List): 처리 중 발생한 오류
        metadata (Dict): 추가 메타데이터
    """
    crawl_result: CrawlResult
    processed_policies: List[Dict[str, Any]] = None
    embeddings: Dict[str, List[float]] = None
    errors: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """초기화 후 기본값 설정"""
        if self.processed_policies is None:
            self.processed_policies = []
        if self.embeddings is None:
            self.embeddings = {}
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}


class PipelineStep(ABC):
    """
    파이프라인 단계 추상 클래스

    Chain of Responsibility 패턴의 핸들러 역할을 합니다.
    각 단계는 데이터를 처리하고 다음 단계로 전달합니다.
    """

    def __init__(self):
        """단계 초기화"""
        self._next_step: Optional['PipelineStep'] = None
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )

    def set_next(self, step: 'PipelineStep') -> 'PipelineStep':
        """
        다음 단계 설정 (체이닝 지원)

        Args:
            step: 다음 단계

        Returns:
            PipelineStep: 설정된 다음 단계 (체이닝용)
        """
        self._next_step = step
        return step

    async def handle(self, context: PipelineContext) -> PipelineContext:
        """
        단계 실행 및 다음 단계 전달

        Args:
            context: 파이프라인 컨텍스트

        Returns:
            PipelineContext: 처리된 컨텍스트
        """
        try:
            # 현재 단계 처리
            context = await self.process(context)
            self._logger.debug(f"{self.__class__.__name__} 완료")

            # 다음 단계로 전달
            if self._next_step:
                return await self._next_step.handle(context)

        except Exception as e:
            error_msg = f"{self.__class__.__name__} 오류: {str(e)}"
            context.errors.append(error_msg)
            self._logger.error(error_msg)

        return context

    @abstractmethod
    async def process(self, context: PipelineContext) -> PipelineContext:
        """
        단계 처리 로직 (하위 클래스에서 구현)

        Args:
            context: 입력 컨텍스트

        Returns:
            PipelineContext: 처리된 컨텍스트
        """
        pass


class DataCleaningStep(PipelineStep):
    """
    데이터 정제 단계

    크롤링된 원시 데이터를 정제하고 정규화합니다.
    """

    async def process(self, context: PipelineContext) -> PipelineContext:
        """
        데이터 정제 처리

        - 빈 문자열 제거
        - 텍스트 정규화 (공백, 특수문자)
        - 중복 데이터 제거
        """
        cleaned_policies = []

        for policy in context.crawl_result.policies:
            # 빈 데이터 스킵
            if not policy.content.strip():
                continue

            # 텍스트 정규화
            cleaned_content = self._normalize_text(policy.content)

            # Vector DB 포맷으로 변환
            db_format = policy.to_vector_db_format(
                context.crawl_result.source_name,
                policy.official_link
            )

            # 정제된 콘텐츠로 업데이트
            db_format["content"] = cleaned_content

            cleaned_policies.append(db_format)

        context.processed_policies = cleaned_policies
        context.metadata["cleaning_stats"] = {
            "original_count": len(context.crawl_result.policies),
            "cleaned_count": len(cleaned_policies)
        }

        return context

    def _normalize_text(self, text: str) -> str:
        """텍스트 정규화"""
        import re

        # 연속된 공백을 단일 공백으로
        text = re.sub(r'\s+', ' ', text)

        # 앞뒤 공백 제거
        text = text.strip()

        # HTML 엔티티 변환
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')

        return text


class EmbeddingGenerationStep(PipelineStep):
    """
    임베딩 생성 단계

    정제된 텍스트에 대한 벡터 임베딩을 생성합니다.
    """

    def __init__(self, openai_api_key: str, model: str = "text-embedding-ada-002"):
        """
        임베딩 생성 단계 초기화

        Args:
            openai_api_key: OpenAI API 키
            model: 임베딩 모델명
        """
        super().__init__()
        self._api_key = openai_api_key
        self._model = model

    async def process(self, context: PipelineContext) -> PipelineContext:
        """
        임베딩 생성 처리

        OpenAI API를 사용하여 텍스트 임베딩을 생성합니다.
        """
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._api_key)
            embeddings = {}

            for policy in context.processed_policies:
                policy_id = policy["id"]
                content = policy["content"]

                # 임베딩 생성
                response = client.embeddings.create(
                    input=content[:8000],  # 토큰 제한
                    model=self._model
                )

                embeddings[policy_id] = response.data[0].embedding

                # Rate limit 방지
                await asyncio.sleep(0.1)

            context.embeddings = embeddings
            context.metadata["embedding_stats"] = {
                "generated_count": len(embeddings),
                "model": self._model
            }

        except ImportError:
            self._logger.warning("OpenAI 라이브러리가 설치되지 않음. 임베딩 스킵.")
        except Exception as e:
            context.errors.append(f"임베딩 생성 실패: {str(e)}")

        return context


class VectorDBInsertionStep(PipelineStep):
    """
    Vector DB 삽입 단계

    처리된 데이터를 Vector Database에 저장합니다.
    """

    def __init__(self, pinecone_api_key: str, index_name: str):
        """
        Vector DB 삽입 단계 초기화

        Args:
            pinecone_api_key: Pinecone API 키
            index_name: 인덱스 이름
        """
        super().__init__()
        self._api_key = pinecone_api_key
        self._index_name = index_name

    async def process(self, context: PipelineContext) -> PipelineContext:
        """
        Vector DB 삽입 처리
        """
        try:
            from pinecone import Pinecone

            pc = Pinecone(api_key=self._api_key)
            index = pc.Index(self._index_name)

            vectors = []

            for policy in context.processed_policies:
                policy_id = policy["id"]

                if policy_id not in context.embeddings:
                    continue

                vectors.append({
                    "id": policy_id,
                    "values": context.embeddings[policy_id],
                    "metadata": policy["metadata"]
                })

            # 배치 업서트
            if vectors:
                index.upsert(vectors=vectors, batch_size=100)

            context.metadata["insertion_stats"] = {
                "inserted_count": len(vectors),
                "index_name": self._index_name
            }

        except ImportError:
            self._logger.warning("Pinecone 라이브러리가 설치되지 않음. 삽입 스킵.")
        except Exception as e:
            context.errors.append(f"Vector DB 삽입 실패: {str(e)}")

        return context


class DataPipeline:
    """
    데이터 파이프라인 매니저

    파이프라인 단계들을 조합하고 실행합니다.

    Example:
        >>> pipeline = DataPipeline()
        >>> pipeline.add_step(DataCleaningStep())
        >>> pipeline.add_step(EmbeddingGenerationStep(api_key))
        >>> pipeline.add_step(VectorDBInsertionStep(api_key, index))
        >>>
        >>> result = await pipeline.execute(crawl_result)
    """

    def __init__(self):
        """파이프라인 초기화"""
        self._steps: List[PipelineStep] = []
        self._logger = logging.getLogger(__name__)

    def add_step(self, step: PipelineStep) -> 'DataPipeline':
        """
        파이프라인에 단계 추가

        Args:
            step: 추가할 단계

        Returns:
            DataPipeline: 체이닝을 위한 self
        """
        if self._steps:
            # 마지막 단계에 연결
            self._steps[-1].set_next(step)

        self._steps.append(step)
        return self

    async def execute(self, crawl_result: CrawlResult) -> PipelineContext:
        """
        파이프라인 실행

        Args:
            crawl_result: 크롤링 결과

        Returns:
            PipelineContext: 처리 결과
        """
        if not self._steps:
            raise ValueError("파이프라인에 단계가 없습니다.")

        # 컨텍스트 생성
        context = PipelineContext(crawl_result=crawl_result)

        self._logger.info(
            f"파이프라인 실행 시작: {len(self._steps)}개 단계, "
            f"{len(crawl_result.policies)}개 정책"
        )

        # 첫 번째 단계부터 실행
        context = await self._steps[0].handle(context)

        self._logger.info(
            f"파이프라인 완료: {len(context.processed_policies)}개 처리됨, "
            f"{len(context.errors)}개 오류"
        )

        return context

    @classmethod
    def create_default(
        cls,
        openai_api_key: str,
        pinecone_api_key: str,
        index_name: str
    ) -> 'DataPipeline':
        """
        기본 파이프라인 생성

        Args:
            openai_api_key: OpenAI API 키
            pinecone_api_key: Pinecone API 키
            index_name: 인덱스 이름

        Returns:
            DataPipeline: 구성된 파이프라인
        """
        pipeline = cls()
        pipeline.add_step(DataCleaningStep())
        pipeline.add_step(EmbeddingGenerationStep(openai_api_key))
        pipeline.add_step(VectorDBInsertionStep(pinecone_api_key, index_name))

        return pipeline
