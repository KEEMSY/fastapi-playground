# Redis 학습 커리큘럼 실습 모듈

FastAPI + Redis 조합으로 Redis의 핵심 개념부터 실무 패턴, 성능 최적화, 고급 주제까지 7단계로 체계적으로 학습한다.
총 47개 엔드포인트를 통해 각 명령어가 실제로 어떻게 동작하는지 응답에서 직접 확인할 수 있다.

| 단계 | 주제 | 엔드포인트 수 |
|------|------|:---:|
| 1단계 | Redis 기초 이해 | 7 |
| 2단계 | 핵심 자료구조 실습 | 13 |
| 3단계 | 실무 패턴 구현 (FastAPI 연동) | 9 |
| 4단계 | 데이터 영속성 & 메모리 관리 | 5 |
| 5단계 | 성능 최적화 | 6 |
| 6단계 | 고가용성 구성 | _(별도 인프라 필요, 미구현)_ |
| 7단계 | 고급 주제 | 7 |
| **합계** | | **47** |

**베이스 URL:** `/api/v1/redis`

---

## 1. 실행 방법

### Redis 컨테이너 확인

`docker-compose-dev.yml`에 Redis 7.2.5-alpine 컨테이너가 정의되어 있다.

```bash
# 개발 환경 전체 실행
docker compose -f docker-compose-dev.yml up -d

# Redis만 따로 실행
docker compose -f docker-compose-dev.yml up -d redis
```

포트 매핑: `localhost:16379 → 컨테이너:6379`

### Swagger UI 접근

서버 실행 후 브라우저에서 Swagger UI로 전 엔드포인트를 직접 실행할 수 있다.

```
http://localhost:8000/docs#/
```

태그 필터: `Redis-1단계: 기초` ~ `Redis-7단계: 고급 주제`

---

## 2. 파일 구조

```
src/domains/redis/
├── constants.py                              # 키 prefix 상수 및 make_key() 헬퍼
├── router.py                                 # 단계별 라우터 통합 (/api/v1/redis)
└── presentation/
    ├── schemas.py                            # Pydantic 요청/응답 스키마
    ├── stage1_basics_router.py               # 1단계: 기초 (7개)
    ├── stage2_data_structures_router.py      # 2단계: 자료구조 (13개)
    ├── stage3_patterns_router.py             # 3단계: 실무 패턴 (9개)
    ├── stage4_persistence_router.py          # 4단계: 영속성&메모리 (5개)
    ├── stage5_performance_router.py          # 5단계: 성능 최적화 (6개)
    └── stage7_advanced_router.py             # 7단계: 고급 주제 (7개)
```

**키 네이밍 규칙:** 모든 실습용 키는 `redis_lab:{stage}:{topic}:...` 형태로 저장되어
다른 도메인 키와 충돌하지 않는다.

---

## 3. 단계별 엔드포인트

### 1단계: Redis 기초 이해

**목표:** Redis의 핵심 명령어(SET/GET/DEL/EXPIRE/SCAN)와 Single-thread 작동 원리 파악

| Method | Path | 설명 | 핵심 명령어 |
|--------|------|------|------------|
| `POST` | `/stage1/set` | 키-값 저장 (TTL 선택) | `SET key value [EX seconds]` |
| `GET` | `/stage1/get/{key}` | 키 조회 (없으면 null) | `GET key` |
| `DELETE` | `/stage1/del/{key}` | 키 삭제 | `DEL key` |
| `POST` | `/stage1/expire` | TTL 설정/조회/제거 데모 | `EXPIRE`, `TTL`, `PERSIST` |
| `GET` | `/stage1/exists/{key}` | 키 존재 여부 및 타입 확인 | `EXISTS key`, `TYPE key` |
| `GET` | `/stage1/scan-vs-keys` | SCAN vs KEYS 비교 데모 | `SCAN cursor MATCH pattern COUNT n` |
| `DELETE` | `/stage1/cleanup` | Stage 1 실습 키 전체 삭제 | `SCAN` + `DEL` |

---

### 2단계: 핵심 자료구조 실습

**목표:** String / List / Set / Sorted Set / Hash / HyperLogLog 각 자료구조의 사용 시나리오와 내부 인코딩 이해

| Method | Path | 설명 | 핵심 명령어 |
|--------|------|------|------------|
| `POST` | `/stage2/string/counter/incr` | 원자적 카운터 증가 | `INCR`, `INCRBY`, `DECRBY` |
| `DELETE` | `/stage2/string/counter/reset` | 카운터 초기화 | `SET key 0` |
| `POST` | `/stage2/list/queue/push` | 큐 Enqueue | `RPUSH key value` |
| `GET` | `/stage2/list/queue/pop` | 큐 Dequeue | `LPOP key`, `LLEN key` |
| `POST` | `/stage2/list/recent/add` | 최근 N개 목록 관리 | `LPUSH`, `LTRIM`, `LRANGE` |
| `POST` | `/stage2/set/tags/add` | 태그 추가 및 조회 | `SADD`, `SMEMBERS`, `SISMEMBER` |
| `GET` | `/stage2/set/operations` | 집합 연산 시연 | `SUNION`, `SINTER`, `SDIFF` |
| `POST` | `/stage2/zset/ranking/add` | 랭킹 점수 추가 | `ZADD key score member`, `ZREVRANK` |
| `GET` | `/stage2/zset/ranking/top` | 상위 랭킹 조회 | `ZRANGE key 0 N REV WITHSCORES`, `ZCARD` |
| `POST` | `/stage2/hash/user/{user_id}/set` | 사용자 프로필 필드 저장 | `HSET key field value`, `HGETALL` |
| `GET` | `/stage2/hash/user/{user_id}` | 전체 프로필 조회 | `HGETALL key` |
| `POST` | `/stage2/hll/visitors/add` | 유니크 방문자 수 추정 | `PFADD key element`, `PFCOUNT key` |
| `DELETE` | `/stage2/cleanup` | Stage 2 실습 키 전체 삭제 | `SCAN` + `DEL` |

---

### 3단계: 실무 패턴 구현 (FastAPI 연동)

**목표:** FastAPI 환경에서 가장 자주 쓰이는 Redis 패턴 구현 및 이해

| Method | Path | 설명 | 핵심 명령어 |
|--------|------|------|------------|
| `GET` | `/stage3/cache/{resource_id}` | Cache-Aside: DB 쿼리 결과 캐싱 | `GET`, `SET key value EX 300` |
| `DELETE` | `/stage3/cache/{resource_id}` | 캐시 무효화 (Cache Invalidation) | `DEL cache_key` |
| `POST` | `/stage3/blacklist/token` | JWT 토큰 블랙리스트 등록 | `SET blacklist:{jti} revoked EX ttl` |
| `GET` | `/stage3/blacklist/check/{token}` | 토큰 유효성 검사 | `EXISTS blacklist:{token}` |
| `POST` | `/stage3/rate-limit/check` | 슬라이딩 윈도우 Rate Limiting | `ZADD`, `ZREMRANGEBYSCORE`, `ZCARD` |
| `POST` | `/stage3/lock/acquire` | 분산 락 획득 | `SET lock:{resource} {id} NX EX ttl` |
| `DELETE` | `/stage3/lock/release/{resource}` | 분산 락 해제 (Lua 원자적) | `EVAL lua_script 1 key value` |
| `POST` | `/stage3/pubsub/publish` | Pub/Sub 메시지 발행 | `PUBLISH channel message` |
| `DELETE` | `/stage3/cleanup` | Stage 3 실습 키 전체 삭제 | `SCAN` + `DEL` |

---

### 4단계: 데이터 영속성 & 메모리 관리

**목표:** 프로덕션 운영에 필요한 영속성 설정과 메모리 관리 정책 이해

| Method | Path | 설명 | 핵심 명령어 |
|--------|------|------|------------|
| `GET` | `/stage4/persistence/config` | RDB / AOF 설정 조회 | `CONFIG GET save`, `CONFIG GET appendonly` |
| `POST` | `/stage4/persistence/bgsave` | RDB 수동 스냅샷 트리거 | `BGSAVE`, `LASTSAVE` |
| `GET` | `/stage4/memory/info` | 메모리 사용량 분석 | `INFO memory`, `CONFIG GET maxmemory-policy` |
| `GET` | `/stage4/memory/usage/{key}` | 특정 키 메모리 사용량 | `MEMORY USAGE key`, `OBJECT ENCODING key` |
| `GET` | `/stage4/eviction/policies` | Eviction 8가지 정책 설명 | `CONFIG GET maxmemory-policy` |

---

### 5단계: 성능 최적화

**목표:** RTT 최소화, 원자적 연산, 병목 분석, 비동기 삭제 등 실무 성능 이슈 대응

| Method | Path | 설명 | 핵심 명령어 |
|--------|------|------|------------|
| `POST` | `/stage5/pipeline/benchmark` | Pipeline vs 개별 전송 벤치마크 | `pipeline().execute()` |
| `POST` | `/stage5/lua/atomic-counter` | Lua 원자적 조건부 카운터 | `EVAL script numkeys key arg` |
| `GET` | `/stage5/scan/demo` | SCAN 커서 순회 상세 데모 | `SCAN cursor MATCH pattern COUNT n` |
| `GET` | `/stage5/slowlog` | 느린 명령어 분석 | `SLOWLOG GET`, `SLOWLOG LEN` |
| `POST` | `/stage5/unlink/demo` | DEL vs UNLINK 비교 | `UNLINK key`, `DEL key` |
| `GET` | `/stage5/server/stats` | 서버 전반 성능 통계 | `INFO server/stats/clients/replication` |

---

### 7단계: 고급 주제

**목표:** Stream, 트랜잭션, 보안 설정 등 실무 심화 활용

| Method | Path | 설명 | 핵심 명령어 |
|--------|------|------|------------|
| `POST` | `/stage7/stream/publish` | Stream 메시지 발행 | `XADD key * field value`, `XLEN` |
| `GET` | `/stage7/stream/read` | Stream 메시지 읽기 & Consumer Group 조회 | `XRANGE key 0 + COUNT n`, `XINFO GROUPS` |
| `DELETE` | `/stage7/stream/trim` | Stream 크기 제한 | `XTRIM key MAXLEN n` |
| `POST` | `/stage7/transaction/multi-exec` | MULTI/EXEC 트랜잭션 | `MULTI`, `EXEC`, `DISCARD` |
| `POST` | `/stage7/transaction/watch` | WATCH Optimistic Locking | `WATCH key`, `MULTI`, `EXEC` |
| `GET` | `/stage7/security/overview` | 보안 설정 개요 (AUTH/ACL/TLS) | `ACL WHOAMI`, `ACL LIST` |
| `DELETE` | `/stage7/cleanup` | Stage 7 실습 키 전체 삭제 | `SCAN` + `DEL` |

---

## 4. 핵심 개념 치트시트

### 자료구조별 주요 명령어

| 자료구조 | 대표 명령어 | 내부 인코딩 | 주요 활용 |
|----------|------------|------------|----------|
| **String** | `SET`, `GET`, `INCR`, `SETNX` | `embstr` / `raw` / `int` | 캐싱, 카운터, 분산 락 |
| **List** | `RPUSH`, `LPOP`, `LRANGE`, `LTRIM` | `listpack` → `quicklist` | FIFO 큐, 최근 N개 목록 |
| **Set** | `SADD`, `SMEMBERS`, `SINTER`, `SUNION` | `listpack` → `hashtable` | 태그, 팔로우 관계, 중복 제거 |
| **Sorted Set** | `ZADD`, `ZRANGE`, `ZREVRANK`, `ZCARD` | `listpack` → `skiplist` | 랭킹 보드, 우선순위 큐 |
| **Hash** | `HSET`, `HGET`, `HGETALL`, `HINCRBY` | `listpack` → `hashtable` | 사용자 프로필, 세션 데이터 |
| **HyperLogLog** | `PFADD`, `PFCOUNT`, `PFMERGE` | 고정 12KB | 유니크 방문자 수 추정 (오차 ±0.81%) |
| **Stream** | `XADD`, `XRANGE`, `XREADGROUP`, `XACK` | — | 영속 메시지 큐 (Kafka 대용) |

### 실무 패턴 요약

| 패턴 | 구현 | 핵심 포인트 |
|------|------|------------|
| **Cache-Aside** | `GET` → MISS 시 DB 조회 → `SET EX` | TTL 설정 필수, Cache Stampede 주의 |
| **JWT Blacklist** | 로그아웃 시 `SET blacklist:{jti} 1 EX ttl` | 토큰 만료 시 자동 삭제 → 메모리 누수 없음 |
| **Rate Limiting** | Sorted Set + `ZREMRANGEBYSCORE` + `ZCARD` | 슬라이딩 윈도우로 경계 취약점 해소 |
| **분산 락** | `SET lock:{res} {uuid} NX EX ttl` | NX=원자적 확인, TTL=Deadlock 방지, Lua로 해제 |
| **Pub/Sub** | `PUBLISH channel message` | 영속성 없음 → 영속성 필요 시 Stream 사용 |

### Cache-Aside 흐름

```
Client
  │
  ▼
GET cache:{id}
  │
  ├─ Cache HIT ──────────────────────────────────► 즉시 반환 (수 ms)
  │
  └─ Cache MISS
        │
        ▼
      DB 조회 (수십~수백 ms)
        │
        ▼
      SET cache:{id} <json> EX 300
        │
        ▼
      응답 반환
```

### 프로덕션 안티패턴

| 안티패턴 | 문제 | 대안 |
|----------|------|------|
| `KEYS *` | Single-thread 전체 블로킹 → 서비스 장애 | `SCAN cursor MATCH * COUNT 100` |
| `DEL` (대용량 키) | 수백ms 블로킹 | `UNLINK` (비동기 백그라운드 삭제) |
| `SAVE` | 메인 스레드 동기 블로킹 | `BGSAVE` (fork 후 자식 프로세스 저장) |
| `noeviction` (캐시 서버) | 메모리 초과 시 쓰기 오류 | `allkeys-lru` 또는 `allkeys-lfu` |
| JSON을 String으로 전체 저장 후 필드 수정 | 불필요한 직렬화/역직렬화 | Hash로 필드 단위 관리 (`HSET`/`HGET`) |

---

## 5. 6단계 (고가용성) 별도 안내

6단계 — Sentinel / Cluster는 다수의 Redis 컨테이너가 필요하므로
이 프로젝트에서는 구현하지 않았다.

### Sentinel vs Cluster

| 구성 | 목적 | 구조 |
|------|------|------|
| **Replication** | 읽기 부하 분산 | Master 1 + Replica N |
| **Sentinel** | 자동 Failover | Sentinel 3대 이상으로 Master 감시 |
| **Cluster** | 수평 확장 (샤딩) | Hash Slot (0~16383)을 N개 Master에 분산 |

### 로컬 실습 방법

`docker-compose-monitoring.yml`을 참고하여 별도 Redis 클러스터 환경을 구성할 수 있다.

```bash
docker compose -f docker-compose-monitoring.yml up -d
```

---

## 6. 참고 자료

| 플랫폼 | 강의명 | 특징 |
|--------|--------|------|
| 인프런 | [실전! Redis 활용](https://www.inflearn.com/course/%EC%8B%A4%EC%A0%84-redis-%ED%99%9C%EC%9A%A9) | 실무 패턴 중심 |
| 패스트캠퍼스 | The RED: Redis by 강대명 | 대용량 트래픽 아키텍처 |
| redisGate | [교육 과정](http://redisgate.kr/redisgate/education/redis_education.php) | 5단계 체계적 커리큘럼 |
| Hello Interview | [Redis Deep Dive](https://www.hellointerview.com/learn/system-design/deep-dives/redis) | 시스템 디자인 관점 |
| Udemy | Redis 완벽 가이드 (한글 자막) | 이커머스 앱 구축 실습 |
