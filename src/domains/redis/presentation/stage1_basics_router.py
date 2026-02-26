"""
1단계: Redis 기초 이해
──────────────────────────────────────────────────────────────────────────────
목표: Redis의 핵심 명령어와 작동 원리 파악

주요 개념:
  - Redis: In-memory 데이터 저장소 / Single-thread 이벤트 루프 / 비동기 I/O
  - 기본 명령어: SET, GET, DEL, EXPIRE, TTL, EXISTS
  - 대량 키 조회: KEYS (위험) vs SCAN (안전)
  - 만료 정책: 키 단위 TTL 설정
"""

import time
from typing import Any, Dict, List

import aioredis
from fastapi import APIRouter, Depends

from src.database.database import get_async_redis_client
from src.domains.redis.constants import KEY_PREFIX, make_key
from src.domains.redis.presentation.schemas import RedisLabResponse, SetKeyRequest

router = APIRouter(prefix="/stage1", tags=["Redis-1단계: 기초"])


# ──────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────

async def _get_redis() -> aioredis.Redis:
    return await get_async_redis_client()


# ──────────────────────────────────────────
# 1-1. SET / GET / DEL
# ──────────────────────────────────────────

@router.post(
    "/set",
    response_model=RedisLabResponse,
    summary="[1-1] SET — 키-값 저장",
    description="""
**Redis SET 명령어** 실습

- `SET key value` : 값 저장 (영구)
- `SET key value EX seconds` : TTL과 함께 저장
- 같은 키로 다시 SET 하면 값이 덮어쓰여짐 (멱등)

**학습 포인트**
Redis는 모든 값을 **바이트 배열**로 저장한다.
`decode_responses=True` 옵션을 주면 Python str로 자동 변환된다.
""",
)
async def set_key(req: SetKeyRequest):
    redis = await _get_redis()
    full_key = make_key("stage1", req.key)

    if req.ttl:
        await redis.set(full_key, req.value, ex=req.ttl)
        cmd = f"SET {full_key} {req.value!r} EX {req.ttl}"
    else:
        await redis.set(full_key, req.value)
        cmd = f"SET {full_key} {req.value!r}"

    return RedisLabResponse(
        stage="1단계: 기초",
        topic="SET — 키-값 저장",
        description="SET key value [EX seconds] — 값을 저장한다. EX를 주면 지정 초 후 자동 삭제된다.",
        commands_used=[cmd],
        result={"key": full_key, "value": req.value, "ttl": req.ttl},
    )


@router.get(
    "/get/{key}",
    response_model=RedisLabResponse,
    summary="[1-1] GET — 키 조회",
    description="""
**Redis GET 명령어** 실습

- `GET key` : 값 조회
- 키가 없으면 `nil` (Python: `None`) 반환
- 만료된 키도 `nil` 반환 (Lazy Expiration)
""",
)
async def get_key(key: str):
    redis = await _get_redis()
    full_key = make_key("stage1", key)
    value = await redis.get(full_key)

    return RedisLabResponse(
        stage="1단계: 기초",
        topic="GET — 키 조회",
        description="GET key — 값을 조회한다. 키가 없거나 만료됐으면 None을 반환한다.",
        commands_used=[f"GET {full_key}"],
        result={"key": full_key, "value": value, "exists": value is not None},
    )


@router.delete(
    "/del/{key}",
    response_model=RedisLabResponse,
    summary="[1-1] DEL — 키 삭제",
    description="""
**Redis DEL 명령어** 실습

- `DEL key [key ...]` : 하나 이상의 키를 삭제
- 반환값: 실제로 삭제된 키의 수
- 존재하지 않는 키는 무시됨

**비교: DEL vs UNLINK**
`DEL`은 동기 삭제 (블로킹), `UNLINK`는 비동기 삭제 (Non-blocking).
대용량 값 삭제 시 `UNLINK`를 권장한다. (5단계에서 자세히 다룸)
""",
)
async def del_key(key: str):
    redis = await _get_redis()
    full_key = make_key("stage1", key)
    deleted_count = await redis.delete(full_key)

    return RedisLabResponse(
        stage="1단계: 기초",
        topic="DEL — 키 삭제",
        description="DEL key — 키를 삭제한다. 반환값은 실제 삭제된 키의 수다.",
        commands_used=[f"DEL {full_key}"],
        result={"key": full_key, "deleted_count": deleted_count, "was_deleted": deleted_count > 0},
    )


# ──────────────────────────────────────────
# 1-2. EXPIRE / TTL / PERSIST
# ──────────────────────────────────────────

@router.post(
    "/expire",
    response_model=RedisLabResponse,
    summary="[1-2] EXPIRE / TTL — 만료 시간 설정 및 확인",
    description="""
**Redis 만료(Expiry) 메커니즘** 실습

- `EXPIRE key seconds` : 기존 키에 TTL 설정
- `TTL key` : 남은 만료 시간(초) 조회
  - 양수: 남은 초
  - `-1`: TTL 없음 (영구)
  - `-2`: 키가 존재하지 않음
- `PERSIST key` : TTL 제거 (영구 보존으로 변경)

**만료 구현 방식 (2가지)**
1. Lazy Expiration: 접근 시 만료 여부 확인
2. Active Expiration: 백그라운드에서 주기적으로 만료 키 정리
""",
)
async def expire_demo():
    redis = await _get_redis()
    key = make_key("stage1", "expire_demo")

    # 1) 키 저장 (TTL 없음)
    await redis.set(key, "hello")
    ttl_before = await redis.ttl(key)  # -1 (영구)

    # 2) TTL 설정
    await redis.expire(key, 30)
    ttl_after = await redis.ttl(key)

    # 3) PERSIST로 TTL 제거
    await redis.persist(key)
    ttl_persisted = await redis.ttl(key)

    # 4) 정리
    await redis.delete(key)

    return RedisLabResponse(
        stage="1단계: 기초",
        topic="EXPIRE / TTL / PERSIST",
        description=(
            "EXPIRE key seconds: TTL 설정 | "
            "TTL key: 남은 시간 조회 (-1=영구, -2=없음) | "
            "PERSIST key: TTL 제거"
        ),
        commands_used=[
            f"SET {key} hello",
            f"TTL {key}  → {ttl_before}  (TTL 없음)",
            f"EXPIRE {key} 30",
            f"TTL {key}  → {ttl_after}  (약 30초)",
            f"PERSIST {key}",
            f"TTL {key}  → {ttl_persisted}  (다시 영구)",
        ],
        result={
            "ttl_before_expire": ttl_before,
            "ttl_after_expire": ttl_after,
            "ttl_after_persist": ttl_persisted,
        },
    )


# ──────────────────────────────────────────
# 1-3. EXISTS / TYPE
# ──────────────────────────────────────────

@router.get(
    "/exists/{key}",
    response_model=RedisLabResponse,
    summary="[1-3] EXISTS / TYPE — 키 존재 여부 및 타입 확인",
)
async def exists_type_demo(key: str):
    redis = await _get_redis()
    full_key = make_key("stage1", key)

    exists = await redis.exists(full_key)
    key_type = await redis.type(full_key)  # string / list / set / zset / hash / stream / none

    return RedisLabResponse(
        stage="1단계: 기초",
        topic="EXISTS / TYPE",
        description=(
            "EXISTS key: 키 존재 여부 (1=있음, 0=없음) | "
            "TYPE key: 자료구조 타입 반환 (string/list/set/zset/hash/stream/none)"
        ),
        commands_used=[f"EXISTS {full_key}", f"TYPE {full_key}"],
        result={
            "key": full_key,
            "exists": bool(exists),
            "type": key_type,
        },
    )


# ──────────────────────────────────────────
# 1-4. KEYS vs SCAN (중요!)
# ──────────────────────────────────────────

@router.get(
    "/scan-vs-keys",
    response_model=RedisLabResponse,
    summary="[1-4] SCAN vs KEYS — 대용량 키 조회",
    description="""
**KEYS vs SCAN 비교** — 프로덕션에서 매우 중요한 차이점

| 명령어 | 특징 | 프로덕션 사용 |
|--------|------|--------------|
| `KEYS pattern` | 한 번에 전체 스캔, **Single-thread 블로킹** | ❌ 절대 금지 |
| `SCAN cursor [MATCH pattern] [COUNT count]` | 커서 기반 분할 스캔, Non-blocking | ✅ 권장 |

**SCAN 동작 원리**
- 커서 0에서 시작 → 다음 커서 반환 → 커서가 다시 0이 되면 완료
- COUNT는 힌트일 뿐 (정확한 수 보장 안 됨)
- 중간에 추가/삭제된 키는 누락되거나 중복될 수 있음
""",
)
async def scan_vs_keys_demo():
    redis = await _get_redis()

    # 테스트용 키 10개 생성
    test_keys = []
    for i in range(10):
        k = make_key("stage1", "scan_test", str(i))
        await redis.set(k, f"value_{i}", ex=60)
        test_keys.append(k)

    # SCAN으로 커서 기반 조회
    pattern = make_key("stage1", "scan_test", "*")
    scanned_keys: List[str] = []
    cursor = 0
    scan_iterations = 0

    while True:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=3)
        scanned_keys.extend(keys)
        scan_iterations += 1
        if cursor == 0:
            break

    # 정리
    for k in test_keys:
        await redis.delete(k)

    return RedisLabResponse(
        stage="1단계: 기초",
        topic="SCAN vs KEYS",
        description=(
            "KEYS pattern: 전체 블로킹 스캔 — 프로덕션 금지! | "
            "SCAN cursor MATCH pattern COUNT hint: 커서 기반 분할 스캔 — 프로덕션 권장"
        ),
        commands_used=[
            "❌ KEYS redis_lab:stage1:scan_test:*  (블로킹, 위험)",
            f"✅ SCAN 0 MATCH {pattern} COUNT 3  (커서 기반, 안전)",
        ],
        result={
            "keys_found": len(scanned_keys),
            "scan_iterations": scan_iterations,
            "note": "SCAN은 여러 번 반복 호출이 필요하지만 서버를 블로킹하지 않는다.",
        },
    )


# ──────────────────────────────────────────
# 1-5. 전체 키 정리
# ──────────────────────────────────────────

@router.delete(
    "/cleanup",
    response_model=RedisLabResponse,
    summary="[유틸] Stage 1 키 전체 삭제",
    description="실습 중 생성된 `redis_lab:stage1:*` 키를 모두 삭제한다.",
)
async def cleanup_stage1():
    redis = await _get_redis()
    pattern = make_key("stage1", "*")
    deleted = 0
    cursor = 0

    while True:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
        if keys:
            await redis.delete(*keys)
            deleted += len(keys)
        if cursor == 0:
            break

    return RedisLabResponse(
        stage="1단계: 기초",
        topic="정리",
        description=f"redis_lab:stage1:* 패턴의 키를 모두 삭제했다.",
        commands_used=[f"SCAN 0 MATCH {pattern} COUNT 100", "DEL <keys...>"],
        result={"deleted_count": deleted},
    )
