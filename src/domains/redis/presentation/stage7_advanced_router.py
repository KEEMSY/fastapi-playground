"""
7단계: 고급 주제
──────────────────────────────────────────────────────────────────────────────
목표: 실무 심화 활용 — Stream, 트랜잭션, 보안/모니터링 개요

주요 주제:
  Redis Stream   — Kafka 대용 영속 메시지 스트림 (Consumer Group)
  트랜잭션       — MULTI/EXEC, WATCH (Optimistic Locking)
  보안 설정 개요 — AUTH, ACL, TLS
  모니터링 개요  — Redis INFO, MONITOR
"""

import time
from typing import Any, Dict, List, Optional

import aioredis
from fastapi import APIRouter

from src.database.database import get_async_redis_client
from src.domains.redis.constants import STAGE7_STREAM, STAGE7_TRANSACTION, make_key
from src.domains.redis.presentation.schemas import (
    RedisLabResponse,
    StreamPublishRequest,
    TransactionRequest,
)

router = APIRouter(prefix="/stage7", tags=["Redis-7단계: 고급 주제"])


async def _get_redis() -> aioredis.Redis:
    return await get_async_redis_client()


# ══════════════════════════════════════════
# 7-1. Redis Stream — 영속 메시지 스트림
# ══════════════════════════════════════════

@router.post(
    "/stream/publish",
    response_model=RedisLabResponse,
    summary="[7-1] Stream — XADD 메시지 발행",
    description="""
**Redis Stream** — Pub/Sub의 영속성 문제를 해결한 메시지 스트림

**Pub/Sub과의 차이점**

| 특징 | Pub/Sub | Stream |
|------|---------|--------|
| 메시지 영속성 | ❌ (연결 끊기면 유실) | ✅ (디스크 저장) |
| 과거 메시지 조회 | ❌ | ✅ |
| Consumer Group | ❌ | ✅ (Kafka와 유사) |
| 처리 확인 (ACK) | ❌ | ✅ |

**핵심 명령어**
- `XADD key * field value ...` : 메시지 추가 (ID 자동 생성)
- `XREAD COUNT n STREAMS key id` : 메시지 읽기
- `XRANGE key start end` : 범위 조회
- `XLEN key` : 스트림 길이
- `XGROUP CREATE key group id` : Consumer Group 생성
- `XREADGROUP GROUP group consumer STREAMS key >` : 그룹에서 읽기
- `XACK key group id` : 처리 완료 확인
""",
)
async def stream_publish(req: StreamPublishRequest):
    redis = await _get_redis()

    # XADD: * = 자동 ID 생성 (milliseconds-sequence 형식)
    fields = {"event_type": req.event_type, **req.payload}
    message_id = await redis.xadd(STAGE7_STREAM, fields)

    stream_len = await redis.xlen(STAGE7_STREAM)

    # 최근 3개 메시지 조회
    recent = await redis.xrevrange(STAGE7_STREAM, count=3)
    recent_formatted = [
        {"id": msg_id, "data": data}
        for msg_id, data in recent
    ]

    return RedisLabResponse(
        stage="7단계: 고급 주제",
        topic="Redis Stream — XADD 메시지 발행",
        description=(
            "XADD key * field value: 타임스탬프 기반 자동 ID로 메시지 추가 | "
            "영속 저장 (Pub/Sub과 달리 과거 메시지 조회 가능) | "
            "Consumer Group으로 Kafka-like 분산 처리 가능"
        ),
        commands_used=[
            f"XADD {STAGE7_STREAM} * event_type {req.event_type} ...",
            f"XLEN {STAGE7_STREAM}",
            f"XREVRANGE {STAGE7_STREAM} + - COUNT 3",
        ],
        result={
            "message_id": message_id,
            "stream_length": stream_len,
            "recent_messages": recent_formatted,
        },
        metadata={
            "id_format": "milliseconds-sequence (예: 1704067200000-0)",
            "tip": "같은 스트림에 여러 번 publish 후 /stream/read로 메시지를 읽어보세요.",
        },
    )


@router.get(
    "/stream/read",
    response_model=RedisLabResponse,
    summary="[7-1] Stream — XRANGE 메시지 읽기 & Consumer Group 개요",
    description="""
**Stream 읽기 방법**

1. **XRANGE key start end** : 범위 기반 조회 (start=0, end=+)
2. **XREAD COUNT n STREAMS key id** : 특정 ID 이후 새 메시지 읽기 (Polling)
3. **XREADGROUP** : Consumer Group 기반 읽기 (분산 처리)

**Consumer Group 패턴 (Kafka-like)**
```
XGROUP CREATE stream_key my_group $ MKSTREAM   # 그룹 생성
XREADGROUP GROUP my_group consumer1 COUNT 10 STREAMS stream_key >
# > : 이 컨슈머가 아직 읽지 않은 새 메시지
XACK stream_key my_group <message_id>           # 처리 완료 확인
```

여러 Consumer가 같은 Group에 속하면 메시지가 분산 배분된다.
한 Consumer가 죽으면 XPENDING으로 미처리 메시지를 다른 Consumer가 재처리 가능.
""",
)
async def stream_read(count: int = 10):
    redis = await _get_redis()

    stream_len = await redis.xlen(STAGE7_STREAM)
    messages = await redis.xrange(STAGE7_STREAM, count=count)

    formatted = [{"id": msg_id, "data": data} for msg_id, data in messages]

    # Consumer Group 상태 (없으면 생략)
    groups_info = []
    try:
        groups = await redis.xinfo_groups(STAGE7_STREAM)
        for g in groups:
            groups_info.append({
                "name": g.get("name"),
                "consumers": g.get("consumers"),
                "pending": g.get("pending"),
                "last_delivered_id": g.get("last-delivered-id"),
            })
    except Exception:
        pass

    return RedisLabResponse(
        stage="7단계: 고급 주제",
        topic="Redis Stream — XRANGE 읽기 & Consumer Group",
        description=(
            "XRANGE key 0 + COUNT n: 처음부터 최대 n개 메시지 조회 | "
            "XINFO GROUPS key: Consumer Group 상태 | "
            "Consumer Group은 여러 워커가 메시지를 분산 처리할 때 사용"
        ),
        commands_used=[
            f"XRANGE {STAGE7_STREAM} 0 + COUNT {count}",
            f"XLEN {STAGE7_STREAM}",
            f"XINFO GROUPS {STAGE7_STREAM}",
        ],
        result={
            "stream_length": stream_len,
            "messages": formatted,
            "consumer_groups": groups_info if groups_info else "Consumer Group 없음",
        },
    )


@router.delete(
    "/stream/trim",
    response_model=RedisLabResponse,
    summary="[7-1] Stream — XTRIM (스트림 크기 제한)",
    description="""
**XTRIM** — 스트림 크기를 제한해 메모리를 관리한다.

- `XTRIM key MAXLEN count` : 최대 N개만 유지 (오래된 것 삭제)
- `XTRIM key MAXLEN ~ count` : 근사값 트리밍 (더 효율적)
- `XADD key MAXLEN ~ count * ...` : 추가와 동시에 트리밍

**메모리 관리 전략**
스트림이 무한히 커지는 것을 막으려면:
1. XADD 시 MAXLEN 옵션 사용
2. 별도 스케줄러로 주기적 XTRIM
3. 처리 완료된 메시지를 XDEL로 삭제
""",
)
async def stream_trim(maxlen: int = 5):
    redis = await _get_redis()

    before = await redis.xlen(STAGE7_STREAM)
    await redis.xtrim(STAGE7_STREAM, maxlen=maxlen)
    after = await redis.xlen(STAGE7_STREAM)

    return RedisLabResponse(
        stage="7단계: 고급 주제",
        topic="Redis Stream — XTRIM",
        description=f"XTRIM key MAXLEN {maxlen}: 스트림을 최대 {maxlen}개로 제한 (오래된 메시지 삭제)",
        commands_used=[f"XTRIM {STAGE7_STREAM} MAXLEN {maxlen}"],
        result={
            "before_length": before,
            "after_length": after,
            "trimmed_count": before - after,
        },
    )


# ══════════════════════════════════════════
# 7-2. 트랜잭션 — MULTI/EXEC / WATCH
# ══════════════════════════════════════════

@router.post(
    "/transaction/multi-exec",
    response_model=RedisLabResponse,
    summary="[7-2] 트랜잭션 — MULTI/EXEC",
    description="""
**Redis 트랜잭션 (MULTI/EXEC)**

```
MULTI         # 트랜잭션 시작
SET key1 v1   # 큐에 추가 (아직 실행 안 됨)
INCR key2     # 큐에 추가
EXEC          # 일괄 실행 → [OK, 1]
```

**특징**
- 큐잉된 명령어는 EXEC 시 한 번에 실행
- DISCARD로 취소 가능
- 다른 클라이언트 명령어가 중간에 끼어들지 못함 (원자적)
- **단, 에러 처리가 특이**: 문법 오류는 EXEC 전에 전체 취소, 런타임 오류는 해당 명령만 실패하고 나머지 실행

**MULTI/EXEC vs Lua**
- MULTI/EXEC: 중간 결과 기반 조건 분기 불가
- Lua: 중간 결과 사용 가능, 더 유연

**WATCH (Optimistic Locking)**
```
WATCH key          # key 감시 시작
value = GET key    # 현재 값 읽기
MULTI              # 트랜잭션 시작
SET key new_value  # 큐에 추가
EXEC               # key가 변경됐으면 nil 반환 (트랜잭션 중단)
```
CAS(Compare-And-Swap) 패턴으로 동시성 충돌 감지.
""",
)
async def multi_exec_demo(req: TransactionRequest):
    redis = await _get_redis()
    key = f"{STAGE7_TRANSACTION}:{req.key}"

    # MULTI/EXEC 트랜잭션
    pipe = redis.pipeline(transaction=True)   # transaction=True → MULTI/EXEC
    pipe.set(key, "0")
    pipe.incr(key)
    pipe.incr(key)
    pipe.incr(key)
    pipe.get(key)
    results = await pipe.execute()

    final_value = results[-1]
    await redis.expire(key, 60)

    return RedisLabResponse(
        stage="7단계: 고급 주제",
        topic="트랜잭션 — MULTI/EXEC",
        description=(
            "MULTI/EXEC: 큐잉된 명령어 일괄 원자적 실행 | "
            "중간에 다른 클라이언트 끼어들기 불가 | "
            "aioredis에서 pipeline(transaction=True)로 구현"
        ),
        commands_used=[
            f"MULTI",
            f"SET {key} 0",
            f"INCR {key}  (×3)",
            f"GET {key}",
            f"EXEC  → {results}",
        ],
        result={
            "key": key,
            "transaction_results": [str(r) for r in results],
            "final_value": final_value,
        },
    )


@router.post(
    "/transaction/watch",
    response_model=RedisLabResponse,
    summary="[7-2] 트랜잭션 — WATCH (Optimistic Locking)",
    description="""
**WATCH — Optimistic Locking (낙관적 잠금)**

감시 중인 키가 EXEC 전에 변경되면 트랜잭션이 자동 중단된다.
충돌 빈도가 낮을 때 효율적 (충돌 없으면 락 오버헤드 없음).

**재시도 패턴**
```python
while True:
    await redis.watch(key)
    current = int(await redis.get(key) or 0)
    pipe = redis.pipeline(transaction=True)
    try:
        pipe.multi()
        pipe.set(key, current + 1)
        await pipe.execute()
        break  # 성공
    except WatchError:
        continue  # 충돌 → 재시도
```
""",
)
async def watch_demo(req: TransactionRequest):
    redis = await _get_redis()
    key = f"{STAGE7_TRANSACTION}:watch:{req.key}"

    # 초기값 설정
    await redis.set(key, "10")

    success = False
    attempts = 0
    max_attempts = 3

    while attempts < max_attempts:
        attempts += 1
        try:
            async with redis.pipeline(transaction=True) as pipe:
                await pipe.watch(key)
                current = int(await pipe.get(key) or 0)

                # MULTI 이전에 외부에서 키 변경 시뮬레이션 (1번만)
                if attempts == 1:
                    # 다른 클라이언트가 키를 변경하는 상황 시뮬레이션
                    another_redis = await get_async_redis_client()
                    await another_redis.set(key, "99")  # 충돌 유발

                pipe.multi()
                pipe.set(key, current + 1)
                results = await pipe.execute()
                success = True
                final = results[0]
                break
        except aioredis.WatchError:
            # 충돌 감지 → 재시도
            pass

    final_value = await redis.get(key)
    await redis.delete(key)

    return RedisLabResponse(
        stage="7단계: 고급 주제",
        topic="WATCH — Optimistic Locking",
        description=(
            "WATCH key: 키 감시 시작 | "
            "감시 중 다른 클라이언트가 키 변경 시 EXEC가 nil 반환 (트랜잭션 중단) | "
            "재시도 루프로 CAS 패턴 구현 | "
            "충돌 빈도 낮을 때 분산 락보다 효율적"
        ),
        commands_used=[
            f"WATCH {key}",
            f"GET {key}  → current value",
            f"[다른 클라이언트가 키 변경 — 1번째 시도에서 충돌 유발]",
            "MULTI",
            f"SET {key} {{current + 1}}",
            "EXEC  → WatchError 발생 시 nil, 성공 시 [OK]",
        ],
        result={
            "key": key,
            "attempts": attempts,
            "success": success,
            "final_value": final_value,
            "explanation": f"1번째 시도: WatchError(충돌) → {attempts - 1}번 재시도 후 성공" if attempts > 1 else "1번에 성공",
        },
    )


# ══════════════════════════════════════════
# 7-3. 보안 설정 개요
# ══════════════════════════════════════════

@router.get(
    "/security/overview",
    response_model=RedisLabResponse,
    summary="[7-3] 보안 설정 개요 (AUTH / ACL / TLS)",
    description="""
**Redis 보안 설정 3가지**

**1. AUTH (패스워드 인증)**
```
# redis.conf
requirepass myStrongPassword

# 클라이언트
AUTH myStrongPassword
```

**2. ACL (Access Control List) — Redis 6.0+**
```
# ACL 사용자 생성
ACL SETUSER alice on >alice_pw ~cache:* &* +GET +SET +DEL

# 의미: alice 사용자, 비밀번호 alice_pw,
#       cache:* 키에만 접근, GET/SET/DEL만 허용
ACL LIST   # 전체 ACL 조회
ACL WHOAMI # 현재 사용자 확인
```

**3. TLS (전송 암호화)**
```
# redis.conf
tls-port 6380
tls-cert-file /path/to/redis.crt
tls-key-file /path/to/redis.key
tls-ca-cert-file /path/to/ca.crt
```

**추가 보안 권장사항**
- bind 설정으로 내부 네트워크만 허용
- protected-mode yes (기본값 유지)
- rename-command FLUSHALL "" (위험 명령어 비활성화)
""",
)
async def security_overview():
    redis = await _get_redis()

    # ACL WHOAMI: 현재 연결된 사용자
    try:
        current_user = await redis.acl_whoami()
    except Exception:
        current_user = "N/A (ACL not supported)"

    # ACL LIST: 전체 ACL 규칙
    try:
        acl_list = await redis.acl_list()
    except Exception:
        acl_list = ["N/A"]

    # TLS 설정 확인
    try:
        tls_port = await redis.config_get("tls-port")
    except Exception:
        tls_port = {"tls-port": "not configured"}

    return RedisLabResponse(
        stage="7단계: 고급 주제",
        topic="보안 설정 (AUTH / ACL / TLS)",
        description=(
            "AUTH: 패스워드 인증 | "
            "ACL: 사용자별 명령어/키 접근 제어 (Redis 6.0+) | "
            "TLS: 전송 암호화 | "
            "bind + protected-mode로 외부 노출 차단"
        ),
        commands_used=[
            "ACL WHOAMI",
            "ACL LIST",
            "CONFIG GET tls-port",
        ],
        result={
            "current_acl_user": current_user,
            "acl_rules": acl_list,
            "tls_port": tls_port.get("tls-port", "disabled"),
        },
        metadata={
            "security_checklist": [
                "requirepass 설정 (강력한 패스워드)",
                "ACL로 최소 권한 원칙 적용",
                "bind 설정으로 내부 네트워크만 허용",
                "TLS 활성화 (프로덕션)",
                "FLUSHALL/FLUSHDB/CONFIG/DEBUG 명령어 rename 또는 비활성화",
                "Redis 최신 버전 유지",
            ],
        },
    )


# ══════════════════════════════════════════
# 정리
# ══════════════════════════════════════════

@router.delete(
    "/cleanup",
    response_model=RedisLabResponse,
    summary="[유틸] Stage 7 키 전체 삭제",
)
async def cleanup_stage7():
    redis = await _get_redis()
    pattern = make_key("stage7", "*")
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
        stage="7단계: 고급 주제",
        topic="정리",
        description="redis_lab:stage7:* 패턴의 키를 모두 삭제했다.",
        commands_used=[f"SCAN 0 MATCH {pattern} COUNT 100", "DEL <keys...>"],
        result={"deleted_count": deleted},
    )
