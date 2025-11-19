#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
복지로 크롤러 (Bokjiro Crawler)
=============================================================================

복지로(https://www.bokjiro.go.kr) 웹사이트에서
청년 복지 정책 정보를 크롤링합니다.

Tier 1 정부 공식 데이터 소스입니다.

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import re
import json
from typing import List, Optional
from datetime import datetime
from urllib.parse import urljoin, urlencode

from .base_crawler import BaseCrawler, CrawlerConfig, PolicyData, SourceTier


class BokjiroCrawler(BaseCrawler):
    """
    복지로 정책 크롤러

    복지로 웹사이트에서 청년 대상 복지 정책을 수집합니다.
    """

    def __init__(self, config: Optional[CrawlerConfig] = None):
        if config is None:
            config = CrawlerConfig(
                base_url="https://www.bokjiro.go.kr",
                source_name="복지로",
                source_tier=SourceTier.TIER_1,
                request_delay=2.5,
                max_pages=10,
                timeout=45
            )
        super().__init__(config)

        self._list_url = urljoin(
            self._config.base_url,
            "/ssis-tbu/twataa/wlfareInfo/selectWlfareInfo.do"
        )
        self._detail_url = urljoin(
            self._config.base_url,
            "/ssis-tbu/twataa/wlfareInfo/selectWlfareInfoDetail.do"
        )
        self._category_mapping = {
            "주거": "주거", "생활": "생활지원", "고용": "취업",
            "교육": "교육", "건강": "건강", "창업": "창업"
        }
        self._youth_keywords = ["청년", "청소년", "대학생", "취준생", "사회초년생"]

    async def fetch_policy_list(self) -> List[str]:
        """정책 목록 URL 수집"""
        policy_urls = []
        current_page = 1

        while current_page <= self._config.max_pages:
            try:
                params = {
                    "page": current_page, "rows": 20,
                    "searchKeyword": "청년", "lifeArray": "004"
                }
                page_url = f"{self._list_url}?{urlencode(params)}"
                html = await self._fetch_page(page_url)

                if not html:
                    break

                soup = self._parse_html(html)
                items = soup.select(
                    ".policy-list-item, .welfare-list li, "
                    "tr[data-wlfare-info-id], .list-item[data-id]"
                )

                if not items:
                    items = self._extract_from_json(html)

                if not items:
                    break

                for item in items:
                    policy_id = self._extract_policy_id(item)
                    if policy_id:
                        detail_url = f"{self._detail_url}?wlfareInfoId={policy_id}"
                        item_text = (
                            item.get_text() if hasattr(item, 'get_text')
                            else str(item)
                        )
                        if self._is_youth_policy(item_text):
                            policy_urls.append(detail_url)

                current_page += 1

            except Exception as e:
                self._logger.error(f"목록 페이지 처리 오류: {e}")
                break

        return list(set(policy_urls))

    async def parse_policy(self, html: str, url: str) -> Optional[PolicyData]:
        """정책 데이터 파싱"""
        try:
            soup = self._parse_html(html)

            policy_name = self._extract_text(
                soup, "h1.policy-title, .detail-title, .tit", "제목 없음"
            )
            summary = self._extract_text(soup, ".policy-summary, .intro-text")

            content_parts = [f"정책명: {policy_name}"]
            if summary:
                content_parts.append(f"요약: {summary}")

            target = self._extract_text(soup, ".support-target, [class*='대상']")
            benefits = self._extract_text(soup, ".support-content, [class*='지원내용']")

            if target:
                content_parts.append(f"지원대상: {target}")
            if benefits:
                content_parts.append(f"지원내용: {benefits}")

            age_min, age_max = self._extract_age_range(target + soup.get_text())
            income_limit = self._extract_income_limit(target)
            required_documents = self._extract_documents(soup)
            start_date, end_date = self._extract_dates(soup)
            category = self._determine_category(policy_name + summary)

            return PolicyData(
                policy_id=self._generate_policy_id(url),
                policy_name=policy_name,
                category=category,
                content="\n\n".join(content_parts),
                summary=summary,
                eligibility=target,
                benefits=benefits,
                required_documents=required_documents,
                application_url=url,
                official_link=url,
                start_date=start_date,
                end_date=end_date,
                target_age_min=age_min,
                target_age_max=age_max,
                income_limit=income_limit,
                location=["전국"],
                keywords=["청년", "복지", category],
                raw_html=html[:3000],
                crawled_at=datetime.now()
            )
        except Exception as e:
            self._logger.error(f"파싱 오류 ({url}): {e}")
            return None

    def _extract_policy_id(self, item) -> Optional[str]:
        """정책 ID 추출"""
        if hasattr(item, 'get'):
            policy_id = item.get('data-wlfare-info-id') or item.get('data-id')
            if policy_id:
                return policy_id
            link = item.select_one('a[href]')
            if link:
                match = re.search(r'wlfareInfoId=(\w+)', link.get('href', ''))
                if match:
                    return match.group(1)
        elif isinstance(item, dict):
            return item.get('wlfareInfoId') or item.get('id')
        return None

    def _extract_from_json(self, html: str) -> List[dict]:
        """JSON에서 정책 목록 추출"""
        try:
            if html.strip().startswith(('{', '[')):
                data = json.loads(html)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get('list') or data.get('data') or []
        except json.JSONDecodeError:
            pass
        return []

    def _is_youth_policy(self, text: str) -> bool:
        """청년 정책 여부 확인"""
        return any(kw in text.lower() for kw in self._youth_keywords)

    def _determine_category(self, text: str) -> str:
        """카테고리 결정"""
        for kw, cat in self._category_mapping.items():
            if kw in text:
                return cat
        return "생활지원"

    def _extract_age_range(self, text: str) -> tuple:
        """연령 범위 추출"""
        match = re.search(r'(\d{1,2})\s*[~-]\s*(\d{1,2})\s*세', text)
        if match:
            return int(match.group(1)), int(match.group(2))
        return 19, 34

    def _extract_income_limit(self, text: str) -> Optional[int]:
        """소득 제한 추출"""
        match = re.search(r'중위소득\s*(\d+)\s*%', text)
        if match:
            return int(match.group(1)) * 500000
        return None

    def _extract_documents(self, soup) -> List[str]:
        """필수 서류 추출"""
        items = soup.select(".document-list li, [class*='서류'] li")
        if items:
            return [i.get_text().strip() for i in items if i.get_text().strip()][:10]
        text = soup.get_text()
        docs = ["신분증", "주민등록등본", "소득증명서", "재직증명서"]
        return [d for d in docs if d in text]

    def _extract_dates(self, soup) -> tuple:
        """신청 기간 추출"""
        dates = re.findall(r'(\d{4})[.\-년](\d{1,2})[.\-월](\d{1,2})', soup.get_text())
        if dates:
            d = dates[0]
            start = f"{d[0]}-{int(d[1]):02d}-{int(d[2]):02d}"
            end = None
            if len(dates) > 1:
                d = dates[1]
                end = f"{d[0]}-{int(d[1]):02d}-{int(d[2]):02d}"
            return start, end
        return None, None
