"""동시성 실험 라우터

API 엔드포인트:
  POST   /api/concurrency/run              - 실험 시작
  GET    /api/concurrency/stream/{id}      - SSE 실시간 진행 스트림
  GET    /api/concurrency/result/{id}      - 최종 결과 조회
  GET    /api/concurrency/history          - 실험 이력 목록
  DELETE /api/concurrency/clear            - 완료된 실험 삭제
"""

import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from starlette import status

from src.domains.concurrency import service as concurrency_service
from src.domains.concurrency.executor import run_experiment
from src.domains.concurrency.schemas import (
    ExperimentRequest,
    ExperimentResponse,
    ExperimentSummary,
)

router = APIRouter(prefix="/api/concurrency")
logger = logging.getLogger(__name__)


@router.post("/run", response_model=dict)
async def concurrency_run(
    _request: ExperimentRequest,
    background_tasks: BackgroundTasks,
):
    """실험 시작

    즉시 experiment_id를 반환하고, 실험은 백그라운드에서 실행됩니다.
    SSE 스트림(/stream/{id})으로 실시간 진행 상황을 받으세요.
    """
    state = concurrency_service.create_experiment(_request)
    background_tasks.add_task(run_experiment, state)
    logger.info(
        f"실험 시작: id={state.experiment_id}, "
        f"type={_request.concurrency_type}, task_type={_request.task_type}"
    )
    return {
        "experiment_id": state.experiment_id,
        "status": "running",
        "message": f"{_request.concurrency_type} 실험이 시작되었습니다.",
    }


@router.get("/stream/{experiment_id}")
async def concurrency_stream(experiment_id: str):
    """SSE 실시간 진행 스트림

    Events:
      - task_start    : 개별 태스크 시작 { task_id, worker_id, start_time }
      - task_complete : 개별 태스크 완료 { task_id, worker_id, start_time, end_time, elapsed }
      - completed     : 실험 전체 완료   { total_elapsed, throughput, task_count }
      - error         : 오류 발생        { message }
      - heartbeat     : 연결 유지 (5초)
    """
    state = concurrency_service.get_experiment(experiment_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="실험을 찾을 수 없습니다.",
        )

    async def event_generator():
        yield f"event: connected\ndata: {json.dumps({'experiment_id': experiment_id})}\n\n"

        while True:
            try:
                data = await asyncio.wait_for(state.progress_queue.get(), timeout=5.0)
                event_type = data.get("type", "message")
                yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

                if event_type in ("completed", "error"):
                    break

            except asyncio.TimeoutError:
                # 실험이 이미 완료됐으면 종료
                if state.status in ("completed", "error"):
                    break
                yield "event: heartbeat\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/result/{experiment_id}", response_model=ExperimentResponse)
async def concurrency_result(experiment_id: str):
    """실험 최종 결과 조회"""
    state = concurrency_service.get_experiment(experiment_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="실험을 찾을 수 없습니다.",
        )
    return concurrency_service.to_response(state)


@router.get("/history", response_model=list[ExperimentSummary])
async def concurrency_history():
    """실험 이력 목록 (최신순)"""
    return concurrency_service.get_all_experiments()


@router.delete("/clear", status_code=status.HTTP_204_NO_CONTENT)
async def concurrency_clear():
    """완료된 실험 이력 삭제"""
    deleted = concurrency_service.clear_experiments()
    logger.info(f"실험 이력 {deleted}건 삭제")
