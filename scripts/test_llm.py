#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-LLM 테스트 스크립트 (Windows + PyCharm 호환)

OpenAI, Groq, Gemini 병렬 처리 테스트
"""

import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm.multi_llm import MultiLLMOrchestrator
from src.llm.providers import ProviderConfig
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


async def main():
    """Multi-LLM 테스트"""

    print("=" * 60)
    print("Multi-LLM 병렬 처리 테스트")
    print("=" * 60)

    # API 키 확인
    openai_key = os.getenv("OPENAI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if not openai_key:
        print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 API 키를 추가하세요.")
        return

    print(f"\n✅ OpenAI API 키: {openai_key[:20]}...")
    print(f"✅ Groq API 키: {groq_key[:20] if groq_key else '미설정'}...")
    print(f"✅ Gemini API 키: {gemini_key[:20] if gemini_key else '미설정'}...")

    # Multi-LLM 오케스트레이터 생성
    orchestrator = MultiLLMOrchestrator()

    # 테스트 질문
    query = "청년 주거 지원 정책에는 어떤 것이 있나요?"
    context = """
    청년 주거 지원 정책:
    1. 청년 월세 지원: 만 19~34세, 월 최대 20만원
    2. 청년 전세대출: 연 1~2% 저금리, 최대 2억원
    3. 주거급여: 중위소득 50% 이하, 월세 지원
    """

    print(f"\n질문: {query}")
    print(f"컨텍스트: {context[:100]}...")

    # Multi-LLM 호출
    print("\n🚀 Multi-LLM 병렬 처리 시작...")
    result = await orchestrator.generate_with_best(
        prompt=query,
        context=context
    )

    # 결과 출력
    print("\n" + "=" * 60)
    print("📊 응답 결과")
    print("=" * 60)

    print(f"\n🏆 최고 품질: {result.best_response.provider}")
    print(f"   점수: {result.evaluation.total_score:.2f}/100")
    print(f"   응답 시간: {result.best_response.latency:.2f}초")
    print(f"\n   응답 내용:\n{result.best_response.content[:200]}...\n")

    # 모든 응답 비교
    print("\n📈 전체 응답 비교:")
    for eval_result in result.all_evaluations:
        provider = eval_result.provider
        score = eval_result.total_score
        response = next(r for r in result.all_responses if r.provider == provider)
        latency = response.latency

        print(f"\n   [{provider.upper()}]")
        print(f"   - 점수: {score:.2f}/100")
        print(f"   - 속도: {latency:.2f}초")
        print(f"   - 강점: {', '.join(eval_result.strengths[:2])}")


if __name__ == "__main__":
    # Windows에서 asyncio 이벤트 루프 정책 설정
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # LLM 테스트 실행
    asyncio.run(main())
