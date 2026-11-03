"""배치 실행기

BackgroundTasks 방식과 APScheduler 방식의 배치 실행을 담당합니다.
"""

import asyncio
import logging
import uuid

from src.common.scheduler import scheduler
from src.domains.batch.schemas import BatchMethod, BatchStatus
from src.domains.batch.service import (
    BatchJob,
    create_batch,
    process_batch,
)

logger = logging.getLogger(__name__)


async def execute_background_batch(
    _batch_job: BatchJob, _fail_rate: float
) -> None:
    """BackgroundTasks 진입점

    예외 발생 시 status=FAILED로 전환합니다.
    """
    try:
        await process_batch(_batch_job, _fail_rate)
    except Exception as e:
        _batch_job.status = BatchStatus.FAILED
        _batch_job.error = "배치 처리 중 오류가 발생했습니다"
        logger.error(f"배치 {_batch_job.job_id} 실패: {e}")


def register_scheduler_batch(
    _total_items: int,
    _chunk_size: int,
    _fail_rate: float,
    _interval_seconds: int,
) -> str:
    """APScheduler interval 작업 등록

    scheduler_job_id를 반환합니다.
    max_instances=1로 중복 실행을 방지합니다.
    매 interval마다 새 BatchJob을 생성하여 /api/batch/jobs에 기록됩니다.
    """
    scheduler_job_id = f"batch_{uuid.uuid4().hex[:8]}"

    async def _run():
        batch_job = create_batch(
            method=BatchMethod.SCHEDULER,
            total_items=_total_items,
            chunk_size=_chunk_size,
            fail_rate=_fail_rate,
        )
        batch_job.scheduler_job_id = scheduler_job_id
        try:
            await process_batch(batch_job, _fail_rate)
        except Exception as e:
            batch_job.status = BatchStatus.FAILED
            batch_job.error = "스케줄러 배치 처리 중 오류가 발생했습니다"
            logger.error(f"스케줄러 배치 {batch_job.job_id} 실패: {e}")

    scheduler.add_job(
        _run,
        trigger="interval",
        seconds=_interval_seconds,
        id=scheduler_job_id,
        name=f"배치 작업 ({scheduler_job_id})",
        max_instances=1,
        replace_existing=True,
    )

    logger.info(
        f"스케줄러 배치 등록: {scheduler_job_id}, "
        f"간격={_interval_seconds}초"
    )
    return scheduler_job_id


def remove_scheduler_batch(_scheduler_job_id: str) -> None:
    """스케줄러에서 배치 작업 제거"""
    scheduler.remove_job(_scheduler_job_id)
    logger.info(f"스케줄러 배치 제거: {_scheduler_job_id}")
