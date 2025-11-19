#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
크롤러 팩토리 클래스 (Crawler Factory)
=============================================================================

Factory Pattern을 사용하여 크롤러 인스턴스를 생성합니다.
클라이언트 코드가 구체적인 크롤러 클래스에 의존하지 않도록 합니다.

설계 패턴:
    - Factory Method Pattern: 객체 생성 로직 캡슐화
    - Registry Pattern: 크롤러 클래스 등록 및 관리

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

from typing import Dict, Type, Optional, List
import logging

from .base_crawler import BaseCrawler, CrawlerConfig, SourceTier


class PolicyCrawlerFactory:
    """
    정책 크롤러 팩토리 클래스

    크롤러 인스턴스 생성을 중앙화하고, 새로운 크롤러 추가를
    용이하게 합니다.

    클래스 변수:
        _registry (Dict): 등록된 크롤러 클래스 레지스트리
        _configs (Dict): 사전 정의된 크롤러 설정

    Example:
        >>> # 기본 설정으로 크롤러 생성
        >>> crawler = PolicyCrawlerFactory.create('kinfa')
        >>>
        >>> # 커스텀 설정으로 크롤러 생성
        >>> custom_config = CrawlerConfig(...)
        >>> crawler = PolicyCrawlerFactory.create('kinfa', custom_config)
        >>>
        >>> # 모든 크롤러 생성
        >>> crawlers = PolicyCrawlerFactory.create_all()
    """

    # =========================================================================
    # 클래스 변수 (Class Variables)
    # =========================================================================

    # 크롤러 클래스 레지스트리
    _registry: Dict[str, Type[BaseCrawler]] = {}

    # 사전 정의된 크롤러 설정
    _configs: Dict[str, CrawlerConfig] = {}

    # 로거
    _logger = logging.getLogger(__name__)

    # =========================================================================
    # 클래스 메서드 - 레지스트리 관리
    # =========================================================================

    @classmethod
    def register(
        cls,
        name: str,
        crawler_class: Type[BaseCrawler],
        default_config: Optional[CrawlerConfig] = None
    ) -> None:
        """
        크롤러 클래스를 레지스트리에 등록

        새로운 크롤러를 시스템에 추가할 때 사용합니다.

        Args:
            name: 크롤러 식별자 (소문자)
            crawler_class: 크롤러 클래스
            default_config: 기본 설정 (선택)

        Raises:
            ValueError: 이미 등록된 이름인 경우

        Example:
            >>> PolicyCrawlerFactory.register(
            ...     'custom',
            ...     CustomCrawler,
            ...     CrawlerConfig(...)
            ... )
        """
        name = name.lower()

        if name in cls._registry:
            cls._logger.warning(f"크롤러 '{name}'이 이미 등록되어 있습니다. 덮어씁니다.")

        cls._registry[name] = crawler_class

        if default_config:
            cls._configs[name] = default_config

        cls._logger.info(f"크롤러 등록 완료: {name}")

    @classmethod
    def unregister(cls, name: str) -> None:
        """
        크롤러를 레지스트리에서 제거

        Args:
            name: 제거할 크롤러 식별자
        """
        name = name.lower()

        if name in cls._registry:
            del cls._registry[name]
            cls._logger.info(f"크롤러 제거 완료: {name}")

        if name in cls._configs:
            del cls._configs[name]

    @classmethod
    def list_registered(cls) -> List[str]:
        """
        등록된 모든 크롤러 이름 반환

        Returns:
            List[str]: 등록된 크롤러 이름 목록
        """
        return list(cls._registry.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        크롤러가 등록되어 있는지 확인

        Args:
            name: 확인할 크롤러 이름

        Returns:
            bool: 등록 여부
        """
        return name.lower() in cls._registry

    # =========================================================================
    # 클래스 메서드 - 크롤러 생성
    # =========================================================================

    @classmethod
    def create(
        cls,
        name: str,
        config: Optional[CrawlerConfig] = None
    ) -> BaseCrawler:
        """
        크롤러 인스턴스 생성

        등록된 크롤러 이름으로 인스턴스를 생성합니다.
        설정이 제공되지 않으면 기본 설정을 사용합니다.

        Args:
            name: 크롤러 식별자
            config: 크롤러 설정 (선택)

        Returns:
            BaseCrawler: 생성된 크롤러 인스턴스

        Raises:
            ValueError: 등록되지 않은 크롤러 이름인 경우

        Example:
            >>> crawler = PolicyCrawlerFactory.create('kinfa')
            >>> result = await crawler.crawl()
        """
        name = name.lower()

        # 등록 여부 확인
        if name not in cls._registry:
            available = ", ".join(cls._registry.keys())
            raise ValueError(
                f"등록되지 않은 크롤러: '{name}'. "
                f"사용 가능한 크롤러: {available}"
            )

        # 크롤러 클래스 가져오기
        crawler_class = cls._registry[name]

        # 설정 결정 (제공된 설정 > 기본 설정 > None)
        final_config = config or cls._configs.get(name)

        # 인스턴스 생성
        crawler = crawler_class(final_config)
        cls._logger.debug(f"크롤러 생성: {name}")

        return crawler

    @classmethod
    def create_all(
        cls,
        configs: Optional[Dict[str, CrawlerConfig]] = None
    ) -> Dict[str, BaseCrawler]:
        """
        등록된 모든 크롤러의 인스턴스 생성

        Args:
            configs: 크롤러별 커스텀 설정 딕셔너리 (선택)

        Returns:
            Dict[str, BaseCrawler]: 크롤러 이름과 인스턴스의 딕셔너리

        Example:
            >>> crawlers = PolicyCrawlerFactory.create_all()
            >>> for name, crawler in crawlers.items():
            ...     result = await crawler.crawl()
        """
        configs = configs or {}
        crawlers = {}

        for name in cls._registry.keys():
            config = configs.get(name)
            crawlers[name] = cls.create(name, config)

        cls._logger.info(f"총 {len(crawlers)}개 크롤러 생성 완료")
        return crawlers

    @classmethod
    def create_by_tier(
        cls,
        tier: SourceTier
    ) -> Dict[str, BaseCrawler]:
        """
        특정 신뢰도 등급의 크롤러만 생성

        Args:
            tier: 데이터 소스 신뢰도 등급

        Returns:
            Dict[str, BaseCrawler]: 해당 등급의 크롤러 딕셔너리

        Example:
            >>> tier1_crawlers = PolicyCrawlerFactory.create_by_tier(
            ...     SourceTier.TIER_1
            ... )
        """
        crawlers = {}

        for name in cls._registry.keys():
            config = cls._configs.get(name)
            if config and config.source_tier == tier:
                crawlers[name] = cls.create(name)

        return crawlers


# =============================================================================
# 기본 크롤러 등록 (자동 실행)
# =============================================================================

def _register_default_crawlers():
    """
    기본 크롤러들을 팩토리에 등록

    모듈 로드 시 자동으로 실행됩니다.
    """
    # 순환 임포트 방지를 위해 여기서 임포트
    from .kinfa_crawler import KinfaCrawler

    # ==========================================================================
    # Tier 1 크롤러 (공식 출처)
    # ==========================================================================

    # 1. 서민금융진흥원
    PolicyCrawlerFactory.register(
        'kinfa',
        KinfaCrawler,
        CrawlerConfig(
            base_url="https://www.kinfa.or.kr",
            source_name="서민금융진흥원",
            source_tier=SourceTier.TIER_1,
            request_delay=2.0,
            max_pages=5
        )
    )

    # 2. 복지로 (구현 필요)
    # PolicyCrawlerFactory.register(
    #     'bokjiro',
    #     BokjiroCrawler,
    #     CrawlerConfig(
    #         base_url="https://www.bokjiro.go.kr",
    #         source_name="복지로",
    #         source_tier=SourceTier.TIER_1,
    #         request_delay=2.0,
    #         max_pages=10
    #     )
    # )

    # 3. 청년정책 (OnStop) (구현 필요)
    # PolicyCrawlerFactory.register(
    #     'youthcenter',
    #     YouthCenterCrawler,
    #     CrawlerConfig(
    #         base_url="https://www.youthcenter.go.kr",
    #         source_name="온통청년",
    #         source_tier=SourceTier.TIER_1,
    #         request_delay=1.5,
    #         max_pages=20
    #     )
    # )


# 모듈 로드 시 기본 크롤러 등록
_register_default_crawlers()
