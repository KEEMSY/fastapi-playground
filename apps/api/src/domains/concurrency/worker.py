"""멀티 인스턴스 워커 모듈 (표준 라이브러리만 사용)

spawn으로 자식 프로세스가 시작될 때 이 모듈만 임포트합니다.
FastAPI / SQLAlchemy / Pydantic 등을 임포트하지 않아 기동 시간이 빠릅니다.

실제 운영에서도 워커 코드는 최소한의 의존성만 갖도록 설계합니다.
"""

import asyncio
import math
import time


# ── 태스크 함수 (최상위 레벨, pickle 호환) ───────────────────────────────────

def cpu_task(task_id: int, complexity: int) -> dict:
    """CPU 집약적 작업: 소수(prime) 계산"""
    start = time.perf_counter()
    limit = complexity * 3000
    count = 0
    for n in range(2, limit):
        if all(n % i != 0 for i in range(2, int(math.sqrt(n)) + 1)):
            count += 1
    elapsed = time.perf_counter() - start
    return {"task_id": task_id, "elapsed": round(elapsed, 4), "result": count}


def io_task(task_id: int, sleep_seconds: float) -> dict:
    """I/O 집약적 작업: blocking sleep"""
    start = time.perf_counter()
    time.sleep(sleep_seconds)
    return {"task_id": task_id, "elapsed": round(time.perf_counter() - start, 4)}


# ── 인스턴스 이벤트 루프 ─────────────────────────────────────────────────────

def instance_event_loop(
    instance_id: int,
    task_ids: list,
    task_type: str,
    param: float,
    result_queue,       # multiprocessing.Queue
    exp_start_time: float,
) -> None:
    """독립 asyncio 이벤트 루프 — 실제 uvicorn worker 구조 시뮬레이션

    각 인스턴스(프로세스)가 자신만의 asyncio.run()을 실행합니다.
    할당받은 태스크를 asyncio.gather로 동시 처리합니다.
    """
    async def run_instance() -> None:
        async def handle_task(task_id: int) -> None:
            start_abs = time.perf_counter()
            start_rel = start_abs - exp_start_time
            result_queue.put({
                "type": "task_start",
                "task_id": task_id,
                "instance_id": instance_id,
                "start_time": round(start_rel, 4),
            })

            if task_type == "io":
                await asyncio.sleep(param)
                elapsed = param
            else:
                loop = asyncio.get_running_loop()
                raw = await loop.run_in_executor(None, cpu_task, task_id, int(param))
                elapsed = raw["elapsed"]

            end_abs = time.perf_counter()
            result_queue.put({
                "type": "task_done",
                "task_id": task_id,
                "instance_id": instance_id,
                "start_time": round(start_rel, 4),
                "end_time": round(end_abs - exp_start_time, 4),
                "elapsed": round(elapsed, 4),
            })

        await asyncio.gather(*[handle_task(tid) for tid in task_ids])
        result_queue.put({"type": "instance_done", "instance_id": instance_id})

    asyncio.run(run_instance())
