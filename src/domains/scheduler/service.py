"""
스케줄러 서비스 로직

스케줄 작업 실행 이력 관리 기능을 제공합니다.
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session

from src.domains.scheduler.models import ScheduledJobHistory

logger = logging.getLogger(__name__)


def create_job_history(
    db: Session,
    job_id: str,
    job_name: str,
    status: str = "running"
) -> ScheduledJobHistory:
    """스케줄 작업 실행 이력 생성

    Args:
        db: DB 세션
        job_id: 작업 ID
        job_name: 작업 이름
        status: 작업 상태 (running, success, failed)

    Returns:
        ScheduledJobHistory: 생성된 실행 이력
    """
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
    error_message: str = None
) -> ScheduledJobHistory:
    """스케줄 작업 실행 이력 업데이트

    Args:
        db: DB 세션
        history_id: 실행 이력 ID
        status: 작업 상태 (success, failed)
        error_message: 에러 메시지 (실패 시)

    Returns:
        ScheduledJobHistory: 업데이트된 실행 이력
    """
    history = db.query(ScheduledJobHistory).filter(
        ScheduledJobHistory.id == history_id
    ).first()

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
    offset: int = 0
):
    """스케줄 작업 실행 이력 조회

    Args:
        db: DB 세션
        job_id: 작업 ID 필터
        status: 상태 필터
        limit: 조회 개수 제한
        offset: 오프셋

    Returns:
        list: 실행 이력 목록
    """
    query = db.query(ScheduledJobHistory)

    if job_id:
        query = query.filter(ScheduledJobHistory.job_id == job_id)

    if status:
        query = query.filter(ScheduledJobHistory.status == status)

    query = query.order_by(ScheduledJobHistory.created_at.desc())
    query = query.limit(limit).offset(offset)

    return query.all()
