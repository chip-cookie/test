#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
크롤러 테스트 스크립트 (Windows + PyCharm 호환)

PyCharm에서 직접 실행 가능합니다.
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.crawlers.bokjiro_crawler import BokjiroCrawler
from src.crawlers.kinfa_crawler import KinfaCrawler


async def main():
    """크롤러 테스트 메인 함수"""

    print("=" * 60)
    print("청년 정책 크롤러 테스트")
    print("=" * 60)

    # 복지로 크롤러 테스트
    print("\n[1/2] 복지로 크롤러 실행 중...")
    bokjiro = BokjiroCrawler()
    result1 = await bokjiro.crawl()

    print(f"✅ 복지로: {result1.total_policies}개 정책 수집")
    print(f"   - 성공: {result1.success_count}개")
    print(f"   - 실패: {result1.error_count}개")
    print(f"   - 소요 시간: {result1.elapsed_time:.2f}초")

    # 서민금융진흥원 크롤러 테스트
    print("\n[2/2] 서민금융진흥원 크롤러 실행 중...")
    kinfa = KinfaCrawler()
    result2 = await kinfa.crawl()

    print(f"✅ 서민금융진흥원: {result2.total_policies}개 정책 수집")
    print(f"   - 성공: {result2.success_count}개")
    print(f"   - 실패: {result2.error_count}개")
    print(f"   - 소요 시간: {result2.elapsed_time:.2f}초")

    # 전체 결과
    total = result1.total_policies + result2.total_policies
    print("\n" + "=" * 60)
    print(f"✨ 전체 수집: {total}개 정책")
    print("=" * 60)

    # 샘플 정책 출력
    if result1.policies:
        print("\n📋 샘플 정책 (복지로):")
        sample = result1.policies[0]
        print(f"   제목: {sample.policy_name}")
        print(f"   카테고리: {sample.category}")
        print(f"   대상 연령: {sample.target_age_min}~{sample.target_age_max}세")
        print(f"   링크: {sample.official_link}")


if __name__ == "__main__":
    # Windows에서 asyncio 이벤트 루프 정책 설정
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 크롤러 실행
    asyncio.run(main())
