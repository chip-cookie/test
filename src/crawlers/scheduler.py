#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
크롤러 스케줄러 (Crawler Scheduler)
=============================================================================

크롤링 작업을 정기적으로 실행하는 스케줄러입니다.
APScheduler를 사용하여 Cron 표현식 기반 스케줄링을 지원합니다.

Author: Youth Policy System Team
Version: 1.0.0
=============================================================================
"""

import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from dataclasses import dataclass, field
import logging

from .factory import PolicyCrawlerFactory
from .base_crawler import CrawlResult


@dataclass
class ScheduledJob:
    """
    스케줄링된 크롤링 작업 정보

    Attributes:
        job_id (str): 작업 고유 ID
        crawler_name (str): 크롤러 이름
        cron_expression (str): Cron 표현식
        enabled (bool): 활성화 여부
        last_run (Optional[datetime]): 마지막 실행 시각
        next_run (Optional[datetime]): 다음 실행 예정 시각
        run_count (int): 총 실행 횟수
        success_count (int): 성공 횟수
        failure_count (int): 실패 횟수
    """
    job_id: str
    crawler_name: str
    cron_expression: str
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0


class CrawlerScheduler:
    """
    크롤링 작업 스케줄러

    정기적인 크롤링 작업을 관리하고 실행합니다.
    옵저버 패턴을 통해 작업 결과를 외부에 알립니다.

    Attributes:
        _jobs (Dict): 등록된 작업 목록
        _is_running (bool): 스케줄러 실행 상태
        _logger (logging.Logger): 로거
        _observers (List): 옵저버 콜백 목록

    Example:
        >>> scheduler = CrawlerScheduler()
        >>>
        >>> # 작업 등록 (매일 오전 6시)
        >>> scheduler.add_job('kinfa', '0 6 * * *')
        >>> scheduler.add_job('bokjiro', '0 12 * * *')
        >>>
        >>> # 결과 콜백 등록
        >>> scheduler.on_complete(lambda result: print(result))
        >>>
        >>> # 스케줄러 시작
        >>> await scheduler.start()
    """

    def __init__(self):
        """스케줄러 초기화"""
        # Private 속성
        self._jobs: Dict[str, ScheduledJob] = {}
        self._is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._logger = logging.getLogger(__name__)

        # 옵저버 콜백
        self._on_complete_callbacks: List[Callable] = []
        self._on_error_callbacks: List[Callable] = []
        self._on_start_callbacks: List[Callable] = []

    # =========================================================================
    # 프로퍼티
    # =========================================================================

    @property
    def is_running(self) -> bool:
        """스케줄러 실행 상태"""
        return self._is_running

    @property
    def jobs(self) -> Dict[str, ScheduledJob]:
        """등록된 작업 목록 (읽기 전용 복사본)"""
        return self._jobs.copy()

    # =========================================================================
    # 작업 관리 메서드
    # =========================================================================

    def add_job(
        self,
        crawler_name: str,
        cron_expression: str,
        job_id: Optional[str] = None,
        enabled: bool = True
    ) -> str:
        """
        크롤링 작업 등록

        Args:
            crawler_name: 실행할 크롤러 이름 (팩토리에 등록된 이름)
            cron_expression: Cron 표현식 (예: '0 6 * * *')
            job_id: 작업 ID (None이면 자동 생성)
            enabled: 활성화 여부

        Returns:
            str: 등록된 작업 ID

        Raises:
            ValueError: 크롤러가 팩토리에 등록되지 않은 경우

        Example:
            >>> # 매일 오전 6시 실행
            >>> scheduler.add_job('kinfa', '0 6 * * *')
            >>>
            >>> # 매주 월요일 오전 9시 실행
            >>> scheduler.add_job('bokjiro', '0 9 * * 1')
        """
        # 크롤러 존재 확인
        if not PolicyCrawlerFactory.is_registered(crawler_name):
            raise ValueError(f"등록되지 않은 크롤러: {crawler_name}")

        # 작업 ID 생성
        if job_id is None:
            job_id = f"{crawler_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 작업 생성 및 등록
        job = ScheduledJob(
            job_id=job_id,
            crawler_name=crawler_name,
            cron_expression=cron_expression,
            enabled=enabled
        )

        self._jobs[job_id] = job
        self._logger.info(
            f"작업 등록: {job_id} ({crawler_name}, {cron_expression})"
        )

        return job_id

    def remove_job(self, job_id: str) -> bool:
        """
        작업 제거

        Args:
            job_id: 제거할 작업 ID

        Returns:
            bool: 제거 성공 여부
        """
        if job_id in self._jobs:
            del self._jobs[job_id]
            self._logger.info(f"작업 제거: {job_id}")
            return True
        return False

    def enable_job(self, job_id: str) -> bool:
        """작업 활성화"""
        if job_id in self._jobs:
            self._jobs[job_id].enabled = True
            return True
        return False

    def disable_job(self, job_id: str) -> bool:
        """작업 비활성화"""
        if job_id in self._jobs:
            self._jobs[job_id].enabled = False
            return True
        return False

    def get_job_status(self, job_id: str) -> Optional[ScheduledJob]:
        """작업 상태 조회"""
        return self._jobs.get(job_id)

    # =========================================================================
    # 옵저버 콜백 등록
    # =========================================================================

    def on_start(self, callback: Callable[[str], None]) -> None:
        """
        작업 시작 콜백 등록

        Args:
            callback: (job_id) -> None
        """
        self._on_start_callbacks.append(callback)

    def on_complete(self, callback: Callable[[CrawlResult], None]) -> None:
        """
        작업 완료 콜백 등록

        Args:
            callback: (result) -> None
        """
        self._on_complete_callbacks.append(callback)

    def on_error(self, callback: Callable[[str, Exception], None]) -> None:
        """
        오류 발생 콜백 등록

        Args:
            callback: (job_id, exception) -> None
        """
        self._on_error_callbacks.append(callback)

    # =========================================================================
    # 스케줄러 제어
    # =========================================================================

    async def start(self) -> None:
        """
        스케줄러 시작

        백그라운드에서 스케줄러를 실행합니다.
        """
        if self._is_running:
            self._logger.warning("스케줄러가 이미 실행 중입니다.")
            return

        self._is_running = True
        self._task = asyncio.create_task(self._run_scheduler())
        self._logger.info("스케줄러 시작됨")

    async def stop(self) -> None:
        """스케줄러 중지"""
        self._is_running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self._logger.info("스케줄러 중지됨")

    async def run_now(self, job_id: str) -> Optional[CrawlResult]:
        """
        작업 즉시 실행

        Args:
            job_id: 실행할 작업 ID

        Returns:
            Optional[CrawlResult]: 크롤링 결과
        """
        if job_id not in self._jobs:
            self._logger.error(f"존재하지 않는 작업: {job_id}")
            return None

        return await self._execute_job(self._jobs[job_id])

    async def run_all_now(self) -> Dict[str, CrawlResult]:
        """
        모든 활성화된 작업 즉시 실행

        Returns:
            Dict[str, CrawlResult]: 작업별 결과
        """
        results = {}

        for job_id, job in self._jobs.items():
            if job.enabled:
                result = await self._execute_job(job)
                if result:
                    results[job_id] = result

        return results

    # =========================================================================
    # Private 메서드
    # =========================================================================

    async def _run_scheduler(self) -> None:
        """
        스케줄러 메인 루프 (private)

        1분마다 작업 목록을 확인하고 실행할 작업이 있으면 실행합니다.
        """
        while self._is_running:
            try:
                current_time = datetime.now()

                for job_id, job in self._jobs.items():
                    if not job.enabled:
                        continue

                    # Cron 표현식 평가 (간단한 구현)
                    if self._should_run(job, current_time):
                        asyncio.create_task(self._execute_job(job))

                # 1분 대기
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"스케줄러 오류: {e}")
                await asyncio.sleep(60)

    def _should_run(self, job: ScheduledJob, current_time: datetime) -> bool:
        """
        작업 실행 여부 판단 (private)

        간단한 Cron 표현식 파서입니다.
        프로덕션에서는 croniter 라이브러리 사용을 권장합니다.

        Args:
            job: 작업 정보
            current_time: 현재 시각

        Returns:
            bool: 실행 여부
        """
        # Cron 표현식 파싱: 분 시 일 월 요일
        parts = job.cron_expression.split()

        if len(parts) != 5:
            return False

        minute, hour, day, month, weekday = parts

        # 간단한 매칭 (정확한 구현은 croniter 사용)
        checks = [
            self._match_cron_field(minute, current_time.minute),
            self._match_cron_field(hour, current_time.hour),
            self._match_cron_field(day, current_time.day),
            self._match_cron_field(month, current_time.month),
            self._match_cron_field(weekday, current_time.weekday())
        ]

        return all(checks)

    def _match_cron_field(self, field: str, value: int) -> bool:
        """Cron 필드 매칭 (private)"""
        if field == '*':
            return True

        if field.isdigit():
            return int(field) == value

        if '/' in field:
            # */5 형태 (5분마다)
            _, interval = field.split('/')
            return value % int(interval) == 0

        return False

    async def _execute_job(self, job: ScheduledJob) -> Optional[CrawlResult]:
        """
        작업 실행 (private)

        Args:
            job: 실행할 작업

        Returns:
            Optional[CrawlResult]: 크롤링 결과
        """
        job.run_count += 1
        job.last_run = datetime.now()

        # 시작 콜백 호출
        for callback in self._on_start_callbacks:
            try:
                callback(job.job_id)
            except Exception as e:
                self._logger.error(f"시작 콜백 오류: {e}")

        try:
            # 크롤러 생성 및 실행
            crawler = PolicyCrawlerFactory.create(job.crawler_name)
            result = await crawler.crawl()

            # 통계 업데이트
            if result.success:
                job.success_count += 1
            else:
                job.failure_count += 1

            # 완료 콜백 호출
            for callback in self._on_complete_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    self._logger.error(f"완료 콜백 오류: {e}")

            return result

        except Exception as e:
            job.failure_count += 1
            self._logger.error(f"작업 실행 오류 ({job.job_id}): {e}")

            # 오류 콜백 호출
            for callback in self._on_error_callbacks:
                try:
                    callback(job.job_id, e)
                except Exception as cb_e:
                    self._logger.error(f"오류 콜백 실행 실패: {cb_e}")

            return None

    # =========================================================================
    # 매직 메서드
    # =========================================================================

    def __repr__(self) -> str:
        """객체 문자열 표현"""
        status = "running" if self._is_running else "stopped"
        return f"CrawlerScheduler(jobs={len(self._jobs)}, status={status})"
