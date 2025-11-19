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

                    # 청년 관련 정책만 필터링
                    link_text = link.get_text().lower()
                    if self._is_youth_policy(link_text):
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

            # 연령 조건 추출
            age_min, age_max = self._extract_age_range(eligibility + detail_content)

            # 소득 조건 추출
            income_limit = self._extract_income_limit(eligibility + detail_content)

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
            # 필수 서류 추출
            # =================================================================

            required_documents = self._extract_documents(soup)

            # =================================================================
            # 신청 기간 추출
            # =================================================================

            start_date, end_date = self._extract_dates(soup)

            # =================================================================
            # 카테고리 결정
            # =================================================================

            category = self._determine_category(policy_name + summary)

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
                policy_id=self._generate_policy_id(url),
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
                keywords=self._extract_keywords(policy_name, summary),
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

    def _is_youth_policy(self, text: str) -> bool:
        """
        청년 관련 정책인지 확인

        Args:
            text: 확인할 텍스트

        Returns:
            bool: 청년 정책 여부
        """
        youth_keywords = [
            "청년", "youth", "대학생", "사회초년생",
            "취준생", "19세", "34세", "39세"
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in youth_keywords)

    def _determine_category(self, text: str) -> str:
        """
        텍스트에서 정책 카테고리 결정

        Args:
            text: 분석할 텍스트

        Returns:
            str: 정책 카테고리
        """
        for keyword, category in self._category_mapping.items():
            if keyword in text:
                return category
        return "금융상품"  # 기본값

    def _extract_age_range(self, text: str) -> tuple:
        """
        텍스트에서 연령 범위 추출

        Args:
            text: 분석할 텍스트

        Returns:
            tuple: (최소 연령, 최대 연령)
        """
        # 패턴 예시: "만 19세 ~ 34세", "19~34세"
        patterns = [
            r'만?\s*(\d{1,2})\s*세?\s*[~-]\s*(\d{1,2})\s*세',
            r'(\d{1,2})\s*[~-]\s*(\d{1,2})\s*세',
            r'만\s*(\d{1,2})\s*세\s*이하',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return int(groups[0]), int(groups[1])
                elif len(groups) == 1:
                    return 19, int(groups[0])  # 기본 최소 19세

        # 기본값 (청년 기준)
        return 19, 34

    def _extract_income_limit(self, text: str) -> Optional[int]:
        """
        텍스트에서 소득 제한 추출

        Args:
            text: 분석할 텍스트

        Returns:
            Optional[int]: 소득 제한 (원 단위)
        """
        # 패턴 예시: "연소득 5,000만원", "연 5천만원"
        patterns = [
            r'연\s*소득\s*(\d{1,2}),?(\d{3})\s*만\s*원',
            r'(\d{1,2})\s*천\s*만\s*원',
            r'소득\s*(\d{1,2}),?(\d{3})\s*만',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    # "5,000만원" 형태
                    amount = int(groups[0]) * 1000 + int(groups[1])
                    return amount * 10000
                elif len(groups) == 1:
                    # "5천만원" 형태
                    return int(groups[0]) * 10000000

        return None

    def _extract_documents(self, soup) -> List[str]:
        """
        필수 서류 목록 추출

        Args:
            soup: BeautifulSoup 객체

        Returns:
            List[str]: 필수 서류 목록
        """
        # 서류 관련 섹션 찾기
        documents = []

        # 리스트 형태로 된 서류 목록
        doc_lists = soup.select(
            ".documents li, .required-docs li, "
            "[class*='서류'] li, .doc-list li"
        )

        if doc_lists:
            documents = [
                li.get_text().strip()
                for li in doc_lists
                if li.get_text().strip()
            ]
        else:
            # 텍스트에서 서류 추출
            text = soup.get_text()
            common_docs = [
                "신분증", "주민등록등본", "소득증명", "재직증명서",
                "원천징수영수증", "사업자등록증", "통장사본"
            ]
            documents = [doc for doc in common_docs if doc in text]

        return documents[:10]  # 최대 10개

    def _extract_dates(self, soup) -> tuple:
        """
        신청 기간 추출

        Args:
            soup: BeautifulSoup 객체

        Returns:
            tuple: (시작일, 종료일)
        """
        # 날짜 패턴: "2025.01.01", "2025-01-01", "2025년 1월 1일"
        date_pattern = r'(\d{4})[.\-년]\s*(\d{1,2})[.\-월]\s*(\d{1,2})'

        text = soup.get_text()
        dates = re.findall(date_pattern, text)

        start_date = None
        end_date = None

        if dates:
            # 첫 번째 날짜를 시작일로
            d = dates[0]
            start_date = f"{d[0]}-{int(d[1]):02d}-{int(d[2]):02d}"

            # 두 번째 날짜를 종료일로
            if len(dates) > 1:
                d = dates[1]
                end_date = f"{d[0]}-{int(d[1]):02d}-{int(d[2]):02d}"

        return start_date, end_date

    def _extract_keywords(
        self,
        policy_name: str,
        summary: str
    ) -> List[str]:
        """
        검색 키워드 추출

        Args:
            policy_name: 정책명
            summary: 정책 요약

        Returns:
            List[str]: 키워드 목록
        """
        # 기본 키워드
        keywords = ["청년", "서민금융"]

        # 정책명에서 키워드 추출
        name_keywords = [
            word for word in policy_name.split()
            if len(word) >= 2 and not word.isdigit()
        ]
        keywords.extend(name_keywords[:3])

        # 주요 키워드 추가
        text = policy_name + " " + summary
        important_words = ["대출", "저축", "계좌", "대환", "저금리", "지원금"]
        keywords.extend([w for w in important_words if w in text])

        # 중복 제거 및 반환
        return list(set(keywords))[:10]
