"""
4단계: 데이터 영속성 & 메모리 관리
──────────────────────────────────────────────────────────────────────────────
목표: 프로덕션 운영에 필요한 영속성 설정과 메모리 정책 이해

주요 개념:
  RDB (Snapshot)     — 주기적으로 메모리 → 디스크 덤프 (BGSAVE)
  AOF (Append-Only)  — 모든 쓰기 명령어를 로그로 기록 (더 안전)
  하이브리드 방식     — RDB + AOF 조합 (Redis 4.0+)
  Eviction 정책      — 메모리 가득 찼을 때 어떤 키를 제거할지
  OBJECT ENCODING    — 내부 인코딩 확인 (메모리 최적화)
"""

from typing import Any, Dict

import aioredis
from fastapi import APIRouter

from src.database.database import get_async_redis_client
from src.domains.redis.constants import make_key
from src.domains.redis.presentation.schemas import RedisLabResponse

router = APIRouter(prefix="/stage4", tags=["Redis-4단계: 영속성&메모리"])


async def _get_redis() -> aioredis.Redis:
    return await get_async_redis_client()


# ══════════════════════════════════════════
# 4-1. 영속성 설정 확인 (RDB / AOF)
# ══════════════════════════════════════════

@router.get(
    "/persistence/config",
    response_model=RedisLabResponse,
    summary="[4-1] RDB / AOF 설정 확인",
    description="""
**Redis 영속성 메커니즘 비교**

| 방식 | 특징 | 장점 | 단점 |
|------|------|------|------|
| **RDB** | 주기적 스냅샷 | 빠른 재시작, 작은 파일 | 마지막 스냅샷 이후 데이터 유실 가능 |
| **AOF** | 쓰기 명령 로그 | 데이터 유실 최소화 | 파일 크기 큼, 재시작 느림 |
| **하이브리드** | RDB+AOF 조합 | 두 방식의 장점 결합 | Redis 4.0+ |

**RDB 스냅샷 트리거 조건 (save 설정)**
```
save 3600 1    # 1시간 내 1개 이상 변경 시
save 300 100   # 5분 내 100개 이상 변경 시
save 60 10000  # 1분 내 10000개 이상 변경 시
```

**AOF fsync 정책**
- `always` : 매 쓰기마다 동기화 (가장 안전, 가장 느림)
- `everysec` : 1초마다 동기화 (균형, **권장**)
- `no` : OS에 맡김 (빠름, 위험)
""",
)
async def persistence_config():
    redis = await _get_redis()

    # CONFIG GET으로 영속성 설정 조회
    rdb_config = await redis.config_get("save")
    aof_enabled = await redis.config_get("appendonly")
    aof_fsync = await redis.config_get("appendfsync")
    aof_rewrite = await redis.config_get("auto-aof-rewrite-percentage")
    rdb_filename = await redis.config_get("dbfilename")
    aof_filename = await redis.config_get("appendfilename")

    # 마지막 저장 정보
    last_save = await redis.lastsave()

    return RedisLabResponse(
        stage="4단계: 영속성&메모리",
        topic="RDB / AOF 설정 조회",
        description=(
            "CONFIG GET save: RDB 스냅샷 조건 | "
            "CONFIG GET appendonly: AOF 활성화 여부 | "
            "CONFIG GET appendfsync: AOF 동기화 정책 | "
            "LASTSAVE: 마지막 RDB 저장 시각"
        ),
        commands_used=[
            "CONFIG GET save",
            "CONFIG GET appendonly",
            "CONFIG GET appendfsync",
            "CONFIG GET auto-aof-rewrite-percentage",
            "LASTSAVE",
        ],
        result={
            "rdb": {
                "filename": rdb_filename.get("dbfilename"),
                "save_conditions": rdb_config.get("save"),
                "last_save_timestamp": last_save,
            },
            "aof": {
                "enabled": aof_enabled.get("appendonly"),
                "filename": aof_filename.get("appendfilename"),
                "fsync_policy": aof_fsync.get("appendfsync"),
                "auto_rewrite_percentage": aof_rewrite.get("auto-aof-rewrite-percentage"),
            },
        },
        metadata={
            "recommendation": "프로덕션에서는 AOF everysec + RDB 하이브리드 방식을 권장",
        },
    )


@router.post(
    "/persistence/bgsave",
    response_model=RedisLabResponse,
    summary="[4-1] RDB — BGSAVE 수동 스냅샷",
    description="""
**BGSAVE vs SAVE**

- `BGSAVE`: fork() 후 자식 프로세스에서 비동기 저장. **메인 스레드 블로킹 없음** → 권장
- `SAVE`: 메인 스레드에서 동기 저장. 완료까지 모든 명령 블로킹 → **프로덕션 금지**
- `BGREWRITEAOF`: AOF 파일을 압축/재작성 (Background)
""",
)
async def bgsave():
    redis = await _get_redis()
    result = await redis.bgsave()
    last_save = await redis.lastsave()

    return RedisLabResponse(
        stage="4단계: 영속성&메모리",
        topic="RDB 수동 스냅샷 (BGSAVE)",
        description=(
            "BGSAVE: fork() 후 자식 프로세스에서 비동기 RDB 저장 → 메인 스레드 블로킹 없음. "
            "SAVE는 동기식이라 프로덕션 금지!"
        ),
        commands_used=["BGSAVE", "LASTSAVE"],
        result={
            "bgsave_response": str(result),
            "last_save_timestamp": last_save,
            "note": "BGSAVE가 진행 중일 때 다시 BGSAVE를 호출하면 에러가 발생할 수 있다.",
        },
    )


# ══════════════════════════════════════════
# 4-2. 메모리 사용량 분석
# ══════════════════════════════════════════

@router.get(
    "/memory/info",
    response_model=RedisLabResponse,
    summary="[4-2] 메모리 사용량 분석 (INFO memory)",
    description="""
**Redis 메모리 정보 주요 항목**

| 항목 | 설명 |
|------|------|
| `used_memory_human` | 현재 사용 메모리 (RSS 아님) |
| `used_memory_rss_human` | OS가 Redis에 할당한 실제 메모리 (RSS) |
| `mem_fragmentation_ratio` | RSS / used_memory. **1.5 이상이면 단편화 문제** |
| `maxmemory_human` | maxmemory 설정값 (0 = 무제한) |
| `maxmemory_policy` | Eviction 정책 |

**메모리 단편화 해소**
Redis 4.0+ 에서는 `MEMORY PURGE` 명령으로 단편화된 메모리를 반환할 수 있다.
""",
)
async def memory_info():
    redis = await _get_redis()

    raw_info = await redis.info("memory")
    maxmemory = await redis.config_get("maxmemory")
    maxmemory_policy = await redis.config_get("maxmemory-policy")

    # 핵심 항목만 추출
    relevant_fields = [
        "used_memory_human",
        "used_memory_rss_human",
        "used_memory_peak_human",
        "mem_fragmentation_ratio",
        "mem_allocator",
        "lazyfree_pending_objects",
    ]
    memory_summary = {k: raw_info.get(k) for k in relevant_fields if k in raw_info}

    return RedisLabResponse(
        stage="4단계: 영속성&메모리",
        topic="메모리 사용량 분석 (INFO memory)",
        description=(
            "used_memory: 실제 데이터 메모리 | "
            "used_memory_rss: OS 할당 메모리 | "
            "mem_fragmentation_ratio: 단편화 비율 (1.5+ 경고) | "
            "maxmemory_policy: Eviction 정책"
        ),
        commands_used=[
            "INFO memory",
            "CONFIG GET maxmemory",
            "CONFIG GET maxmemory-policy",
        ],
        result={
            "memory": memory_summary,
            "limits": {
                "maxmemory": maxmemory.get("maxmemory", "0 (무제한)"),
                "maxmemory_policy": maxmemory_policy.get("maxmemory-policy", "noeviction"),
            },
        },
        metadata={
            "fragmentation_guide": {
                "< 1.0": "메모리 스왑 발생 (위험)",
                "1.0 ~ 1.5": "정상",
                "> 1.5": "메모리 단편화 심각 — MEMORY PURGE 고려",
            },
        },
    )


@router.get(
    "/memory/usage/{key}",
    response_model=RedisLabResponse,
    summary="[4-2] 특정 키 메모리 사용량 (MEMORY USAGE)",
    description="""
**MEMORY USAGE key** : 특정 키가 사용하는 바이트 수를 반환한다.

자료구조 종류, 값의 크기, 내부 인코딩에 따라 메모리 사용량이 다르다.
이를 통해 메모리 최적화 포인트를 찾을 수 있다.

**OBJECT ENCODING** : 내부 인코딩 확인
- String: `embstr` (≤44 bytes) / `raw` (>44 bytes) / `int`
- List: `listpack` (소규모) / `quicklist` (대규모)
- Set: `listpack` / `hashtable`
- ZSet: `listpack` / `skiplist`
- Hash: `listpack` / `hashtable`
""",
)
async def memory_usage(key: str):
    redis = await _get_redis()

    exists = await redis.exists(key)
    if not exists:
        return RedisLabResponse(
            stage="4단계: 영속성&메모리",
            topic="MEMORY USAGE — 키 없음",
            description=f"키 '{key}'가 존재하지 않는다.",
            commands_used=[f"EXISTS {key}  → 0"],
            result={"key": key, "exists": False},
        )

    usage_bytes = await redis.memory_usage(key)
    encoding = await redis.object_encoding(key)
    key_type = await redis.type(key)
    ttl = await redis.ttl(key)

    return RedisLabResponse(
        stage="4단계: 영속성&메모리",
        topic="특정 키 메모리 사용량 (MEMORY USAGE / OBJECT ENCODING)",
        description=(
            "MEMORY USAGE key: 키가 사용하는 바이트 수 | "
            "OBJECT ENCODING key: 내부 인코딩 (listpack/quicklist/skiplist/hashtable 등)"
        ),
        commands_used=[
            f"MEMORY USAGE {key}  → {usage_bytes} bytes",
            f"OBJECT ENCODING {key}  → {encoding}",
            f"TYPE {key}  → {key_type}",
        ],
        result={
            "key": key,
            "type": key_type,
            "encoding": encoding,
            "memory_bytes": usage_bytes,
            "ttl": ttl,
        },
        metadata={
            "encoding_guide": {
                "embstr": "문자열 ≤44 bytes, 메모리 효율 최적",
                "raw": "문자열 >44 bytes",
                "int": "정수형 (별도 저장 없이 포인터로 처리)",
                "listpack": "소규모 자료구조, 연속 메모리 배열 (효율적)",
                "quicklist": "대규모 List, listpack 노드들의 연결 리스트",
                "skiplist": "대규모 Sorted Set, O(log N) 연산",
                "hashtable": "대규모 Set/Hash, O(1) 연산",
            },
        },
    )


# ══════════════════════════════════════════
# 4-3. Eviction 정책
# ══════════════════════════════════════════

@router.get(
    "/eviction/policies",
    response_model=RedisLabResponse,
    summary="[4-3] Eviction 정책 설명",
    description="""
**Redis Eviction 정책 (8가지)**

`maxmemory` 초과 시 어떤 키를 제거할지 결정한다.

| 정책 | 동작 |
|------|------|
| `noeviction` | 제거 안 함, 쓰기 오류 반환 **(기본값)** |
| `allkeys-lru` | 전체 키 중 가장 오래 사용되지 않은 것 제거 |
| `volatile-lru` | TTL 있는 키 중 LRU 제거 |
| `allkeys-lfu` | 전체 키 중 가장 사용 빈도 낮은 것 제거 (Redis 4.0+) |
| `volatile-lfu` | TTL 있는 키 중 LFU 제거 |
| `allkeys-random` | 전체 키 중 랜덤 제거 |
| `volatile-random` | TTL 있는 키 중 랜덤 제거 |
| `volatile-ttl` | TTL 가장 짧은 키 우선 제거 |

**권장 설정**
- 캐시 용도: `allkeys-lru` 또는 `allkeys-lfu`
- 세션 저장소: `volatile-lru`
- 메시지 큐: `noeviction` (메시지 유실 방지)
""",
)
async def eviction_policies():
    redis = await _get_redis()

    current_policy = await redis.config_get("maxmemory-policy")
    maxmemory = await redis.config_get("maxmemory")

    policies = {
        "noeviction": "제거 안 함, 쓰기 오류 반환 (기본값, 메시지 큐에 적합)",
        "allkeys-lru": "전체 키 중 LRU 제거 (캐시 서버에 권장)",
        "volatile-lru": "TTL 있는 키 중 LRU 제거 (세션 서버에 권장)",
        "allkeys-lfu": "전체 키 중 LFU 제거 (Redis 4.0+, allkeys-lru 대안)",
        "volatile-lfu": "TTL 있는 키 중 LFU 제거",
        "allkeys-random": "전체 키 중 랜덤 제거",
        "volatile-random": "TTL 있는 키 중 랜덤 제거",
        "volatile-ttl": "TTL 가장 짧은 키 우선 제거",
    }

    return RedisLabResponse(
        stage="4단계: 영속성&메모리",
        topic="Eviction 정책",
        description=(
            "maxmemory 초과 시 어떤 키를 제거할지 결정하는 8가지 정책. "
            "용도에 맞는 정책 선택이 중요하다."
        ),
        commands_used=[
            "CONFIG GET maxmemory-policy",
            "CONFIG GET maxmemory",
            "# 변경: CONFIG SET maxmemory-policy allkeys-lru",
        ],
        result={
            "current_policy": current_policy.get("maxmemory-policy"),
            "maxmemory": maxmemory.get("maxmemory", "0 (무제한)"),
            "all_policies": policies,
        },
        metadata={
            "lru_vs_lfu": {
                "LRU": "가장 최근 사용 시각 기준 — 최근에 쓴 데이터가 중요할 때",
                "LFU": "사용 빈도 기준 — 자주 쓰이는 데이터를 더 오래 유지",
            },
        },
    )
