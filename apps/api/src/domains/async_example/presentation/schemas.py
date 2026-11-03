import datetime
from typing import Optional

from pydantic import BaseModel

from src.domains.user.schemas import User


class CreateAsyncExample(BaseModel):
    name: str
    description: str

    model_config = {
        'extra': 'forbid',
        'from_attributes': True,
    }


class ReadAsyncExample(BaseModel):
    page: int = 0
    size: int = 10
    keyword: Optional[str] = None

    model_config = {
        'extra': 'forbid',
        'from_attributes': True,
    }


class AsyncExampleResponse(BaseModel):
    id: int
    name: str
    description: str
    create_date: datetime.datetime
    modify_date: Optional[datetime.datetime] = None
    user: Optional[User]

    model_config = {
        'extra': 'forbid',
        'from_attributes': True,
    }


class ASyncExampleListResponse(BaseModel):
    total: int
    example_list: list[AsyncExampleResponse] = []

    model_config = {
        'extra': 'forbid',
        'from_attributes': True,
    }


class UpdateAsyncExampleV1(CreateAsyncExample):
    pass

    model_config = {
        'extra': 'forbid',
        'from_attributes': True,
    }


class UpdateAsyncExampleV2(CreateAsyncExample):
    async_example_id: int
