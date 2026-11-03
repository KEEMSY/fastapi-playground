from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class StandardResponse(BaseModel):
    message: str

    model_config = ConfigDict(
        from_attributes=True,
        extra='forbid',
        json_schema_extra={
            "example": {
                "message": "test"
            },
            "description": "Standard API response format"
        }
    )

class DatabaseSessionInfo(BaseModel):
    total_connections: int
    active_connections: int
    threads_connected: str
    threads_running: str
    max_used_connections: str
    max_connections: int
    current_connections: int
    available_connections: int
    wait_timeout: int
    database_name: str
    user: str
    host: str
    port: int

class PoolInfo(BaseModel):
    max_connections: int
    current_connections: int
    available_connections: int
    wait_timeout: int

class QueryExecutionInfo(BaseModel):
    query_number: int
    delay_seconds: float
    actual_duration_seconds: float

class StandardDbResponse(BaseModel):
    message: str
    session_info: DatabaseSessionInfo
    pool_info: PoolInfo
    query_executions: Optional[List[QueryExecutionInfo]] = None


class PerformanceDataItem(BaseModel):
    """성능 테스트 데이터 아이템"""
    id: int
    title: str
    content: str
    category: str
    status: str
    view_count: int
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class BulkReadResponse(BaseModel):
    """대용량 조회 응답"""
    items: List[PerformanceDataItem]
    total_count: int
    limit: int
    offset: int
    query_time_ms: float
    message: str