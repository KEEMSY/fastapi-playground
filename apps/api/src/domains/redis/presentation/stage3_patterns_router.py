"""
3단계: 실무 패턴 구현 (FastAPI + Redis)
──────────────────────────────────────────────────────────────────────────────
목표: FastAPI 환경에서 자주 사용되는 Redis 패턴 구현

패턴 목록:
  1. Cache-Aside (Lazy Loading)  — DB 쿼리 결과 캐싱
  2. Token Blacklist             — JWT 토큰 무효화
  3. Sliding Window Rate Limiter — API 요청 속도 제한
  4. Distributed Lock            — SETNX 기반 동시성 제어
  5. Pub/Sub                     — 실시간 메시지 브로드캐스트
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, Optional

import aioredis
from fastapi import APIRouter, HTTPException, status

from src.database.database import get_async_redis_client
from src.domains.redis.constants import (
    STAGE3_BLACKLIST_PREFIX,
    STAGE3_CACHE_PREFIX,
    STAGE3_LOCK_PREFIX,
    STAGE3_RATELIMIT_PREFIX,
    STAGE3_SESSION_PREFIX,
    make_key,
)
from src.domains.redis.presentation.schemas import (
    CacheQueryRequest,
    DistributedLockRequest,
    RateLimitRequest,
    RedisLabResponse,
    SessionCreateRequest,
    TokenBlacklistRequest,
)

router = APIRouter(prefix="/stage3", tags=["Redis-3단계: 실무 패턴"])


async def _get_redis() -> aioredis.Redis:
    return await get_async_redis_client()


# ══════════════════════════════════════════
# 3-1. Cache-Aside (Lazy Loading)
# ══════════════════════════════════════════

async def _fake_db_query(resource_id: int) -> Dict[str, Any]:
    """DB 조회를 흉내 내는 함수 (100ms 지연)"""
    await asyncio.sleep(0.1)
    return {
        "id": resource_id,
        "title": f"Resource #{resource_id}",
        "content": "This is fetched from the database",
        "created_at": "2024-01-01T00:00:00",
    }


@router.get(
    "/cache/{resource_id}",
    response_model=RedisLabResponse,
    summary="[3-1] Cache-Aside — DB 쿼리 결과 캐싱",
    description="""
**Cache-Aside (Lazy Loading) 패턴**

```
요청 → Redis 조회
         ↓ (Cache HIT)  → 즉시 반환
         ↓ (Cache MISS) → DB 조회 → Redis 저장 → 반환
```

**구현 포인트**
- 캐시 키: `cache:{resource_id}`
- TTL: 300초 (5분) — 데이터 신선도와 캐시 효율의 균형점
- 직렬화: JSON (Redis는 String만 저장하므로 dict를 JSON으로 변환)

**주의사항 — Cache Stampede**
캐시가 만료되는 순간 다수의 요청이 동시에 DB를 치는 현상.
해결: Mutex Lock, Probabilistic Early Expiration, Background Refresh
""",
)
async def cache_aside(resource_id: int):
    redis = await _get_redis()
    cache_key = f"{STAGE3_CACHE_PREFIX}:{resource_id}"

    start = time.monotonic()

    # 1) 캐시 조회
    cached = await redis.get(cache_key)
    cache_hit = cached is not None

    if cache_hit:
        data = json.loads(cached)
        source = "cache"
    else:
        # 2) DB 조회 (시뮬레이션)
        data = await _fake_db_query(resource_id)
        # 3) 캐시 저장 (TTL 300초)
        await redis.set(cache_key, json.dumps(data), ex=300)
        source = "database"

    elapsed_ms = round((time.monotonic() - start) * 1000, 2)
    ttl = await redis.ttl(cache_key)

    return RedisLabResponse(
        stage="3단계: 실무 패턴",
        topic="Cache-Aside (Lazy Loading)",
        description=(
            "1) GET cache_key → HIT: 즉시 반환 | MISS: DB 조회 후 SET cache_key value EX 300 | "
            "직렬화: JSON | Cache Stampede 주의"
        ),
        commands_used=(
            [f"GET {cache_key}  → HIT"]
            if cache_hit
            else [
                f"GET {cache_key}  → MISS",
                "_fake_db_query(resource_id)  [100ms 지연 시뮬레이션]",
                f"SET {cache_key} <json> EX 300",
            ]
        ),
        result={
            "resource_id": resource_id,
            "data": data,
            "source": source,
            "cache_hit": cache_hit,
            "elapsed_ms": elapsed_ms,
            "ttl_seconds": ttl,
        },
        metadata={
            "tip": "같은 ID로 두 번 호출해 Cache HIT 속도 차이를 확인해보세요.",
        },
    )


@router.delete(
    "/cache/{resource_id}",
    response_model=RedisLabResponse,
    summary="[3-1] Cache-Aside — 캐시 무효화 (Cache Invalidation)",
    description="DB 데이터 수정 시 해당 캐시 키를 삭제해 다음 요청에서 최신 데이터를 가져오게 한다.",
)
async def cache_invalidate(resource_id: int):
    redis = await _get_redis()
    cache_key = f"{STAGE3_CACHE_PREFIX}:{resource_id}"
    deleted = await redis.delete(cache_key)

    return RedisLabResponse(
        stage="3단계: 실무 패턴",
        topic="Cache Invalidation",
        description="DB 업데이트 후 DEL cache_key → 다음 요청 시 Cache MISS → DB 재조회 → 캐시 갱신",
        commands_used=[f"DEL {cache_key}  → {deleted}"],
        result={"invalidated": bool(deleted), "cache_key": cache_key},
    )


# ══════════════════════════════════════════
# 3-2. JWT 토큰 블랙리스트
# ══════════════════════════════════════════

@router.post(
    "/blacklist/token",
    response_model=RedisLabResponse,
    summary="[3-2] Token Blacklist — JWT 무효화",
    description="""
**JWT 토큰 블랙리스트 패턴**

JWT는 Stateless라 서버가 직접 무효화할 수 없다.
로그아웃 시 토큰의 jti(JWT ID)를 Redis에 저장하고,
모든 요청에서 블랙리스트를 확인하면 토큰을 사실상 무효화할 수 있다.

- `SET blacklist:{jti} 1 EX {remaining_ttl}` : 토큰 등록
- 토큰 TTL이 만료되면 Redis에서도 자동 삭제됨 → 메모리 누수 없음

**미들웨어 검증 흐름**
```
요청 헤더 JWT 추출 → jti 파싱
  → EXISTS blacklist:{jti}
    1 → 401 Unauthorized (무효 토큰)
    0 → 정상 처리
```
""",
)
async def blacklist_token(req: TokenBlacklistRequest):
    redis = await _get_redis()
    blacklist_key = f"{STAGE3_BLACKLIST_PREFIX}:{req.token}"

    await redis.set(blacklist_key, "revoked", ex=req.ttl)
    ttl = await redis.ttl(blacklist_key)

    return RedisLabResponse(
        stage="3단계: 실무 패턴",
        topic="JWT Token Blacklist",
        description=(
            "SET blacklist:{token} revoked EX {ttl}: 토큰 무효화 등록 | "
            "토큰 만료 시 자동 삭제 | 모든 요청에서 EXISTS 체크로 유효성 확인"
        ),
        commands_used=[
            f"SET {blacklist_key} revoked EX {req.ttl}",
            f"TTL {blacklist_key}  → {ttl}",
        ],
        result={"blacklisted_token": req.token, "expires_in": ttl},
    )


@router.get(
    "/blacklist/check/{token}",
    response_model=RedisLabResponse,
    summary="[3-2] Token Blacklist — 토큰 유효성 검사",
)
async def check_blacklist(token: str):
    redis = await _get_redis()
    blacklist_key = f"{STAGE3_BLACKLIST_PREFIX}:{token}"
    is_blacklisted = await redis.exists(blacklist_key)

    return RedisLabResponse(
        stage="3단계: 실무 패턴",
        topic="Token Blacklist 확인",
        description="EXISTS blacklist:{token}: 0이면 유효, 1이면 무효화된 토큰",
        commands_used=[f"EXISTS {blacklist_key}  → {is_blacklisted}"],
        result={
            "token": token,
            "is_blacklisted": bool(is_blacklisted),
            "status": "무효 토큰 (401 반환)" if is_blacklisted else "유효 토큰",
        },
    )


# ══════════════════════════════════════════
# 3-3. Sliding Window Rate Limiter
# ══════════════════════════════════════════

@router.post(
    "/rate-limit/check",
    response_model=RedisLabResponse,
    summary="[3-3] Rate Limiting — 슬라이딩 윈도우 방식",
    description="""
**슬라이딩 윈도우(Sliding Window) Rate Limiter**

Sorted Set을 이용해 요청 타임스탬프를 저장하고,
window 크기 이전의 오래된 항목을 제거하면서 현재 창 내 요청 수를 센다.

**알고리즘**
```
now = time.time()
window_start = now - window_seconds

ZADD   ratelimit:{client_id}  now  unique_request_id
ZREMRANGEBYSCORE  ratelimit:{client_id}  0  window_start   (만료 항목 제거)
count = ZCARD ratelimit:{client_id}
EXPIRE ratelimit:{client_id}  window_seconds

if count > limit → 429 Too Many Requests
```

**vs Fixed Window**
Fixed Window는 윈도우 경계에서 2배 요청이 가능한 취약점이 있다.
Sliding Window는 이를 해결하지만 메모리 사용량이 더 높다.
""",
)
async def rate_limit_check(req: RateLimitRequest):
    redis = await _get_redis()
    rl_key = f"{STAGE3_RATELIMIT_PREFIX}:{req.client_id}"

    now = time.time()
    window_start = now - req.window
    request_id = str(uuid.uuid4())

    pipe = redis.pipeline()
    pipe.zadd(rl_key, {request_id: now})
    pipe.zremrangebyscore(rl_key, 0, window_start)
    pipe.zcard(rl_key)
    pipe.expire(rl_key, req.window)
    results = await pipe.execute()

    current_count = results[2]
    allowed = current_count <= req.limit
    remaining = max(0, req.limit - current_count)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": req.limit,
                "window_seconds": req.window,
                "current_count": current_count,
                "retry_after": req.window,
            },
        )

    return RedisLabResponse(
        stage="3단계: 실무 패턴",
        topic="Sliding Window Rate Limiter",
        description=(
            "ZADD: 요청 타임스탬프 추가 | "
            "ZREMRANGEBYSCORE: 만료 항목 제거 | "
            "ZCARD: 현재 창 내 요청 수 확인 | "
            "limit 초과 시 429 반환"
        ),
        commands_used=[
            f"ZADD {rl_key} {now:.3f} <request_id>",
            f"ZREMRANGEBYSCORE {rl_key} 0 {window_start:.3f}",
            f"ZCARD {rl_key}  → {current_count}",
            f"EXPIRE {rl_key} {req.window}",
        ],
        result={
            "client_id": req.client_id,
            "allowed": allowed,
            "current_count": current_count,
            "limit": req.limit,
            "remaining": remaining,
            "window_seconds": req.window,
        },
    )


# ══════════════════════════════════════════
# 3-4. Distributed Lock (분산 락)
# ══════════════════════════════════════════

@router.post(
    "/lock/acquire",
    response_model=RedisLabResponse,
    summary="[3-4] Distributed Lock — SET NX EX 기반 락 획득",
    description="""
**분산 락 (Distributed Lock) 패턴**

여러 서버/프로세스가 동시에 같은 자원에 접근하는 것을 방지한다.

**핵심 명령어**
```
SET lock:{resource}  {unique_id}  NX  EX  {ttl}
```
- `NX`: 키가 없을 때만 SET (원자적!)
- `EX`: TTL 설정 (프로세스 죽어도 락 자동 해제 = Deadlock 방지)
- 반환값: `OK` (성공) or `nil` (이미 락 있음)

**해제 시 주의 (Lua 스크립트 사용)**
```lua
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
end
return 0
```
자신이 건 락만 해제 (다른 프로세스의 락을 실수로 해제하지 않음)

**Redlock 알고리즘**: 단일 Redis가 아닌 N대에 과반수 락 획득 방식 (N≥3 홀수)
""",
)
async def acquire_lock(req: DistributedLockRequest):
    redis = await _get_redis()
    lock_key = f"{STAGE3_LOCK_PREFIX}:{req.resource}"
    lock_value = str(uuid.uuid4())   # 고유 식별자 (누가 걸었는지 식별)

    # SET key value NX EX ttl
    acquired = await redis.set(lock_key, lock_value, nx=True, ex=req.ttl)
    ttl = await redis.ttl(lock_key)
    current_holder = await redis.get(lock_key)

    return RedisLabResponse(
        stage="3단계: 실무 패턴",
        topic="Distributed Lock (SET NX EX)",
        description=(
            "SET lock:{resource} {unique_id} NX EX {ttl}: NX=없을 때만 설정(원자적) | "
            "고유 ID로 소유권 식별 | TTL로 Deadlock 방지 | "
            "해제 시 Lua 스크립트로 소유자 확인 후 삭제"
        ),
        commands_used=[
            f"SET {lock_key} {lock_value} NX EX {req.ttl}  → {'OK' if acquired else 'nil (락 획득 실패)'}",
        ],
        result={
            "resource": req.resource,
            "lock_acquired": bool(acquired),
            "lock_value": lock_value if acquired else None,
            "current_holder": current_holder,
            "ttl": ttl,
            "tip": "같은 resource로 다시 호출하면 락 획득 실패를 확인할 수 있다." if acquired else "이미 락이 걸려 있다.",
        },
    )


@router.delete(
    "/lock/release/{resource}",
    response_model=RedisLabResponse,
    summary="[3-4] Distributed Lock — 락 해제 (Lua 스크립트)",
)
async def release_lock(resource: str, lock_value: str):
    redis = await _get_redis()
    lock_key = f"{STAGE3_LOCK_PREFIX}:{resource}"

    # Lua 스크립트: 소유자 확인 후 삭제 (원자적)
    lua_script = """
    if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("DEL", KEYS[1])
    else
        return 0
    end
    """
    result = await redis.eval(lua_script, 1, lock_key, lock_value)
    released = bool(result)

    return RedisLabResponse(
        stage="3단계: 실무 패턴",
        topic="Distributed Lock — 해제 (Lua 원자적 확인+삭제)",
        description=(
            "Lua 스크립트로 GET lock_key == lock_value 확인 후 DEL → "
            "자신이 건 락만 해제 (타인 락 실수 해제 방지)"
        ),
        commands_used=[
            f"EVAL 'if GET({lock_key})=={lock_value!r} then DEL({lock_key}) end'  → {int(result)}",
        ],
        result={
            "resource": resource,
            "lock_released": released,
            "message": "락 해제 성공" if released else "락 해제 실패 (소유자가 아니거나 이미 만료됨)",
        },
    )


# ══════════════════════════════════════════
# 3-5. Pub/Sub
# ══════════════════════════════════════════

@router.post(
    "/pubsub/publish",
    response_model=RedisLabResponse,
    summary="[3-5] Pub/Sub — 메시지 발행",
    description="""
**Redis Pub/Sub — 발행/구독 메시징**

- `PUBLISH channel message` : 채널에 메시지 발행
- `SUBSCRIBE channel` : 채널 구독 (별도 연결 필요)
- `PSUBSCRIBE pattern` : 패턴 기반 구독 (예: `user.*`)

**특징**
- Fire-and-Forget: 구독자가 없어도 오류 없음 (메시지 유실)
- 메시지 영속성 없음 (구독 전 메시지, 연결 끊김 중 메시지 유실)
- 영속성이 필요하면 → **Redis Stream** 사용 (7단계)

**현재 프로젝트 활용**
현재 프로젝트의 알림 시스템(SSE)을 Pub/Sub으로 대체 가능:
- 알림 생성 서버 → `PUBLISH notification:{user_id} {payload}`
- SSE 서버 → `SUBSCRIBE notification:{user_id}` → 클라이언트에 전달
""",
)
async def pubsub_publish(channel: str, message: str):
    redis = await _get_redis()
    receiver_count = await redis.publish(channel, message)

    return RedisLabResponse(
        stage="3단계: 실무 패턴",
        topic="Pub/Sub — 메시지 발행 (PUBLISH)",
        description=(
            "PUBLISH channel message: 채널에 메시지 발행 | "
            "반환값: 메시지를 수신한 구독자 수 | "
            "영속성 없음 → 메시지 유실 가능 → 영속성 필요 시 Stream 사용 (7단계)"
        ),
        commands_used=[f"PUBLISH {channel} {message!r}  → {receiver_count} (수신 구독자 수)"],
        result={
            "channel": channel,
            "message": message,
            "receivers": receiver_count,
            "note": "receivers=0 이면 현재 구독자 없음 (메시지 유실). SUBSCRIBE로 먼저 구독해야 수신 가능.",
        },
    )


# ══════════════════════════════════════════
# 정리
# ══════════════════════════════════════════

@router.delete(
    "/cleanup",
    response_model=RedisLabResponse,
    summary="[유틸] Stage 3 키 전체 삭제",
)
async def cleanup_stage3():
    redis = await _get_redis()
    pattern = make_key("stage3", "*")
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
        stage="3단계: 실무 패턴",
        topic="정리",
        description="redis_lab:stage3:* 패턴의 키를 모두 삭제했다.",
        commands_used=[f"SCAN 0 MATCH {pattern} COUNT 100", "DEL <keys...>"],
        result={"deleted_count": deleted},
    )
