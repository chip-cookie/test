#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
서민금융진흥원 크롤러 (Kinfa Crawler)
=============================================================================

서민금융진흥원(https://www.kinfa.or.kr) 웹사이트에서
청년 대출 및 금융 정책 정보를 크롤링합니다.

Tier 1 공식 데이터 소스입니다.

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import re
from typing import List, Optional
from datetime import datetime
from urllib.parse import urljoin

from .base_crawler import (
    BaseCrawler,
    CrawlerConfig,
    PolicyData,
    SourceTier
)
from .utils import PolicyDataExtractor


class KinfaCrawler(BaseCrawler):
    """
    서민금융진흥원 정책 크롤러

    서민금융진흥원 웹사이트에서 청년 대상 금융 정책을 수집합니다.
    주요 수집 대상:
        - 청년 전용 대환대출
        - 청년도약계좌
        - 햇살론 유스
        - 기타 청년 금융 상품

    Attributes:
        _policy_list_url (str): 정책 목록 페이지 URL
        _category_mapping (dict): 카테고리 매핑 테이블

    Example:
        >>> config = CrawlerConfig(
        ...     base_url="https://www.kinfa.or.kr",
        ...     source_name="서민금융진흥원",
        ...     source_tier=SourceTier.TIER_1
        ... )
        >>> crawler = KinfaCrawler(config)
        >>> result = await crawler.crawl()
    """

    def __init__(self, config: Optional[CrawlerConfig] = None):
        """
        서민금융진흥원 크롤러 초기화

        Args:
            config: 크롤러 설정 (None이면 기본값 사용)
        """
        # 기본 설정 생성
        if config is None:
            config = CrawlerConfig(
                base_url="https://www.kinfa.or.kr",
                source_name="서민금융진흥원",
                source_tier=SourceTier.TIER_1,
                request_delay=2.0,  # 서버 부하 방지를 위해 2초 지연
                max_pages=5
            )

        super().__init__(config)

        # 정책 목록 페이지 URL (실제 URL로 변경 필요)
        self._policy_list_url = urljoin(
            self._config.base_url,
            "/main/policy/youth/list.do"
        )

        # 카테고리 매핑
        self._category_mapping = {
            "대출": "대출",
            "대환": "대출",
            "계좌": "자산형성",
            "저축": "자산형성",
            "적금": "자산형성",
            "보험": "금융상품",
            "보증": "금융상품"
        }

        # 데이터 추출기 (공통 유틸리티)
        self._extractor = PolicyDataExtractor()

    # =========================================================================
    # 추상 메서드 구현
    # =========================================================================

    async def fetch_policy_list(self) -> List[str]:
        """
        정책 목록 페이지에서 개별 정책 URL 추출

        서민금융진흥원의 청년 정책 목록 페이지를 크롤링하여
        각 정책의 상세 페이지 URL을 수집합니다.

        Returns:
            List[str]: 정책 상세 페이지 URL 목록
        """
        policy_urls = []
        current_page = 1

        while current_page <= self._config.max_pages:
            # 페이지 URL 생성
            page_url = f"{self._policy_list_url}?page={current_page}"

            # 페이지 HTML 가져오기
            html = await self._fetch_page(page_url)

            if not html:
                self._logger.warning(f"페이지 로드 실패: {page_url}")
                break

            # HTML 파싱
            soup = self._parse_html(html)

            # 정책 링크 추출 (사이트 구조에 맞게 수정 필요)
            # 예시: <a class="policy-link" href="/policy/view/123">
            links = soup.select("a.policy-link, .board-list a[href*='view']")

            if not links:
                # 더 이상 정책이 없으면 종료
                self._logger.debug(f"페이지 {current_page}에서 정책을 찾을 수 없음")
                break

            # URL 추출 및 정규화
            for link in links:
                href = link.get("href", "")
                if href:
                    # 절대 URL로 변환
                    full_url = urljoin(self._config.base_url, href)

                    # 청년 관련 정책만 필터링 (공통 유틸리티 사용)
                    link_text = link.get_text().lower()
                    if self._extractor.is_youth_policy(link_text):
                        policy_urls.append(full_url)
                        self._logger.debug(f"정책 발견: {full_url}")

            current_page += 1

        # 중복 제거
        policy_urls = list(set(policy_urls))
        self._logger.info(f"총 {len(policy_urls)}개의 청년 정책 URL 수집 완료")

        return policy_urls

    async def parse_policy(
        self,
        html: str,
        url: str
    ) -> Optional[PolicyData]:
        """
        HTML에서 정책 데이터 추출

        서민금융진흥원 정책 상세 페이지의 HTML을 파싱하여
        구조화된 정책 데이터를 추출합니다.

        Args:
            html: 정책 상세 페이지 HTML
            url: 페이지 URL

        Returns:
            Optional[PolicyData]: 추출된 정책 데이터
        """
        try:
            soup = self._parse_html(html)

            # =================================================================
            # 기본 정보 추출
            # =================================================================

            # 정책명 추출
            policy_name = self._extract_text(
                soup,
                "h1.policy-title, .view-title, .board-view h2",
                "제목 없음"
            )

            # 정책 내용 추출 (임베딩 대상)
            content_parts = []

            # 요약/개요
            summary = self._extract_text(
                soup,
                ".policy-summary, .view-summary, .intro"
            )
            if summary:
                content_parts.append(f"개요: {summary}")

            # 상세 내용
            detail_content = self._extract_text(
                soup,
                ".policy-content, .view-content, .board-content"
            )
            if detail_content:
                content_parts.append(detail_content)

            # =================================================================
            # 자격 조건 추출
            # =================================================================

            eligibility = self._extract_text(
                soup,
                ".eligibility, .target-info, [class*='자격']"
            )

            # 연령 조건 추출 (공통 유틸리티 사용)
            age_min, age_max = self._extractor.extract_age_range(
                eligibility + detail_content
            )

            # 소득 조건 추출 (공통 유틸리티 사용)
            income_limit = self._extractor.extract_income_limit(
                eligibility + detail_content
            )

            # =================================================================
            # 지원 내용 추출
            # =================================================================

            benefits = self._extract_text(
                soup,
                ".benefits, .support-content, [class*='지원']"
            )
            if benefits:
                content_parts.append(f"지원내용: {benefits}")

            # =================================================================
            # 필수 서류 추출 (공통 유틸리티 사용)
            # =================================================================

            required_documents = self._extractor.extract_documents(soup)

            # =================================================================
            # 신청 기간 추출 (공통 유틸리티 사용)
            # =================================================================

            start_date, end_date = self._extractor.extract_dates(soup)

            # =================================================================
            # 카테고리 결정 (공통 유틸리티 사용)
            # =================================================================

            category = self._extractor.determine_category(
                policy_name + summary,
                self._category_mapping,
                default_category="금융상품"
            )

            # =================================================================
            # 전체 콘텐츠 조합
            # =================================================================

            full_content = f"{policy_name}\n\n" + "\n\n".join(content_parts)

            # 자격 조건 추가
            if eligibility:
                full_content += f"\n\n자격조건: {eligibility}"

            # 필수 서류 추가
            if required_documents:
                full_content += f"\n\n필수서류: {', '.join(required_documents)}"

            # =================================================================
            # PolicyData 객체 생성
            # =================================================================

            policy = PolicyData(
                policy_id=self._extractor.generate_policy_id(
                    url,
                    self._config.source_name
                ),
                policy_name=policy_name,
                category=category,
                content=full_content,
                summary=summary,
                eligibility=eligibility,
                benefits=benefits,
                required_documents=required_documents,
                application_url=url,
                official_link=url,
                start_date=start_date,
                end_date=end_date,
                target_age_min=age_min,
                target_age_max=age_max,
                income_limit=income_limit,
                location=["전국"],  # 서민금융진흥원은 전국 대상
                keywords=self._extractor.extract_keywords(
                    policy_name,
                    summary,
                    base_keywords=["청년", "서민금융"],
                    important_words=["대출", "저축", "계좌", "대환", "저금리", "지원금"]
                ),
                raw_html=html[:5000],  # 디버깅용 (처음 5000자만)
                crawled_at=datetime.now()
            )

            self._logger.debug(f"정책 파싱 완료: {policy_name}")
            return policy

        except Exception as e:
            self._logger.error(f"정책 파싱 오류 ({url}): {e}")
            return None

    # =========================================================================
    # Private 헬퍼 메서드
    # =========================================================================

    # 참고: 대부분의 데이터 추출 로직은 PolicyDataExtractor 유틸리티로 이동됨
    # (중복 코드 제거 및 재사용성 향상)
