import datetime
from typing import Optional

from pydantic import BaseModel

from src.domains.user.schemas import User


class AsyncExampleSchema(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    create_date: Optional[datetime.datetime] = None
    modify_date: Optional[datetime.datetime] = None
    user: Optional[User] = None

    class Config:
        orm_mode = True
        extra = 'forbid'
        from_attributes = True


class ASyncExampleSchemaList(BaseModel):
    total: int
    example_list: list[AsyncExampleSchema] = []

    class Config:
        orm_mode = True
        extra = 'forbid'
        from_attributes = True


class RelatedAsyncExampleSchema(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    create_date: Optional[datetime.datetime] = None
    modify_date: Optional[datetime.datetime] = None
    async_example_id: Optional[int] = None

    class Config:
        orm_mode = True
        extra = 'forbid'
        from_attributes = True


class RelatedAsyncExampleSchemaList(BaseModel):
    total: int
    example_list: list[AsyncExampleSchema] = []

    class Config:
        orm_mode = True
        extra = 'forbid'
        from_attributes = True
