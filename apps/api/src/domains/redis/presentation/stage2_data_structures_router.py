"""
2단계: 핵심 자료구조 실습
──────────────────────────────────────────────────────────────────────────────
목표: 각 자료구조의 사용 시나리오 및 내부 인코딩 이해

자료구조 요약:
  String   — 가장 기본. 캐싱, 카운터, 분산 락
  List     — Linked List 기반. 큐/스택, 최근 목록
  Set      — 중복 없는 집합. 태그, 친구 관계
  Sorted Set (ZSet) — Score 기반 정렬. 랭킹, 우선순위 큐
  Hash     — 필드-값 맵. 사용자 프로필, 세션
  HyperLogLog — 유니크 원소 수 근사 추정 (오차 ±0.81%)
"""

import time
from typing import Any, Dict, List

import aioredis
from fastapi import APIRouter

from src.database.database import get_async_redis_client
from src.domains.redis.constants import (
    STAGE2_HLL_VISITORS,
    STAGE2_HASH_USER,
    STAGE2_LIST_QUEUE,
    STAGE2_LIST_RECENT,
    STAGE2_SET_TAGS,
    STAGE2_SET_ONLINE,
    STAGE2_STRING_COUNTER,
    STAGE2_ZSET_RANKING,
    make_key,
)
from src.domains.redis.presentation.schemas import (
    HashSetRequest,
    HyperLogLogAddRequest,
    ListPushRequest,
    RedisLabResponse,
    SetAddRequest,
    ZSetAddRequest,
)

router = APIRouter(prefix="/stage2", tags=["Redis-2단계: 자료구조"])


async def _get_redis() -> aioredis.Redis:
    return await get_async_redis_client()


# ══════════════════════════════════════════
# 2-1. String — 카운터
# ══════════════════════════════════════════

@router.post(
    "/string/counter/incr",
    response_model=RedisLabResponse,
    summary="[2-1] String — INCR/INCRBY 카운터",
    description="""
**String 자료구조: 카운터 패턴**

`INCR` / `INCRBY` 는 **원자적(Atomic)** 연산이다.
Single-thread 특성 덕분에 별도 Lock 없이 동시성 안전 카운터를 구현할 수 있다.

사용 예시:
- 게시글 조회수
- API 요청 카운트
- 좋아요 수
""",
)
async def string_counter_incr():
    redis = await _get_redis()

    # INCR: 1씩 증가 (키 없으면 0에서 시작)
    v1 = await redis.incr(STAGE2_STRING_COUNTER)
    v2 = await redis.incr(STAGE2_STRING_COUNTER)

    # INCRBY: 지정값만큼 증가
    v3 = await redis.incrby(STAGE2_STRING_COUNTER, 10)

    # DECR / DECRBY
    v4 = await redis.decrby(STAGE2_STRING_COUNTER, 5)

    current = await redis.get(STAGE2_STRING_COUNTER)

    return RedisLabResponse(
        stage="2단계: 자료구조",
        topic="String — 카운터 (INCR/INCRBY)",
        description=(
            "INCR key: +1 원자적 증가 | "
            "INCRBY key delta: 지정값 증가 | "
            "DECR/DECRBY: 감소. 모두 Single-thread 덕분에 Race Condition 없음"
        ),
        commands_used=[
            f"INCR {STAGE2_STRING_COUNTER}  → {v1}",
            f"INCR {STAGE2_STRING_COUNTER}  → {v2}",
            f"INCRBY {STAGE2_STRING_COUNTER} 10  → {v3}",
            f"DECRBY {STAGE2_STRING_COUNTER} 5   → {v4}",
        ],
        result={"current_value": int(current)},
        metadata={"use_cases": ["조회수", "좋아요", "API 호출 횟수", "재고 감소"]},
    )


@router.delete(
    "/string/counter/reset",
    response_model=RedisLabResponse,
    summary="[2-1] String — 카운터 초기화",
)
async def string_counter_reset():
    redis = await _get_redis()
    await redis.set(STAGE2_STRING_COUNTER, 0)
    return RedisLabResponse(
        stage="2단계: 자료구조",
        topic="String — 카운터 초기화",
        description="SET key 0 으로 카운터를 초기화한다.",
        commands_used=[f"SET {STAGE2_STRING_COUNTER} 0"],
        result={"value": 0},
    )


# ══════════════════════════════════════════
# 2-2. List — 큐 / 최근 방문 목록
# ══════════════════════════════════════════

@router.post(
    "/list/queue/push",
    response_model=RedisLabResponse,
    summary="[2-2] List — RPUSH (큐 enqueue)",
    description="""
**List 자료구조: 큐 패턴**

- `RPUSH key value` → 오른쪽(tail)에 추가 = **Enqueue**
- `LPOP key` → 왼쪽(head)에서 꺼냄 = **Dequeue**
- 이를 통해 FIFO 큐를 구현한다.

반대로 Stack(LIFO)을 원하면 `RPUSH` + `RPOP` 사용.

**내부 인코딩**
- 원소 수 ≤ 128, 각 값 ≤ 64 bytes → `listpack` (메모리 효율적)
- 그 이상 → `quicklist` (연결 리스트)
""",
)
async def list_enqueue(req: ListPushRequest):
    redis = await _get_redis()
    length = await redis.rpush(STAGE2_LIST_QUEUE, req.value)

    return RedisLabResponse(
        stage="2단계: 자료구조",
        topic="List — 큐 (RPUSH/LPOP)",
        description="RPUSH key value: tail에 추가(Enqueue). LPOP key: head에서 제거(Dequeue). → FIFO 큐",
        commands_used=[f"RPUSH {STAGE2_LIST_QUEUE} {req.value!r}"],
        result={"enqueued_value": req.value, "queue_length": length},
    )


@router.get(
    "/list/queue/pop",
    response_model=RedisLabResponse,
    summary="[2-2] List — LPOP (큐 dequeue)",
)
async def list_dequeue():
    redis = await _get_redis()
    value = await redis.lpop(STAGE2_LIST_QUEUE)
    length = await redis.llen(STAGE2_LIST_QUEUE)

    return RedisLabResponse(
        stage="2단계: 자료구조",
        topic="List — 큐 (LPOP)",
        description="LPOP key: head에서 꺼낸다. 큐가 비어 있으면 None을 반환한다.",
        commands_used=[f"LPOP {STAGE2_LIST_QUEUE}", f"LLEN {STAGE2_LIST_QUEUE}"],
        result={"dequeued_value": value, "remaining_length": length},
    )


@router.post(
    "/list/recent/add",
    response_model=RedisLabResponse,
    summary="[2-2] List — 최근 방문 목록 (LPUSH + LTRIM)",
    description="""
**List: 최근 N개 목록 관리 패턴**

1. `LPUSH` : 왼쪽(head)에 새 항목 추가
2. `LTRIM` : 처음 N개만 유지, 나머지 삭제

이 패턴으로 최신 5개 방문 페이지, 최근 검색어 등을 O(1)으로 관리한다.
""",
)
async def list_recent_add(req: ListPushRequest):
    redis = await _get_redis()
    max_recent = 5

    length = await redis.lpush(STAGE2_LIST_RECENT, req.value)
    await redis.ltrim(STAGE2_LIST_RECENT, 0, max_recent - 1)

    recent = await redis.lrange(STAGE2_LIST_RECENT, 0, -1)

    return RedisLabResponse(
        stage="2단계: 자료구조",
        topic="List — 최근 방문 목록",
        description=f"LPUSH: 새 항목을 head에 추가 | LTRIM: 최신 {max_recent}개만 유지",
        commands_used=[
            f"LPUSH {STAGE2_LIST_RECENT} {req.value!r}",
            f"LTRIM {STAGE2_LIST_RECENT} 0 {max_recent - 1}",
            f"LRANGE {STAGE2_LIST_RECENT} 0 -1",
        ],
        result={"added": req.value, "recent_list": recent},
        metadata={"max_items": max_recent},
    )


# ══════════════════════════════════════════
# 2-3. Set — 태그 / 집합 연산
# ══════════════════════════════════════════

@router.post(
    "/set/tags/add",
    response_model=RedisLabResponse,
    summary="[2-3] Set — SADD 태그 추가",
    description="""
**Set 자료구조: 태그 시스템**

- 중복 없는 멤버 집합
- `SADD key member` : 추가 (이미 있으면 무시)
- `SMEMBERS key` : 전체 조회
- `SISMEMBER key member` : 멤버 포함 여부 (O(1))
- `SUNION key [key ...]` : 합집합
- `SINTER key [key ...]` : 교집합
- `SDIFF key [key ...]` : 차집합

**활용 예시**
- 게시글 태그
- 팔로우/팔로워 관계
- 온라인 사용자 목록
""",
)
async def set_add_tag(req: SetAddRequest):
    redis = await _get_redis()
    added = await redis.sadd(STAGE2_SET_TAGS, req.member)
    members = await redis.smembers(STAGE2_SET_TAGS)
    is_member = await redis.sismember(STAGE2_SET_TAGS, req.member)

    return RedisLabResponse(
        stage="2단계: 자료구조",
        topic="Set — 태그 (SADD/SMEMBERS/SISMEMBER)",
        description="SADD: 멤버 추가(중복 무시) | SMEMBERS: 전체 조회 | SISMEMBER: O(1) 포함 여부 확인",
        commands_used=[
            f"SADD {STAGE2_SET_TAGS} {req.member!r}  → {added} (1=추가됨, 0=이미 있음)",
            f"SMEMBERS {STAGE2_SET_TAGS}",
            f"SISMEMBER {STAGE2_SET_TAGS} {req.member!r}  → {int(is_member)}",
        ],
        result={"added_count": added, "all_tags": sorted(list(members)), "is_member": bool(is_member)},
    )


@router.get(
    "/set/operations",
    response_model=RedisLabResponse,
    summary="[2-3] Set — 집합 연산 (SUNION/SINTER/SDIFF)",
    description="두 사용자의 태그 집합으로 합집합·교집합·차집합을 시연한다.",
)
async def set_operations():
    redis = await _get_redis()

    key_a = make_key("stage2", "set", "user_a_tags")
    key_b = make_key("stage2", "set", "user_b_tags")

    # 샘플 데이터
    await redis.delete(key_a, key_b)
    await redis.sadd(key_a, "python", "fastapi", "redis", "docker")
    await redis.sadd(key_b, "python", "django", "redis", "postgres")

    union = await redis.sunion(key_a, key_b)
    inter = await redis.sinter(key_a, key_b)
    diff_a = await redis.sdiff(key_a, key_b)   # A에만 있는 것
    diff_b = await redis.sdiff(key_b, key_a)   # B에만 있는 것

    await redis.delete(key_a, key_b)

    return RedisLabResponse(
        stage="2단계: 자료구조",
        topic="Set — 집합 연산",
        description="SUNION: 합집합 | SINTER: 교집합 | SDIFF: 차집합. 공통 관심사, 추천 시스템에 활용",
        commands_used=[
            f"SUNION {key_a} {key_b}",
            f"SINTER {key_a} {key_b}",
            f"SDIFF {key_a} {key_b}",
        ],
        result={
            "user_a": ["python", "fastapi", "redis", "docker"],
            "user_b": ["python", "django", "redis", "postgres"],
            "union_공통+전체": sorted(list(union)),
            "intersection_공통관심사": sorted(list(inter)),
            "only_in_a": sorted(list(diff_a)),
            "only_in_b": sorted(list(diff_b)),
        },
    )


# ══════════════════════════════════════════
# 2-4. Sorted Set (ZSet) — 랭킹 보드
# ══════════════════════════════════════════

@router.post(
    "/zset/ranking/add",
    response_model=RedisLabResponse,
    summary="[2-4] Sorted Set — ZADD 점수 추가",
    description="""
**Sorted Set 자료구조: 랭킹 보드**

- `ZADD key score member` : score 기준으로 정렬된 멤버 추가
- `ZRANGE key start stop [REV] [WITHSCORES]` : 범위 조회
- `ZRANK key member` : 순위 조회 (0-indexed, 낮은 점수 = 낮은 순위)
- `ZREVRANK key member` : 역순 순위 (높은 점수 = 낮은 순위 번호)

**내부 인코딩**
- 원소 수 ≤ 128, 값 ≤ 64 bytes → `listpack`
- 그 이상 → `skiplist` (O(log N) 삽입/삭제/조회)
""",
)
async def zset_add(req: ZSetAddRequest):
    redis = await _get_redis()
    await redis.zadd(STAGE2_ZSET_RANKING, {req.member: req.score})

    # 상위 10명 조회 (점수 내림차순)
    top10 = await redis.zrange(STAGE2_ZSET_RANKING, 0, 9, desc=True, withscores=True)
    rank = await redis.zrevrank(STAGE2_ZSET_RANKING, req.member)   # 0-indexed

    return RedisLabResponse(
        stage="2단계: 자료구조",
        topic="Sorted Set — 랭킹 보드",
        description="ZADD: score 기반 정렬 삽입 | ZRANGE REV WITHSCORES: 상위 N명 조회 | ZREVRANK: 내 순위",
        commands_used=[
            f"ZADD {STAGE2_ZSET_RANKING} {req.score} {req.member!r}",
            f"ZRANGE {STAGE2_ZSET_RANKING} 0 9 REV WITHSCORES",
            f"ZREVRANK {STAGE2_ZSET_RANKING} {req.member!r}",
        ],
        result={
            "added": {"member": req.member, "score": req.score},
            "my_rank": rank + 1 if rank is not None else None,  # 1-indexed
            "top10": [{"member": m, "score": s} for m, s in top10],
        },
    )


@router.get(
    "/zset/ranking/top",
    response_model=RedisLabResponse,
    summary="[2-4] Sorted Set — 상위 랭킹 조회",
)
async def zset_top_ranking(top: int = 5):
    redis = await _get_redis()
    ranking = await redis.zrange(STAGE2_ZSET_RANKING, 0, top - 1, desc=True, withscores=True)
    total = await redis.zcard(STAGE2_ZSET_RANKING)

    return RedisLabResponse(
        stage="2단계: 자료구조",
        topic="Sorted Set — 상위 랭킹",
        description=f"ZRANGE key 0 {top - 1} REV WITHSCORES: 상위 {top}명 조회 | ZCARD: 전체 멤버 수",
        commands_used=[
            f"ZRANGE {STAGE2_ZSET_RANKING} 0 {top - 1} REV WITHSCORES",
            f"ZCARD {STAGE2_ZSET_RANKING}",
        ],
        result={
            "top_ranking": [
                {"rank": i + 1, "member": m, "score": s}
                for i, (m, s) in enumerate(ranking)
            ],
            "total_members": total,
        },
    )


# ══════════════════════════════════════════
# 2-5. Hash — 사용자 프로필
# ══════════════════════════════════════════

@router.post(
    "/hash/user/{user_id}/set",
    response_model=RedisLabResponse,
    summary="[2-5] Hash — HSET 필드 저장",
    description="""
**Hash 자료구조: 사용자 프로필**

- `HSET key field value [field value ...]` : 필드-값 저장
- `HGET key field` : 단일 필드 조회
- `HGETALL key` : 전체 필드 조회 (Dict 반환)
- `HMGET key field [field ...]` : 여러 필드 한 번에 조회
- `HDEL key field` : 필드 삭제
- `HINCRBY key field increment` : 숫자 필드 증가

**String vs Hash**
사용자 프로필을 String(JSON)으로 저장하면 필드 하나만 변경해도 전체를 읽고 쓴다.
Hash는 필드 단위로 읽고 쓸 수 있어 메모리와 처리량이 효율적이다.
""",
)
async def hash_set(user_id: str, req: HashSetRequest):
    redis = await _get_redis()
    key = f"{STAGE2_HASH_USER}:{user_id}"

    await redis.hset(key, req.field, req.value)
    profile = await redis.hgetall(key)

    return RedisLabResponse(
        stage="2단계: 자료구조",
        topic="Hash — 사용자 프로필 (HSET/HGETALL)",
        description="HSET key field value: 필드 저장 | HGETALL key: 전체 프로필 조회",
        commands_used=[
            f"HSET {key} {req.field} {req.value!r}",
            f"HGETALL {key}",
        ],
        result={"user_id": user_id, "profile": profile},
    )


@router.get(
    "/hash/user/{user_id}",
    response_model=RedisLabResponse,
    summary="[2-5] Hash — HGETALL 전체 프로필 조회",
)
async def hash_get(user_id: str):
    redis = await _get_redis()
    key = f"{STAGE2_HASH_USER}:{user_id}"
    profile = await redis.hgetall(key)

    return RedisLabResponse(
        stage="2단계: 자료구조",
        topic="Hash — 전체 프로필 조회 (HGETALL)",
        description="HGETALL key: 모든 필드-값 쌍을 Dict로 반환한다.",
        commands_used=[f"HGETALL {key}"],
        result={"user_id": user_id, "profile": profile, "exists": bool(profile)},
    )


# ══════════════════════════════════════════
# 2-6. HyperLogLog — 유니크 방문자 수
# ══════════════════════════════════════════

@router.post(
    "/hll/visitors/add",
    response_model=RedisLabResponse,
    summary="[2-6] HyperLogLog — PFADD 방문자 추가",
    description="""
**HyperLogLog: 유니크 원소 수 근사 추정**

- 실제 원소를 저장하지 않고 **확률적 알고리즘**으로 개수만 추정
- 오차율: ±0.81%
- 최대 메모리: **12KB** (원소 수와 무관!)
- `PFADD key element [element ...]` : 원소 추가
- `PFCOUNT key [key ...]` : 유니크 원소 수 추정
- `PFMERGE destkey sourcekey [sourcekey ...]` : 여러 HLL 합산

**vs Set**
- Set: 정확한 개수, 멤버 조회 가능, **원소 수만큼 메모리 증가**
- HLL: 근사값, 멤버 조회 불가, **항상 12KB**

수백만 명의 DAU(일일 활성 사용자)를 Set으로 추적하면 수백 MB가 필요하지만,
HLL은 12KB로 해결된다.
""",
)
async def hll_add_visitor(req: HyperLogLogAddRequest):
    redis = await _get_redis()

    added = await redis.pfadd(STAGE2_HLL_VISITORS, req.user_id)
    count = await redis.pfcount(STAGE2_HLL_VISITORS)

    return RedisLabResponse(
        stage="2단계: 자료구조",
        topic="HyperLogLog — 유니크 방문자 수 (PFADD/PFCOUNT)",
        description=(
            "PFADD key element: 원소 추가 (내부적으로 해시만 저장) | "
            "PFCOUNT key: 유니크 수 근사 추정 (오차 ±0.81%, 최대 메모리 12KB)"
        ),
        commands_used=[
            f"PFADD {STAGE2_HLL_VISITORS} {req.user_id!r}  → {added}",
            f"PFCOUNT {STAGE2_HLL_VISITORS}  → {count}",
        ],
        result={
            "added_new": bool(added),
            "estimated_unique_visitors": count,
            "memory_note": "원소 수와 무관하게 최대 12KB만 사용",
        },
    )


# ══════════════════════════════════════════
# 정리
# ══════════════════════════════════════════

@router.delete(
    "/cleanup",
    response_model=RedisLabResponse,
    summary="[유틸] Stage 2 키 전체 삭제",
)
async def cleanup_stage2():
    redis = await _get_redis()
    pattern = make_key("stage2", "*")
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
        stage="2단계: 자료구조",
        topic="정리",
        description=f"redis_lab:stage2:* 패턴의 키를 모두 삭제했다.",
        commands_used=[f"SCAN 0 MATCH {pattern} COUNT 100", "DEL <keys...>"],
        result={"deleted_count": deleted},
    )
