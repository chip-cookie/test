#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
온통청년 크롤러 (Youth Center Crawler) - 플레이스홀더
=============================================================================

온통청년(https://www.youthcenter.go.kr) 웹사이트 크롤러입니다.

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

from typing import List, Optional
from .base_crawler import BaseCrawler, CrawlerConfig, PolicyData, SourceTier


class YouthCenterCrawler(BaseCrawler):
    """온통청년 정책 크롤러 (구현 필요)"""

    def __init__(self, config: Optional[CrawlerConfig] = None):
        if config is None:
            config = CrawlerConfig(
                base_url="https://www.youthcenter.go.kr",
                source_name="온통청년",
                source_tier=SourceTier.TIER_1,
                request_delay=1.5,
                max_pages=20
            )
        super().__init__(config)

    async def fetch_policy_list(self) -> List[str]:
        """정책 목록 URL 수집 (구현 필요)"""
        self._logger.warning("YouthCenterCrawler.fetch_policy_list() 미구현")
        return []

    async def parse_policy(self, html: str, url: str) -> Optional[PolicyData]:
        """정책 데이터 파싱 (구현 필요)"""
        self._logger.warning("YouthCenterCrawler.parse_policy() 미구현")
        return None
