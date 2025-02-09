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
