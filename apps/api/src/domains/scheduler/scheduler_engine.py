"""
APScheduler AsyncIOScheduler 싱글턴 래퍼

DB에 저장된 Schedule을 APScheduler에 등록/제거/일시정지/재개합니다.
앱 시작 시 DB에서 활성 스케줄을 복원합니다.
"""
from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.database.database import AsyncSessionPrimary
from src.domains.scheduler.job_registry import get_job_func
from src.domains.scheduler.models import Schedule, ScheduledJobHistory

logger = logging.getLogger(__name__)


def _build_trigger(trigger_type: str, trigger_config: dict):
    """trigger_type에 따라 APScheduler 트리거 생성"""
    if trigger_type == "cron":
        return CronTrigger(**trigger_config)
    elif trigger_type == "interval":
        return IntervalTrigger(**trigger_config)
    elif trigger_type == "date":
        return DateTrigger(**trigger_config)
    else:
        raise ValueError(f"지원하지 않는 트리거 유형입니다: {trigger_type}")


class SchedulerEngine:
    """APScheduler AsyncIOScheduler 싱글턴 래퍼"""

    def __init__(self):
        self._scheduler = AsyncIOScheduler()

    @property
    def running(self) -> bool:
        return self._scheduler.running

    async def start(self):
        """스케줄러 시작"""
        if self._scheduler.running:
            logger.warning("SchedulerEngine이 이미 실행 중입니다.")
            return
        self._scheduler.start()
        logger.info("SchedulerEngine 시작 완료")

    async def stop(self):
        """스케줄러 종료"""
        if not self._scheduler.running:
            return
        self._scheduler.shutdown(wait=True)
        logger.info("SchedulerEngine 종료 완료")

    async def add_schedule(self, schedule: Schedule):
        """Schedule 모델로부터 APScheduler에 작업 등록"""
        job_func = get_job_func(schedule.job_type)
        trigger = _build_trigger(schedule.trigger_type, schedule.trigger_config)

        self._scheduler.add_job(
            _run_job_with_tracking,
            trigger=trigger,
            id=schedule.job_id,
            name=schedule.name,
            replace_existing=True,
            kwargs={
                "schedule_id": schedule.id,
                "job_id": schedule.job_id,
                "job_name": schedule.name,
                "job_type": schedule.job_type,
                "job_params": schedule.job_params,
            },
        )
        logger.info(
            f"스케줄 등록: {schedule.job_id} ({schedule.trigger_type})"
        )

    async def remove_schedule(self, job_id: str):
        """APScheduler에서 작업 제거"""
        job = self._scheduler.get_job(job_id)
        if job:
            self._scheduler.remove_job(job_id)
            logger.info(f"스케줄 제거: {job_id}")

    async def pause_schedule(self, job_id: str):
        """작업 일시정지"""
        job = self._scheduler.get_job(job_id)
        if job:
            self._scheduler.pause_job(job_id)
            logger.info(f"스케줄 일시정지: {job_id}")

    async def resume_schedule(self, job_id: str):
        """작업 재개"""
        job = self._scheduler.get_job(job_id)
        if job:
            self._scheduler.resume_job(job_id)
            logger.info(f"스케줄 재개: {job_id}")

    async def run_now(self, job_id: str, schedule_id: int, job_name: str, job_type: str, job_params: dict = None):
        """작업 즉시 실행 (별도 트리거로 1회 실행)"""
        job_func = get_job_func(job_type)
        self._scheduler.add_job(
            _run_job_with_tracking,
            trigger=DateTrigger(),
            id=f"{job_id}_manual_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            name=f"{job_name} (수동 실행)",
            kwargs={
                "schedule_id": schedule_id,
                "job_id": job_id,
                "job_name": job_name,
                "job_type": job_type,
                "job_params": job_params,
            },
        )
        logger.info(f"수동 실행 요청: {job_id}")

    async def sync_from_db(self, schedules: list[Schedule]):
        """앱 시작 시 DB의 활성 스케줄을 APScheduler에 복원"""
        for schedule in schedules:
            try:
                await self.add_schedule(schedule)
            except Exception as e:
                logger.error(
                    f"스케줄 복원 실패: {schedule.job_id} - {e}"
                )
        logger.info(f"{len(schedules)}개 스케줄 복원 완료")

    def get_next_run_time(self, job_id: str) -> datetime | None:
        """다음 실행 시각 조회"""
        job = self._scheduler.get_job(job_id)
        if job and job.next_run_time:
            return job.next_run_time.replace(tzinfo=None)
        return None

    def get_status(self) -> dict:
        """스케줄러 상태 조회"""
        jobs = self._scheduler.get_jobs()
        return {
            "running": self._scheduler.running,
            "jobs_count": len(jobs),
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": (
                        job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                        if job.next_run_time
                        else None
                    ),
                    "trigger": str(job.trigger),
                }
                for job in jobs
            ],
        }


async def _run_job_with_tracking(
    schedule_id: int,
    job_id: str,
    job_name: str,
    job_type: str,
    job_params: dict = None,
):
    """작업 실행 + 이력 기록 (자체 DB 세션 사용)"""
    async with AsyncSessionPrimary() as db:
        # 1. history 생성 (status=running)
        history = ScheduledJobHistory(
            job_id=job_id,
            job_name=job_name,
            status="running",
            started_at=datetime.utcnow(),
            schedule_id=schedule_id,
            created_at=datetime.utcnow(),
        )
        db.add(history)
        await db.commit()
        await db.refresh(history)

        started = datetime.utcnow()
        try:
            # 2. 작업 함수 실행
            job_func = get_job_func(job_type)
            result_summary = await job_func(job_params)

            # 3. 성공 처리
            finished = datetime.utcnow()
            history.status = "success"
            history.finished_at = finished
            history.duration_seconds = int(
                (finished - started).total_seconds()
            )
            history.result_summary = result_summary
            await db.commit()

            # Schedule 상태 업데이트
            from sqlalchemy import select, update

            stmt = (
                update(Schedule)
                .where(Schedule.id == schedule_id)
                .values(
                    last_run_at=finished,
                    last_status="success",
                )
            )
            await db.execute(stmt)
            await db.commit()

            logger.info(f"[{job_name}] 실행 성공: {result_summary}")

        except Exception as e:
            # 3. 실패 처리
            finished = datetime.utcnow()
            history.status = "failed"
            history.finished_at = finished
            history.duration_seconds = int(
                (finished - started).total_seconds()
            )
            history.error_message = str(e)[:1000]
            await db.commit()

            # Schedule 상태 업데이트
            from sqlalchemy import update

            stmt = (
                update(Schedule)
                .where(Schedule.id == schedule_id)
                .values(
                    last_run_at=finished,
                    last_status="failed",
                )
            )
            await db.execute(stmt)
            await db.commit()

            logger.error(f"[{job_name}] 실행 실패: {e}", exc_info=True)


# 싱글턴 인스턴스
scheduler_engine = SchedulerEngine()
