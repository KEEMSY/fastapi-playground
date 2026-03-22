"""
스케줄러 관련 DB 모델
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from src.database.database import Base


class Schedule(Base):
    """스케줄 작업 정의

    DB 기반 스케줄 관리를 위한 모델.
    APScheduler와 동기화하여 동적 스케줄 CRUD를 지원합니다.
    """

    __tablename__ = "schedule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    job_type = Column(
        String(50), nullable=False
    )  # data_cleanup|api_sync|notification|sample_log
    trigger_type = Column(String(20), nullable=False)  # cron|interval|date
    trigger_config = Column(JSON, nullable=False)
    job_params = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    next_run_at = Column(DateTime, nullable=True)
    last_run_at = Column(DateTime, nullable=True)
    last_status = Column(String(20), nullable=True)  # success|failed|running
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    histories = relationship(
        "ScheduledJobHistory",
        back_populates="schedule",
        order_by="desc(ScheduledJobHistory.created_at)",
    )


class ScheduledJobHistory(Base):
    """스케줄 작업 실행 이력

    각 스케줄 작업의 실행 기록을 저장합니다.
    - 실행 시작/종료 시간
    - 성공/실패 상태
    - 에러 메시지 (실패 시)
    """

    __tablename__ = "scheduled_job_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(
        String(100), nullable=False, index=True
    )  # 작업 ID (예: test_job_every_minute)
    job_name = Column(String(200), nullable=False)  # 작업 이름
    status = Column(
        String(20), nullable=False, index=True
    )  # success, failed, running
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # 실행 시간 (초)
    error_message = Column(Text, nullable=True)  # 에러 메시지
    result_summary = Column(Text, nullable=True)  # 실행 결과 요약
    schedule_id = Column(
        Integer, ForeignKey("schedule.id"), nullable=True
    )  # Schedule FK
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    schedule = relationship("Schedule", back_populates="histories")

    __table_args__ = (
        Index("ix_job_history_job_id_created", "job_id", "created_at"),
        Index("ix_job_history_status_created", "status", "created_at"),
        Index("ix_job_history_schedule_id", "schedule_id"),
    )
