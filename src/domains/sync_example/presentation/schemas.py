import datetime
from typing import Optional, Union

from pydantic import BaseModel

from src.domains.user.schemas import User


class CreateSyncExample(BaseModel):
    name: str
    description: str

    class Config:
        from_attributes = True
        extra = 'forbid'


class SyncExampleResponse(BaseModel):
    id: int
    name: str
    description: str
    create_date: datetime.datetime
    modify_date: Optional[datetime.datetime] = None
    user: Union[User, None]

    class Config:
        from_attributes = True
        extra = 'forbid'


class SyncExampleListResponse(BaseModel):
    total: int
    example_list: list[SyncExampleResponse] = []

    class Config:
        from_attributes = True
        extra = 'forbid'


class UpdateSyncExampleV1(CreateSyncExample):
    pass


class UpdateSyncExampleV2(CreateSyncExample):
    sync_example_id: int

