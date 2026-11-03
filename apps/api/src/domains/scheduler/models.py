"""
스케줄러 관련 DB 모델
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index

from src.database.database import Base


class ScheduledJobHistory(Base):
    """스케줄 작업 실행 이력

    각 스케줄 작업의 실행 기록을 저장합니다.
    - 실행 시작/종료 시간
    - 성공/실패 상태
    - 에러 메시지 (실패 시)
    """
    __tablename__ = "scheduled_job_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), nullable=False, index=True)  # 작업 ID (예: test_job_every_minute)
    job_name = Column(String(200), nullable=False)  # 작업 이름
    status = Column(String(20), nullable=False, index=True)  # success, failed, running
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # 실행 시간 (초)
    error_message = Column(Text, nullable=True)  # 에러 메시지
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_job_history_job_id_created", "job_id", "created_at"),
        Index("ix_job_history_status_created", "status", "created_at"),
    )
