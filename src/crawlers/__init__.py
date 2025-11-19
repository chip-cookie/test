#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
청년 정책 웹 크롤링 패키지 (Youth Policy Web Crawling Package)
=============================================================================

이 패키지는 정부 공식 사이트에서 청년 정책 데이터를 자동으로 수집하는
크롤러 시스템을 제공합니다.

주요 컴포넌트:
    - BaseCrawler: 모든 크롤러의 추상 기본 클래스
    - PolicyCrawlerFactory: 크롤러 인스턴스 생성 팩토리
    - CrawlerScheduler: 정기적인 크롤링 스케줄러
    - DataPipeline: 수집 데이터 처리 파이프라인

디자인 패턴:
    - Factory Pattern: 크롤러 인스턴스 생성
    - Strategy Pattern: 사이트별 크롤링 전략
    - Template Method Pattern: 크롤링 프로세스 표준화
    - Observer Pattern: 크롤링 이벤트 알림

사용 예시:
    >>> from src.crawlers import PolicyCrawlerFactory, CrawlerScheduler
    >>>
    >>> # 특정 사이트 크롤러 생성
    >>> crawler = PolicyCrawlerFactory.create('kinfa')
    >>> policies = await crawler.crawl()
    >>>
    >>> # 스케줄러를 통한 자동 크롤링
    >>> scheduler = CrawlerScheduler()
    >>> scheduler.add_job('kinfa', cron='0 6 * * *')  # 매일 오전 6시
    >>> scheduler.start()

Author: Youth Policy System Team
Version: 1.0.0
License: MIT
=============================================================================
"""

# 버전 정보
__version__ = '1.0.0'
__author__ = 'Youth Policy System Team'

# 공개 API 정의
from .base_crawler import BaseCrawler, CrawlerConfig, CrawlResult
from .factory import PolicyCrawlerFactory
from .scheduler import CrawlerScheduler
from .pipeline import DataPipeline

# 개별 크롤러 (필요시 직접 임포트)
from .kinfa_crawler import KinfaCrawler
from .bokjiro_crawler import BokjiroCrawler
from .youth_center_crawler import YouthCenterCrawler

__all__ = [
    # 핵심 클래스
    'BaseCrawler',
    'CrawlerConfig',
    'CrawlResult',
    'PolicyCrawlerFactory',
    'CrawlerScheduler',
    'DataPipeline',

    # 개별 크롤러
    'KinfaCrawler',
    'BokjiroCrawler',
    'YouthCenterCrawler',
]
