#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
크롤러 → SQLite 어댑터 (Crawler Adapter)
=============================================================================

크롤러의 PolicyData를 SQLAlchemy ORM 모델로 변환하여
SQLite에 저장합니다.

Author: Youth Policy System Team
Version: 2.0.0 (MVP)
=============================================================================
"""

import json
import logging
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..crawlers.base_crawler import PolicyData, CrawlResult
from .models import Policy
from .repository import PolicyRepository


logger = logging.getLogger(__name__)


class CrawlerAdapter:
    """
    크롤러 데이터를 SQLite에 저장하는 어댑터

    크롤러의 PolicyData 객체를 ORM 모델로 변환하고
    중복 검사, 업데이트 등을 처리합니다.
    """

    def __init__(self, db: Session):
        """
        Args:
            db: SQLAlchemy 세션
        """
        self.db = db
        self.repo = PolicyRepository(db)

    def policy_data_to_dict(self, policy_data: PolicyData) -> Dict[str, Any]:
        """
        PolicyData를 ORM 모델용 딕셔너리로 변환

        Args:
            policy_data: 크롤러의 PolicyData 객체

        Returns:
            Dict: ORM 모델에 전달할 데이터
        """
        return {
            "policy_id": policy_data.policy_id,
            "policy_name": policy_data.policy_name,
            "category": policy_data.category,
            "content": policy_data.content,
            "summary": policy_data.summary,

            # 자격 조건
            "eligibility": policy_data.eligibility,
            "target_age_min": policy_data.target_age_min,
            "target_age_max": policy_data.target_age_max,
            "income_limit": policy_data.income_limit,

            # 지원 내용
            "benefits": policy_data.benefits,
            "required_documents": policy_data.required_documents,  # List → JSON

            # URL 및 소스
            "application_url": policy_data.application_url,
            "official_link": policy_data.official_link,
            "source_name": policy_data.source_name,
            "source_tier": policy_data.source_tier.value if policy_data.source_tier else "Tier 2",

            # 날짜
            "start_date": self._parse_date(policy_data.start_date),
            "end_date": self._parse_date(policy_data.end_date),
            "crawled_at": policy_data.crawled_at or datetime.now(),

            # 검색 최적화
            "keywords": policy_data.keywords,  # List → JSON
            "location": policy_data.location,  # List → JSON

            # 상태
            "is_active": True,
            "view_count": 0,
        }

    def _parse_date(self, date_str: str) -> datetime:
        """
        날짜 문자열을 datetime 객체로 변환

        Args:
            date_str: 날짜 문자열 ("YYYY-MM-DD" 형식)

        Returns:
            datetime: 변환된 datetime 객체 또는 None
        """
        if not date_str:
            return None

        try:
            # "YYYY-MM-DD" 형식
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                # "YYYY.MM.DD" 형식
                return datetime.strptime(date_str, "%Y.%m.%d")
            except ValueError:
                logger.warning(f"날짜 파싱 실패: {date_str}")
                return None

    def save_policy(self, policy_data: PolicyData, update_if_exists: bool = True) -> Policy:
        """
        단일 정책 저장

        Args:
            policy_data: 크롤러의 PolicyData 객체
            update_if_exists: 이미 존재하면 업데이트 여부

        Returns:
            Policy: 저장된 정책 ORM 객체

        Example:
            >>> adapter = CrawlerAdapter(db)
            >>> policy = await crawler.parse_policy(html, url)
            >>> saved = adapter.save_policy(policy)
        """
        # 기존 정책 확인
        existing = self.repo.get_by_policy_id(policy_data.policy_id)

        if existing:
            if update_if_exists:
                # 업데이트
                data = self.policy_data_to_dict(policy_data)
                data["updated_at"] = datetime.now()
                updated = self.repo.update(existing.id, data)
                logger.info(f"정책 업데이트: {policy_data.policy_name} ({policy_data.policy_id})")
                return updated
            else:
                logger.debug(f"정책 이미 존재 (스킵): {policy_data.policy_id}")
                return existing

        # 새로 생성
        data = self.policy_data_to_dict(policy_data)
        try:
            policy = self.repo.create(data)
            logger.info(f"정책 저장 완료: {policy_data.policy_name} ({policy_data.policy_id})")
            return policy
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"정책 저장 실패 (무결성 오류): {policy_data.policy_id} - {e}")
            return None

    def save_policies_bulk(
        self,
        policies_data: List[PolicyData],
        update_if_exists: bool = False
    ) -> Dict[str, int]:
        """
        여러 정책 일괄 저장

        Args:
            policies_data: PolicyData 리스트
            update_if_exists: 이미 존재하면 업데이트 여부

        Returns:
            Dict: 저장 결과 통계
                - created: 새로 생성된 수
                - updated: 업데이트된 수
                - skipped: 스킵된 수
                - failed: 실패한 수

        Example:
            >>> result = await crawler.crawl()
            >>> stats = adapter.save_policies_bulk(result.policies)
            >>> print(f"생성: {stats['created']}, 업데이트: {stats['updated']}")
        """
        stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0
        }

        for policy_data in policies_data:
            try:
                # 기존 정책 확인
                existing = self.repo.get_by_policy_id(policy_data.policy_id)

                if existing:
                    if update_if_exists:
                        # 업데이트
                        data = self.policy_data_to_dict(policy_data)
                        data["updated_at"] = datetime.now()
                        self.repo.update(existing.id, data)
                        stats["updated"] += 1
                    else:
                        stats["skipped"] += 1
                else:
                    # 새로 생성
                    data = self.policy_data_to_dict(policy_data)
                    self.repo.create(data)
                    stats["created"] += 1

            except Exception as e:
                logger.error(f"정책 저장 실패: {policy_data.policy_id} - {e}")
                stats["failed"] += 1

        logger.info(
            f"일괄 저장 완료 - "
            f"생성: {stats['created']}, "
            f"업데이트: {stats['updated']}, "
            f"스킵: {stats['skipped']}, "
            f"실패: {stats['failed']}"
        )

        return stats

    def save_crawl_result(
        self,
        crawl_result: CrawlResult,
        update_if_exists: bool = False
    ) -> Dict[str, int]:
        """
        크롤링 결과 전체 저장

        Args:
            crawl_result: 크롤러의 CrawlResult 객체
            update_if_exists: 이미 존재하면 업데이트 여부

        Returns:
            Dict: 저장 결과 통계

        Example:
            >>> result = await crawler.crawl()
            >>> stats = adapter.save_crawl_result(result)
        """
        logger.info(
            f"크롤링 결과 저장 시작 - "
            f"소스: {crawl_result.source_name}, "
            f"정책 수: {crawl_result.total_policies}"
        )

        stats = self.save_policies_bulk(crawl_result.policies, update_if_exists)

        logger.info(
            f"크롤링 결과 저장 완료 - "
            f"소스: {crawl_result.source_name}, "
            f"성공: {stats['created'] + stats['updated']}/{crawl_result.total_policies}"
        )

        return stats
