import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.domains.user.schemas import User


class AsyncExampleSchema(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    create_date: Optional[datetime.datetime] = None
    modify_date: Optional[datetime.datetime] = None
    user: Optional[User] = None

    model_config = ConfigDict(
        from_attributes=True,
        extra='forbid'
    )


class ASyncExampleSchemaList(BaseModel):
    total: int
    example_list: list[AsyncExampleSchema] = []

    model_config = ConfigDict(
        from_attributes=True,
        extra='forbid'
    )


class RelatedAsyncExampleSchema(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    create_date: Optional[datetime.datetime] = None
    modify_date: Optional[datetime.datetime] = None
    async_example_id: Optional[int] = None

    model_config = ConfigDict(
        from_attributes=True,
        extra='forbid'
    )


class RelatedAsyncExampleSchemaList(BaseModel):
    total: int
    example_list: list[AsyncExampleSchema] = []

    model_config = ConfigDict(
        from_attributes=True,
        extra='forbid'
    )
