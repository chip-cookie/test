#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
응답 평가기 (Response Evaluator)
=============================================================================

여러 LLM의 응답을 다양한 기준으로 평가하여 최적의 응답을 선택합니다.

평가 기준:
    - 완성도 (Completeness): 답변이 질문을 충분히 다루는가
    - 정확성 (Accuracy): 정보가 정확하고 신뢰할 수 있는가
    - 관련성 (Relevance): 질문과 얼마나 관련이 있는가
    - 명확성 (Clarity): 답변이 명확하고 이해하기 쉬운가
    - 구조화 (Structure): 적절한 포맷과 구조를 갖추었는가

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import re
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


# =============================================================================
# 평가 기준 정의
# =============================================================================

class EvaluationCriteria(Enum):
    """
    평가 기준 열거형

    각 기준에 대한 가중치를 정의합니다.
    """
    COMPLETENESS = "completeness"    # 완성도
    ACCURACY = "accuracy"            # 정확성
    RELEVANCE = "relevance"          # 관련성
    CLARITY = "clarity"              # 명확성
    STRUCTURE = "structure"          # 구조화


@dataclass
class EvaluationResult:
    """
    평가 결과 데이터

    Attributes:
        provider (str): 제공자 이름
        total_score (float): 총점 (0-100)
        criteria_scores (Dict): 각 기준별 점수
        strengths (List[str]): 강점 목록
        weaknesses (List[str]): 약점 목록
        recommendation (str): 추천 이유
    """
    provider: str
    total_score: float
    criteria_scores: Dict[str, float] = field(default_factory=dict)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendation: str = ""


# =============================================================================
# 응답 평가기
# =============================================================================

class ResponseEvaluator:
    """
    LLM 응답 품질 평가기

    여러 LLM의 응답을 분석하고 점수를 매겨
    가장 우수한 응답을 선택합니다.

    평가 방식:
        1. 규칙 기반 평가 (빠름, 기본)
        2. LLM 기반 평가 (정확, 선택적)

    Example:
        >>> evaluator = ResponseEvaluator()
        >>> results = evaluator.evaluate_all(responses, query)
        >>> best = evaluator.select_best(results)
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        use_llm_evaluation: bool = False
    ):
        """
        평가기 초기화

        Args:
            weights: 평가 기준별 가중치
            use_llm_evaluation: LLM 기반 평가 사용 여부
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        # 기본 가중치 설정
        self.weights = weights or {
            EvaluationCriteria.COMPLETENESS.value: 0.25,
            EvaluationCriteria.ACCURACY.value: 0.25,
            EvaluationCriteria.RELEVANCE.value: 0.20,
            EvaluationCriteria.CLARITY.value: 0.15,
            EvaluationCriteria.STRUCTURE.value: 0.15
        }

        self.use_llm_evaluation = use_llm_evaluation

        # 청년 정책 관련 키워드 (정확성 평가용)
        self.policy_keywords = [
            "청년", "지원", "정책", "신청", "자격", "조건",
            "금액", "기간", "서류", "문의", "홈페이지",
            "만원", "개월", "세", "소득", "자산"
        ]

        # 구조화 요소 패턴
        self.structure_patterns = {
            "markdown_table": r"\|.*\|.*\|",
            "bullet_list": r"^[\-\*\•]\s",
            "numbered_list": r"^\d+[\.\)]\s",
            "headers": r"^#+\s|^\*\*.*\*\*",
            "links": r"\[.*\]\(.*\)",
        }

    def evaluate_all(
        self,
        responses: List[Any],  # List[LLMResponse]
        query: str,
        context: Optional[str] = None
    ) -> List[EvaluationResult]:
        """
        모든 응답 평가

        Args:
            responses: LLM 응답 목록
            query: 원본 질문
            context: RAG 컨텍스트

        Returns:
            List[EvaluationResult]: 평가 결과 목록
        """
        results = []

        for response in responses:
            if not response.success:
                # 실패한 응답은 0점
                results.append(EvaluationResult(
                    provider=response.provider,
                    total_score=0,
                    weaknesses=[f"응답 실패: {response.error}"]
                ))
                continue

            result = self._evaluate_single(response, query, context)
            results.append(result)

        # 점수순 정렬
        results.sort(key=lambda x: x.total_score, reverse=True)

        return results

    def _evaluate_single(
        self,
        response: Any,  # LLMResponse
        query: str,
        context: Optional[str]
    ) -> EvaluationResult:
        """
        단일 응답 평가

        Args:
            response: LLM 응답
            query: 원본 질문
            context: RAG 컨텍스트

        Returns:
            EvaluationResult: 평가 결과
        """
        content = response.content
        criteria_scores = {}
        strengths = []
        weaknesses = []

        # 1. 완성도 평가
        completeness_score = self._evaluate_completeness(content, query)
        criteria_scores[EvaluationCriteria.COMPLETENESS.value] = completeness_score

        if completeness_score >= 80:
            strengths.append("질문에 대해 충분히 상세한 답변 제공")
        elif completeness_score < 50:
            weaknesses.append("답변이 불완전하거나 너무 짧음")

        # 2. 정확성 평가
        accuracy_score = self._evaluate_accuracy(content, context)
        criteria_scores[EvaluationCriteria.ACCURACY.value] = accuracy_score

        if accuracy_score >= 80:
            strengths.append("정책 관련 키워드와 정보를 정확히 포함")
        elif accuracy_score < 50:
            weaknesses.append("정책 정보가 부족하거나 불명확")

        # 3. 관련성 평가
        relevance_score = self._evaluate_relevance(content, query)
        criteria_scores[EvaluationCriteria.RELEVANCE.value] = relevance_score

        if relevance_score >= 80:
            strengths.append("질문과 높은 관련성")
        elif relevance_score < 50:
            weaknesses.append("질문과의 관련성이 낮음")

        # 4. 명확성 평가
        clarity_score = self._evaluate_clarity(content)
        criteria_scores[EvaluationCriteria.CLARITY.value] = clarity_score

        if clarity_score >= 80:
            strengths.append("명확하고 이해하기 쉬운 문장")
        elif clarity_score < 50:
            weaknesses.append("문장이 복잡하거나 불명확")

        # 5. 구조화 평가
        structure_score = self._evaluate_structure(content)
        criteria_scores[EvaluationCriteria.STRUCTURE.value] = structure_score

        if structure_score >= 80:
            strengths.append("잘 구조화된 포맷 (표, 리스트 등)")
        elif structure_score < 50:
            weaknesses.append("구조화가 부족하여 가독성이 낮음")

        # 총점 계산 (가중 평균)
        total_score = sum(
            score * self.weights[criterion]
            for criterion, score in criteria_scores.items()
        )

        # 추천 이유 생성
        recommendation = self._generate_recommendation(
            response.provider,
            total_score,
            strengths,
            weaknesses
        )

        return EvaluationResult(
            provider=response.provider,
            total_score=round(total_score, 2),
            criteria_scores=criteria_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendation=recommendation
        )

    def _evaluate_completeness(self, content: str, query: str) -> float:
        """
        완성도 평가

        답변의 길이, 세부 정보 포함 여부 등을 평가합니다.

        Args:
            content: 응답 내용
            query: 원본 질문

        Returns:
            float: 점수 (0-100)
        """
        score = 0

        # 길이 기반 점수 (최소 100자, 최적 500-1500자)
        length = len(content)
        if length < 100:
            score += 20
        elif length < 300:
            score += 40
        elif length < 500:
            score += 60
        elif length < 1500:
            score += 80
        else:
            score += 70  # 너무 길면 감점

        # 문장 수 (최소 3문장)
        sentences = len(re.findall(r'[.!?。]', content))
        if sentences >= 5:
            score += 20
        elif sentences >= 3:
            score += 10

        return min(score, 100)

    def _evaluate_accuracy(
        self,
        content: str,
        context: Optional[str]
    ) -> float:
        """
        정확성 평가

        정책 관련 키워드, 숫자 정보 포함 여부를 평가합니다.

        Args:
            content: 응답 내용
            context: RAG 컨텍스트

        Returns:
            float: 점수 (0-100)
        """
        score = 0

        # 정책 키워드 포함 여부
        keyword_count = sum(
            1 for keyword in self.policy_keywords
            if keyword in content
        )
        score += min(keyword_count * 5, 40)

        # 숫자 정보 포함 (금액, 기간, 나이 등)
        numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', content)
        if len(numbers) >= 3:
            score += 30
        elif len(numbers) >= 1:
            score += 15

        # URL 또는 연락처 포함
        if re.search(r'https?://|www\.|\.go\.kr|\.or\.kr', content):
            score += 15
        if re.search(r'\d{2,4}[-\s]?\d{3,4}[-\s]?\d{4}', content):
            score += 15

        return min(score, 100)

    def _evaluate_relevance(self, content: str, query: str) -> float:
        """
        관련성 평가

        질문의 키워드가 답변에 포함되어 있는지 평가합니다.

        Args:
            content: 응답 내용
            query: 원본 질문

        Returns:
            float: 점수 (0-100)
        """
        # 질문에서 주요 키워드 추출
        query_words = set(re.findall(r'[\w가-힣]+', query.lower()))

        # 불용어 제거
        stopwords = {'은', '는', '이', '가', '을', '를', '에', '의', '로', '와', '과', '도'}
        query_words -= stopwords

        if not query_words:
            return 50

        # 답변에 키워드 포함 비율
        content_lower = content.lower()
        matched = sum(1 for word in query_words if word in content_lower)

        score = (matched / len(query_words)) * 100

        return min(score, 100)

    def _evaluate_clarity(self, content: str) -> float:
        """
        명확성 평가

        문장 길이, 복잡성 등을 평가합니다.

        Args:
            content: 응답 내용

        Returns:
            float: 점수 (0-100)
        """
        score = 70  # 기본 점수

        # 문장 분리
        sentences = re.split(r'[.!?。]', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 30

        # 평균 문장 길이 (20-50자가 이상적)
        avg_length = sum(len(s) for s in sentences) / len(sentences)

        if 20 <= avg_length <= 50:
            score += 20
        elif avg_length < 20:
            score += 10  # 너무 짧음
        elif avg_length > 100:
            score -= 20  # 너무 김

        # 특수 문자 과다 사용 체크
        special_ratio = len(re.findall(r'[^\w\s가-힣]', content)) / max(len(content), 1)
        if special_ratio > 0.1:
            score -= 10

        return max(min(score, 100), 0)

    def _evaluate_structure(self, content: str) -> float:
        """
        구조화 평가

        마크다운 요소(표, 리스트, 헤더 등) 사용 여부를 평가합니다.

        Args:
            content: 응답 내용

        Returns:
            float: 점수 (0-100)
        """
        score = 40  # 기본 점수

        # 각 구조화 요소 체크
        for pattern_name, pattern in self.structure_patterns.items():
            if re.search(pattern, content, re.MULTILINE):
                if pattern_name == "markdown_table":
                    score += 25  # 표는 높은 가산점
                elif pattern_name in ["bullet_list", "numbered_list"]:
                    score += 15
                else:
                    score += 10

        # 줄바꿈으로 단락 구분
        paragraphs = content.split('\n\n')
        if len(paragraphs) >= 3:
            score += 10

        return min(score, 100)

    def _generate_recommendation(
        self,
        provider: str,
        score: float,
        strengths: List[str],
        weaknesses: List[str]
    ) -> str:
        """
        추천 이유 생성

        Args:
            provider: 제공자 이름
            score: 총점
            strengths: 강점 목록
            weaknesses: 약점 목록

        Returns:
            str: 추천 이유
        """
        if score >= 80:
            quality = "매우 우수"
        elif score >= 60:
            quality = "우수"
        elif score >= 40:
            quality = "보통"
        else:
            quality = "미흡"

        recommendation = f"{provider} 응답은 {quality}한 품질입니다."

        if strengths:
            recommendation += f" 강점: {', '.join(strengths[:2])}."

        if weaknesses and score < 60:
            recommendation += f" 개선 필요: {', '.join(weaknesses[:1])}."

        return recommendation

    def select_best(
        self,
        results: List[EvaluationResult]
    ) -> Optional[EvaluationResult]:
        """
        최적의 응답 선택

        Args:
            results: 평가 결과 목록

        Returns:
            Optional[EvaluationResult]: 최고 점수 결과
        """
        if not results:
            return None

        # 이미 정렬되어 있으므로 첫 번째가 최고점
        best = results[0]

        self.logger.info(
            f"최적 응답 선택: {best.provider} "
            f"(점수: {best.total_score})"
        )

        return best

    def get_consensus(
        self,
        results: List[EvaluationResult],
        threshold: float = 70.0
    ) -> List[EvaluationResult]:
        """
        합의된 응답들 반환

        특정 점수 이상의 응답들을 반환합니다.

        Args:
            results: 평가 결과 목록
            threshold: 최소 점수 기준

        Returns:
            List[EvaluationResult]: 기준을 통과한 결과들
        """
        return [r for r in results if r.total_score >= threshold]
