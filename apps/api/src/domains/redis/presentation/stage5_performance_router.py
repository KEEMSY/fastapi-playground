"""
5단계: 성능 최적화
──────────────────────────────────────────────────────────────────────────────
목표: 실무에서 자주 발생하는 성능 이슈 대응 방법 이해

주요 주제:
  Pipeline    — RTT 최소화로 대량 명령어 일괄 처리
  Lua Script  — 서버 측 원자적 복합 연산
  SCAN        — 커서 기반 안전한 키 조회 (KEYS 대체)
  SLOWLOG     — 느린 명령어 병목 분석
  DEL vs UNLINK — 동기 vs 비동기 삭제
"""

import asyncio
import time
from typing import Any, Dict, List

import aioredis
from fastapi import APIRouter

from src.database.database import get_async_redis_client
from src.domains.redis.constants import STAGE5_LUA, STAGE5_PIPELINE, make_key
from src.domains.redis.presentation.schemas import PipelineRequest, RedisLabResponse

router = APIRouter(prefix="/stage5", tags=["Redis-5단계: 성능 최적화"])


async def _get_redis() -> aioredis.Redis:
    return await get_async_redis_client()


# ══════════════════════════════════════════
# 5-1. Pipeline — RTT 최소화
# ══════════════════════════════════════════

@router.post(
    "/pipeline/benchmark",
    response_model=RedisLabResponse,
    summary="[5-1] Pipeline — 일괄 전송 vs 개별 전송 벤치마크",
    description="""
**Pipeline (파이프라이닝)** — RTT(Round-Trip Time) 최소화

**문제**: N개 명령어를 개별 전송하면 N번의 네트워크 왕복 발생
```
Client → SET 1 → Server → OK → Client    (RTT 1번)
Client → SET 2 → Server → OK → Client    (RTT 1번)
...  N개 = N * RTT
```

**해결**: 파이프라인으로 일괄 전송
```
Client → [SET 1, SET 2, ..., SET N] → Server → [OK, OK, ..., OK] → Client
                                                (RTT 1번!)
```

**주의**: Pipeline은 원자성 보장 안 함. 원자성 필요 시 MULTI/EXEC 또는 Lua 사용.
""",
)
async def pipeline_benchmark(req: PipelineRequest):
    redis = await _get_redis()
    n = req.count

    # --- 1) 개별 전송 ---
    start = time.monotonic()
    for i in range(n):
        await redis.set(f"{STAGE5_PIPELINE}:no_pipe:{i}", f"v{i}", ex=60)
    elapsed_no_pipe = round((time.monotonic() - start) * 1000, 2)

    # --- 2) Pipeline 전송 ---
    start = time.monotonic()
    pipe = redis.pipeline()
    for i in range(n):
        pipe.set(f"{STAGE5_PIPELINE}:pipe:{i}", f"v{i}", ex=60)
    await pipe.execute()
    elapsed_pipe = round((time.monotonic() - start) * 1000, 2)

    speedup = round(elapsed_no_pipe / elapsed_pipe, 2) if elapsed_pipe > 0 else 0

    # 정리
    cursor = 0
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match=f"{STAGE5_PIPELINE}:*", count=200)
        if keys:
            await redis.delete(*keys)
        if cursor == 0:
            break

    return RedisLabResponse(
        stage="5단계: 성능 최적화",
        topic="Pipeline — RTT 최소화",
        description=(
            "개별 전송: N개 명령 = N번 RTT | "
            "파이프라인: N개 명령 = 1번 RTT (응답도 일괄 수신) | "
            "원자성 보장 안 됨 → 원자성 필요 시 MULTI/EXEC 또는 Lua 사용"
        ),
        commands_used=[
            f"# 개별 전송: {n}번 개별 SET",
            f"# 파이프라인: pipe = redis.pipeline(); [pipe.set(k,v) for ...]; await pipe.execute()",
        ],
        result={
            "commands": n,
            "without_pipeline_ms": elapsed_no_pipe,
            "with_pipeline_ms": elapsed_pipe,
            "speedup_ratio": speedup,
        },
        metadata={
            "note": "로컬 환경에서는 RTT가 매우 짧아 차이가 미미할 수 있다. 원격 Redis에서 효과가 크다.",
        },
    )


# ══════════════════════════════════════════
# 5-2. Lua 스크립팅 — 원자적 복합 연산
# ══════════════════════════════════════════

@router.post(
    "/lua/atomic-counter",
    response_model=RedisLabResponse,
    summary="[5-2] Lua 스크립팅 — 원자적 조건부 연산",
    description="""
**Lua 스크립팅** — 서버 측 원자적 실행

Redis는 단일 스레드이므로 Lua 스크립트는 실행 중 다른 명령어가 끼어들 수 없다.
즉, 여러 명령어를 **원자적으로** 실행하는 유일한 방법이다.

**사용 예시**: 조건부 카운터 (limit 초과 시 증가 거부)
```lua
local current = tonumber(redis.call('GET', KEYS[1])) or 0
if current < tonumber(ARGV[1]) then
    return redis.call('INCR', KEYS[1])
else
    return -1  -- 한도 초과
end
```

**vs MULTI/EXEC (트랜잭션)**
- MULTI/EXEC: 명령어 큐잉 후 한 번에 실행, 중간 결과 기반 조건 분기 불가
- Lua: 중간 결과 사용 가능, 더 복잡한 로직 구현 가능

**EVALSHA**: 스크립트를 서버에 캐싱 후 SHA로 호출 (네트워크 절약)
""",
)
async def lua_atomic_counter(limit: int = 10):
    redis = await _get_redis()

    # 조건부 증가 Lua 스크립트
    lua_script = """
    local current = tonumber(redis.call('GET', KEYS[1])) or 0
    if current < tonumber(ARGV[1]) then
        return redis.call('INCR', KEYS[1])
    else
        return -1
    end
    """
    results = []
    for _ in range(limit + 3):   # limit 이후 3번 더 시도
        val = await redis.eval(lua_script, 1, STAGE5_LUA, limit)
        results.append(int(val))

    current = int(await redis.get(STAGE5_LUA) or 0)
    await redis.delete(STAGE5_LUA)

    return RedisLabResponse(
        stage="5단계: 성능 최적화",
        topic="Lua 스크립팅 — 원자적 조건부 카운터",
        description=(
            "EVAL script numkeys [key ...] [arg ...]: Lua 스크립트 원자적 실행 | "
            "중간 결과 기반 조건 분기 가능 | -1은 한도 초과 반환"
        ),
        commands_used=[
            f"EVAL <lua_script> 1 {STAGE5_LUA} {limit}  (x{limit + 3}번 실행)",
        ],
        result={
            "limit": limit,
            "execution_results": results,
            "final_value": current,
            "explanation": f"처음 {limit}번은 증가, 이후엔 -1(한도 초과) 반환",
        },
    )


# ══════════════════════════════════════════
# 5-3. SCAN — 커서 기반 안전한 키 조회
# ══════════════════════════════════════════

@router.get(
    "/scan/demo",
    response_model=RedisLabResponse,
    summary="[5-3] SCAN — 커서 기반 안전한 대량 키 조회",
    description="""
**SCAN 명령어 상세**

```
SCAN cursor [MATCH pattern] [COUNT count] [TYPE type]
```

- `cursor`: 시작점. 처음은 0, 완료 시 0으로 돌아옴
- `MATCH`: 패턴 필터 (서버에서 필터링, COUNT 이후 적용)
- `COUNT`: 한 번 스캔할 키 수 힌트 (정확하지 않음)
- `TYPE`: Redis 7.0+, 특정 타입만 반환 (string/list/set/zset/hash)

**주의사항**
1. 중복 반환 가능 (사용자가 직접 dedup 처리)
2. 추가/삭제된 키 누락 가능 (스냅샷이 아님)
3. 기타 변형: `HSCAN` (Hash), `SSCAN` (Set), `ZSCAN` (Sorted Set)

**KEYS 절대 사용 금지 이유**
프로덕션 Redis에 수백만 키가 있을 때 `KEYS *`는 수초~수분간 전체 블로킹 발생
→ 모든 명령어 처리 중단 → 타임아웃 → 서비스 장애
""",
)
async def scan_demo():
    redis = await _get_redis()

    # 테스트 키 생성
    test_pattern = make_key("stage5", "scan_demo")
    for i in range(20):
        await redis.set(f"{test_pattern}:{i}", f"v{i}", ex=60)

    # SCAN 수행
    pattern = f"{test_pattern}:*"
    all_keys: List[str] = []
    cursor = 0
    iterations = 0
    cursor_trace = []

    while True:
        prev_cursor = cursor
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=5)
        all_keys.extend(keys)
        iterations += 1
        cursor_trace.append({
            "iteration": iterations,
            "prev_cursor": prev_cursor,
            "next_cursor": cursor,
            "keys_returned": len(keys),
        })
        if cursor == 0:
            break

    # 정리
    for k in all_keys:
        await redis.delete(k)

    return RedisLabResponse(
        stage="5단계: 성능 최적화",
        topic="SCAN — 커서 기반 키 조회",
        description=(
            "SCAN cursor MATCH pattern COUNT hint: 커서 기반 분할 조회. "
            "cursor=0이 될 때까지 반복. 중복 가능하므로 dedup 필요."
        ),
        commands_used=[
            f"SCAN 0 MATCH {pattern} COUNT 5",
            "# cursor가 0이 될 때까지 반복",
        ],
        result={
            "total_keys_found": len(all_keys),
            "scan_iterations": iterations,
            "cursor_trace": cursor_trace,
            "note": "COUNT는 힌트일 뿐 — 한 번에 반환되는 키 수는 다를 수 있다",
        },
    )


# ══════════════════════════════════════════
# 5-4. SLOWLOG — 느린 명령어 분석
# ══════════════════════════════════════════

@router.get(
    "/slowlog",
    response_model=RedisLabResponse,
    summary="[5-4] SLOWLOG — 느린 명령어 분석",
    description="""
**SLOWLOG** — Redis 내장 성능 진단 도구

- `SLOWLOG GET [count]`: 최근 N개 느린 명령어 조회
- `SLOWLOG LEN`: Slowlog 저장된 항목 수
- `SLOWLOG RESET`: Slowlog 초기화

**설정 항목**
```
CONFIG SET slowlog-log-slower-than 10000   # 10ms 이상 걸린 명령어 기록 (마이크로초 단위)
CONFIG SET slowlog-max-len 128              # 최대 저장 항목 수
```

**slowlog 항목 구조**
1. ID
2. 발생 시각 (Unix timestamp)
3. 실행 시간 (마이크로초)
4. 명령어 + 인자

**활용 팁**
SLOWLOG로 병목 명령어 발견 → 해당 명령어의 시간 복잡도 확인 →
O(N) 명령어(KEYS, SMEMBERS, HGETALL 등)를 O(1)/O(log N) 명령어로 대체
""",
)
async def slowlog_info():
    redis = await _get_redis()

    slowlog_len = await redis.slowlog_len()
    slowlog_entries = await redis.slowlog_get(10)
    slowlog_config = await redis.config_get("slowlog-log-slower-than")
    slowlog_maxlen = await redis.config_get("slowlog-max-len")

    formatted_entries = []
    for entry in slowlog_entries:
        formatted_entries.append({
            "id": entry.get("id"),
            "timestamp": entry.get("start_time"),
            "duration_microseconds": entry.get("duration"),
            "duration_ms": round(entry.get("duration", 0) / 1000, 3),
            "command": entry.get("command"),
        })

    return RedisLabResponse(
        stage="5단계: 성능 최적화",
        topic="SLOWLOG — 느린 명령어 분석",
        description=(
            "SLOWLOG GET: 느린 명령어 목록 조회 | "
            "slowlog-log-slower-than: 기록 기준 시간 (마이크로초) | "
            "O(N) 명령어를 O(1)/O(log N)으로 대체하는 것이 핵심"
        ),
        commands_used=[
            "SLOWLOG LEN",
            "SLOWLOG GET 10",
            "CONFIG GET slowlog-log-slower-than",
        ],
        result={
            "total_slowlog_entries": slowlog_len,
            "threshold_microseconds": slowlog_config.get("slowlog-log-slower-than"),
            "max_entries": slowlog_maxlen.get("slowlog-max-len"),
            "recent_slow_commands": formatted_entries,
        },
        metadata={
            "common_slow_commands": {
                "KEYS *": "O(N) — 프로덕션 절대 금지, SCAN으로 대체",
                "SMEMBERS": "O(N) — 원소 수가 많으면 SSCAN으로 대체",
                "HGETALL": "O(N) — 필드가 많으면 HMGET으로 필요 필드만 조회",
                "SORT": "O(N+M*log(M)) — 데이터 정렬은 클라이언트에서 처리 권장",
            },
        },
    )


# ══════════════════════════════════════════
# 5-5. DEL vs UNLINK
# ══════════════════════════════════════════

@router.post(
    "/unlink/demo",
    response_model=RedisLabResponse,
    summary="[5-5] DEL vs UNLINK — 동기 vs 비동기 삭제",
    description="""
**DEL vs UNLINK 비교**

| 명령어 | 삭제 방식 | 특징 |
|--------|----------|------|
| `DEL key` | 동기 (메인 스레드) | 큰 자료구조 삭제 시 블로킹 발생 |
| `UNLINK key` | 비동기 (백그라운드) | 즉시 키 공간에서 제거 후 메모리 해제는 비동기 |

**언제 UNLINK를 써야 하나?**
- 수백만 원소를 가진 Set/ZSet/List/Hash 삭제 시
- 수 MB 이상의 큰 String 삭제 시

**lazyfree-lazy-eviction** 설정으로 Eviction도 비동기로 처리 가능 (Redis 4.0+)
""",
)
async def unlink_demo():
    redis = await _get_redis()

    # 큰 Set 생성 (1000개 원소)
    big_set_key = make_key("stage5", "big_set")
    pipe = redis.pipeline()
    for i in range(1000):
        pipe.sadd(big_set_key, f"member_{i}")
    await pipe.execute()

    size = await redis.scard(big_set_key)

    # UNLINK (비동기 삭제)
    start = time.monotonic()
    await redis.unlink(big_set_key)
    elapsed_unlink = round((time.monotonic() - start) * 1000, 3)

    # 같은 크기 Set 재생성 후 DEL 비교
    pipe = redis.pipeline()
    for i in range(1000):
        pipe.sadd(big_set_key, f"member_{i}")
    await pipe.execute()

    start = time.monotonic()
    await redis.delete(big_set_key)
    elapsed_del = round((time.monotonic() - start) * 1000, 3)

    return RedisLabResponse(
        stage="5단계: 성능 최적화",
        topic="DEL vs UNLINK — 동기 vs 비동기 삭제",
        description=(
            "DEL: 동기 삭제 (메인 스레드 블로킹) | "
            "UNLINK: 키 공간에서 즉시 제거 + 메모리 해제는 백그라운드 스레드 → Non-blocking | "
            "대용량 키 삭제는 반드시 UNLINK 사용"
        ),
        commands_used=[
            f"UNLINK {big_set_key}  (1000개 원소 Set)",
            f"DEL {big_set_key}  (1000개 원소 Set, 비교용)",
        ],
        result={
            "set_size": size,
            "del_ms": elapsed_del,
            "unlink_ms": elapsed_unlink,
            "note": "로컬 환경에서는 차이가 미미하나, 수백만 원소나 수십MB 키에서는 DEL이 수백ms 블로킹 가능",
        },
    )


# ══════════════════════════════════════════
# 5-6. 서버 전체 통계 (INFO all)
# ══════════════════════════════════════════

@router.get(
    "/server/stats",
    response_model=RedisLabResponse,
    summary="[5-6] 서버 성능 통계 (INFO stats / server)",
    description="""
**INFO 명령어** — Redis 서버 전반적인 상태 조회

섹션:
- `server`: 버전, OS, 포트, 업타임
- `clients`: 연결된 클라이언트 수, 블로킹 클라이언트
- `stats`: 총 명령어 수, 초당 명령어, Keyspace Hit/Miss
- `replication`: 마스터/레플리카 상태
- `cpu`: CPU 사용량

**Keyspace Hit Ratio** (캐시 효율 핵심 지표)
```
hit_ratio = keyspace_hits / (keyspace_hits + keyspace_misses)
```
캐시 서버라면 95% 이상이 목표.
""",
)
async def server_stats():
    redis = await _get_redis()

    server_info = await redis.info("server")
    stats_info = await redis.info("stats")
    clients_info = await redis.info("clients")
    replication_info = await redis.info("replication")

    hits = stats_info.get("keyspace_hits", 0)
    misses = stats_info.get("keyspace_misses", 0)
    total = hits + misses
    hit_ratio = round(hits / total * 100, 2) if total > 0 else 0.0

    return RedisLabResponse(
        stage="5단계: 성능 최적화",
        topic="서버 성능 통계 (INFO)",
        description=(
            "INFO server/stats/clients/replication으로 서버 전반 상태 파악 | "
            "Keyspace Hit Ratio: 캐시 효율 핵심 지표 (목표 95%+)"
        ),
        commands_used=[
            "INFO server",
            "INFO stats",
            "INFO clients",
            "INFO replication",
        ],
        result={
            "server": {
                "version": server_info.get("redis_version"),
                "mode": server_info.get("redis_mode"),
                "os": server_info.get("os"),
                "uptime_days": server_info.get("uptime_in_days"),
                "tcp_port": server_info.get("tcp_port"),
            },
            "performance": {
                "total_commands_processed": stats_info.get("total_commands_processed"),
                "instantaneous_ops_per_sec": stats_info.get("instantaneous_ops_per_sec"),
                "keyspace_hits": hits,
                "keyspace_misses": misses,
                "keyspace_hit_ratio_percent": hit_ratio,
            },
            "clients": {
                "connected": clients_info.get("connected_clients"),
                "blocked": clients_info.get("blocked_clients"),
                "max_clients": server_info.get("maxclients"),
            },
            "replication": {
                "role": replication_info.get("role"),
                "connected_slaves": replication_info.get("connected_slaves"),
            },
        },
    )
