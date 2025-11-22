#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
크롤러 공통 유틸리티 (Crawler Utilities)
=============================================================================

크롤러들이 공통으로 사용하는 데이터 추출 및 처리 유틸리티입니다.

중복 코드 제거(DRY 원칙)와 재사용성을 위해 설계되었습니다.

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import re
import hashlib
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
import logging


class PolicyDataExtractor:
    """
    정책 데이터 추출을 위한 공통 유틸리티 클래스

    여러 크롤러에서 반복되는 데이터 추출 로직을 통합하여
    코드 중복을 제거하고 유지보수성을 향상시킵니다.

    주요 기능:
        - 연령 범위 추출
        - 소득 제한 추출
        - 필수 서류 추출
        - 신청 기간 추출
        - 카테고리 결정
        - 청년 정책 여부 판단

    사용 방법:
        >>> extractor = PolicyDataExtractor()
        >>> age_min, age_max = extractor.extract_age_range("만 19세 ~ 34세 청년")
        >>> print(age_min, age_max)  # 19, 34

    설계 원칙:
        - Static Method: 상태를 유지하지 않아 스레드 세이프
        - 단일 책임: 각 메서드는 하나의 추출 작업만 수행
        - 확장 가능: 새로운 추출 패턴 추가 용이
    """

    # =========================================================================
    # 연령 관련 추출
    # =========================================================================

    @staticmethod
    def extract_age_range(
        text: str,
        default_min: int = 19,
        default_max: int = 34
    ) -> Tuple[int, int]:
        """
        텍스트에서 연령 범위를 추출합니다.

        다양한 형식의 연령 표기를 인식하여 최소/최대 연령을 추출합니다.

        인식 가능한 형식:
            - "만 19세 ~ 34세"
            - "19~34세"
            - "19세-34세"
            - "만 34세 이하"
            - "19세 이상 34세 이하"

        Args:
            text: 분석할 텍스트 (자격조건, 정책 설명 등)
            default_min: 패턴 미발견 시 기본 최소 연령 (기본값: 19)
            default_max: 패턴 미발견 시 기본 최대 연령 (기본값: 34)

        Returns:
            Tuple[int, int]: (최소 연령, 최대 연령)

        Examples:
            >>> PolicyDataExtractor.extract_age_range("만 19세 ~ 34세 청년")
            (19, 34)

            >>> PolicyDataExtractor.extract_age_range("만 34세 이하")
            (19, 34)

            >>> PolicyDataExtractor.extract_age_range("청년 대상 정책")
            (19, 34)  # 기본값 반환

        Note:
            - 정확한 범위를 찾지 못하면 기본값(청년 기준)을 반환합니다.
            - 복수의 연령 표기가 있으면 첫 번째 매칭을 우선합니다.
        """
        # 패턴 1: "만 19세 ~ 34세" (가장 명확한 형식)
        # 설명: '만' 키워드 포함, 범위 표기
        pattern_range_with_man = r'만?\s*(\d{1,2})\s*세?\s*[~-]\s*(\d{1,2})\s*세'
        match = re.search(pattern_range_with_man, text)
        if match:
            return int(match.group(1)), int(match.group(2))

        # 패턴 2: "19~34세" (간략 형식)
        pattern_range_simple = r'(\d{1,2})\s*[~-]\s*(\d{1,2})\s*세'
        match = re.search(pattern_range_simple, text)
        if match:
            return int(match.group(1)), int(match.group(2))

        # 패턴 3: "만 34세 이하" (상한만 명시)
        pattern_max_only = r'만?\s*(\d{1,2})\s*세\s*이하'
        match = re.search(pattern_max_only, text)
        if match:
            return default_min, int(match.group(1))

        # 패턴 4: "19세 이상" (하한만 명시)
        pattern_min_only = r'(\d{1,2})\s*세\s*이상'
        match = re.search(pattern_min_only, text)
        if match:
            return int(match.group(1)), default_max

        # 패턴을 찾지 못한 경우: 기본값 반환
        # 대한민국 청년 기준: 만 19~34세
        return default_min, default_max

    # =========================================================================
    # 소득 관련 추출
    # =========================================================================

    @staticmethod
    def extract_income_limit(text: str) -> Optional[int]:
        """
        텍스트에서 소득 제한을 추출합니다.

        다양한 형식의 소득 표기를 인식하여 연 소득 제한(원 단위)을 반환합니다.

        인식 가능한 형식:
            - "연소득 5,000만원"
            - "연 5천만원 이하"
            - "소득 5,000만 이하"
            - "중위소득 150%"

        Args:
            text: 분석할 텍스트

        Returns:
            Optional[int]: 연 소득 제한 (원 단위), 없으면 None

        Examples:
            >>> PolicyDataExtractor.extract_income_limit("연소득 5,000만원 이하")
            50000000

            >>> PolicyDataExtractor.extract_income_limit("중위소득 150%")
            75000000  # 중위소득 기준 약 5천만원 * 1.5

            >>> PolicyDataExtractor.extract_income_limit("소득 제한 없음")
            None

        Note:
            - 중위소득 퍼센트는 기준 중위소득(약 5천만원)을 기준으로 계산됩니다.
            - 천만원 단위로 반환됩니다.
        """
        # 패턴 1: "연소득 5,000만원" 형태
        # 그룹 1: 천의 자리 (예: 5)
        # 그룹 2: 나머지 (예: 000)
        pattern_comma = r'연?\s*소득\s*(\d{1,2}),?(\d{3})\s*만\s*원?'
        match = re.search(pattern_comma, text)
        if match:
            thousands = int(match.group(1))  # 5
            remainder = int(match.group(2))  # 000
            # 5,000만원 = (5 * 1000 + 000) * 10,000 = 50,000,000
            amount_in_man = thousands * 1000 + remainder
            return amount_in_man * 10000

        # 패턴 2: "5천만원" 형태
        pattern_cheon = r'(\d{1,2})\s*천\s*만\s*원?'
        match = re.search(pattern_cheon, text)
        if match:
            # 5천만원 = 5 * 1000만원 = 50,000,000
            return int(match.group(1)) * 10000000

        # 패턴 3: "중위소득 150%" 형태
        # 기준 중위소득: 약 5천만원 (2025년 기준)
        pattern_median = r'중위소득\s*(\d+)\s*%'
        match = re.search(pattern_median, text)
        if match:
            percentage = int(match.group(1))
            # 중위소득 5천만원 기준
            base_median_income = 50000000
            return int(base_median_income * percentage / 100)

        # 패턴 4: "소득 5,000만" (단위 생략)
        pattern_simple = r'소득\s*(\d{1,2}),?(\d{3})\s*만'
        match = re.search(pattern_simple, text)
        if match:
            thousands = int(match.group(1))
            remainder = int(match.group(2))
            amount_in_man = thousands * 1000 + remainder
            return amount_in_man * 10000

        # 소득 제한 정보를 찾지 못한 경우
        return None

    # =========================================================================
    # 서류 관련 추출
    # =========================================================================

    @staticmethod
    def extract_documents(soup: Any) -> List[str]:
        """
        BeautifulSoup 객체에서 필수 서류 목록을 추출합니다.

        두 가지 방식으로 추출을 시도합니다:
            1. HTML 리스트(<li>) 형태의 서류 목록
            2. 일반 텍스트에서 일반적인 서류명 검색

        Args:
            soup: BeautifulSoup 파싱된 HTML 객체

        Returns:
            List[str]: 필수 서류 목록 (최대 10개)

        Examples:
            >>> soup = BeautifulSoup(html, 'html.parser')
            >>> docs = PolicyDataExtractor.extract_documents(soup)
            >>> print(docs)
            ['신분증', '주민등록등본', '소득증명서']

        Note:
            - 리스트 형태가 우선 순위가 높습니다.
            - 중복 제거 및 빈 문자열 필터링이 적용됩니다.
            - 최대 10개까지만 반환합니다.
        """
        documents = []

        # 방법 1: 리스트 형태로 된 서류 목록 찾기
        # 일반적인 서류 목록 CSS 클래스/선택자
        doc_selectors = [
            ".documents li",           # 표준 클래스
            ".required-docs li",       # 필수 서류 클래스
            "[class*='서류'] li",      # '서류' 포함 클래스
            ".doc-list li",            # 서류 리스트
            ".document-list li",       # 문서 리스트
            "[class*='필요서류'] li"   # '필요서류' 포함 클래스
        ]

        for selector in doc_selectors:
            doc_lists = soup.select(selector)
            if doc_lists:
                documents = [
                    li.get_text().strip()
                    for li in doc_lists
                    if li.get_text().strip()  # 빈 문자열 제외
                ]
                break  # 첫 번째 매칭에서 종료

        # 방법 2: 리스트를 못 찾은 경우, 텍스트에서 일반적인 서류명 찾기
        if not documents:
            text = soup.get_text()

            # 대한민국 공공 서비스에서 자주 요구되는 서류
            common_documents = [
                "신분증",            # 주민등록증, 운전면허증 등
                "주민등록등본",      # 가족 관계 증명
                "주민등록초본",      # 거주지 증명
                "소득증명서",        # 소득 확인
                "재직증명서",        # 재직 여부 확인
                "원천징수영수증",    # 근로소득 확인
                "사업자등록증",      # 사업자 확인
                "통장사본",          # 계좌 확인
                "가족관계증명서",    # 가족 구성 확인
                "건강보험자격득실확인서"  # 소득 및 자격 확인
            ]

            # 텍스트에 포함된 서류만 추출
            documents = [
                doc for doc in common_documents
                if doc in text
            ]

        # 중복 제거 및 최대 10개 반환
        return list(set(documents))[:10]

    # =========================================================================
    # 날짜 관련 추출
    # =========================================================================

    @staticmethod
    def extract_dates(soup: Any) -> Tuple[Optional[str], Optional[str]]:
        """
        BeautifulSoup 객체에서 신청 기간(시작일, 종료일)을 추출합니다.

        다양한 날짜 형식을 인식합니다:
            - 2025.01.01
            - 2025-01-01
            - 2025년 1월 1일

        Args:
            soup: BeautifulSoup 파싱된 HTML 객체

        Returns:
            Tuple[Optional[str], Optional[str]]: (시작일, 종료일)
                날짜 형식: "YYYY-MM-DD"
                찾지 못하면 None 반환

        Examples:
            >>> soup = BeautifulSoup(html, 'html.parser')
            >>> start, end = PolicyDataExtractor.extract_dates(soup)
            >>> print(start, end)
            ('2025-01-01', '2025-12-31')

        Note:
            - 첫 번째 날짜를 시작일로, 두 번째 날짜를 종료일로 간주합니다.
            - ISO 8601 형식(YYYY-MM-DD)으로 반환합니다.
        """
        # 날짜 정규식 패턴
        # 그룹 1: 연도 (4자리)
        # 그룹 2: 월 (1-2자리)
        # 그룹 3: 일 (1-2자리)
        # 구분자: . - 년/월
        date_pattern = r'(\d{4})[.\-년]\s*(\d{1,2})[.\-월]\s*(\d{1,2})'

        # 전체 텍스트에서 날짜 찾기
        text = soup.get_text()
        dates = re.findall(date_pattern, text)

        start_date = None
        end_date = None

        if dates:
            # 첫 번째 날짜: 시작일
            year, month, day = dates[0]
            start_date = f"{year}-{int(month):02d}-{int(day):02d}"

            # 두 번째 날짜: 종료일 (있으면)
            if len(dates) > 1:
                year, month, day = dates[1]
                end_date = f"{year}-{int(month):02d}-{int(day):02d}"

        return start_date, end_date

    # =========================================================================
    # 카테고리 및 분류
    # =========================================================================

    @staticmethod
    def determine_category(
        text: str,
        category_mapping: Dict[str, str],
        default_category: str = "기타"
    ) -> str:
        """
        텍스트에서 정책 카테고리를 결정합니다.

        매핑 테이블을 기반으로 키워드를 찾아 카테고리를 분류합니다.

        Args:
            text: 분석할 텍스트 (정책명, 요약 등)
            category_mapping: 키워드 → 카테고리 매핑 딕셔너리
                예: {"대출": "금융", "주거": "주거"}
            default_category: 매칭 실패 시 기본 카테고리

        Returns:
            str: 결정된 카테고리

        Examples:
            >>> mapping = {"대출": "금융", "주거": "주거"}
            >>> PolicyDataExtractor.determine_category(
            ...     "청년 전용 대출 상품",
            ...     mapping
            ... )
            '금융'

            >>> PolicyDataExtractor.determine_category(
            ...     "일반 지원 정책",
            ...     mapping,
            ...     default_category="생활지원"
            ... )
            '생활지원'

        Note:
            - 첫 번째로 매칭되는 키워드의 카테고리를 반환합니다.
            - 대소문자 구분 없이 검색합니다.
        """
        text_lower = text.lower()

        # 매핑 테이블에서 키워드 검색
        for keyword, category in category_mapping.items():
            if keyword.lower() in text_lower:
                return category

        # 매칭 실패: 기본 카테고리 반환
        return default_category

    @staticmethod
    def is_youth_policy(
        text: str,
        youth_keywords: Optional[List[str]] = None
    ) -> bool:
        """
        텍스트가 청년 관련 정책인지 판단합니다.

        청년 관련 키워드의 포함 여부를 확인합니다.

        Args:
            text: 분석할 텍스트
            youth_keywords: 청년 관련 키워드 목록 (None이면 기본값 사용)

        Returns:
            bool: 청년 정책이면 True

        Examples:
            >>> PolicyDataExtractor.is_youth_policy("청년 주거 지원 정책")
            True

            >>> PolicyDataExtractor.is_youth_policy("노인 복지 정책")
            False

        Note:
            - 대소문자 구분 없이 검색합니다.
            - 기본 키워드: 청년, youth, 대학생, 사회초년생, 취준생 등
        """
        # 기본 청년 키워드
        if youth_keywords is None:
            youth_keywords = [
                "청년",
                "youth",
                "대학생",
                "사회초년생",
                "취준생",
                "취업준비생",
                "19세", "20대", "30대",
                "34세", "39세"  # 청년 상한 연령
            ]

        text_lower = text.lower()

        # 키워드 중 하나라도 포함되면 청년 정책
        return any(
            keyword.lower() in text_lower
            for keyword in youth_keywords
        )

    # =========================================================================
    # 키워드 추출
    # =========================================================================

    @staticmethod
    def extract_keywords(
        policy_name: str,
        summary: str,
        base_keywords: Optional[List[str]] = None,
        important_words: Optional[List[str]] = None,
        max_keywords: int = 10
    ) -> List[str]:
        """
        정책명과 요약에서 검색 키워드를 추출합니다.

        다음 순서로 키워드를 수집합니다:
            1. 기본 키워드 (예: "청년")
            2. 정책명에서 추출한 단어
            3. 중요 키워드 (본문에 포함된 경우만)

        Args:
            policy_name: 정책명
            summary: 정책 요약
            base_keywords: 기본 키워드 목록 (None이면 ["청년"])
            important_words: 중요 키워드 후보 목록
            max_keywords: 최대 키워드 수 (기본값: 10)

        Returns:
            List[str]: 추출된 키워드 목록 (중복 제거됨)

        Examples:
            >>> PolicyDataExtractor.extract_keywords(
            ...     "청년 전용 대출",
            ...     "저금리 청년 대출 상품"
            ... )
            ['청년', '전용', '대출', '저금리']

        Note:
            - 숫자만으로 된 단어는 제외됩니다.
            - 2글자 이상 단어만 포함됩니다.
            - 중복이 제거되며, 최대 개수로 제한됩니다.
        """
        keywords = []

        # 1. 기본 키워드 추가
        if base_keywords is None:
            base_keywords = ["청년"]
        keywords.extend(base_keywords)

        # 2. 정책명에서 키워드 추출
        # 공백으로 분리하여 2글자 이상, 숫자 아닌 단어만
        name_keywords = [
            word for word in policy_name.split()
            if len(word) >= 2 and not word.isdigit()
        ]
        # 상위 3개만 추가
        keywords.extend(name_keywords[:3])

        # 3. 중요 키워드 추가 (본문에 포함된 경우만)
        if important_words is None:
            important_words = [
                "대출", "저축", "계좌", "주거", "취업",
                "창업", "교육", "지원금", "보조금"
            ]

        combined_text = policy_name + " " + summary
        keywords.extend([
            word for word in important_words
            if word in combined_text
        ])

        # 중복 제거 및 최대 개수 제한
        unique_keywords = list(set(keywords))
        return unique_keywords[:max_keywords]

    # =========================================================================
    # ID 생성
    # =========================================================================

    @staticmethod
    def generate_policy_id(
        url: str,
        source_name: str = ""
    ) -> str:
        """
        정책 고유 ID를 생성합니다.

        URL을 기반으로 SHA-256 해시를 생성하여 고유 ID를 만듭니다.

        Args:
            url: 정책 URL
            source_name: 데이터 소스명 (선택사항, 추가 고유성 보장)

        Returns:
            str: 16자리 16진수 ID

        Examples:
            >>> PolicyDataExtractor.generate_policy_id(
            ...     "https://example.com/policy/123",
            ...     "복지로"
            ... )
            '7a3f9c2e1b4d8f5a'

        Note:
            - 동일한 URL은 항상 동일한 ID를 생성합니다.
            - SHA-256 해시의 앞 16자리를 사용합니다.
        """
        # URL + 소스명을 조합하여 해시 생성
        hash_input = f"{source_name}:{url}"

        # SHA-256 해시 계산
        hash_object = hashlib.sha256(hash_input.encode('utf-8'))

        # 16진수로 변환 후 앞 16자리 사용
        return hash_object.hexdigest()[:16]


class TextNormalizer:
    """
    텍스트 정규화 유틸리티 클래스

    크롤링한 텍스트 데이터를 정제하고 정규화합니다.

    주요 기능:
        - 공백 정규화
        - 특수문자 제거
        - HTML 태그 제거
        - 유니코드 정규화
    """

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        공백을 정규화합니다.

        연속된 공백, 탭, 줄바꿈을 단일 공백으로 변환합니다.

        Args:
            text: 원본 텍스트

        Returns:
            str: 정규화된 텍스트

        Examples:
            >>> TextNormalizer.normalize_whitespace("청년  정책\\n\\n안내")
            '청년 정책 안내'
        """
        # 연속된 공백 문자를 하나의 공백으로 변환
        # \s: 공백, 탭, 줄바꿈 등 모든 공백 문자
        text = re.sub(r'\s+', ' ', text)

        # 앞뒤 공백 제거
        return text.strip()

    @staticmethod
    def remove_special_chars(
        text: str,
        keep_chars: str = ".,!?-"
    ) -> str:
        """
        특수문자를 제거합니다.

        Args:
            text: 원본 텍스트
            keep_chars: 유지할 특수문자 (기본값: ".,!?-")

        Returns:
            str: 특수문자가 제거된 텍스트

        Examples:
            >>> TextNormalizer.remove_special_chars("청년@정책#안내!")
            '청년정책안내!'
        """
        # 한글, 영문, 숫자, 공백, 유지할 특수문자만 남김
        pattern = f'[^가-힣a-zA-Z0-9\\s{re.escape(keep_chars)}]'
        return re.sub(pattern, '', text)

    @staticmethod
    def clean_html(text: str) -> str:
        """
        HTML 태그를 제거합니다.

        Args:
            text: HTML이 포함된 텍스트

        Returns:
            str: HTML 태그가 제거된 순수 텍스트

        Examples:
            >>> TextNormalizer.clean_html("<p>청년 정책</p>")
            '청년 정책'
        """
        # HTML 태그 제거 (간단한 방식)
        # 주의: 복잡한 HTML은 BeautifulSoup 사용 권장
        text = re.sub(r'<[^>]+>', '', text)

        # HTML 엔티티 처리
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')

        return text
