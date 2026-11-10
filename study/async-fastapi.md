# 비동기 FastAPI

[study/README.md](./README.md) 의 한 주제. 실습은 [apps/consign](../apps/consign/README.md), 기존 실험은 [fastapi-sync-async-performance.md](../docs/fastapi-sync-async-performance.md) · `apps/api/src/domains/sync_example`·`async_example`.

## 출발점

동기 코드 기반(엔드포인트 대부분이 `def`, SQLAlchemy + psycopg2, Pydantic v1, crontab 배치와 로컬 파일 상태)에서 출발한다. 핵심은 프레임워크 사용법이 아니라 **"서버 한 대 + 동기" → "여러 Pod + 비동기"로 바뀔 때 깨지는 가정**이다. 그 차이는 [single-to-multi-pod.md](single-to-multi-pod.md).

## 알아야 할 것

| 주제 | 알아야 할 것 |
|---|---|
| `def` vs `async def` | `def` 는 스레드풀(기본 40)에서, `async def` 는 이벤트 루프에서 돈다. **`async def` 안의 동기 호출(`requests`·`psycopg2`·`boto3`·`time.sleep`·CPU 연산)은 그 Pod 의 모든 요청을 멈춘다** |
| 동기 코드를 써야 할 때 | `run_in_threadpool` / `asyncio.to_thread`, 또는 엔드포인트를 `def` 로 둔다. 섞는 기준을 정한다 |
| 비동기 SQLAlchemy | `create_async_engine` + asyncpg, 요청당 세션, `expire_on_commit=False`. 지연 로딩은 `MissingGreenlet` → `selectinload` |
| 커넥션 풀 | `pool_size × 워커 × Pod 수` 가 Postgres `max_connections` 를 넘지 않는지. 오토스케일 시 터진다. PgBouncer 유무 확인 |
| 외부 호출 | `httpx.AsyncClient` 는 lifespan 에서 하나 만들어 재사용. 타임아웃 필수. `CancelledError` 동작 |
| 동시 실행 | `asyncio.gather` vs `TaskGroup` — 하나가 실패할 때 나머지 |
| `BackgroundTasks` 한계 | Pod 재시작 시 유실. 결제·발송처럼 잃으면 안 되는 일은 큐(Celery·arq·Redis Streams) |
| 요청 ID | `contextvars` 로 로그·하위 호출에 전파 |
| Pydantic v2 | `model_validate`·`field_validator`·`ConfigDict` 등 v1과 다른 점 |

## 자료

- FastAPI 공식 문서 "Concurrency and async / await", "Lifespan Events"
- SQLAlchemy 2.0 "Asynchronous I/O (asyncio)"
- Pydantic "Migration Guide"(v1 → v2)
