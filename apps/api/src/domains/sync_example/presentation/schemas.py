import datetime
from enum import Enum
from typing import Optional, Union, TypeVar, Generic

from pydantic import BaseModel, Field

from src.domains.user.schemas import User

T = TypeVar('T')


class ResultCode(Enum):
    SUCCESS = "정상 처리 되었습니다."
    ERROR = "에러가 발생했습니다."

    @property
    def msg(self):
        return self.value


class BaseResponse(BaseModel, Generic[T]):
    result_code: str = Field(default=ResultCode.SUCCESS.name, description="Result code of the operation")
    message: str = Field(default=ResultCode.SUCCESS.msg, description="Message associated with the result")
    data: Optional[T] = Field(default=None, description="Data returned by the operation")


class CreateSyncExample(BaseModel):
    name: str
    description: str

    model_config = {
        'extra': 'forbid',
        'from_attributes': True,
    }


class SyncExampleResponse(BaseModel):
    id: int
    name: str
    description: str
    create_date: datetime.datetime
    modify_date: Optional[datetime.datetime] = None
    user: Union[User, None]

    model_config = {
        'extra': 'forbid',
        'from_attributes': True,
    }


class SyncExampleListResponse(BaseModel):
    total: int
    example_list: list[SyncExampleResponse] = []

    model_config = {
        'extra': 'forbid',
        'from_attributes': True,
    }


class UpdateSyncExampleV1(CreateSyncExample):
    pass


class UpdateSyncExampleV2(CreateSyncExample):
    sync_example_id: int
