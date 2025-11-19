#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
복지로 크롤러 (Bokjiro Crawler) - 플레이스홀더
=============================================================================

복지로(https://www.bokjiro.go.kr) 웹사이트 크롤러입니다.
실제 구현 시 사이트 구조에 맞게 parse_policy 메서드를 구현해야 합니다.

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

from typing import List, Optional
from .base_crawler import BaseCrawler, CrawlerConfig, PolicyData, SourceTier


class BokjiroCrawler(BaseCrawler):
    """복지로 정책 크롤러 (구현 필요)"""

    def __init__(self, config: Optional[CrawlerConfig] = None):
        if config is None:
            config = CrawlerConfig(
                base_url="https://www.bokjiro.go.kr",
                source_name="복지로",
                source_tier=SourceTier.TIER_1,
                request_delay=2.0,
                max_pages=10
            )
        super().__init__(config)

    async def fetch_policy_list(self) -> List[str]:
        """정책 목록 URL 수집 (구현 필요)"""
        # TODO: 복지로 사이트 구조에 맞게 구현
        self._logger.warning("BokjiroCrawler.fetch_policy_list() 미구현")
        return []

    async def parse_policy(self, html: str, url: str) -> Optional[PolicyData]:
        """정책 데이터 파싱 (구현 필요)"""
        # TODO: 복지로 사이트 구조에 맞게 구현
        self._logger.warning("BokjiroCrawler.parse_policy() 미구현")
        return None
