"""동시성 실험 실행기

4가지 동시성 패턴을 실제로 실행하고 성능을 측정합니다.

주의: multiprocessing 사용 시 pickle 직렬화가 필요하므로
      _cpu_bound_task, _io_bound_task 함수는 반드시 최상위 레벨에 정의합니다.
"""

import asyncio
import math
import multiprocessing
import os
import queue
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import List, Optional

from src.domains.concurrency.schemas import (
    ConcurrencyType,
    ExperimentRequest,
    TaskResult,
    TaskType,
)


# ── 최상위 레벨 함수 (multiprocessing pickle 호환) ──────────────────────────

def _cpu_bound_task(task_id: int, complexity: int) -> dict:
    """CPU 집약적 작업: 소수(prime) 계산

    complexity에 비례하여 계산량이 증가합니다.
    Python GIL로 인해 threading에서 병렬 효과가 제한됩니다.
    """
    start = time.perf_counter()
    limit = complexity * 3000
    count = 0
    for n in range(2, limit):
        if all(n % i != 0 for i in range(2, int(math.sqrt(n)) + 1)):
            count += 1
    elapsed = time.perf_counter() - start
    return {
        "task_id": task_id,
        "elapsed": round(elapsed, 4),
        "result": count,
        "worker_pid": os.getpid(),
    }


def _io_bound_task(task_id: int, sleep_seconds: float) -> dict:
    """I/O 집약적 작업: sleep으로 네트워크/디스크 I/O 대기 시뮬레이션

    실제 blocking I/O를 흉내냅니다.
    threading에서 GIL이 해제되므로 효과적으로 병렬 실행됩니다.
    """
    start = time.perf_counter()
    time.sleep(sleep_seconds)
    elapsed = time.perf_counter() - start
    return {
        "task_id": task_id,
        "elapsed": round(elapsed, 4),
        "worker_pid": os.getpid(),
    }


# worker 모듈의 instance_event_loop를 re-export
# spawn 자식 프로세스는 이 모듈 대신 worker.py만 임포트하므로 기동이 빠릅니다.
from src.domains.concurrency.worker import instance_event_loop as _instance_event_loop


# ── 실험 상태 ────────────────────────────────────────────────────────────────

@dataclass
class ExperimentState:
    experiment_id: str
    request: ExperimentRequest
    status: str = "running"
    start_wall_time: float = 0.0
    total_elapsed: Optional[float] = None
    task_results: List[TaskResult] = field(default_factory=list)
    throughput: Optional[float] = None
    error: Optional[str] = None
    progress_queue: asyncio.Queue = field(default_factory=asyncio.Queue)


# ── 동시성 실행기 ────────────────────────────────────────────────────────────

async def _run_asyncio(state: ExperimentState) -> List[TaskResult]:
    """asyncio 동시성

    - asyncio.Semaphore로 동시 실행 태스크 수를 worker_count로 제한
    - I/O 작업: await asyncio.sleep() → 이벤트 루프를 블로킹하지 않음 (효율적)
    - CPU 작업: run_in_executor(None) → 기본 ThreadPoolExecutor 사용 (GIL로 제한)
    """
    req = state.request
    semaphore = asyncio.Semaphore(req.worker_count)

    # worker_id 풀: 동시에 실행 가능한 슬롯을 큐로 관리
    worker_pool: asyncio.Queue = asyncio.Queue()
    for w in range(req.worker_count):
        await worker_pool.put(w)

    results: List[TaskResult] = []
    loop = asyncio.get_running_loop()

    async def run_one(task_id: int) -> TaskResult:
        async with semaphore:
            worker_id = await worker_pool.get()
            try:
                start = time.perf_counter() - state.start_wall_time
                await state.progress_queue.put({
                    "type": "task_start",
                    "task_id": task_id,
                    "worker_id": worker_id,
                    "start_time": round(start, 4),
                })

                if req.task_type == TaskType.io:
                    sleep_time = req.complexity * 0.2
                    await asyncio.sleep(sleep_time)
                    elapsed = sleep_time
                else:
                    # CPU 작업은 run_in_executor로 이벤트 루프 블로킹 방지
                    raw = await loop.run_in_executor(None, _cpu_bound_task, task_id, req.complexity)
                    elapsed = raw["elapsed"]

                end = time.perf_counter() - state.start_wall_time
                tr = TaskResult(
                    task_id=task_id,
                    worker_id=worker_id,
                    start_time=round(start, 4),
                    end_time=round(end, 4),
                    elapsed=round(elapsed, 4),
                )
                await state.progress_queue.put({
                    "type": "task_complete",
                    "task_id": task_id,
                    "worker_id": worker_id,
                    "start_time": round(start, 4),
                    "end_time": round(end, 4),
                    "elapsed": round(elapsed, 4),
                })
                return tr
            finally:
                await worker_pool.put(worker_id)

    gathered = await asyncio.gather(*[run_one(i) for i in range(req.task_count)])
    return list(gathered)


async def _run_threading(state: ExperimentState) -> List[TaskResult]:
    """threading 동시성 (ThreadPoolExecutor + loop.run_in_executor)

    - blocking 함수를 스레드 풀에서 실행
    - I/O 작업: GIL이 sleep 중 해제 → 진정한 병렬 I/O
    - CPU 작업: GIL이 해제되지 않음 → 순차 실행과 큰 차이 없음
    """
    req = state.request
    executor = ThreadPoolExecutor(max_workers=req.worker_count)
    loop = asyncio.get_running_loop()

    worker_pool: asyncio.Queue = asyncio.Queue()
    for w in range(req.worker_count):
        await worker_pool.put(w)

    async def run_one(task_id: int) -> TaskResult:
        worker_id = await worker_pool.get()
        try:
            start = time.perf_counter() - state.start_wall_time
            await state.progress_queue.put({
                "type": "task_start",
                "task_id": task_id,
                "worker_id": worker_id,
                "start_time": round(start, 4),
            })

            if req.task_type == TaskType.io:
                raw = await loop.run_in_executor(
                    executor, _io_bound_task, task_id, req.complexity * 0.2
                )
            else:
                raw = await loop.run_in_executor(
                    executor, _cpu_bound_task, task_id, req.complexity
                )

            end = time.perf_counter() - state.start_wall_time
            tr = TaskResult(
                task_id=task_id,
                worker_id=worker_id,
                start_time=round(start, 4),
                end_time=round(end, 4),
                elapsed=raw["elapsed"],
            )
            await state.progress_queue.put({
                "type": "task_complete",
                "task_id": task_id,
                "worker_id": worker_id,
                "start_time": round(start, 4),
                "end_time": round(end, 4),
                "elapsed": raw["elapsed"],
            })
            return tr
        finally:
            await worker_pool.put(worker_id)

    gathered = await asyncio.gather(*[run_one(i) for i in range(req.task_count)])
    executor.shutdown(wait=False)
    return list(gathered)


async def _run_multiprocessing(state: ExperimentState) -> List[TaskResult]:
    """multiprocessing 동시성 (ProcessPoolExecutor + loop.run_in_executor)

    - 별도 프로세스에서 실행 → GIL 완전 우회
    - CPU 작업: 진정한 병렬 실행 (코어 수만큼 선형 성능 향상)
    - I/O 작업: 프로세스 생성 오버헤드로 threading보다 느릴 수 있음
    - 주의: 인수/반환값이 pickle 직렬화되어야 함 (lambda 불가)
    """
    req = state.request
    executor = ProcessPoolExecutor(max_workers=req.worker_count)
    loop = asyncio.get_running_loop()

    worker_pool: asyncio.Queue = asyncio.Queue()
    for w in range(req.worker_count):
        await worker_pool.put(w)

    async def run_one(task_id: int) -> TaskResult:
        worker_id = await worker_pool.get()
        try:
            start = time.perf_counter() - state.start_wall_time
            await state.progress_queue.put({
                "type": "task_start",
                "task_id": task_id,
                "worker_id": worker_id,
                "start_time": round(start, 4),
            })

            if req.task_type == TaskType.io:
                raw = await loop.run_in_executor(
                    executor, _io_bound_task, task_id, req.complexity * 0.2
                )
            else:
                raw = await loop.run_in_executor(
                    executor, _cpu_bound_task, task_id, req.complexity
                )

            end = time.perf_counter() - state.start_wall_time
            tr = TaskResult(
                task_id=task_id,
                worker_id=worker_id,
                start_time=round(start, 4),
                end_time=round(end, 4),
                elapsed=raw["elapsed"],
            )
            await state.progress_queue.put({
                "type": "task_complete",
                "task_id": task_id,
                "worker_id": worker_id,
                "start_time": round(start, 4),
                "end_time": round(end, 4),
                "elapsed": raw["elapsed"],
            })
            return tr
        finally:
            await worker_pool.put(worker_id)

    gathered = await asyncio.gather(*[run_one(i) for i in range(req.task_count)])
    executor.shutdown(wait=False)
    return list(gathered)


async def _run_multi_instance(state: ExperimentState) -> List[TaskResult]:
    """멀티 인스턴스 동시성 (실제 uvicorn worker 구조 시뮬레이션)

    구조:
      1. 로드밸런서(round-robin)가 태스크를 N개 인스턴스에 분배
      2. 각 인스턴스(프로세스)가 독립 asyncio.run()으로 자신의 태스크를 동시 처리
      3. 결과를 multiprocessing.Queue로 메인 프로세스에 실시간 전달
      4. 메인 프로세스는 큐를 polling하며 SSE progress_queue에 중계

    실제 Nginx + Gunicorn + uvicorn worker 동작과 동일한 패턴입니다.
    """
    req = state.request

    # 로드밸런서 역할: 태스크를 round-robin으로 인스턴스에 분배
    batches: List[List[int]] = [[] for _ in range(req.worker_count)]
    for i in range(req.task_count):
        batches[i % req.worker_count].append(i)

    param = req.complexity * 0.2 if req.task_type == TaskType.io else float(req.complexity)

    # spawn context: fork 시 uvicorn 스레드의 mutex를 상속하면 교착 발생
    # spawn은 새 Python 인터프리터를 시작 → asyncio 상태 상속 없음
    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue()

    # 각 인스턴스를 독립 프로세스로 시작
    processes = []
    active_instances = 0
    for instance_id, task_ids in enumerate(batches):
        if not task_ids:
            continue
        p = ctx.Process(
            target=_instance_event_loop,
            args=(instance_id, task_ids, req.task_type.value, param,
                  result_queue, state.start_wall_time),
        )
        p.start()
        processes.append(p)
        active_instances += 1

    # 결과 수집: non-blocking poll → asyncio.sleep으로 이벤트 루프 양보
    task_results: dict = {}
    instances_done = 0

    while instances_done < active_instances:
        try:
            msg = result_queue.get_nowait()
        except queue.Empty:
            await asyncio.sleep(0.03)
            # 모든 프로세스가 예기치 않게 종료된 경우 탈출
            if all(not p.is_alive() for p in processes):
                break
            continue

        if msg["type"] == "task_start":
            await state.progress_queue.put({
                "type": "task_start",
                "task_id": msg["task_id"],
                "worker_id": msg["instance_id"],
                "start_time": msg["start_time"],
            })

        elif msg["type"] == "task_done":
            tr = TaskResult(
                task_id=msg["task_id"],
                worker_id=msg["instance_id"],
                start_time=msg["start_time"],
                end_time=msg["end_time"],
                elapsed=msg["elapsed"],
            )
            task_results[msg["task_id"]] = tr
            await state.progress_queue.put({
                "type": "task_complete",
                "task_id": msg["task_id"],
                "worker_id": msg["instance_id"],
                "start_time": msg["start_time"],
                "end_time": msg["end_time"],
                "elapsed": msg["elapsed"],
            })

        elif msg["type"] == "instance_done":
            instances_done += 1

    for p in processes:
        p.join(timeout=5)
        if p.is_alive():
            p.terminate()

    return list(task_results.values())


# ── 메인 진입점 ──────────────────────────────────────────────────────────────

async def run_experiment(state: ExperimentState) -> None:
    """실험 실행 및 결과 기록 (백그라운드 태스크로 실행)"""
    state.start_wall_time = time.perf_counter()

    try:
        if state.request.concurrency_type == ConcurrencyType.asyncio:
            results = await _run_asyncio(state)
        elif state.request.concurrency_type == ConcurrencyType.threading:
            results = await _run_threading(state)
        elif state.request.concurrency_type == ConcurrencyType.multiprocessing:
            results = await _run_multiprocessing(state)
        else:
            results = await _run_multi_instance(state)

        total_elapsed = time.perf_counter() - state.start_wall_time
        state.total_elapsed = round(total_elapsed, 4)
        state.task_results = results
        state.throughput = round(len(results) / total_elapsed, 2)
        state.status = "completed"

        await state.progress_queue.put({
            "type": "completed",
            "total_elapsed": state.total_elapsed,
            "throughput": state.throughput,
            "task_count": len(results),
        })

    except Exception as e:
        state.status = "error"
        state.error = "실험 실행 중 오류가 발생했습니다."
        await state.progress_queue.put({"type": "error", "message": state.error})
        raise
