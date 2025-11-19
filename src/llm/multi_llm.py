#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
Multi-LLM 오케스트레이터 (Multi-LLM Orchestrator)
=============================================================================

OpenAI, Groq, Gemini 3개의 LLM을 병렬로 호출하고
가장 우수한 응답을 선택하는 핵심 시스템입니다.

주요 기능:
    - 3개 LLM 동시 병렬 호출
    - 응답 품질 자동 평가
    - 최적 응답 선택 (best_quality, fastest, consensus)
    - 폴백 처리 (일부 실패 시 다른 응답 사용)
    - 상세 메트릭스 수집

설계 패턴:
    - Strategy Pattern: 응답 선택 전략
    - Factory Pattern: 제공자 생성
    - Facade Pattern: 복잡한 병렬 처리를 단순화

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .providers import (
    LLMProvider,
    ProviderConfig,
    LLMResponse,
    ProviderFactory
)
from .evaluator import (
    ResponseEvaluator,
    EvaluationResult
)


# =============================================================================
# 설정 및 열거형
# =============================================================================

class SelectionStrategy(Enum):
    """
    응답 선택 전략

    Attributes:
        BEST_QUALITY: 가장 높은 품질의 응답 선택
        FASTEST: 가장 빠른 응답 선택
        CONSENSUS: 여러 LLM이 동의하는 응답 선택
    """
    BEST_QUALITY = "best_quality"
    FASTEST = "fastest"
    CONSENSUS = "consensus"


@dataclass
class LLMConfig:
    """
    Multi-LLM 시스템 설정

    Attributes:
        openai_api_key: OpenAI API 키
        openai_model: OpenAI 모델명
        groq_api_key: Groq API 키
        groq_model: Groq 모델명
        gemini_api_key: Gemini API 키
        gemini_model: Gemini 모델명
        enabled_providers: 활성화된 제공자 목록
        strategy: 응답 선택 전략
        timeout: 전체 타임아웃 (초)
        temperature: 생성 온도
        max_tokens: 최대 토큰 수
    """
    # API 키
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    # 모델 설정
    openai_model: str = "gpt-4"
    groq_model: str = "llama-3.1-70b-versatile"
    gemini_model: str = "gemini-1.5-pro"

    # 시스템 설정
    enabled_providers: List[str] = field(
        default_factory=lambda: ["openai", "groq", "gemini"]
    )
    strategy: SelectionStrategy = SelectionStrategy.BEST_QUALITY
    timeout: int = 30
    temperature: float = 0.7
    max_tokens: int = 2000


@dataclass
class OrchestratorResult:
    """
    오케스트레이터 실행 결과

    Attributes:
        best_response: 선택된 최적 응답
        all_responses: 모든 LLM 응답
        evaluation_results: 평가 결과
        selected_provider: 선택된 제공자
        total_latency: 전체 소요 시간
        strategy_used: 사용된 전략
        metadata: 추가 메타데이터
    """
    best_response: str
    all_responses: List[LLMResponse]
    evaluation_results: List[EvaluationResult]
    selected_provider: str
    total_latency: float
    strategy_used: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Multi-LLM 오케스트레이터
# =============================================================================

class MultiLLMOrchestrator:
    """
    Multi-LLM 병렬 처리 오케스트레이터

    3개의 LLM(OpenAI, Groq, Gemini)을 병렬로 호출하고
    가장 우수한 응답을 자동으로 선택합니다.

    Example:
        >>> config = LLMConfig(
        ...     openai_api_key="sk-...",
        ...     groq_api_key="gsk-...",
        ...     gemini_api_key="...",
        ...     strategy=SelectionStrategy.BEST_QUALITY
        ... )
        >>> orchestrator = MultiLLMOrchestrator(config)
        >>>
        >>> result = await orchestrator.generate(
        ...     prompt="청년 주거 정책 추천해주세요",
        ...     context=retrieved_documents,
        ...     system_prompt="당신은 청년 정책 전문가입니다."
        ... )
        >>>
        >>> print(f"선택된 제공자: {result.selected_provider}")
        >>> print(f"응답: {result.best_response}")
    """

    def __init__(self, config: LLMConfig):
        """
        오케스트레이터 초기화

        Args:
            config: Multi-LLM 설정
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.evaluator = ResponseEvaluator()

        # 제공자 초기화
        self.providers: Dict[str, LLMProvider] = {}
        self._initialize_providers()

        self.logger.info(
            f"MultiLLMOrchestrator 초기화 완료: "
            f"{len(self.providers)}개 제공자 활성화"
        )

    def _initialize_providers(self):
        """
        활성화된 제공자들을 초기화합니다.
        """
        provider_configs = {
            "openai": ProviderConfig(
                api_key=self.config.openai_api_key or "",
                model=self.config.openai_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout
            ),
            "groq": ProviderConfig(
                api_key=self.config.groq_api_key or "",
                model=self.config.groq_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout
            ),
            "gemini": ProviderConfig(
                api_key=self.config.gemini_api_key or "",
                model=self.config.gemini_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout
            )
        }

        for provider_name in self.config.enabled_providers:
            provider_name = provider_name.lower()

            if provider_name not in provider_configs:
                self.logger.warning(f"알 수 없는 제공자: {provider_name}")
                continue

            config = provider_configs[provider_name]

            # API 키가 없으면 건너뜀
            if not config.api_key:
                self.logger.warning(
                    f"{provider_name} API 키가 설정되지 않아 비활성화됨"
                )
                continue

            try:
                provider = ProviderFactory.create(provider_name, config)
                self.providers[provider_name] = provider
                self.logger.info(f"{provider_name} 제공자 초기화 완료")
            except Exception as e:
                self.logger.error(
                    f"{provider_name} 제공자 초기화 실패: {str(e)}"
                )

    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> OrchestratorResult:
        """
        병렬로 모든 LLM을 호출하고 최적의 응답을 선택합니다.

        Args:
            prompt: 사용자 프롬프트
            context: RAG 검색 결과 컨텍스트
            system_prompt: 시스템 프롬프트

        Returns:
            OrchestratorResult: 실행 결과
        """
        start_time = asyncio.get_event_loop().time()

        if not self.providers:
            raise RuntimeError("활성화된 LLM 제공자가 없습니다")

        self.logger.info(
            f"병렬 생성 시작: {len(self.providers)}개 제공자"
        )

        # 1. 모든 제공자에 병렬 요청
        tasks = [
            self._call_provider(name, provider, prompt, context, system_prompt)
            for name, provider in self.providers.items()
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 예외를 LLMResponse로 변환
        processed_responses = []
        for i, response in enumerate(responses):
            provider_name = list(self.providers.keys())[i]

            if isinstance(response, Exception):
                self.logger.error(
                    f"{provider_name} 예외 발생: {str(response)}"
                )
                processed_responses.append(LLMResponse(
                    provider=provider_name,
                    content="",
                    model="",
                    latency=0,
                    success=False,
                    error=str(response)
                ))
            else:
                processed_responses.append(response)

        # 2. 응답 평가
        evaluation_results = self.evaluator.evaluate_all(
            processed_responses, prompt, context
        )

        # 3. 전략에 따라 최적 응답 선택
        selected = self._select_response(
            processed_responses,
            evaluation_results
        )

        total_latency = asyncio.get_event_loop().time() - start_time

        # 결과 구성
        result = OrchestratorResult(
            best_response=selected.content if selected else "응답을 생성할 수 없습니다.",
            all_responses=processed_responses,
            evaluation_results=evaluation_results,
            selected_provider=selected.provider if selected else "none",
            total_latency=total_latency,
            strategy_used=self.config.strategy.value,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "providers_called": list(self.providers.keys()),
                "successful_responses": sum(
                    1 for r in processed_responses if r.success
                ),
                "evaluation_scores": {
                    r.provider: r.total_score for r in evaluation_results
                }
            }
        )

        self.logger.info(
            f"병렬 생성 완료: {result.selected_provider} 선택, "
            f"{total_latency:.2f}s"
        )

        return result

    async def _call_provider(
        self,
        name: str,
        provider: LLMProvider,
        prompt: str,
        context: Optional[str],
        system_prompt: Optional[str]
    ) -> LLMResponse:
        """
        단일 제공자 호출

        Args:
            name: 제공자 이름
            provider: 제공자 인스턴스
            prompt: 프롬프트
            context: 컨텍스트
            system_prompt: 시스템 프롬프트

        Returns:
            LLMResponse: 응답
        """
        try:
            self.logger.debug(f"{name} 호출 시작")
            response = await provider.generate(prompt, context, system_prompt)
            self.logger.debug(
                f"{name} 호출 완료: {response.latency:.2f}s"
            )
            return response

        except Exception as e:
            self.logger.error(f"{name} 호출 실패: {str(e)}")
            return LLMResponse(
                provider=name,
                content="",
                model=provider.config.model,
                latency=0,
                success=False,
                error=str(e)
            )

    def _select_response(
        self,
        responses: List[LLMResponse],
        evaluations: List[EvaluationResult]
    ) -> Optional[LLMResponse]:
        """
        전략에 따라 최적의 응답을 선택합니다.

        Args:
            responses: 모든 응답
            evaluations: 평가 결과

        Returns:
            Optional[LLMResponse]: 선택된 응답
        """
        # 성공한 응답만 필터링
        successful = [r for r in responses if r.success]

        if not successful:
            self.logger.warning("성공한 응답이 없습니다")
            return None

        # 전략별 선택
        if self.config.strategy == SelectionStrategy.FASTEST:
            # 가장 빠른 응답 선택
            selected = min(successful, key=lambda r: r.latency)
            self.logger.info(
                f"가장 빠른 응답 선택: {selected.provider} "
                f"({selected.latency:.2f}s)"
            )
            return selected

        elif self.config.strategy == SelectionStrategy.CONSENSUS:
            # 일정 점수 이상의 응답들 중 선택
            consensus = self.evaluator.get_consensus(evaluations, threshold=60)

            if consensus:
                # 합의된 응답 중 가장 높은 점수
                best_eval = consensus[0]
                selected = next(
                    r for r in successful
                    if r.provider == best_eval.provider
                )
                self.logger.info(
                    f"합의 응답 선택: {selected.provider} "
                    f"(점수: {best_eval.total_score})"
                )
                return selected

            # 합의 실패 시 최고 품질로 폴백
            self.logger.warning("합의 실패, 최고 품질로 폴백")

        # BEST_QUALITY (기본값)
        if evaluations:
            best_eval = evaluations[0]
            selected = next(
                (r for r in successful if r.provider == best_eval.provider),
                successful[0]
            )
            self.logger.info(
                f"최고 품질 응답 선택: {selected.provider} "
                f"(점수: {best_eval.total_score})"
            )
            return selected

        # 평가 없이 첫 번째 성공 응답 반환
        return successful[0]

    async def close(self):
        """
        모든 리소스 정리
        """
        for provider in self.providers.values():
            await provider.close()
        self.logger.info("모든 제공자 연결 종료")

    def get_provider_status(self) -> Dict[str, bool]:
        """
        제공자 상태 확인

        Returns:
            Dict[str, bool]: 제공자별 활성화 상태
        """
        return {
            name: True for name in self.providers.keys()
        }


# =============================================================================
# 편의 함수
# =============================================================================

async def quick_generate(
    prompt: str,
    openai_key: str,
    groq_key: str,
    gemini_key: str,
    context: Optional[str] = None
) -> str:
    """
    빠른 병렬 생성 (편의 함수)

    Args:
        prompt: 프롬프트
        openai_key: OpenAI API 키
        groq_key: Groq API 키
        gemini_key: Gemini API 키
        context: 컨텍스트

    Returns:
        str: 최적 응답

    Example:
        >>> response = await quick_generate(
        ...     "청년 정책 추천",
        ...     "sk-...", "gsk-...", "..."
        ... )
    """
    config = LLMConfig(
        openai_api_key=openai_key,
        groq_api_key=groq_key,
        gemini_api_key=gemini_key
    )

    orchestrator = MultiLLMOrchestrator(config)

    try:
        result = await orchestrator.generate(prompt, context)
        return result.best_response
    finally:
        await orchestrator.close()
