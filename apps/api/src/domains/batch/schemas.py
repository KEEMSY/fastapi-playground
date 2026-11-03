"""배치 처리 스키마

배치 작업의 요청/응답 Pydantic 모델을 정의합니다.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, computed_field


class BatchMethod(str, Enum):
    BACKGROUND_TASK = "background_task"
    SCHEDULER = "scheduler"


class BatchStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BatchRunRequest(BaseModel):
    total_items: int = Field(ge=100, le=1000, default=500)
    chunk_size: int = Field(ge=10, le=200, default=50)
    fail_rate: float = Field(ge=0.0, le=0.5, default=0.05)


class SchedulerRegisterRequest(BaseModel):
    total_items: int = Field(ge=100, le=1000, default=500)
    chunk_size: int = Field(ge=10, le=200, default=50)
    fail_rate: float = Field(ge=0.0, le=0.5, default=0.05)
    interval_seconds: int = Field(ge=10, le=3600, default=60)


class ChunkResultResponse(BaseModel):
    chunk_index: int
    size: int
    success_count: int
    fail_count: int
    started_at: datetime
    completed_at: datetime
    error: Optional[str] = None


class BatchJobResponse(BaseModel):
    job_id: str
    method: str
    status: str
    total_items: int
    chunk_size: int
    fail_rate: float
    created_at: datetime
    processed_items: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    scheduler_job_id: Optional[str] = None
    chunks: List[ChunkResultResponse] = []

    @computed_field
    @property
    def progress_percent(self) -> float:
        if self.total_items == 0:
            return 0.0
        return round(self.processed_items / self.total_items * 100, 2)

    @computed_field
    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return round(
                (self.completed_at - self.started_at).total_seconds(), 4
            )
        return None


class BatchJobSummary(BaseModel):
    job_id: str
    method: str
    status: str
    total_items: int
    processed_items: int
    created_at: datetime
    progress_percent: float
    duration_seconds: Optional[float] = None
    scheduler_job_id: Optional[str] = None


class SchedulerRegisterResponse(BaseModel):
    """스케줄러 배치 등록 응답 — BatchJob과 별개로 등록 정보만 반환"""
    scheduler_job_id: str
    interval_seconds: int
    total_items: int
    chunk_size: int
    message: str
