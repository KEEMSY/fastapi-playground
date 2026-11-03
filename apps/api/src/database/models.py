from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Index

from src.database.database import Base


class PerformanceTestData(Base):
    """
    성능 테스트용 데이터 모델
    - 동기/비동기 대용량 조회 성능 비교를 위한 테이블
    - 10만 건 이상의 데이터로 실제 운영 환경 시뮬레이션
    """
    __tablename__ = "performance_test_data"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="active")
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_perf_category_status', 'category', 'status'),
        Index('ix_perf_created_at_status', 'created_at', 'status'),
    )

    def __repr__(self):
        return f"<PerformanceTestData(id={self.id}, title='{self.title}', category='{self.category}')>"
