"""배치 처리 서비스

배치 작업 상태를 인메모리에서 관리하고, 청크 단위 배치 처리를 실행합니다.
"""

import asyncio
import logging
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from src.domains.batch.schemas import (
    BatchJobResponse,
    BatchJobSummary,
    BatchMethod,
    BatchStatus,
    ChunkResultResponse,
)

logger = logging.getLogger(__name__)


@dataclass
class ChunkResult:
    chunk_index: int
    size: int
    success_count: int
    fail_count: int
    started_at: datetime
    completed_at: datetime
    error: Optional[str] = None


@dataclass
class BatchJob:
    job_id: str
    method: BatchMethod
    status: BatchStatus
    total_items: int
    chunk_size: int
    fail_rate: float
    created_at: datetime
    processed_items: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    scheduler_job_id: Optional[str] = None
    chunks: list = field(default_factory=list)


# 인메모리 배치 저장소 (서버 재시작 시 초기화)
_batch_jobs: Dict[str, BatchJob] = {}
MAX_HISTORY = 50


def create_batch(
    method: BatchMethod,
    total_items: int,
    chunk_size: int,
    fail_rate: float,
) -> BatchJob:
    """새 배치 작업 생성 및 저장소 등록"""
    job_id = uuid.uuid4().hex
    batch_job = BatchJob(
        job_id=job_id,
        method=method,
        status=BatchStatus.PENDING,
        total_items=total_items,
        chunk_size=chunk_size,
        fail_rate=fail_rate,
        created_at=datetime.now(),
    )
    _batch_jobs[job_id] = batch_job

    # MAX_HISTORY 초과 시 가장 오래된 항목 자동 삭제
    if len(_batch_jobs) > MAX_HISTORY:
        oldest_key = min(
            _batch_jobs, key=lambda k: _batch_jobs[k].created_at
        )
        del _batch_jobs[oldest_key]

    return batch_job


def get_batch(job_id: str) -> Optional[BatchJob]:
    return _batch_jobs.get(job_id)


def get_all_batches(
    method: Optional[str] = None,
    batch_status: Optional[str] = None,
) -> List[BatchJob]:
    """배치 작업 목록 조회 (최신순, 필터 지원)"""
    jobs = list(_batch_jobs.values())

    if method:
        jobs = [j for j in jobs if j.method.value == method]
    if batch_status:
        jobs = [j for j in jobs if j.status.value == batch_status]

    return sorted(jobs, key=lambda j: j.created_at, reverse=True)


def clear_batches() -> List[BatchJob]:
    """완료/실패 배치 삭제 (실행 중 제외) — 삭제된 BatchJob 목록 반환

    caller가 scheduler_job_id를 확인하여 APScheduler에서도 제거할 수 있도록
    삭제된 BatchJob 목록을 반환합니다.
    """
    to_delete = [
        k
        for k, v in _batch_jobs.items()
        if v.status not in (BatchStatus.PENDING, BatchStatus.RUNNING)
    ]
    return [_batch_jobs.pop(k) for k in to_delete]


def to_response(batch_job: BatchJob) -> BatchJobResponse:
    return BatchJobResponse(
        job_id=batch_job.job_id,
        method=batch_job.method.value,
        status=batch_job.status.value,
        total_items=batch_job.total_items,
        chunk_size=batch_job.chunk_size,
        fail_rate=batch_job.fail_rate,
        created_at=batch_job.created_at,
        processed_items=batch_job.processed_items,
        started_at=batch_job.started_at,
        completed_at=batch_job.completed_at,
        error=batch_job.error,
        scheduler_job_id=batch_job.scheduler_job_id,
        chunks=[
            ChunkResultResponse(
                chunk_index=c.chunk_index,
                size=c.size,
                success_count=c.success_count,
                fail_count=c.fail_count,
                started_at=c.started_at,
                completed_at=c.completed_at,
                error=c.error,
            )
            for c in batch_job.chunks
        ],
    )


def to_summary(batch_job: BatchJob) -> BatchJobSummary:
    duration = None
    if batch_job.started_at and batch_job.completed_at:
        duration = round(
            (batch_job.completed_at - batch_job.started_at).total_seconds(),
            4,
        )

    progress = 0.0
    if batch_job.total_items > 0:
        progress = round(
            batch_job.processed_items / batch_job.total_items * 100, 2
        )

    return BatchJobSummary(
        job_id=batch_job.job_id,
        method=batch_job.method.value,
        status=batch_job.status.value,
        total_items=batch_job.total_items,
        processed_items=batch_job.processed_items,
        created_at=batch_job.created_at,
        progress_percent=progress,
        duration_seconds=duration,
        scheduler_job_id=batch_job.scheduler_job_id,
    )


async def process_batch(
    _batch_job: BatchJob, _fail_rate: float
) -> None:
    """청크 단위 배치 처리 실행

    각 아이템에 대해 I/O 시뮬레이션(asyncio.sleep)을 수행하고,
    fail_rate 확률로 실패를 발생시킵니다.
    """
    _batch_job.status = BatchStatus.RUNNING
    _batch_job.started_at = datetime.now()

    total = _batch_job.total_items
    chunk_size = _batch_job.chunk_size
    chunk_index = 0

    for offset in range(0, total, chunk_size):
        current_chunk_size = min(chunk_size, total - offset)
        chunk_started = datetime.now()
        success_count = 0
        fail_count = 0
        chunk_error = None

        try:
            for _ in range(current_chunk_size):
                await asyncio.sleep(0.01)  # I/O 시뮬레이션

                if random.random() < _fail_rate:
                    fail_count += 1
                else:
                    success_count += 1

                _batch_job.processed_items += 1
        except Exception as e:
            chunk_error = "청크 처리 중 오류가 발생했습니다"
            logger.error(f"청크 {chunk_index} 처리 오류: {e}")

        chunk_result = ChunkResult(
            chunk_index=chunk_index,
            size=current_chunk_size,
            success_count=success_count,
            fail_count=fail_count,
            started_at=chunk_started,
            completed_at=datetime.now(),
            error=chunk_error,
        )
        _batch_job.chunks.append(chunk_result)
        chunk_index += 1

        logger.info(
            f"배치 {_batch_job.job_id}: 청크 {chunk_index} 완료 "
            f"({_batch_job.processed_items}/{total})"
        )

    _batch_job.completed_at = datetime.now()
    _batch_job.status = BatchStatus.COMPLETED
    logger.info(f"배치 {_batch_job.job_id}: 처리 완료")
