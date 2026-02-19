"""
스케줄러 관리 API

스케줄 작업 조회, 수동 실행 등의 관리 기능을 제공합니다.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from src.common.scheduler import get_scheduled_jobs, run_job_now, scheduler
from src.database.database import SessionLocal
from src.domains.scheduler.service import get_job_histories
from sqlalchemy.orm import Session


def get_db():
    """동기 DB 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


class ScheduledJobResponse(BaseModel):
    """스케줄 작업 응답 모델"""
    id: str
    name: str
    next_run: Optional[str]
    trigger: str


class JobExecutionResponse(BaseModel):
    """작업 실행 응답 모델"""
    success: bool
    message: str
    job_id: str


class JobHistoryResponse(BaseModel):
    """작업 실행 이력 응답 모델"""
    id: int
    job_id: str
    job_name: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    duration_seconds: Optional[int]
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/jobs", response_model=List[ScheduledJobResponse])
async def list_scheduled_jobs():
    """등록된 모든 스케줄 작업 조회

    Returns:
        List[ScheduledJobResponse]: 스케줄 작업 목록
    """
    jobs = get_scheduled_jobs()
    return jobs


@router.post("/jobs/{job_id}/run", response_model=JobExecutionResponse)
async def run_job_manually(job_id: str):
    """스케줄 작업 수동 실행

    Args:
        job_id: 실행할 작업 ID

    Returns:
        JobExecutionResponse: 실행 결과

    Raises:
        HTTPException: 작업을 찾을 수 없는 경우
    """
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"작업을 찾을 수 없습니다: {job_id}"
        )

    success = run_job_now(job_id)

    return JobExecutionResponse(
        success=success,
        message="작업 실행 완료" if success else "작업 실행 실패",
        job_id=job_id
    )


@router.get("/status")
async def get_scheduler_status():
    """스케줄러 상태 조회

    Returns:
        dict: 스케줄러 상태 정보
    """
    return {
        "running": scheduler.running,
        "jobs_count": len(scheduler.get_jobs()),
        "state": scheduler.state
    }


@router.get("/history", response_model=List[JobHistoryResponse])
async def list_job_histories(
    job_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """스케줄 작업 실행 이력 조회

    Args:
        job_id: 작업 ID 필터 (선택)
        status: 상태 필터 (success, failed, running) (선택)
        limit: 조회 개수 제한
        offset: 오프셋
        db: DB 세션

    Returns:
        List[JobHistoryResponse]: 실행 이력 목록
    """
    histories = get_job_histories(
        db=db,
        job_id=job_id,
        status=status,
        limit=limit,
        offset=offset
    )
    return histories
