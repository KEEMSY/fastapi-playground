import datetime
from typing import Optional

from pydantic import BaseModel

from src.domains.user.schemas import User


class CreateAsyncExample(BaseModel):
    name: str
    description: str


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


class UpdateAsyncExampleV1(CreateAsyncExample):
    pass


class UpdateAsyncExampleV2(CreateAsyncExample):
    async_example_id: int

