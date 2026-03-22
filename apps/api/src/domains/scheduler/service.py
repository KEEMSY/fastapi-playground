"""
스케줄러 서비스 로직

기존 동기 서비스 유지 + async 서비스 추가
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from src.domains.scheduler.models import Schedule, ScheduledJobHistory

logger = logging.getLogger(__name__)


# ===== 기존 동기 서비스 (하위 호환) =====


def create_job_history(
    db: Session,
    job_id: str,
    job_name: str,
    status: str = "running",
) -> ScheduledJobHistory:
    """스케줄 작업 실행 이력 생성 (동기)"""
    history = ScheduledJobHistory(
        job_id=job_id,
        job_name=job_name,
        status=status,
        started_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history


def update_job_history(
    db: Session,
    history_id: int,
    status: str,
    error_message: str = None,
) -> ScheduledJobHistory:
    """스케줄 작업 실행 이력 업데이트 (동기)"""
    history = (
        db.query(ScheduledJobHistory)
        .filter(ScheduledJobHistory.id == history_id)
        .first()
    )

    if history:
        history.status = status
        history.finished_at = datetime.utcnow()
        history.duration_seconds = int(
            (history.finished_at - history.started_at).total_seconds()
        )
        if error_message:
            history.error_message = error_message
        db.commit()
        db.refresh(history)

    return history


def get_job_histories(
    db: Session,
    job_id: str = None,
    status: str = None,
    limit: int = 100,
    offset: int = 0,
):
    """스케줄 작업 실행 이력 조회 (동기)"""
    query = db.query(ScheduledJobHistory)

    if job_id:
        query = query.filter(ScheduledJobHistory.job_id == job_id)

    if status:
        query = query.filter(ScheduledJobHistory.status == status)

    query = query.order_by(ScheduledJobHistory.created_at.desc())
    query = query.limit(limit).offset(offset)

    return query.all()


# ===== 신규 async 서비스 =====


async def get_schedule_list(
    db: AsyncSession,
    page: int = 0,
    size: int = 20,
    is_active: bool = None,
):
    """스케줄 목록 조회 (async)"""
    query = select(Schedule)

    if is_active is not None:
        query = query.where(Schedule.is_active == is_active)

    # 총 개수
    count_stmt = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # 페이징 + 정렬
    query = (
        query.order_by(Schedule.created_at.desc())
        .offset(page * size)
        .limit(size)
    )
    result = await db.execute(query)
    schedules = result.scalars().all()

    return total, schedules


async def get_schedule(db: AsyncSession, schedule_id: int) -> Schedule | None:
    """스케줄 상세 조회 (이력 포함, async)"""
    stmt = (
        select(Schedule)
        .where(Schedule.id == schedule_id)
        .options(selectinload(Schedule.histories))
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_schedule_by_job_id(
    db: AsyncSession, job_id: str
) -> Schedule | None:
    """job_id로 스케줄 조회"""
    stmt = select(Schedule).where(Schedule.job_id == job_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def create_schedule(
    db: AsyncSession,
    _schedule_create,
    user_id: int = None,
) -> Schedule:
    """스케줄 생성 (async)"""
    job_id = f"{_schedule_create.job_type}_{uuid.uuid4().hex[:8]}"

    schedule = Schedule(
        job_id=job_id,
        name=_schedule_create.name,
        description=_schedule_create.description,
        job_type=_schedule_create.job_type,
        trigger_type=_schedule_create.trigger_type,
        trigger_config=_schedule_create.trigger_config,
        job_params=_schedule_create.job_params,
        is_active=True,
        user_id=user_id,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def update_schedule(
    db: AsyncSession,
    schedule_model: Schedule,
    _schedule_update,
) -> Schedule:
    """스케줄 수정 (async)"""
    if _schedule_update.name is not None:
        schedule_model.name = _schedule_update.name
    if _schedule_update.description is not None:
        schedule_model.description = _schedule_update.description
    if _schedule_update.job_type is not None:
        schedule_model.job_type = _schedule_update.job_type
    if _schedule_update.trigger_type is not None:
        schedule_model.trigger_type = _schedule_update.trigger_type
    if _schedule_update.trigger_config is not None:
        schedule_model.trigger_config = _schedule_update.trigger_config
    if _schedule_update.job_params is not None:
        schedule_model.job_params = _schedule_update.job_params

    schedule_model.updated_at = datetime.utcnow()
    db.add(schedule_model)
    await db.commit()
    await db.refresh(schedule_model)
    return schedule_model


async def delete_schedule(db: AsyncSession, schedule_model: Schedule):
    """스케줄 삭제 (async)"""
    await db.delete(schedule_model)
    await db.commit()


async def toggle_schedule(
    db: AsyncSession, schedule_model: Schedule
) -> Schedule:
    """스케줄 활성/비활성 토글 (async)"""
    schedule_model.is_active = not schedule_model.is_active
    schedule_model.updated_at = datetime.utcnow()
    db.add(schedule_model)
    await db.commit()
    await db.refresh(schedule_model)
    return schedule_model


async def get_active_schedules(db: AsyncSession) -> list[Schedule]:
    """활성 스케줄 전체 조회 (앱 시작 시 복원용)"""
    stmt = select(Schedule).where(Schedule.is_active == True)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_schedule_history(
    db: AsyncSession,
    schedule_id: int,
    limit: int = 50,
    offset: int = 0,
):
    """특정 스케줄의 이력 조회 (async)"""
    query = select(ScheduledJobHistory).where(
        ScheduledJobHistory.schedule_id == schedule_id
    )

    count_stmt = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    query = (
        query.order_by(ScheduledJobHistory.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    histories = result.scalars().all()

    return total, histories


async def get_all_history(
    db: AsyncSession,
    job_id: str = None,
    status: str = None,
    limit: int = 100,
    offset: int = 0,
):
    """전체 이력 조회 (async)"""
    query = select(ScheduledJobHistory)

    if job_id:
        query = query.where(ScheduledJobHistory.job_id == job_id)
    if status:
        query = query.where(ScheduledJobHistory.status == status)

    count_stmt = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    query = (
        query.order_by(ScheduledJobHistory.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    histories = result.scalars().all()

    return total, histories


async def update_schedule_next_run(
    db: AsyncSession, schedule_id: int, next_run_at: datetime
):
    """스케줄 다음 실행 시각 업데이트"""
    from sqlalchemy import update

    stmt = (
        update(Schedule)
        .where(Schedule.id == schedule_id)
        .values(next_run_at=next_run_at)
    )
    await db.execute(stmt)
    await db.commit()
