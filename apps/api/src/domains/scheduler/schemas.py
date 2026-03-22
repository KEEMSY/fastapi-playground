"""
스케줄러 Pydantic 스키마
"""

from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, field_validator


# ===== Schedule 스키마 =====


class ScheduleCreate(BaseModel):
    """스케줄 생성 요청"""

    name: str
    description: Optional[str] = None
    job_type: str  # data_cleanup|api_sync|notification|sample_log
    trigger_type: str  # cron|interval|date
    trigger_config: dict
    job_params: Optional[dict] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("스케줄 이름은 비어있을 수 없습니다")
        return v.strip()

    @field_validator("job_type")
    @classmethod
    def valid_job_type(cls, v):
        allowed = {"data_cleanup", "api_sync", "notification", "sample_log"}
        if v not in allowed:
            raise ValueError(
                f"허용되지 않는 작업 유형입니다: {v}. 허용: {', '.join(sorted(allowed))}"
            )
        return v

    @field_validator("trigger_type")
    @classmethod
    def valid_trigger_type(cls, v):
        allowed = {"cron", "interval", "date"}
        if v not in allowed:
            raise ValueError(
                f"허용되지 않는 트리거 유형입니다: {v}. 허용: {', '.join(sorted(allowed))}"
            )
        return v


class ScheduleUpdate(BaseModel):
    """스케줄 수정 요청"""

    name: Optional[str] = None
    description: Optional[str] = None
    job_type: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[dict] = None
    job_params: Optional[dict] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError("스케줄 이름은 비어있을 수 없습니다")
        return v.strip() if v else v

    @field_validator("job_type")
    @classmethod
    def valid_job_type(cls, v):
        if v is None:
            return v
        allowed = {"data_cleanup", "api_sync", "notification", "sample_log"}
        if v not in allowed:
            raise ValueError(
                f"허용되지 않는 작업 유형입니다: {v}. 허용: {', '.join(sorted(allowed))}"
            )
        return v

    @field_validator("trigger_type")
    @classmethod
    def valid_trigger_type(cls, v):
        if v is None:
            return v
        allowed = {"cron", "interval", "date"}
        if v not in allowed:
            raise ValueError(
                f"허용되지 않는 트리거 유형입니다: {v}. 허용: {', '.join(sorted(allowed))}"
            )
        return v


class ScheduleResponse(BaseModel):
    """스케줄 응답"""

    id: int
    job_id: str
    name: str
    description: Optional[str] = None
    job_type: str
    trigger_type: str
    trigger_config: dict
    job_params: Optional[dict] = None
    is_active: bool
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    last_status: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_id: Optional[int] = None

    model_config = {"from_attributes": True}


class ScheduleDetailResponse(ScheduleResponse):
    """스케줄 상세 응답 (이력 포함)"""

    histories: List["HistoryResponse"] = []


class ScheduleListResponse(BaseModel):
    """스케줄 목록 응답"""

    total: int
    schedules: List[ScheduleResponse] = []


# ===== History 스키마 =====


class HistoryResponse(BaseModel):
    """작업 실행 이력 응답"""

    id: int
    job_id: str
    job_name: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    error_message: Optional[str] = None
    result_summary: Optional[str] = None
    schedule_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class HistoryListResponse(BaseModel):
    """이력 목록 응답"""

    total: int
    histories: List[HistoryResponse] = []


# ===== 기존 호환 스키마 =====


class ScheduledJobResponse(BaseModel):
    """기존 스케줄 작업 응답 (하위 호환)"""

    id: str
    name: str
    next_run: Optional[str] = None
    trigger: str


class JobExecutionResponse(BaseModel):
    """작업 실행 응답"""

    success: bool
    message: str
    job_id: str


class SchedulerStatusResponse(BaseModel):
    """스케줄러 상태 응답"""

    running: bool
    jobs_count: int
    scheduled_count: int
    active_schedules: int
