"""동시성 실험 서비스

실험 상태를 메모리에서 관리합니다.
"""

import uuid
from typing import Dict, List, Optional

from src.domains.concurrency.executor import ExperimentState
from src.domains.concurrency.schemas import (
    ExperimentRequest,
    ExperimentResponse,
    ExperimentSummary,
    TaskResult,
)

# 인메모리 실험 저장소 (서버 재시작 시 초기화)
_experiments: Dict[str, ExperimentState] = {}
MAX_HISTORY = 50  # 최대 보관 실험 수


def create_experiment(request: ExperimentRequest) -> ExperimentState:
    """새 실험 생성 및 저장소 등록"""
    experiment_id = str(uuid.uuid4())[:8]
    state = ExperimentState(
        experiment_id=experiment_id,
        request=request,
    )
    _experiments[experiment_id] = state

    # 오래된 실험 정리
    if len(_experiments) > MAX_HISTORY:
        oldest_key = next(iter(_experiments))
        del _experiments[oldest_key]

    return state


def get_experiment(experiment_id: str) -> Optional[ExperimentState]:
    return _experiments.get(experiment_id)


def get_all_experiments() -> List[ExperimentSummary]:
    """실험 이력 목록 (최신순)"""
    return [
        ExperimentSummary(
            experiment_id=s.experiment_id,
            concurrency_type=s.request.concurrency_type.value,
            task_type=s.request.task_type.value,
            task_count=s.request.task_count,
            worker_count=s.request.worker_count,
            complexity=s.request.complexity,
            status=s.status,
            total_elapsed=s.total_elapsed,
            throughput=s.throughput,
        )
        for s in reversed(list(_experiments.values()))
    ]


def clear_experiments() -> int:
    """모든 실험 삭제 (실행 중인 실험 제외)"""
    to_delete = [k for k, v in _experiments.items() if v.status != "running"]
    for k in to_delete:
        del _experiments[k]
    return len(to_delete)


def to_response(state: ExperimentState) -> ExperimentResponse:
    return ExperimentResponse(
        experiment_id=state.experiment_id,
        concurrency_type=state.request.concurrency_type.value,
        task_type=state.request.task_type.value,
        task_count=state.request.task_count,
        worker_count=state.request.worker_count,
        complexity=state.request.complexity,
        status=state.status,
        total_elapsed=state.total_elapsed,
        task_results=state.task_results,
        throughput=state.throughput,
        error=state.error,
    )
