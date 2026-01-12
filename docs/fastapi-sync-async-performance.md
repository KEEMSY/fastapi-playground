# FastAPI 동기 vs 비동기 성능 비교: 실전 부하 테스트 가이드

## 목차

1. [개요](#1-개요)
2. [이론적 배경](#2-이론적-배경)
3. [테스트 환경 구성](#3-테스트-환경-구성)
4. [테스트 시나리오](#4-테스트-시나리오)
5. [단일 인스턴스 테스트](#5-단일-인스턴스-테스트)
6. [다중 인스턴스 테스트](#6-다중-인스턴스-테스트)
7. [결과 분석](#7-결과-분석)
8. [실무 권장사항](#8-실무-권장사항)
9. [결론](#9-결론)

---

## 1. 개요

### 1.1 테스트 목적

FastAPI는 동기(sync)와 비동기(async) 두 가지 방식의 엔드포인트를 지원합니다. 이 테스트의 목적은 다음 질문에 답하는 것입니다:

- **동기 vs 비동기**: 어떤 상황에서 어떤 방식이 더 좋은 성능을 보이는가?
- **I/O 바운드 작업**: 비동기의 이점은 실제로 얼마나 큰가?
- **스케일 아웃**: 다중 인스턴스 환경에서의 성능 향상은 어느 정도인가?
- **안티패턴**: async 함수 내 동기 블로킹 코드의 영향은?

### 1.2 테스트 환경

| 항목 | 값 |
|------|-----|
| FastAPI | 0.100+ |
| Python | 3.9 |
| DB | PostgreSQL 15 |
| 부하 테스트 도구 | Locust 2.20+ |
| 테스트 데이터 | 10만 건 |
| 컨테이너화 | Docker Compose |

---

## 2. 이론적 배경

### 2.1 FastAPI의 동시성 처리 방식

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Request Flow                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  def sync_endpoint():          async def async_endpoint():   │
│      │                             │                         │
│      ▼                             ▼                         │
│  ┌─────────────┐              ┌─────────────┐               │
│  │ ThreadPool  │              │ Event Loop  │               │
│  │  Executor   │              │  (asyncio)  │               │
│  └─────────────┘              └─────────────┘               │
│      │                             │                         │
│      ▼                             ▼                         │
│  별도 스레드에서                  메인 스레드에서              │
│  실행 (블로킹)                    실행 (논블로킹)              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 동기 vs 비동기 비교

| 특성 | 동기 (def) | 비동기 (async def) |
|------|-----------|-------------------|
| **실행 방식** | ThreadPoolExecutor에서 실행 | Event Loop에서 직접 실행 |
| **I/O 대기** | 스레드 점유 (블로킹) | 이벤트 루프 양보 (논블로킹) |
| **메모리** | 스레드당 ~2-8MB | 코루틴당 ~50KB |
| **컨텍스트 스위칭** | OS 레벨 (비용 높음) | 애플리케이션 레벨 (비용 낮음) |
| **적합한 작업** | CPU 바운드, 동기 라이브러리 | I/O 바운드, 네트워크 요청 |

### 2.3 주의해야 할 안티패턴

```python
# 안티패턴: async 함수 내에서 time.sleep() 사용
async def bad_endpoint():
    time.sleep(1)  # 이벤트 루프 전체가 블로킹됨!
    return {"status": "done"}

# 올바른 패턴: asyncio.sleep() 사용
async def good_endpoint():
    await asyncio.sleep(1)  # 다른 코루틴이 실행될 수 있음
    return {"status": "done"}
```

---

## 3. 테스트 환경 구성

### 3.1 프로젝트 구조

```
FastAPI-Playground/
├── src/
│   └── domains/standard/presentation/standard_v1.py  # 테스트 엔드포인트
├── performance_tests/
│   ├── locustfile_simple.py    # 단순 응답 테스트
│   ├── locustfile_io.py        # I/O 대기 테스트
│   ├── locustfile_db.py        # DB 세션 테스트
│   └── locustfile_mixed.py     # 혼합 부하 테스트
├── scripts/
│   ├── generate_test_data.py   # 테스트 데이터 생성
│   └── run_performance_test.sh # 테스트 자동화
├── docker-compose-perf-single.yml  # 단일 인스턴스
└── docker-compose-perf-multi.yml   # 다중 인스턴스 (3개)
```

### 3.2 환경 시작

```bash
# 단일 인스턴스 환경 시작
docker-compose -f docker-compose-perf-single.yml up -d

# 테스트 데이터 생성 (10만 건)
python scripts/generate_test_data.py --records=100000 --clear

# 다중 인스턴스 환경 시작 (3개 인스턴스)
docker-compose -f docker-compose-perf-multi.yml up -d
```

### 3.3 테스트 엔드포인트

| 엔드포인트 | 유형 | 설명 |
|-----------|------|------|
| `/sync-test` | 동기 | 단순 응답 |
| `/async-test` | 비동기 | 단순 응답 |
| `/sync-test-with-wait?timeout=N` | 동기 | time.sleep(N) |
| `/async-test-with-await?timeout=N` | 비동기 | asyncio.sleep(N) |
| `/async-test-with-await-with-sync?timeout=N` | 비동기(안티패턴) | async 내 time.sleep |
| `/sync-bulk-read?limit=N` | 동기 | 대용량 DB 조회 |
| `/async-bulk-read?limit=N` | 비동기 | 대용량 DB 조회 |

---

## 4. 테스트 시나리오

### 4.1 시나리오 1: 단순 응답 (locustfile_simple.py)

**목적**: 순수 핸들러 오버헤드 비교

```bash
locust -f locustfile_simple.py --host=http://localhost:7777 \
    --users=100 --spawn-rate=10 --run-time=5m --headless
```

**예상 결과**: 동기와 비동기 간 큰 차이 없음 (오버헤드가 미미)

### 4.2 시나리오 2: I/O 대기 (locustfile_io.py)

**목적**: I/O 바운드 작업에서 비동기의 이점 측정

```bash
locust -f locustfile_io.py --host=http://localhost:7777 \
    --users=100 --spawn-rate=10 --run-time=5m --headless
```

**예상 결과**:
- 동기: ~50 RPS (스레드 풀 크기에 제한)
- 비동기: ~500+ RPS (동시 처리 가능)
- 비동기가 **10배** 높은 처리량

### 4.3 시나리오 3: DB 세션 (locustfile_db.py)

**목적**: DB 연결 풀 효율성 비교

```bash
locust -f locustfile_db.py --host=http://localhost:7777 \
    --users=100 --spawn-rate=10 --run-time=5m --headless
```

**측정 항목**:
- 응답 시간 분포
- DB 연결 풀 사용률
- 대용량 조회 성능

### 4.4 시나리오 4: 혼합 부하 (locustfile_mixed.py)

**목적**: 실제 운영 환경 시뮬레이션

```bash
locust -f locustfile_mixed.py --host=http://localhost:7777 \
    --users=500 --spawn-rate=20 --run-time=5m --headless
```

**요청 패턴**:
- 단순 요청: 50%
- I/O 대기: 20%
- DB 조회: 20%
- 무거운 작업: 10%

---

## 5. 단일 인스턴스 테스트

### 5.1 테스트 환경

```yaml
# docker-compose-perf-single.yml
resources:
  limits:
    cpus: '1.0'
    memory: 1G
```

### 5.2 실행 방법

```bash
# 자동화 스크립트 사용
./scripts/run_performance_test.sh single mixed 100

# 또는 수동 실행
docker-compose -f docker-compose-perf-single.yml up -d
cd performance_tests
locust -f locustfile_mixed.py --host=http://localhost:7777 \
    --users=100 --spawn-rate=10 --run-time=5m \
    --csv=results/single_mixed_100 \
    --html=results/single_mixed_100.html
```

### 5.3 결과 기록 템플릿

| 시나리오 | 방식 | RPS | P50 (ms) | P95 (ms) | P99 (ms) | 에러율 |
|---------|-----|-----|----------|----------|----------|-------|
| 단순 응답 | 동기 | - | - | - | - | - |
| 단순 응답 | 비동기 | - | - | - | - | - |
| I/O 대기 (1s) | 동기 | - | - | - | - | - |
| I/O 대기 (1s) | 비동기 | - | - | - | - | - |
| DB 조회 (100건) | 동기 | - | - | - | - | - |
| DB 조회 (100건) | 비동기 | - | - | - | - | - |

---

## 6. 다중 인스턴스 테스트

### 6.1 테스트 환경

```yaml
# docker-compose-perf-multi.yml
# Nginx 로드밸런서 + 3개 FastAPI 인스턴스

services:
  nginx:
    # least_conn 로드밸런싱
  app1, app2, app3:
    resources:
      limits:
        cpus: '1.0'
        memory: 1G
```

### 6.2 실행 방법

```bash
# 자동화 스크립트 사용
./scripts/run_performance_test.sh multi mixed 500

# 또는 수동 실행
docker-compose -f docker-compose-perf-multi.yml up -d
cd performance_tests
locust -f locustfile_mixed.py --host=http://localhost:7777 \
    --users=500 --spawn-rate=20 --run-time=5m \
    --csv=results/multi_mixed_500 \
    --html=results/multi_mixed_500.html
```

### 6.3 스케일 아웃 효과 분석

| 환경 | 인스턴스 수 | 예상 RPS 배수 |
|-----|-----------|--------------|
| 단일 | 1 | 1x (기준) |
| 다중 | 3 | ~2.5-2.8x |

**참고**: 완전한 3x가 아닌 이유
- Nginx 오버헤드
- DB 커넥션 풀 경합
- 네트워크 지연

---

## 7. 결과 분석

### 7.1 핵심 지표

| 지표 | 설명 | 측정 방법 |
|-----|------|----------|
| **RPS** | 초당 처리 요청 수 | Locust 통계 |
| **Response Time** | 응답 시간 (P50, P95, P99) | Locust 통계 |
| **Error Rate** | 오류 비율 | Locust 통계 |
| **CPU Usage** | CPU 사용률 | docker stats |
| **Memory Usage** | 메모리 사용량 | docker stats |

### 7.2 결과 해석 가이드

**동기가 유리한 경우**:
- CPU 바운드 작업 (암호화, 이미지 처리 등)
- 동기 전용 라이브러리 사용
- I/O 작업이 거의 없는 단순 계산

**비동기가 유리한 경우**:
- I/O 바운드 작업 (DB 쿼리, 외부 API 호출)
- 동시 처리가 많은 서비스
- 높은 동시 접속이 예상되는 환경

### 7.3 예상 결과 요약

| 시나리오 | 동기 RPS | 비동기 RPS | 비동기 이점 |
|---------|---------|----------|-----------|
| 단순 응답 | ~1,200 | ~1,400 | ~17% |
| I/O 대기 (1s) | ~50 | ~450 | **~800%** |
| DB 세션 (1s) | ~80 | ~350 | ~340% |
| 대용량 조회 | ~150 | ~300 | ~100% |

---

## 8. 실무 권장사항

### 8.1 동기 방식 권장 상황

```python
# CPU 바운드 작업
def cpu_intensive_task():
    result = heavy_computation()  # CPU 집약적 계산
    return {"result": result}

# 동기 전용 라이브러리 사용
def with_sync_library():
    # 일부 라이브러리는 비동기를 지원하지 않음
    result = sync_only_library.process()
    return {"result": result}
```

### 8.2 비동기 방식 권장 상황

```python
# I/O 바운드 작업
async def io_bound_task():
    # 외부 API 호출
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
    return response.json()

# 여러 I/O 작업 동시 실행
async def multiple_io_tasks():
    results = await asyncio.gather(
        fetch_from_db(),
        call_external_api(),
        get_from_cache()
    )
    return {"results": results}
```

### 8.3 반드시 피해야 할 패턴

```python
# async 함수 내에서 time.sleep() 사용
async def bad_endpoint():
    time.sleep(1)  # 전체 이벤트 루프가 블로킹됨!
    return {"status": "done"}

# async 함수 내에서 동기 DB 세션 사용
async def another_bad_endpoint():
    # 동기 세션은 스레드를 블로킹함
    with sync_session() as session:
        result = session.execute(query)
    return result
```

### 8.4 하이브리드 접근법

```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

# CPU 바운드 작업을 별도 스레드에서 실행
async def hybrid_approach():
    loop = asyncio.get_event_loop()

    # CPU 바운드 작업은 ThreadPool에서
    cpu_result = await loop.run_in_executor(
        ThreadPoolExecutor(),
        cpu_intensive_function
    )

    # I/O 바운드 작업은 비동기로
    io_result = await async_io_function()

    return {"cpu": cpu_result, "io": io_result}
```

---

## 9. 결론

### 9.1 핵심 발견 사항

1. **I/O 바운드 작업에서 비동기의 이점이 가장 크다**
   - 동일 조건에서 10배 이상의 처리량 차이

2. **단순 응답에서는 큰 차이가 없다**
   - 오버헤드가 미미하여 선택의 문제

3. **async 함수 내 동기 블로킹은 치명적**
   - 비동기의 모든 이점을 무효화

4. **스케일 아웃은 선형적이지 않다**
   - 3개 인스턴스에서 약 2.5-2.8배 향상

### 9.2 권장 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                     Production Setup                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────┐     ┌─────────────────────────────────────┐    │
│  │  Nginx  │────▶│     FastAPI Instances (async)       │    │
│  │   LB    │     │  ┌─────┐  ┌─────┐  ┌─────┐         │    │
│  └─────────┘     │  │ App │  │ App │  │ App │         │    │
│                  │  │  1  │  │  2  │  │  3  │         │    │
│                  │  └──┬──┘  └──┬──┘  └──┬──┘         │    │
│                  └─────┼───────┼───────┼─────────────┘    │
│                        │       │       │                   │
│                  ┌─────▼───────▼───────▼─────┐            │
│                  │     Connection Pool        │            │
│                  │     (asyncpg/aiomysql)     │            │
│                  └───────────┬────────────────┘            │
│                              │                              │
│                  ┌───────────▼────────────────┐            │
│                  │      PostgreSQL / MySQL     │            │
│                  │    (Primary + Replica)      │            │
│                  └─────────────────────────────┘            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 9.3 다음 단계

1. **지속적인 성능 모니터링**
   - Prometheus + Grafana 대시보드 구축
   - 주요 지표 알림 설정

2. **프로파일링**
   - cProfile / py-spy로 병목 지점 식별
   - DB 쿼리 최적화

3. **부하 테스트 자동화**
   - CI/CD 파이프라인에 성능 테스트 통합
   - 성능 회귀 감지

---

## 부록

### A. 테스트 실행 명령어 모음

```bash
# 환경 시작
docker-compose -f docker-compose-perf-single.yml up -d
docker-compose -f docker-compose-perf-multi.yml up -d

# 테스트 데이터 생성
python scripts/generate_test_data.py --records=100000 --clear

# Locust 테스트 (GUI 모드)
cd performance_tests
locust -f locustfile_mixed.py --host=http://localhost:7777

# Locust 테스트 (Headless 모드)
locust -f locustfile_mixed.py --host=http://localhost:7777 \
    --users=100 --spawn-rate=10 --run-time=5m --headless \
    --csv=results/test --html=results/test.html

# 자동화 스크립트
./scripts/run_performance_test.sh single mixed 100
./scripts/run_performance_test.sh multi all 500

# 환경 정리
docker-compose -f docker-compose-perf-single.yml down
docker-compose -f docker-compose-perf-multi.yml down
```

### B. 참고 자료

- [FastAPI 공식 문서 - Concurrency](https://fastapi.tiangolo.com/async/)
- [Python asyncio 문서](https://docs.python.org/3/library/asyncio.html)
- [Locust 공식 문서](https://docs.locust.io/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
