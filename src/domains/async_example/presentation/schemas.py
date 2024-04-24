import datetime
from typing import Optional

from pydantic import BaseModel

from src.domains.user.schemas import User


class CreateAsyncExample(BaseModel):
    name: str
    description: str

    class Config:
        from_attributes = True
        extra = 'forbid'


class ReadAsyncExample(BaseModel):
    page: int = 0
    size: int = 10
    keyword: Optional[str] = None


class AsyncExampleResponse(BaseModel):
    id: int
    name: str
    description: str
    create_date: datetime.datetime
    modify_date: Optional[datetime.datetime] = None
    user: Optional[User]

    class Config:
        from_attributes = True
        extra = 'forbid'


class ASyncExampleListResponse(BaseModel):
    total: int
    example_list: list[AsyncExampleResponse] = []

    class Config:
        from_attributes = True
        extra = 'forbid'


class UpdateAsyncExampleV1(CreateAsyncExample):
    pass


class UpdateAsyncExampleV2(CreateAsyncExample):
    async_example_id: int
