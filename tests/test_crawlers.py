#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
크롤러 테스트
=============================================================================

웹 크롤러 클래스들을 테스트합니다.

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, '/home/user/test')

from src.crawlers.base_crawler import (
    BaseCrawler,
    CrawlerConfig,
    PolicyData,
    CrawlResult,
    SourceTier,
    CrawlerStatus
)
from src.crawlers.kinfa_crawler import KinfaCrawler
from src.crawlers.bokjiro_crawler import BokjiroCrawler
from src.crawlers.factory import PolicyCrawlerFactory


# =============================================================================
# 픽스처
# =============================================================================

@pytest.fixture
def kinfa_crawler():
    return KinfaCrawler()


@pytest.fixture
def bokjiro_crawler():
    return BokjiroCrawler()


@pytest.fixture
def sample_policy_html():
    return """
    <html>
    <body>
        <h1 class="policy-title">청년 전용 대환대출</h1>
        <div class="policy-summary">청년의 고금리 대출을 저금리로 전환</div>
        <div class="eligibility">만 19세 ~ 34세 청년</div>
        <div class="benefits">최대 5,000만원, 연 4.5%</div>
        <ul class="documents">
            <li>신분증</li>
            <li>소득증명서</li>
        </ul>
        <div class="period">2025.01.01 ~ 2025.12.31</div>
    </body>
    </html>
    """


# =============================================================================
# 크롤러 설정 테스트
# =============================================================================

class TestCrawlerConfig:
    """CrawlerConfig 테스트"""

    def test_default_config(self):
        """기본 설정 테스트"""
        config = CrawlerConfig(
            base_url="https://example.com",
            source_name="테스트",
            source_tier=SourceTier.TIER_1
        )

        assert config.request_delay == 1.0
        assert config.max_retries == 3
        assert config.timeout == 30
        assert config.max_pages == 10

    def test_custom_config(self):
        """커스텀 설정 테스트"""
        config = CrawlerConfig(
            base_url="https://example.com",
            source_name="테스트",
            source_tier=SourceTier.TIER_2,
            request_delay=5.0,
            max_pages=20
        )

        assert config.request_delay == 5.0
        assert config.max_pages == 20
        assert config.source_tier == SourceTier.TIER_2


# =============================================================================
# PolicyData 테스트
# =============================================================================

class TestPolicyData:
    """PolicyData 테스트"""

    def test_create_policy_data(self):
        """정책 데이터 생성 테스트"""
        policy = PolicyData(
            policy_id="test-001",
            policy_name="테스트 정책",
            category="대출",
            content="정책 내용"
        )

        assert policy.policy_id == "test-001"
        assert policy.policy_name == "테스트 정책"
        assert policy.location == ["전국"]  # 기본값

    def test_to_vector_db_format(self):
        """Vector DB 포맷 변환 테스트"""
        policy = PolicyData(
            policy_id="test-001",
            policy_name="청년 대출",
            category="대출",
            content="청년 대출 정책 내용",
            target_age_min=19,
            target_age_max=34,
            income_limit=50000000
        )

        result = policy.to_vector_db_format(
            SourceTier.TIER_1,
            "https://example.com/policy/1"
        )

        assert result["id"] == "test-001"
        assert result["content"] == "청년 대출 정책 내용"
        assert result["metadata"]["source_tier"] == "Tier 1"
        assert result["metadata"]["target_age_min"] == 19
        assert result["metadata"]["income_limit"] == 50000000


# =============================================================================
# 서민금융진흥원 크롤러 테스트
# =============================================================================

class TestKinfaCrawler:
    """KinfaCrawler 테스트"""

    def test_initialization(self, kinfa_crawler):
        """크롤러 초기화 테스트"""
        assert kinfa_crawler.config.source_name == "서민금융진흥원"
        assert kinfa_crawler.config.source_tier == SourceTier.TIER_1
        assert kinfa_crawler.status == CrawlerStatus.IDLE

    def test_is_youth_policy(self, kinfa_crawler):
        """청년 정책 판별 테스트"""
        assert kinfa_crawler._is_youth_policy("청년 대출") is True
        assert kinfa_crawler._is_youth_policy("대학생 지원") is True
        assert kinfa_crawler._is_youth_policy("노인 복지") is False

    def test_determine_category(self, kinfa_crawler):
        """카테고리 결정 테스트"""
        assert kinfa_crawler._determine_category("대출 상품") == "대출"
        assert kinfa_crawler._determine_category("저축 계좌") == "자산형성"
        assert kinfa_crawler._determine_category("기타") == "금융상품"

    def test_extract_age_range(self, kinfa_crawler):
        """연령 범위 추출 테스트"""
        text = "만 19세 ~ 34세 청년"
        age_min, age_max = kinfa_crawler._extract_age_range(text)
        assert age_min == 19
        assert age_max == 34

        # 기본값
        age_min, age_max = kinfa_crawler._extract_age_range("나이 정보 없음")
        assert age_min == 19
        assert age_max == 34

    def test_extract_income_limit(self, kinfa_crawler):
        """소득 제한 추출 테스트"""
        text = "연소득 5,000만원 이하"
        income = kinfa_crawler._extract_income_limit(text)
        assert income == 50000000

        # 천만원 형태
        text = "5천만원 이하"
        income = kinfa_crawler._extract_income_limit(text)
        assert income == 50000000

    @pytest.mark.asyncio
    async def test_parse_policy(self, kinfa_crawler, sample_policy_html):
        """정책 파싱 테스트"""
        policy = await kinfa_crawler.parse_policy(
            sample_policy_html,
            "https://www.kinfa.or.kr/policy/1"
        )

        assert policy is not None
        assert "청년 전용 대환대출" in policy.policy_name
        assert policy.target_age_min == 19
        assert policy.target_age_max == 34


# =============================================================================
# 복지로 크롤러 테스트
# =============================================================================

class TestBokjiroCrawler:
    """BokjiroCrawler 테스트"""

    def test_initialization(self, bokjiro_crawler):
        """크롤러 초기화 테스트"""
        assert bokjiro_crawler.config.source_name == "복지로"
        assert bokjiro_crawler.config.source_tier == SourceTier.TIER_1
        assert bokjiro_crawler.config.request_delay == 2.5

    def test_is_youth_policy(self, bokjiro_crawler):
        """청년 정책 판별 테스트"""
        assert bokjiro_crawler._is_youth_policy("청년 주거지원") is True
        assert bokjiro_crawler._is_youth_policy("취준생 지원") is True
        assert bokjiro_crawler._is_youth_policy("어린이집") is False

    def test_determine_category(self, bokjiro_crawler):
        """카테고리 결정 테스트"""
        assert bokjiro_crawler._determine_category("주거 지원") == "주거"
        assert bokjiro_crawler._determine_category("취업 지원") == "취업"
        assert bokjiro_crawler._determine_category("기타") == "생활지원"

    def test_extract_from_json(self, bokjiro_crawler):
        """JSON 추출 테스트"""
        json_str = '{"list": [{"id": "1"}, {"id": "2"}]}'
        result = bokjiro_crawler._extract_from_json(json_str)
        assert len(result) == 2
        assert result[0]["id"] == "1"

        # 잘못된 JSON
        result = bokjiro_crawler._extract_from_json("not json")
        assert result == []


# =============================================================================
# 크롤러 팩토리 테스트
# =============================================================================

class TestPolicyCrawlerFactory:
    """PolicyCrawlerFactory 테스트"""

    def test_create_kinfa_crawler(self):
        """서민금융진흥원 크롤러 생성"""
        crawler = PolicyCrawlerFactory.create("kinfa")
        assert isinstance(crawler, KinfaCrawler)

    def test_create_bokjiro_crawler(self):
        """복지로 크롤러 생성"""
        crawler = PolicyCrawlerFactory.create("bokjiro")
        assert isinstance(crawler, BokjiroCrawler)

    def test_get_all_crawlers(self):
        """모든 크롤러 생성"""
        crawlers = PolicyCrawlerFactory.get_all_crawlers()
        assert len(crawlers) >= 2


# =============================================================================
# CrawlResult 테스트
# =============================================================================

class TestCrawlResult:
    """CrawlResult 테스트"""

    def test_add_policy(self):
        """정책 추가 테스트"""
        result = CrawlResult(success=False)

        policy = PolicyData(
            policy_id="test-001",
            policy_name="테스트",
            category="테스트",
            content="내용"
        )

        result.add_policy(policy)

        assert result.total_count == 1
        assert len(result.policies) == 1

    def test_add_error(self):
        """오류 추가 테스트"""
        result = CrawlResult(success=False)

        result.add_error("테스트 오류")

        assert result.error_count == 1
        assert "테스트 오류" in result.errors

    def test_finalize(self):
        """완료 처리 테스트"""
        result = CrawlResult(success=True)
        result.finalize()

        assert result.completed_at is not None
        assert result.duration_seconds >= 0


# =============================================================================
# 실행
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
