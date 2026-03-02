---
name: perf-check
description: This skill should be used when the user asks to "performance check", "perf check", "성능 확인", "성능 모니터링", "느린 API", "에러율 확인", or wants to summarize slow endpoints and error rates from Prometheus.
version: 1.0.0
---

# Performance Check

Prometheus(:9090) API를 호출해 느린 엔드포인트와 에러율 상위 5개를 출력하고 Grafana 대시보드 링크를 제공합니다.

## 사용 시점

- "왜 API가 느리지?" 디버깅 시작점
- 배포 후 성능 이상 감지
- 정기적인 성능 루틴 점검
- 예: "/perf-check", "느린 엔드포인트 알려줘"

## 실행 플로우

### 1단계: Prometheus 연결 확인

```bash
curl -s http://localhost:9090/-/healthy
```

연결 실패 시: "Prometheus가 실행 중이지 않습니다. `docker compose -f docker-compose-dev.yml up -d prometheus` 실행 필요"

### 2단계: 핵심 메트릭 수집

#### 2.1 느린 엔드포인트 TOP 5 (p99 레이턴시)

```bash
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.99,sum(rate(http_request_duration_seconds_bucket[5m]))by(handler,le))' \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)['data']['result']
sorted_data = sorted(data, key=lambda x: float(x['value'][1]), reverse=True)
print('=== 느린 엔드포인트 TOP 5 (p99) ===')
for i, r in enumerate(sorted_data[:5], 1):
    handler = r['metric'].get('handler', 'unknown')
    latency = float(r['value'][1])
    print(f'{i}. {handler}: {latency*1000:.1f}ms')
"
```

#### 2.2 에러율 상위 5개 (5xx 응답)

```bash
curl -s 'http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total{status=~"5.."}[5m]))by(handler)' \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)['data']['result']
sorted_data = sorted(data, key=lambda x: float(x['value'][1]), reverse=True)
print('=== 에러율 상위 5개 (5xx) ===')
for i, r in enumerate(sorted_data[:5], 1):
    handler = r['metric'].get('handler', 'unknown')
    rate = float(r['value'][1])
    print(f'{i}. {handler}: {rate:.4f} req/s')
"
```

#### 2.3 현재 요청 처리량 (RPS)

```bash
curl -s 'http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total[5m]))by(handler)' \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)['data']['result']
sorted_data = sorted(data, key=lambda x: float(x['value'][1]), reverse=True)
print('=== 처리량 TOP 5 (req/s) ===')
for i, r in enumerate(sorted_data[:5], 1):
    handler = r['metric'].get('handler', 'unknown')
    rps = float(r['value'][1])
    print(f'{i}. {handler}: {rps:.3f} req/s')
"
```

#### 2.4 DB 커넥션 풀 상태

```bash
curl -s 'http://localhost:9090/api/v1/query?query=sqlalchemy_pool_size' | python3 -c "
import json, sys
data = json.load(sys.stdin)['data']['result']
for r in data:
    print(f'Pool Size: {r[\"value\"][1]}')
"

curl -s 'http://localhost:9090/api/v1/query?query=sqlalchemy_pool_checked_in' | python3 -c "
import json, sys
data = json.load(sys.stdin)['data']['result']
for r in data:
    print(f'Available Connections: {r[\"value\"][1]}')
"
```

#### 2.5 Redis 히트율 (Redis 모듈 사용 시)

```bash
curl -s 'http://localhost:9090/api/v1/query?query=redis_keyspace_hits_total' | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)['data']['result']
    if data:
        print(f'Redis Hits: {data[0][\"value\"][1]}')
    else:
        print('Redis 메트릭 없음')
except:
    print('Redis 메트릭 수집 실패')
"
```

### 3단계: 리포트 출력

```markdown
## 성능 모니터링 요약 — {현재시각}

### 느린 엔드포인트 TOP 5 (p99 레이턴시)

| 순위 | 엔드포인트 | p99 (ms) | 상태 |
|------|-----------|---------|------|
| 1 | GET /api/question/list | 450ms | 🔴 주의 |
| 2 | POST /api/question/create | 230ms | 🟡 보통 |
| 3 | GET /api/answer/list | 120ms | 🟢 양호 |
| 4 | GET /api/user/me | 80ms | 🟢 양호 |
| 5 | POST /api/user/login | 60ms | 🟢 양호 |

기준: 🔴 >300ms | 🟡 100~300ms | 🟢 <100ms

### 에러율 상위 5개 (5xx)

| 순위 | 엔드포인트 | 에러율 (req/s) |
|------|-----------|--------------|
| 1 | POST /api/question/create | 0.05 |

에러율 0이면: ✅ 5xx 에러 없음

### 시스템 현황

- DB 커넥션 풀: {available}/{total} 사용 가능
- Redis 히트율: {hit_rate}%
- 총 처리량: {total_rps} req/s

### Grafana 대시보드

- 전체 개요: http://localhost:3000/d/fastapi-overview
- 엔드포인트별 상세: http://localhost:3000/d/fastapi-endpoints
- DB 성능: http://localhost:3000/d/fastapi-db

### 병목 분석 제안

느린 엔드포인트가 발견된 경우:
1. `selectinload` 누락으로 N+1 쿼리 발생 가능 → service.py 확인
2. DB 인덱스 누락 → EXPLAIN 실행 권장
3. 외부 API 동기 호출 → httpx.AsyncClient 사용 확인
4. 대용량 결과셋 페이지네이션 미적용 → size 기본값 확인
```

## 알림 임계값

| 메트릭 | 주의 | 위험 |
|--------|------|------|
| p99 레이턴시 | >200ms | >500ms |
| 에러율 (5xx) | >0.01 req/s | >0.1 req/s |
| DB 풀 사용률 | >70% | >90% |
| Redis 히트율 | <70% | <50% |

## 참고사항

- Prometheus 포트: 9090 (docker-compose-dev.yml 기준)
- Grafana 포트: 3000
- 메트릭 수집 라이브러리: `prometheus-fastapi-instrumentator`
- 메트릭이 없으면 `instrumentation.py` 설정 확인 필요
