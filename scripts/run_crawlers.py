#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
크롤러 실행 스크립트
=============================================================================

모든 크롤러를 실행하고 데이터를 Vector DB에 적재합니다.

사용법:
    python scripts/run_crawlers.py                    # 전체 크롤링
    python scripts/run_crawlers.py --source kinfa     # 특정 소스만
    python scripts/run_crawlers.py --dry-run          # 테스트 실행

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawlers import (
    PolicyCrawlerFactory,
    BaseCrawler,
    CrawlResult,
    PolicyData
)
from src.vectordb.qdrant_client import QdrantVectorDB
from src.monitoring import MetricsCollector, AlertManager, AlertConfig, AlertLevel


# =============================================================================
# 설정
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'logs/crawler_{datetime.now().strftime("%Y%m%d")}.log')
    ]
)

logger = logging.getLogger(__name__)


# =============================================================================
# 메인 크롤러 실행기
# =============================================================================

class CrawlerRunner:
    """
    크롤러 실행 및 데이터 적재 관리자

    Example:
        >>> runner = CrawlerRunner()
        >>> await runner.run_all()
    """

    def __init__(
        self,
        vector_db: QdrantVectorDB = None,
        metrics: MetricsCollector = None,
        alert_manager: AlertManager = None
    ):
        self.vector_db = vector_db
        self.metrics = metrics or MetricsCollector()
        self.alert_manager = alert_manager

        self.results: Dict[str, CrawlResult] = {}

    async def run_all(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        모든 크롤러 실행

        Args:
            dry_run: True면 DB 적재 없이 테스트만

        Returns:
            Dict: 실행 결과 요약
        """
        crawlers = PolicyCrawlerFactory.get_all_crawlers()
        total_policies = 0
        total_errors = 0

        logger.info(f"크롤링 시작: {len(crawlers)}개 소스")

        for crawler in crawlers:
            try:
                result = await self._run_single_crawler(crawler)
                self.results[crawler.source_name] = result

                total_policies += result.total_count
                total_errors += result.error_count

                # Vector DB 적재
                if not dry_run and result.success and self.vector_db:
                    await self._load_to_vector_db(result)

            except Exception as e:
                logger.error(f"{crawler.source_name} 크롤링 실패: {e}")
                total_errors += 1

                if self.alert_manager:
                    self.alert_manager.send(
                        AlertLevel.ERROR,
                        f"크롤링 실패: {crawler.source_name}",
                        str(e)
                    )

        # 메트릭스 기록
        self.metrics.increment("crawl_runs_total")
        self.metrics.set_gauge("policies_crawled", total_policies)
        self.metrics.set_gauge("crawl_errors", total_errors)

        summary = {
            "total_sources": len(crawlers),
            "total_policies": total_policies,
            "total_errors": total_errors,
            "results": {
                name: {
                    "count": r.total_count,
                    "errors": r.error_count,
                    "duration": r.duration_seconds
                }
                for name, r in self.results.items()
            }
        }

        logger.info(f"크롤링 완료: {total_policies}개 정책, {total_errors}개 오류")

        return summary

    async def run_source(
        self,
        source_name: str,
        dry_run: bool = False
    ) -> CrawlResult:
        """
        특정 소스만 크롤링

        Args:
            source_name: 소스 이름 (kinfa, bokjiro, youth_center)
            dry_run: 테스트 실행

        Returns:
            CrawlResult: 크롤링 결과
        """
        crawler = PolicyCrawlerFactory.create(source_name)

        if not crawler:
            raise ValueError(f"알 수 없는 소스: {source_name}")

        result = await self._run_single_crawler(crawler)

        if not dry_run and result.success and self.vector_db:
            await self._load_to_vector_db(result)

        return result

    async def _run_single_crawler(self, crawler: BaseCrawler) -> CrawlResult:
        """단일 크롤러 실행"""
        logger.info(f"크롤링 시작: {crawler.source_name}")

        start_time = datetime.now()
        result = await crawler.crawl()

        logger.info(
            f"크롤링 완료: {crawler.source_name} - "
            f"{result.total_count}개 정책, "
            f"{result.duration_seconds:.2f}초"
        )

        return result

    async def _load_to_vector_db(self, result: CrawlResult) -> int:
        """
        크롤링 결과를 Vector DB에 적재

        Args:
            result: 크롤링 결과

        Returns:
            int: 적재된 문서 수
        """
        if not self.vector_db:
            logger.warning("Vector DB가 설정되지 않음")
            return 0

        loaded = 0

        for policy in result.policies:
            try:
                # Vector DB 포맷으로 변환
                doc = {
                    "id": policy.policy_id,
                    "content": policy.content,
                    "metadata": {
                        "policy_name": policy.policy_name,
                        "category": policy.category,
                        "source_tier": "Tier 1",
                        "target_age_min": policy.target_age_min,
                        "target_age_max": policy.target_age_max,
                        "income_limit": policy.income_limit,
                        "location": policy.location,
                        "official_link": policy.official_link,
                        "keywords": policy.keywords
                    }
                }

                await self.vector_db.upsert(doc)
                loaded += 1

            except Exception as e:
                logger.error(f"Vector DB 적재 실패 ({policy.policy_id}): {e}")

        logger.info(f"Vector DB 적재 완료: {loaded}/{len(result.policies)}")
        return loaded


# =============================================================================
# CLI 인터페이스
# =============================================================================

async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="청년 정책 크롤러 실행"
    )

    parser.add_argument(
        "--source",
        type=str,
        choices=["kinfa", "bokjiro", "youth_center", "all"],
        default="all",
        help="크롤링할 소스 (기본: all)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="테스트 실행 (DB 적재 없음)"
    )

    parser.add_argument(
        "--qdrant-url",
        type=str,
        default="http://localhost:6333",
        help="Qdrant 서버 URL"
    )

    parser.add_argument(
        "--collection",
        type=str,
        default="youth-policy-kb",
        help="Qdrant 컬렉션 이름"
    )

    args = parser.parse_args()

    # 로그 디렉토리 생성
    os.makedirs("logs", exist_ok=True)

    # Vector DB 연결 (dry-run이 아닌 경우)
    vector_db = None
    if not args.dry_run:
        try:
            vector_db = QdrantVectorDB(
                url=args.qdrant_url,
                collection_name=args.collection
            )
            await vector_db.connect()
            logger.info(f"Qdrant 연결: {args.qdrant_url}")
        except Exception as e:
            logger.warning(f"Qdrant 연결 실패: {e}")

    # 크롤러 실행
    runner = CrawlerRunner(vector_db=vector_db)

    try:
        if args.source == "all":
            result = await runner.run_all(dry_run=args.dry_run)
        else:
            result = await runner.run_source(args.source, dry_run=args.dry_run)

        # 결과 출력
        print("\n" + "=" * 50)
        print("크롤링 결과 요약")
        print("=" * 50)

        if isinstance(result, dict):
            print(f"총 소스: {result['total_sources']}")
            print(f"총 정책: {result['total_policies']}")
            print(f"총 오류: {result['total_errors']}")

            print("\n소스별 결과:")
            for name, data in result.get('results', {}).items():
                print(f"  - {name}: {data['count']}개, {data['duration']:.1f}초")
        else:
            print(f"정책 수: {result.total_count}")
            print(f"오류 수: {result.error_count}")
            print(f"소요 시간: {result.duration_seconds:.1f}초")

    finally:
        if vector_db:
            await vector_db.close()


# =============================================================================
# 실행
# =============================================================================

if __name__ == "__main__":
    asyncio.run(main())
