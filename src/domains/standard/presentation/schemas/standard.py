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

class StandardDbResponse(BaseModel):
    message: str
    session_info: DatabaseSessionInfo