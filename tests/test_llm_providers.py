#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
LLM 제공자 테스트
=============================================================================

Multi-LLM 시스템의 제공자 클래스들을 테스트합니다.

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import sys
sys.path.insert(0, '/home/user/test')

from src.llm.providers import (
    OpenAIProvider,
    GroqProvider,
    GeminiProvider,
    ProviderConfig,
    ProviderFactory,
    LLMResponse
)
from src.llm.evaluator import ResponseEvaluator, EvaluationCriteria
from src.llm.multi_llm import MultiLLMOrchestrator, LLMConfig, SelectionStrategy


# =============================================================================
# 제공자 설정 픽스처
# =============================================================================

@pytest.fixture
def openai_config():
    return ProviderConfig(
        api_key="test-openai-key",
        model="gpt-4",
        temperature=0.7,
        max_tokens=1000,
        timeout=30
    )


@pytest.fixture
def groq_config():
    return ProviderConfig(
        api_key="test-groq-key",
        model="llama-3.1-70b-versatile",
        temperature=0.7,
        max_tokens=1000,
        timeout=30
    )


@pytest.fixture
def gemini_config():
    return ProviderConfig(
        api_key="test-gemini-key",
        model="gemini-1.5-pro",
        temperature=0.7,
        max_tokens=1000,
        timeout=30
    )


# =============================================================================
# 제공자 팩토리 테스트
# =============================================================================

class TestProviderFactory:
    """ProviderFactory 테스트"""

    def test_create_openai_provider(self, openai_config):
        """OpenAI 제공자 생성 테스트"""
        provider = ProviderFactory.create("openai", openai_config)
        assert isinstance(provider, OpenAIProvider)
        assert provider.provider_name == "openai"

    def test_create_groq_provider(self, groq_config):
        """Groq 제공자 생성 테스트"""
        provider = ProviderFactory.create("groq", groq_config)
        assert isinstance(provider, GroqProvider)
        assert provider.provider_name == "groq"

    def test_create_gemini_provider(self, gemini_config):
        """Gemini 제공자 생성 테스트"""
        provider = ProviderFactory.create("gemini", gemini_config)
        assert isinstance(provider, GeminiProvider)
        assert provider.provider_name == "gemini"

    def test_invalid_provider_raises_error(self, openai_config):
        """잘못된 제공자명 오류 테스트"""
        with pytest.raises(ValueError) as exc_info:
            ProviderFactory.create("invalid", openai_config)
        assert "알 수 없는 제공자" in str(exc_info.value)


# =============================================================================
# OpenAI 제공자 테스트
# =============================================================================

class TestOpenAIProvider:
    """OpenAIProvider 테스트"""

    @pytest.mark.asyncio
    async def test_generate_success(self, openai_config):
        """성공적인 응답 생성 테스트"""
        provider = OpenAIProvider(openai_config)

        # Mock HTTP 응답
        mock_response = {
            "choices": [{
                "message": {"content": "테스트 응답입니다."},
                "finish_reason": "stop"
            }],
            "usage": {
                "total_tokens": 100,
                "prompt_tokens": 50,
                "completion_tokens": 50
            }
        }

        with patch.object(provider, '_get_session') as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)

            mock_session.return_value.post = MagicMock(
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp))
            )

            response = await provider.generate("테스트 프롬프트")

            assert response.success is True
            assert response.content == "테스트 응답입니다."
            assert response.provider == "openai"
            assert response.tokens_used == 100

    @pytest.mark.asyncio
    async def test_generate_with_context(self, openai_config):
        """컨텍스트와 함께 응답 생성 테스트"""
        provider = OpenAIProvider(openai_config)

        messages = provider._build_messages(
            prompt="질문",
            context="컨텍스트 정보",
            system_prompt="시스템 프롬프트"
        )

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "컨텍스트" in messages[1]["content"]


# =============================================================================
# 응답 평가기 테스트
# =============================================================================

class TestResponseEvaluator:
    """ResponseEvaluator 테스트"""

    @pytest.fixture
    def evaluator(self):
        return ResponseEvaluator()

    @pytest.fixture
    def sample_responses(self):
        return [
            LLMResponse(
                provider="openai",
                content="""청년 주거 정책 안내

| 정책명 | 대상 | 지원내용 |
|--------|------|----------|
| 청년월세지원 | 만 19~34세 | 월 20만원 |

자격조건: 연소득 5,000만원 이하
신청방법: 복지로 홈페이지 (www.bokjiro.go.kr)""",
                model="gpt-4",
                latency=2.5,
                tokens_used=200,
                success=True
            ),
            LLMResponse(
                provider="groq",
                content="청년 정책이 있습니다.",
                model="llama-3.1-70b",
                latency=0.5,
                tokens_used=50,
                success=True
            ),
            LLMResponse(
                provider="gemini",
                content="",
                model="gemini-1.5-pro",
                latency=0,
                success=False,
                error="API 오류"
            )
        ]

    def test_evaluate_all(self, evaluator, sample_responses):
        """모든 응답 평가 테스트"""
        results = evaluator.evaluate_all(
            sample_responses,
            "청년 주거 정책 추천해주세요"
        )

        # 3개 결과
        assert len(results) == 3

        # 점수순 정렬 확인
        assert results[0].total_score >= results[1].total_score

        # 실패한 응답은 0점
        failed = next(r for r in results if r.provider == "gemini")
        assert failed.total_score == 0

    def test_select_best(self, evaluator, sample_responses):
        """최적 응답 선택 테스트"""
        results = evaluator.evaluate_all(
            sample_responses,
            "청년 주거 정책"
        )

        best = evaluator.select_best(results)

        # OpenAI가 가장 높은 점수 (구조화된 응답)
        assert best is not None
        assert best.provider == "openai"

    def test_evaluate_structure(self, evaluator):
        """구조화 점수 테스트"""
        # 마크다운 테이블이 있는 응답
        content_with_table = "| 항목 | 내용 |\n|------|------|\n| A | B |"
        score = evaluator._evaluate_structure(content_with_table)
        assert score > 60  # 테이블 가산점

        # 일반 텍스트
        plain_text = "일반 텍스트입니다."
        score_plain = evaluator._evaluate_structure(plain_text)
        assert score_plain < score

    def test_evaluate_completeness(self, evaluator):
        """완성도 점수 테스트"""
        # 긴 응답
        long_content = "테스트 " * 100
        score_long = evaluator._evaluate_completeness(long_content, "질문")

        # 짧은 응답
        short_content = "짧음"
        score_short = evaluator._evaluate_completeness(short_content, "질문")

        assert score_long > score_short


# =============================================================================
# Multi-LLM 오케스트레이터 테스트
# =============================================================================

class TestMultiLLMOrchestrator:
    """MultiLLMOrchestrator 테스트"""

    @pytest.fixture
    def llm_config(self):
        return LLMConfig(
            openai_api_key="test-key",
            groq_api_key="test-key",
            gemini_api_key="test-key",
            strategy=SelectionStrategy.BEST_QUALITY,
            timeout=10
        )

    def test_initialization(self, llm_config):
        """오케스트레이터 초기화 테스트"""
        orchestrator = MultiLLMOrchestrator(llm_config)

        # 3개 제공자 활성화
        assert len(orchestrator.providers) == 3
        assert "openai" in orchestrator.providers
        assert "groq" in orchestrator.providers
        assert "gemini" in orchestrator.providers

    def test_provider_status(self, llm_config):
        """제공자 상태 확인 테스트"""
        orchestrator = MultiLLMOrchestrator(llm_config)
        status = orchestrator.get_provider_status()

        assert status["openai"] is True
        assert status["groq"] is True
        assert status["gemini"] is True

    def test_missing_api_key(self):
        """API 키 누락 테스트"""
        config = LLMConfig(
            openai_api_key="test-key",
            # groq, gemini 키 없음
        )

        orchestrator = MultiLLMOrchestrator(config)

        # OpenAI만 활성화
        assert len(orchestrator.providers) == 1
        assert "openai" in orchestrator.providers


# =============================================================================
# 실행
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
