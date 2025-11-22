#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
LLM 제공자 (LLM Providers)
=============================================================================

각 LLM 서비스(OpenAI, Groq, Gemini)에 대한 클라이언트 구현입니다.
Strategy 패턴을 사용하여 일관된 인터페이스를 제공합니다.

설계 패턴:
    - Strategy Pattern: 각 제공자가 동일한 인터페이스 구현
    - Factory Pattern: 제공자 이름으로 인스턴스 생성
    - Template Method: 공통 로직은 기본 클래스에서 처리

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import asyncio
import aiohttp
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum


# =============================================================================
# 데이터 클래스 정의
# =============================================================================

@dataclass(frozen=True)
class ProviderConfig:
    """
    LLM 제공자 불변 설정

    실행 중 설정 변경을 방지하여 안정성을 보장합니다.

    Attributes:
        api_key (str): API 키
        model (str): 사용할 모델명
        temperature (float): 생성 온도 (0.0 ~ 1.0)
        max_tokens (int): 최대 토큰 수
        timeout (int): 요청 타임아웃 (초)

    Note:
        frozen=True로 인해 생성 후 수정할 수 없습니다.
    """
    api_key: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 30


@dataclass(frozen=True)
class LLMResponse:
    """
    LLM 응답 불변 데이터

    응답 결과의 무결성을 보장합니다.

    Attributes:
        provider (str): 제공자 이름 (openai, groq, gemini)
        content (str): 응답 내용
        model (str): 사용된 모델명
        latency (float): 응답 시간 (초)
        tokens_used (int): 사용된 토큰 수
        success (bool): 성공 여부
        error (Optional[str]): 에러 메시지
        metadata (Dict): 추가 메타데이터

    Note:
        frozen=True로 인해 생성 후 수정할 수 없습니다.
    """
    provider: str
    content: str
    model: str
    latency: float
    tokens_used: int = 0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# 추상 기본 클래스
# =============================================================================

class LLMProvider(ABC):
    """
    LLM 제공자 추상 기본 클래스

    모든 LLM 제공자는 이 클래스를 상속받아 구현합니다.
    Strategy 패턴의 Strategy 인터페이스 역할을 합니다.

    Example:
        >>> class CustomProvider(LLMProvider):
        ...     async def generate(self, prompt, context):
        ...         # 구현
        ...         pass
    """

    def __init__(self, config: ProviderConfig):
        """
        제공자 초기화

        Args:
            config: 제공자 설정
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """제공자 이름 반환"""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """
        텍스트 생성

        Args:
            prompt: 사용자 프롬프트
            context: RAG 검색 결과 컨텍스트
            system_prompt: 시스템 프롬프트

        Returns:
            LLMResponse: 생성된 응답
        """
        pass

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        HTTP 세션 가져오기 (지연 초기화)

        Returns:
            aiohttp.ClientSession: HTTP 클라이언트 세션
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """리소스 정리"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _build_messages(
        self,
        prompt: str,
        context: Optional[str],
        system_prompt: Optional[str]
    ) -> List[Dict[str, str]]:
        """
        메시지 목록 구성

        Args:
            prompt: 사용자 프롬프트
            context: 컨텍스트
            system_prompt: 시스템 프롬프트

        Returns:
            List[Dict]: 메시지 목록
        """
        messages = []

        # 시스템 프롬프트
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        # 컨텍스트가 있으면 프롬프트에 포함
        user_content = prompt
        if context:
            user_content = f"""다음 정보를 참고하여 답변해주세요:

[참고 정보]
{context}

[질문]
{prompt}"""

        messages.append({
            "role": "user",
            "content": user_content
        })

        return messages


# =============================================================================
# OpenAI 제공자
# =============================================================================

class OpenAIProvider(LLMProvider):
    """
    OpenAI API 제공자

    GPT-4, GPT-3.5-turbo 등 OpenAI 모델을 사용합니다.

    Example:
        >>> config = ProviderConfig(
        ...     api_key="sk-...",
        ...     model="gpt-4"
        ... )
        >>> provider = OpenAIProvider(config)
        >>> response = await provider.generate("안녕하세요")
    """

    API_URL = "https://api.openai.com/v1/chat/completions"

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """
        OpenAI API를 통한 텍스트 생성

        Args:
            prompt: 사용자 프롬프트
            context: RAG 컨텍스트
            system_prompt: 시스템 프롬프트

        Returns:
            LLMResponse: 생성된 응답
        """
        start_time = time.time()

        try:
            session = await self._get_session()

            # 요청 데이터 구성
            messages = self._build_messages(prompt, context, system_prompt)

            payload = {
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens
            }

            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }

            # API 호출
            async with session.post(
                self.API_URL,
                json=payload,
                headers=headers
            ) as response:

                latency = time.time() - start_time

                if response.status != 200:
                    error_text = await response.text()
                    self.logger.error(f"OpenAI API 오류: {error_text}")
                    return LLMResponse(
                        provider=self.provider_name,
                        content="",
                        model=self.config.model,
                        latency=latency,
                        success=False,
                        error=f"API 오류 ({response.status}): {error_text}"
                    )

                data = await response.json()

                # 응답 파싱
                content = data["choices"][0]["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens", 0)

                self.logger.info(
                    f"OpenAI 응답 완료: {tokens_used} tokens, {latency:.2f}s"
                )

                return LLMResponse(
                    provider=self.provider_name,
                    content=content,
                    model=self.config.model,
                    latency=latency,
                    tokens_used=tokens_used,
                    success=True,
                    metadata={
                        "finish_reason": data["choices"][0].get("finish_reason"),
                        "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                        "completion_tokens": data.get("usage", {}).get("completion_tokens", 0)
                    }
                )

        except asyncio.TimeoutError:
            latency = time.time() - start_time
            self.logger.error(f"OpenAI 타임아웃: {latency:.2f}s")
            return LLMResponse(
                provider=self.provider_name,
                content="",
                model=self.config.model,
                latency=latency,
                success=False,
                error="요청 타임아웃"
            )

        except Exception as e:
            latency = time.time() - start_time
            self.logger.error(f"OpenAI 오류: {str(e)}")
            return LLMResponse(
                provider=self.provider_name,
                content="",
                model=self.config.model,
                latency=latency,
                success=False,
                error=str(e)
            )


# =============================================================================
# Groq 제공자
# =============================================================================

class GroqProvider(LLMProvider):
    """
    Groq API 제공자

    Llama, Mixtral 등 오픈소스 모델을 초고속으로 실행합니다.
    Groq의 LPU(Language Processing Unit)를 활용합니다.

    특징:
        - 매우 빠른 응답 속도 (GPT-4 대비 10배 이상)
        - Llama 3.1, Mixtral 등 오픈소스 모델 지원
        - 비용 효율적

    Example:
        >>> config = ProviderConfig(
        ...     api_key="gsk-...",
        ...     model="llama-3.1-70b-versatile"
        ... )
        >>> provider = GroqProvider(config)
        >>> response = await provider.generate("안녕하세요")
    """

    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def provider_name(self) -> str:
        return "groq"

    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """
        Groq API를 통한 텍스트 생성

        Args:
            prompt: 사용자 프롬프트
            context: RAG 컨텍스트
            system_prompt: 시스템 프롬프트

        Returns:
            LLMResponse: 생성된 응답
        """
        start_time = time.time()

        try:
            session = await self._get_session()

            # 요청 데이터 구성 (OpenAI 호환 형식)
            messages = self._build_messages(prompt, context, system_prompt)

            payload = {
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens
            }

            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }

            # API 호출
            async with session.post(
                self.API_URL,
                json=payload,
                headers=headers
            ) as response:

                latency = time.time() - start_time

                if response.status != 200:
                    error_text = await response.text()
                    self.logger.error(f"Groq API 오류: {error_text}")
                    return LLMResponse(
                        provider=self.provider_name,
                        content="",
                        model=self.config.model,
                        latency=latency,
                        success=False,
                        error=f"API 오류 ({response.status}): {error_text}"
                    )

                data = await response.json()

                # 응답 파싱
                content = data["choices"][0]["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens", 0)

                self.logger.info(
                    f"Groq 응답 완료: {tokens_used} tokens, {latency:.2f}s"
                )

                return LLMResponse(
                    provider=self.provider_name,
                    content=content,
                    model=self.config.model,
                    latency=latency,
                    tokens_used=tokens_used,
                    success=True,
                    metadata={
                        "finish_reason": data["choices"][0].get("finish_reason"),
                        "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                        "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                        # Groq 특유의 메타데이터
                        "x_groq": data.get("x_groq", {})
                    }
                )

        except asyncio.TimeoutError:
            latency = time.time() - start_time
            self.logger.error(f"Groq 타임아웃: {latency:.2f}s")
            return LLMResponse(
                provider=self.provider_name,
                content="",
                model=self.config.model,
                latency=latency,
                success=False,
                error="요청 타임아웃"
            )

        except Exception as e:
            latency = time.time() - start_time
            self.logger.error(f"Groq 오류: {str(e)}")
            return LLMResponse(
                provider=self.provider_name,
                content="",
                model=self.config.model,
                latency=latency,
                success=False,
                error=str(e)
            )


# =============================================================================
# Google Gemini 제공자
# =============================================================================

class GeminiProvider(LLMProvider):
    """
    Google Gemini API 제공자

    Gemini Pro, Gemini 1.5 등 Google의 최신 모델을 사용합니다.

    특징:
        - 대용량 컨텍스트 윈도우 (최대 1M 토큰)
        - 멀티모달 지원 (텍스트, 이미지)
        - Google 생태계 통합

    Example:
        >>> config = ProviderConfig(
        ...     api_key="...",
        ...     model="gemini-1.5-pro"
        ... )
        >>> provider = GeminiProvider(config)
        >>> response = await provider.generate("안녕하세요")
    """

    API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """
        Gemini API를 통한 텍스트 생성

        Args:
            prompt: 사용자 프롬프트
            context: RAG 컨텍스트
            system_prompt: 시스템 프롬프트

        Returns:
            LLMResponse: 생성된 응답
        """
        start_time = time.time()

        try:
            session = await self._get_session()

            # Gemini API URL 구성
            url = f"{self.API_BASE}/{self.config.model}:generateContent"

            # 프롬프트 구성
            full_prompt = ""
            if system_prompt:
                full_prompt += f"{system_prompt}\n\n"

            if context:
                full_prompt += f"""다음 정보를 참고하여 답변해주세요:

[참고 정보]
{context}

[질문]
{prompt}"""
            else:
                full_prompt += prompt

            # Gemini API 형식으로 요청 구성
            payload = {
                "contents": [{
                    "parts": [{
                        "text": full_prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": self.config.temperature,
                    "maxOutputTokens": self.config.max_tokens,
                    "topP": 0.95,
                    "topK": 40
                },
                "safetySettings": [
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_ONLY_HIGH"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_ONLY_HIGH"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_ONLY_HIGH"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_ONLY_HIGH"
                    }
                ]
            }

            # API 호출
            async with session.post(
                url,
                json=payload,
                params={"key": self.config.api_key}
            ) as response:

                latency = time.time() - start_time

                if response.status != 200:
                    error_text = await response.text()
                    self.logger.error(f"Gemini API 오류: {error_text}")
                    return LLMResponse(
                        provider=self.provider_name,
                        content="",
                        model=self.config.model,
                        latency=latency,
                        success=False,
                        error=f"API 오류 ({response.status}): {error_text}"
                    )

                data = await response.json()

                # 응답 파싱
                candidates = data.get("candidates", [])
                if not candidates:
                    return LLMResponse(
                        provider=self.provider_name,
                        content="",
                        model=self.config.model,
                        latency=latency,
                        success=False,
                        error="응답이 비어있습니다"
                    )

                content = candidates[0]["content"]["parts"][0]["text"]

                # 토큰 사용량 추출
                usage_metadata = data.get("usageMetadata", {})
                tokens_used = (
                    usage_metadata.get("promptTokenCount", 0) +
                    usage_metadata.get("candidatesTokenCount", 0)
                )

                self.logger.info(
                    f"Gemini 응답 완료: {tokens_used} tokens, {latency:.2f}s"
                )

                return LLMResponse(
                    provider=self.provider_name,
                    content=content,
                    model=self.config.model,
                    latency=latency,
                    tokens_used=tokens_used,
                    success=True,
                    metadata={
                        "finish_reason": candidates[0].get("finishReason"),
                        "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
                        "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
                        "safety_ratings": candidates[0].get("safetyRatings", [])
                    }
                )

        except asyncio.TimeoutError:
            latency = time.time() - start_time
            self.logger.error(f"Gemini 타임아웃: {latency:.2f}s")
            return LLMResponse(
                provider=self.provider_name,
                content="",
                model=self.config.model,
                latency=latency,
                success=False,
                error="요청 타임아웃"
            )

        except Exception as e:
            latency = time.time() - start_time
            self.logger.error(f"Gemini 오류: {str(e)}")
            return LLMResponse(
                provider=self.provider_name,
                content="",
                model=self.config.model,
                latency=latency,
                success=False,
                error=str(e)
            )


# =============================================================================
# 제공자 팩토리
# =============================================================================

class ProviderFactory:
    """
    LLM 제공자 팩토리

    제공자 이름으로 적절한 제공자 인스턴스를 생성합니다.

    Example:
        >>> config = ProviderConfig(api_key="...", model="gpt-4")
        >>> provider = ProviderFactory.create("openai", config)
    """

    _providers = {
        "openai": OpenAIProvider,
        "groq": GroqProvider,
        "gemini": GeminiProvider
    }

    @classmethod
    def create(cls, name: str, config: ProviderConfig) -> LLMProvider:
        """
        제공자 인스턴스 생성

        Args:
            name: 제공자 이름 (openai, groq, gemini)
            config: 제공자 설정

        Returns:
            LLMProvider: 생성된 제공자 인스턴스

        Raises:
            ValueError: 알 수 없는 제공자 이름
        """
        provider_class = cls._providers.get(name.lower())

        if not provider_class:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"알 수 없는 제공자: {name}. 사용 가능: {available}"
            )

        return provider_class(config)

    @classmethod
    def register(cls, name: str, provider_class: type):
        """
        새 제공자 등록

        Args:
            name: 제공자 이름
            provider_class: 제공자 클래스
        """
        cls._providers[name.lower()] = provider_class
