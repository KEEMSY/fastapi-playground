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