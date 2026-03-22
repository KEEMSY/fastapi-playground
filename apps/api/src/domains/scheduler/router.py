"""
스케줄러 관리 API

기존 엔드포인트 유지 + 10개 신규 엔드포인트 추가
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from starlette import status

from src.common.scheduler import get_scheduled_jobs, run_job_now, scheduler
from src.database.database import get_async_db, get_read_db
from src.domains.scheduler import schemas, service
from src.domains.scheduler.scheduler_engine import scheduler_engine
from src.domains.user.router import get_current_user_with_async
from src.domains.user.schemas import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


# ===== 기존 엔드포인트 (하위 호환) =====


@router.get("/jobs", response_model=List[schemas.ScheduledJobResponse])
async def list_scheduled_jobs():
    """등록된 모든 스케줄 작업 조회 (기존)"""
    jobs = get_scheduled_jobs()
    return jobs


@router.post(
    "/jobs/{job_id}/run", response_model=schemas.JobExecutionResponse
)
async def run_job_manually(job_id: str):
    """스케줄 작업 수동 실행 (기존)"""
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"작업을 찾을 수 없습니다: {job_id}",
        )

    success = run_job_now(job_id)

    return schemas.JobExecutionResponse(
        success=success,
        message="작업 실행 완료" if success else "작업 실행 실패",
        job_id=job_id,
    )


@router.get("/history", response_model=List[schemas.HistoryResponse])
async def list_job_histories(
    job_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_read_db),
):
    """스케줄 작업 실행 이력 조회 (기존)"""
    histories = service.get_job_histories(
        db=db,
        job_id=job_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return histories


# ===== 신규 엔드포인트 (Schedule CRUD) =====


@router.get(
    "/schedules", response_model=schemas.ScheduleListResponse
)
async def schedule_list(
    page: int = 0,
    size: int = 20,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """스케줄 목록 조회"""
    total, schedules = await service.get_schedule_list(
        db, page=page, size=size, is_active=is_active
    )
    return {"total": total, "schedules": schedules}


@router.get(
    "/schedules/{schedule_id}",
    response_model=schemas.ScheduleDetailResponse,
)
async def schedule_detail(
    schedule_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """스케줄 상세 조회 (이력 포함)"""
    schedule = await service.get_schedule(db, schedule_id)
    if schedule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="스케줄을 찾을 수 없습니다",
        )

    # next_run_at 동기화
    next_run = scheduler_engine.get_next_run_time(schedule.job_id)
    if next_run != schedule.next_run_at:
        schedule.next_run_at = next_run

    return schedule


@router.post(
    "/schedules", status_code=status.HTTP_204_NO_CONTENT
)
async def schedule_create(
    _schedule_create: schemas.ScheduleCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async),
):
    """스케줄 생성"""
    schedule = await service.create_schedule(
        db, _schedule_create=_schedule_create, user_id=current_user.id
    )

    # APScheduler에 등록
    await scheduler_engine.add_schedule(schedule)

    # next_run_at 업데이트
    next_run = scheduler_engine.get_next_run_time(schedule.job_id)
    if next_run:
        await service.update_schedule_next_run(db, schedule.id, next_run)


@router.put(
    "/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def schedule_update(
    schedule_id: int,
    _schedule_update: schemas.ScheduleUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async),
):
    """스케줄 수정"""
    schedule = await service.get_schedule(db, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="스케줄을 찾을 수 없습니다",
        )

    if schedule.user_id and schedule.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="수정 권한이 없습니다",
        )

    # APScheduler에서 기존 작업 제거
    await scheduler_engine.remove_schedule(schedule.job_id)

    # DB 업데이트
    updated = await service.update_schedule(
        db, schedule_model=schedule, _schedule_update=_schedule_update
    )

    # 활성 상태면 APScheduler에 재등록
    if updated.is_active:
        await scheduler_engine.add_schedule(updated)
        next_run = scheduler_engine.get_next_run_time(updated.job_id)
        if next_run:
            await service.update_schedule_next_run(db, updated.id, next_run)


@router.delete(
    "/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def schedule_delete(
    schedule_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async),
):
    """스케줄 삭제"""
    schedule = await service.get_schedule(db, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="스케줄을 찾을 수 없습니다",
        )

    if schedule.user_id and schedule.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="삭제 권한이 없습니다",
        )

    # APScheduler에서 제거
    await scheduler_engine.remove_schedule(schedule.job_id)

    # DB 삭제
    await service.delete_schedule(db, schedule_model=schedule)


@router.patch(
    "/schedules/{schedule_id}/toggle",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def schedule_toggle(
    schedule_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async),
):
    """스케줄 활성/비활성 토글"""
    schedule = await service.get_schedule(db, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="스케줄을 찾을 수 없습니다",
        )

    if schedule.user_id and schedule.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다",
        )

    toggled = await service.toggle_schedule(db, schedule_model=schedule)

    if toggled.is_active:
        # 활성화: APScheduler에 등록
        await scheduler_engine.add_schedule(toggled)
        next_run = scheduler_engine.get_next_run_time(toggled.job_id)
        if next_run:
            await service.update_schedule_next_run(db, toggled.id, next_run)
    else:
        # 비활성화: APScheduler에서 제거
        await scheduler_engine.remove_schedule(toggled.job_id)


@router.post(
    "/schedules/{schedule_id}/run",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def schedule_run_now(
    schedule_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async),
):
    """스케줄 즉시 실행"""
    schedule = await service.get_schedule(db, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="스케줄을 찾을 수 없습니다",
        )

    await scheduler_engine.run_now(
        job_id=schedule.job_id,
        schedule_id=schedule.id,
        job_name=schedule.name,
        job_type=schedule.job_type,
        job_params=schedule.job_params,
    )


@router.get(
    "/schedules/{schedule_id}/history",
    response_model=schemas.HistoryListResponse,
)
async def schedule_history(
    schedule_id: int,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_async_db),
):
    """특정 스케줄의 실행 이력 조회"""
    # 스케줄 존재 확인
    schedule = await service.get_schedule(db, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="스케줄을 찾을 수 없습니다",
        )

    total, histories = await service.get_schedule_history(
        db, schedule_id=schedule_id, limit=limit, offset=offset
    )
    return {"total": total, "histories": histories}


@router.get(
    "/history/all",
    response_model=schemas.HistoryListResponse,
)
async def schedule_history_all(
    job_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_async_db),
):
    """전체 이력 조회 (async)"""
    total, histories = await service.get_all_history(
        db, job_id=job_id, status=status_filter, limit=limit, offset=offset
    )
    return {"total": total, "histories": histories}


@router.get("/status", response_model=schemas.SchedulerStatusResponse)
async def schedule_status(
    db: AsyncSession = Depends(get_async_db),
):
    """스케줄러 상태 조회"""
    engine_status = scheduler_engine.get_status()

    # DB에서 활성 스케줄 수 조회
    total, _ = await service.get_schedule_list(db, is_active=True, size=0)

    return {
        "running": engine_status["running"],
        "jobs_count": engine_status["jobs_count"],
        "scheduled_count": len(scheduler.get_jobs()) if scheduler.running else 0,
        "active_schedules": total,
    }
