#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
기본 크롤러 추상 클래스 (Base Crawler Abstract Class)
=============================================================================

모든 정책 크롤러가 상속해야 하는 추상 기본 클래스입니다.
Template Method 패턴을 사용하여 크롤링 프로세스를 표준화합니다.

설계 원칙:
    - SOLID 원칙 준수
    - 캡슐화를 통한 내부 구현 은닉
    - 확장에는 열려있고, 수정에는 닫혀있는 구조 (OCP)
    - 의존성 역전 원칙 (DIP) 적용

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup


# =============================================================================
# 열거형 정의 (Enumerations)
# =============================================================================

class CrawlerStatus(Enum):
    """
    크롤러 실행 상태를 나타내는 열거형

    크롤러의 현재 상태를 추적하고 모니터링하는 데 사용됩니다.
    """
    IDLE = "idle"                    # 대기 상태
    RUNNING = "running"              # 실행 중
    COMPLETED = "completed"          # 완료
    FAILED = "failed"                # 실패
    PAUSED = "paused"                # 일시정지
    RATE_LIMITED = "rate_limited"    # 요청 제한 상태


class SourceTier(Enum):
    """
    데이터 소스의 신뢰도 등급

    Tier 1: 정부 공식 사이트 (최고 신뢰도)
    Tier 2: 비공식 출처 (참고용)
    """
    TIER_1 = "Tier 1"
    TIER_2 = "Tier 2"


# =============================================================================
# 데이터 클래스 정의 (Data Classes)
# =============================================================================

@dataclass(frozen=True)
class CrawlerConfig:
    """
    크롤러 설정을 담는 불변 데이터 클래스

    크롤러의 동작 방식을 세부적으로 제어하는 설정값들을 캡슐화합니다.
    frozen=True로 불변성을 보장하여 실행 중 설정 변경을 방지합니다.

    Attributes:
        base_url (str): 크롤링 대상 사이트의 기본 URL
        source_name (str): 데이터 소스의 이름 (예: '서민금융진흥원')
        source_tier (SourceTier): 데이터 소스의 신뢰도 등급
        request_delay (float): 요청 간 지연 시간 (초), 서버 부하 방지용
        max_retries (int): 요청 실패 시 최대 재시도 횟수
        timeout (int): HTTP 요청 타임아웃 (초)
        max_pages (int): 크롤링할 최대 페이지 수 (0 = 무제한)
        user_agent (str): HTTP 요청에 사용할 User-Agent 헤더
        headers (Dict): 추가 HTTP 헤더
        proxy (Optional[str]): 프록시 서버 URL (필요시)

    Example:
        >>> config = CrawlerConfig(
        ...     base_url="https://www.kinfa.or.kr",
        ...     source_name="서민금융진흥원",
        ...     source_tier=SourceTier.TIER_1,
        ...     request_delay=2.0
        ... )
    """
    base_url: str
    source_name: str
    source_tier: SourceTier
    request_delay: float = 1.0
    max_retries: int = 3
    timeout: int = 30
    max_pages: int = 10
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    headers: Dict[str, str] = field(default_factory=dict)
    proxy: Optional[str] = None


@dataclass
class PolicyData:
    """
    단일 정책 데이터를 담는 데이터 클래스

    크롤링된 개별 정책 정보를 구조화하여 저장합니다.
    Vector DB에 삽입하기 전 중간 데이터 형태로 사용됩니다.

    Attributes:
        policy_id (str): 정책 고유 식별자
        policy_name (str): 정책명
        category (str): 정책 카테고리 (대출, 자산형성, 주거 등)
        content (str): 정책 전체 내용 (임베딩 대상)
        summary (str): 정책 요약
        eligibility (str): 자격 조건
        benefits (str): 지원 내용/혜택
        required_documents (List[str]): 필수 서류 목록
        application_url (str): 신청 페이지 URL
        official_link (str): 공식 정보 페이지 URL
        start_date (Optional[str]): 신청 시작일
        end_date (Optional[str]): 신청 종료일
        target_age_min (Optional[int]): 최소 연령
        target_age_max (Optional[int]): 최대 연령
        income_limit (Optional[int]): 소득 제한 (원)
        location (List[str]): 지역 제한
        keywords (List[str]): 검색 키워드
        raw_html (str): 원본 HTML (디버깅용)
        crawled_at (datetime): 크롤링 시각
    """
    policy_id: str
    policy_name: str
    category: str
    content: str
    summary: str = ""
    eligibility: str = ""
    benefits: str = ""
    required_documents: List[str] = field(default_factory=list)
    application_url: str = ""
    official_link: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    target_age_min: Optional[int] = None
    target_age_max: Optional[int] = None
    income_limit: Optional[int] = None
    location: List[str] = field(default_factory=lambda: ["전국"])
    keywords: List[str] = field(default_factory=list)
    raw_html: str = ""
    crawled_at: datetime = field(default_factory=datetime.now)

    def to_vector_db_format(self, source_tier: SourceTier, source_url: str) -> Dict[str, Any]:
        """
        Vector DB 삽입용 포맷으로 변환

        PolicyData를 Vector DB에 저장할 수 있는 형태로 변환합니다.
        메타데이터 스키마에 맞게 구조화합니다.

        Args:
            source_tier: 데이터 소스의 신뢰도 등급
            source_url: 데이터를 수집한 원본 URL

        Returns:
            Dict[str, Any]: Vector DB 삽입용 딕셔너리

        Example:
            >>> policy = PolicyData(...)
            >>> db_format = policy.to_vector_db_format(
            ...     SourceTier.TIER_1,
            ...     "https://www.kinfa.or.kr/policy/123"
            ... )
        """
        return {
            "id": self.policy_id,
            "content": self.content,
            "metadata": {
                "source_tier": source_tier.value,
                "publish_year": datetime.now().year,
                "policy_end_date": self.end_date or "N/A",
                "policy_name": self.policy_name,
                "policy_category": self.category,
                "target_age_min": self.target_age_min,
                "target_age_max": self.target_age_max,
                "income_limit": self.income_limit,
                "location": self.location,
                "official_link": self.official_link,
                "source_url": source_url,
                "last_updated": self.crawled_at.strftime("%Y-%m-%d"),
                "required_documents": self.required_documents,
                "keywords": self.keywords
            }
        }


@dataclass
class CrawlResult:
    """
    크롤링 결과를 담는 데이터 클래스

    크롤링 작업의 전체 결과를 캡슐화합니다.
    성공/실패 여부, 수집된 데이터, 오류 정보 등을 포함합니다.

    Attributes:
        success (bool): 크롤링 성공 여부
        policies (List[PolicyData]): 수집된 정책 데이터 목록
        total_count (int): 총 수집된 정책 수
        error_count (int): 오류 발생 횟수
        errors (List[str]): 오류 메시지 목록
        started_at (datetime): 크롤링 시작 시각
        completed_at (Optional[datetime]): 크롤링 완료 시각
        duration_seconds (float): 총 소요 시간 (초)
        source_name (str): 데이터 소스 이름
        metadata (Dict): 추가 메타데이터
    """
    success: bool
    policies: List[PolicyData] = field(default_factory=list)
    total_count: int = 0
    error_count: int = 0
    errors: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    source_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_policy(self, policy: PolicyData) -> None:
        """정책 데이터를 결과에 추가"""
        self.policies.append(policy)
        self.total_count += 1

    def add_error(self, error_message: str) -> None:
        """오류 메시지를 결과에 추가"""
        self.errors.append(error_message)
        self.error_count += 1

    def finalize(self) -> None:
        """크롤링 완료 처리"""
        self.completed_at = datetime.now()
        self.duration_seconds = (
            self.completed_at - self.started_at
        ).total_seconds()


# =============================================================================
# 추상 기본 클래스 (Abstract Base Class)
# =============================================================================

class BaseCrawler(ABC):
    """
    모든 정책 크롤러의 추상 기본 클래스

    Template Method 패턴을 사용하여 크롤링 프로세스를 표준화합니다.
    하위 클래스는 추상 메서드를 구현하여 사이트별 크롤링 로직을 정의합니다.

    크롤링 프로세스:
        1. initialize() - 초기화 (세션 생성 등)
        2. fetch_policy_list() - 정책 목록 페이지 크롤링
        3. fetch_policy_detail() - 개별 정책 상세 페이지 크롤링
        4. parse_policy() - HTML에서 정책 데이터 추출
        5. cleanup() - 정리 (세션 종료 등)

    설계 원칙:
        - 단일 책임 원칙 (SRP): 각 메서드는 하나의 역할만 수행
        - 개방-폐쇄 원칙 (OCP): 확장에는 열려있고, 수정에는 닫혀있음
        - 리스코프 치환 원칙 (LSP): 하위 클래스는 상위 클래스를 대체 가능
        - 의존성 역전 원칙 (DIP): 추상화에 의존, 구체화에 의존하지 않음

    Attributes:
        _config (CrawlerConfig): 크롤러 설정 (private)
        _session (Optional[aiohttp.ClientSession]): HTTP 세션 (private)
        _status (CrawlerStatus): 현재 상태 (private)
        _logger (logging.Logger): 로거 인스턴스 (private)
        _observers (List[Callable]): 옵저버 콜백 목록 (private)

    Example:
        >>> class KinfaCrawler(BaseCrawler):
        ...     async def fetch_policy_list(self) -> List[str]:
        ...         # 사이트별 구현
        ...         pass
        ...
        >>> crawler = KinfaCrawler(config)
        >>> result = await crawler.crawl()
    """

    def __init__(self, config: CrawlerConfig):
        """
        크롤러 초기화

        Args:
            config: 크롤러 설정 객체
        """
        # Private 속성 (캡슐화)
        self._config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._status = CrawlerStatus.IDLE
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )
        self._observers: List[Callable] = []

        # 로거 설정
        self._setup_logger()

    # =========================================================================
    # 프로퍼티 (Properties) - 캡슐화된 접근자
    # =========================================================================

    @property
    def config(self) -> CrawlerConfig:
        """크롤러 설정 (읽기 전용)"""
        return self._config

    @property
    def status(self) -> CrawlerStatus:
        """현재 크롤러 상태 (읽기 전용)"""
        return self._status

    @property
    def source_name(self) -> str:
        """데이터 소스 이름 (읽기 전용)"""
        return self._config.source_name

    @property
    def is_running(self) -> bool:
        """크롤러가 실행 중인지 여부"""
        return self._status == CrawlerStatus.RUNNING

    # =========================================================================
    # 옵저버 패턴 메서드 (Observer Pattern)
    # =========================================================================

    def add_observer(self, callback: Callable[[str, Any], None]) -> None:
        """
        옵저버 콜백 등록

        크롤링 이벤트 발생 시 호출될 콜백 함수를 등록합니다.

        Args:
            callback: (event_name, data) 형태의 콜백 함수
        """
        self._observers.append(callback)

    def remove_observer(self, callback: Callable) -> None:
        """옵저버 콜백 제거"""
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self, event: str, data: Any = None) -> None:
        """
        모든 옵저버에게 이벤트 알림 (private)

        Args:
            event: 이벤트 이름
            data: 이벤트 데이터
        """
        for observer in self._observers:
            try:
                observer(event, data)
            except Exception as e:
                self._logger.error(f"옵저버 알림 실패: {e}")

    # =========================================================================
    # 템플릿 메서드 (Template Method) - 메인 크롤링 프로세스
    # =========================================================================

    async def crawl(self) -> CrawlResult:
        """
        메인 크롤링 메서드 (Template Method)

        크롤링 프로세스의 전체 흐름을 정의합니다.
        하위 클래스에서 오버라이드하지 않고, 추상 메서드들을 구현합니다.

        Returns:
            CrawlResult: 크롤링 결과 객체

        Raises:
            CrawlerException: 크롤링 중 복구 불가능한 오류 발생 시
        """
        # 결과 객체 초기화
        result = CrawlResult(
            success=False,
            source_name=self._config.source_name
        )

        try:
            # 1. 상태 변경 및 초기화
            self._set_status(CrawlerStatus.RUNNING)
            self._notify_observers("crawl_started", self._config.source_name)

            await self._initialize()
            self._logger.info(
                f"크롤링 시작: {self._config.source_name} "
                f"({self._config.base_url})"
            )

            # 2. 정책 목록 가져오기
            policy_urls = await self.fetch_policy_list()
            self._logger.info(f"발견된 정책 수: {len(policy_urls)}")

            # 3. 각 정책 상세 정보 크롤링
            for idx, url in enumerate(policy_urls, 1):
                try:
                    # 진행 상황 로깅
                    self._logger.debug(
                        f"정책 크롤링 중 [{idx}/{len(policy_urls)}]: {url}"
                    )

                    # 상세 페이지 크롤링
                    html = await self._fetch_page(url)

                    if html:
                        # HTML 파싱 및 데이터 추출
                        policy = await self.parse_policy(html, url)

                        if policy:
                            result.add_policy(policy)
                            self._notify_observers("policy_crawled", policy)

                    # 요청 간 지연 (서버 부하 방지)
                    await asyncio.sleep(self._config.request_delay)

                except Exception as e:
                    error_msg = f"정책 크롤링 실패 ({url}): {str(e)}"
                    result.add_error(error_msg)
                    self._logger.warning(error_msg)
                    continue

            # 4. 크롤링 완료
            result.success = result.total_count > 0
            result.finalize()

            self._logger.info(
                f"크롤링 완료: {result.total_count}개 정책 수집, "
                f"{result.error_count}개 오류, "
                f"{result.duration_seconds:.2f}초 소요"
            )

        except Exception as e:
            # 크롤링 실패
            error_msg = f"크롤링 실패: {str(e)}"
            result.add_error(error_msg)
            result.finalize()
            self._logger.error(error_msg, exc_info=True)
            self._set_status(CrawlerStatus.FAILED)
            self._notify_observers("crawl_failed", error_msg)

        finally:
            # 5. 정리 작업
            await self._cleanup()

            if result.success:
                self._set_status(CrawlerStatus.COMPLETED)
                self._notify_observers("crawl_completed", result)

        return result

    # =========================================================================
    # 추상 메서드 (Abstract Methods) - 하위 클래스에서 구현 필요
    # =========================================================================

    @abstractmethod
    async def fetch_policy_list(self) -> List[str]:
        """
        정책 목록 페이지에서 개별 정책 URL 추출 (추상 메서드)

        하위 클래스에서 사이트별 로직을 구현해야 합니다.

        Returns:
            List[str]: 정책 상세 페이지 URL 목록

        Example:
            >>> urls = await crawler.fetch_policy_list()
            >>> print(urls)
            ['https://example.com/policy/1', 'https://example.com/policy/2']
        """
        pass

    @abstractmethod
    async def parse_policy(
        self,
        html: str,
        url: str
    ) -> Optional[PolicyData]:
        """
        HTML에서 정책 데이터 추출 (추상 메서드)

        하위 클래스에서 사이트별 HTML 구조에 맞는 파싱 로직을 구현합니다.

        Args:
            html: 정책 상세 페이지의 HTML 문자열
            url: 페이지 URL

        Returns:
            Optional[PolicyData]: 추출된 정책 데이터, 실패 시 None
        """
        pass

    # =========================================================================
    # Protected 메서드 (하위 클래스에서 사용 가능)
    # =========================================================================

    async def _fetch_page(self, url: str) -> Optional[str]:
        """
        HTTP GET 요청으로 페이지 HTML 가져오기 (protected)

        재시도 로직과 에러 핸들링이 포함되어 있습니다.

        Args:
            url: 요청할 URL

        Returns:
            Optional[str]: HTML 문자열, 실패 시 None
        """
        if not self._session:
            self._logger.error("HTTP 세션이 초기화되지 않았습니다.")
            return None

        # 재시도 로직
        for attempt in range(self._config.max_retries):
            try:
                async with self._session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(
                        total=self._config.timeout
                    )
                ) as response:
                    # 상태 코드 확인
                    if response.status == 200:
                        return await response.text()

                    elif response.status == 429:
                        # Rate limit - 대기 후 재시도
                        self._set_status(CrawlerStatus.RATE_LIMITED)
                        wait_time = 2 ** attempt * 5  # 지수 백오프
                        self._logger.warning(
                            f"Rate limited. {wait_time}초 대기 후 재시도..."
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    else:
                        self._logger.warning(
                            f"HTTP {response.status}: {url}"
                        )

            except asyncio.TimeoutError:
                self._logger.warning(
                    f"타임아웃 (시도 {attempt + 1}/{self._config.max_retries}): {url}"
                )
            except aiohttp.ClientError as e:
                self._logger.warning(
                    f"HTTP 오류 (시도 {attempt + 1}/{self._config.max_retries}): {e}"
                )

            # 재시도 전 대기
            if attempt < self._config.max_retries - 1:
                await asyncio.sleep(2 ** attempt)

        return None

    def _parse_html(self, html: str) -> BeautifulSoup:
        """
        HTML 문자열을 BeautifulSoup 객체로 파싱 (protected)

        Args:
            html: HTML 문자열

        Returns:
            BeautifulSoup: 파싱된 HTML 객체
        """
        return BeautifulSoup(html, 'html.parser')

    def _extract_text(
        self,
        soup: BeautifulSoup,
        selector: str,
        default: str = ""
    ) -> str:
        """
        CSS 선택자로 텍스트 추출 (protected)

        Args:
            soup: BeautifulSoup 객체
            selector: CSS 선택자
            default: 요소를 찾지 못했을 때 반환할 기본값

        Returns:
            str: 추출된 텍스트 (정규화됨)
        """
        element = soup.select_one(selector)
        if element:
            # 텍스트 정규화 (공백 정리)
            return ' '.join(element.get_text().split())
        return default

    def _extract_list(
        self,
        soup: BeautifulSoup,
        selector: str
    ) -> List[str]:
        """
        CSS 선택자로 리스트 항목들 추출 (protected)

        Args:
            soup: BeautifulSoup 객체
            selector: CSS 선택자

        Returns:
            List[str]: 추출된 텍스트 리스트
        """
        elements = soup.select(selector)
        return [
            ' '.join(el.get_text().split())
            for el in elements
            if el.get_text().strip()
        ]

    def _generate_policy_id(self, url: str) -> str:
        """
        정책 URL에서 고유 ID 생성 (protected)

        Args:
            url: 정책 페이지 URL

        Returns:
            str: 정책 고유 ID
        """
        import hashlib
        # URL 해시로 고유 ID 생성
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        source_prefix = self._config.source_name[:4].lower()
        return f"{source_prefix}-{datetime.now().year}-{url_hash}"

    # =========================================================================
    # Private 메서드 (내부 구현)
    # =========================================================================

    def _setup_logger(self) -> None:
        """로거 설정 (private)"""
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def _set_status(self, status: CrawlerStatus) -> None:
        """상태 변경 및 알림 (private)"""
        old_status = self._status
        self._status = status
        self._notify_observers(
            "status_changed",
            {"old": old_status, "new": status}
        )

    async def _initialize(self) -> None:
        """HTTP 세션 초기화 (private)"""
        # 기본 헤더 설정
        headers = {
            "User-Agent": self._config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            **self._config.headers
        }

        # aiohttp 세션 생성
        connector = aiohttp.TCPConnector(
            limit=10,  # 최대 동시 연결 수
            ssl=False  # SSL 검증 (프로덕션에서는 True)
        )

        self._session = aiohttp.ClientSession(
            headers=headers,
            connector=connector
        )

    async def _cleanup(self) -> None:
        """리소스 정리 (private)"""
        if self._session:
            await self._session.close()
            self._session = None

    # =========================================================================
    # 매직 메서드 (Magic Methods)
    # =========================================================================

    def __repr__(self) -> str:
        """객체의 문자열 표현"""
        return (
            f"{self.__class__.__name__}("
            f"source='{self._config.source_name}', "
            f"status={self._status.value})"
        )

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self._initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self._cleanup()
        return False
