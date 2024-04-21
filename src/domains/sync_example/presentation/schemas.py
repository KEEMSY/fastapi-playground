import datetime
from typing import Optional, Union

from pydantic import BaseModel

from src.domains.user.schemas import User


class CreateSyncExample(BaseModel):
    name: str
    description: str


class SyncExampleResponse(BaseModel):
    id: int
    name: str
    description: str
    create_date: datetime.datetime
    modify_date: Optional[datetime.datetime] = None
    user: Union[User, None]

    class Config:
        from_attributes = True


class SyncExampleListResponse(BaseModel):
    total: int
    example_list: list[SyncExampleResponse] = []
