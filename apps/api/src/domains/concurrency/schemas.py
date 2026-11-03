from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ConcurrencyType(str, Enum):
    asyncio = "asyncio"
    threading = "threading"
    multiprocessing = "multiprocessing"
    multi_instance = "multi_instance"


class TaskType(str, Enum):
    cpu = "cpu"
    io = "io"


class ExperimentRequest(BaseModel):
    concurrency_type: ConcurrencyType
    task_type: TaskType
    task_count: int = Field(default=8, ge=1, le=32)
    worker_count: int = Field(default=4, ge=1, le=8)
    complexity: int = Field(default=3, ge=1, le=10, description="작업 복잡도 (1=낮음, 10=높음)")


class TaskResult(BaseModel):
    task_id: int
    worker_id: int
    start_time: float
    end_time: float
    elapsed: float


class ExperimentResponse(BaseModel):
    experiment_id: str
    concurrency_type: str
    task_type: str
    task_count: int
    worker_count: int
    complexity: int
    status: str
    total_elapsed: Optional[float] = None
    task_results: List[TaskResult] = []
    throughput: Optional[float] = None
    error: Optional[str] = None


class ExperimentSummary(BaseModel):
    experiment_id: str
    concurrency_type: str
    task_type: str
    task_count: int
    worker_count: int
    complexity: int
    status: str
    total_elapsed: Optional[float] = None
    throughput: Optional[float] = None
