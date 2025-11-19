#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
Multi-LLM 병렬 처리 시스템
=============================================================================

OpenAI, Groq, Gemini 3개의 LLM을 병렬로 실행하고
가장 우수한 응답을 선택하는 시스템입니다.

모듈 구성:
    - providers: 각 LLM 제공자 클래스 (OpenAI, Groq, Gemini)
    - multi_llm: 병렬 처리 오케스트레이터
    - evaluator: 응답 품질 평가기

Example:
    >>> from src.llm import MultiLLMOrchestrator, LLMConfig
    >>>
    >>> config = LLMConfig(
    ...     openai_api_key="sk-...",
    ...     groq_api_key="gsk-...",
    ...     gemini_api_key="..."
    ... )
    >>> orchestrator = MultiLLMOrchestrator(config)
    >>>
    >>> result = await orchestrator.generate(
    ...     prompt="청년 주거 정책에 대해 설명해주세요",
    ...     context=retrieved_documents
    ... )
    >>> print(result.best_response)

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

from .providers import (
    LLMProvider,
    OpenAIProvider,
    GroqProvider,
    GeminiProvider,
    LLMResponse,
    ProviderConfig
)

from .multi_llm import (
    MultiLLMOrchestrator,
    LLMConfig,
    SelectionStrategy,
    OrchestratorResult
)

from .evaluator import (
    ResponseEvaluator,
    EvaluationCriteria,
    EvaluationResult
)

__all__ = [
    # Providers
    'LLMProvider',
    'OpenAIProvider',
    'GroqProvider',
    'GeminiProvider',
    'LLMResponse',
    'ProviderConfig',

    # Orchestrator
    'MultiLLMOrchestrator',
    'LLMConfig',
    'SelectionStrategy',
    'OrchestratorResult',

    # Evaluator
    'ResponseEvaluator',
    'EvaluationCriteria',
    'EvaluationResult',
]
