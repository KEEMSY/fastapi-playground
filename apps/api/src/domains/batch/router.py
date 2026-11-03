"""배치 처리 라우터

API 엔드포인트:
  POST   /api/batch/background/run          - BackgroundTasks 배치 실행
  POST   /api/batch/scheduler/register      - APScheduler 배치 등록
  DELETE /api/batch/scheduler/{job_id}      - 스케줄러 배치 제거
  GET    /api/batch/jobs                    - 배치 작업 목록
  GET    /api/batch/jobs/{job_id}           - 배치 작업 상세
  DELETE /api/batch/clear                   - 완료 배치 삭제
"""

import logging

from apscheduler.jobstores.base import JobLookupError
from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from src.domains.batch import service as batch_service
from src.domains.batch.executor import (
    execute_background_batch,
    register_scheduler_batch,
    remove_scheduler_batch,
)
from src.domains.batch.schemas import (
    BatchJobResponse,
    BatchJobSummary,
    BatchMethod,
    BatchStatus,
    BatchRunRequest,
    SchedulerRegisterRequest,
    SchedulerRegisterResponse,
)

router = APIRouter(prefix="/api/batch")
logger = logging.getLogger(__name__)


@router.post("/background/run", response_model=BatchJobResponse, status_code=status.HTTP_201_CREATED)
async def batch_background_run(
    _batch_run: BatchRunRequest,
    background_tasks: BackgroundTasks,
):
    """BackgroundTasks 방식으로 배치 작업 실행

    즉시 BatchJobResponse를 반환하고, 배치는 백그라운드에서 실행됩니다.
    """
    batch_job = batch_service.create_batch(
        method=BatchMethod.BACKGROUND_TASK,
        total_items=_batch_run.total_items,
        chunk_size=_batch_run.chunk_size,
        fail_rate=_batch_run.fail_rate,
    )
    background_tasks.add_task(
        execute_background_batch, batch_job, _batch_run.fail_rate
    )
    logger.info(
        f"배치 시작 (BackgroundTask): job_id={batch_job.job_id}, "
        f"total={_batch_run.total_items}, chunk={_batch_run.chunk_size}"
    )
    return batch_service.to_response(batch_job)


@router.post(
    "/scheduler/register",
    response_model=SchedulerRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def batch_scheduler_register(
    _register_request: SchedulerRegisterRequest,
):
    """APScheduler interval 방식으로 배치 작업 등록

    지정된 간격(interval_seconds)마다 배치 작업이 자동 실행됩니다.
    실행될 때마다 새 BatchJob이 생성되어 /api/batch/jobs 목록에 기록됩니다.
    """
    scheduler_job_id = register_scheduler_batch(
        _total_items=_register_request.total_items,
        _chunk_size=_register_request.chunk_size,
        _fail_rate=_register_request.fail_rate,
        _interval_seconds=_register_request.interval_seconds,
    )
    logger.info(
        f"배치 등록 (Scheduler): scheduler_job_id={scheduler_job_id}, "
        f"interval={_register_request.interval_seconds}초"
    )
    return SchedulerRegisterResponse(
        scheduler_job_id=scheduler_job_id,
        interval_seconds=_register_request.interval_seconds,
        total_items=_register_request.total_items,
        chunk_size=_register_request.chunk_size,
        message=f"스케줄러 배치 등록 완료. {_register_request.interval_seconds}초마다 자동 실행됩니다.",
    )


@router.delete(
    "/scheduler/{scheduler_job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def batch_scheduler_remove(scheduler_job_id: str):
    """스케줄러에 등록된 배치 작업 제거

    scheduler_job_id는 /scheduler/register 응답의 scheduler_job_id를 사용합니다.
    """
    try:
        remove_scheduler_batch(scheduler_job_id)
    except JobLookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="등록된 스케줄러 작업을 찾을 수 없습니다",
        )
    logger.info(f"스케줄러 배치 제거: {scheduler_job_id}")


@router.get("/jobs", response_model=list[BatchJobSummary])
async def batch_list(
    method: BatchMethod | None = None,
    status_filter: BatchStatus | None = None,
):
    """배치 작업 목록 조회 (최신순, 필터 지원)

    method: background_task | scheduler
    status_filter: pending | running | completed | failed
    """
    jobs = batch_service.get_all_batches(
        method=method.value if method else None,
        batch_status=status_filter.value if status_filter else None,
    )
    return [batch_service.to_summary(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=BatchJobResponse)
async def batch_detail(job_id: str):
    """배치 작업 상세 조회"""
    batch_job = batch_service.get_batch(job_id)
    if not batch_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="배치 작업을 찾을 수 없습니다",
        )
    return batch_service.to_response(batch_job)


@router.delete("/clear", status_code=status.HTTP_204_NO_CONTENT)
async def batch_clear():
    """완료/실패 배치 작업 삭제

    스케줄러 방식 배치는 APScheduler job도 함께 제거합니다.
    """
    deleted_jobs = batch_service.clear_batches()
    for job in deleted_jobs:
        if job.scheduler_job_id:
            try:
                remove_scheduler_batch(job.scheduler_job_id)
            except Exception:
                pass  # 이미 제거됐거나 존재하지 않는 job은 무시
    logger.info(f"배치 이력 {len(deleted_jobs)}건 삭제")
