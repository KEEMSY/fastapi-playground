# SSE 실시간 알림 시스템 운영 가이드

## 목차
1. [환경 설정](#1-환경-설정)
2. [배포 가이드](#2-배포-가이드)
3. [모니터링](#3-모니터링)
4. [트러블슈팅](#4-트러블슈팅)
5. [성능 튜닝](#5-성능-튜닝)

---

## 1. 환경 설정

### 1.1 NGINX 설정

SSE는 long-lived connection이므로 NGINX 설정이 중요합니다.

#### 기본 설정

```nginx
upstream app_servers {
    server app1:8000;
    server app2:8000;
    server app3:8000;
}

server {
    listen 80;
    server_name api.example.com;

    # SSE 전용 설정
    location /api/notification/stream {
        proxy_pass http://app_servers;
        proxy_http_version 1.1;

        # 연결 유지
        proxy_set_header Connection "";

        # SSE timeout (5분)
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;

        # 버퍼링 비활성화 (중요!)
        proxy_buffering off;
        proxy_cache off;

        # 헤더 전달
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # NGINX 버퍼링 비활성화
        proxy_set_header X-Accel-Buffering no;
    }

    # 일반 API 설정
    location /api/ {
        proxy_pass http://app_servers;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 중요 설정 설명

| 설정 | 값 | 설명 |
|------|-----|------|
| `proxy_buffering` | off | NGINX 버퍼링 비활성화 (SSE 즉시 전송) |
| `proxy_cache` | off | 캐싱 비활성화 |
| `proxy_read_timeout` | 300s | 읽기 타임아웃 (5분) |
| `X-Accel-Buffering` | no | NGINX 버퍼링 완전 비활성화 |

### 1.2 Docker 환경 설정

#### docker-compose.yml

```yaml
version: '3.8'

services:
  app1:
    build: .
    environment:
      - DB_POOL_SIZE=20
      - DB_MAX_OVERFLOW=30
      - DB_POOL_TIMEOUT=10
    ports:
      - "8001:8000"

  app2:
    build: .
    environment:
      - DB_POOL_SIZE=20
      - DB_MAX_OVERFLOW=30
      - DB_POOL_TIMEOUT=10
    ports:
      - "8002:8000"

  app3:
    build: .
    environment:
      - DB_POOL_SIZE=20
      - DB_MAX_OVERFLOW=30
      - DB_POOL_TIMEOUT=10
    ports:
      - "8003:8000"

  nginx:
    image: nginx:latest
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
    depends_on:
      - app1
      - app2
      - app3

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=fastapi
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    ports:
      - "5432:5432"
```

### 1.3 환경 변수

#### 필수 환경 변수

```bash
# Database
DB_POOL_SIZE=20          # 연결 풀 크기
DB_MAX_OVERFLOW=30       # 최대 오버플로우
DB_POOL_TIMEOUT=10       # 연결 타임아웃 (초)

# 폴링 설정 (선택)
NOTIFICATION_POLL_INTERVAL=1.5  # 폴링 간격 (초)
```

---

## 2. 배포 가이드

### 2.1 무중단 배포 (롤링 업데이트)

#### 배포 순서

```bash
# 1. 서버 1 재시작
docker-compose restart app1
sleep 10  # 안정화 대기

# 2. 서버 2 재시작
docker-compose restart app2
sleep 10

# 3. 서버 3 재시작
docker-compose restart app3
sleep 10

echo "✅ 배포 완료"
```

#### 배포 스크립트 (deploy.sh)

```bash
#!/bin/bash

SERVICES=("app1" "app2" "app3")

for service in "${SERVICES[@]}"; do
    echo "🔄 Restarting $service..."
    docker-compose restart $service

    # 헬스체크
    max_retries=10
    retry=0
    while [ $retry -lt $max_retries ]; do
        if curl -f http://localhost:8000/ > /dev/null 2>&1; then
            echo "✅ $service is healthy"
            break
        fi
        retry=$((retry+1))
        sleep 3
    done

    if [ $retry -eq $max_retries ]; then
        echo "❌ $service failed to start"
        exit 1
    fi

    sleep 5  # 안정화 대기
done

echo "✅ 모든 서버 배포 완료"
```

### 2.2 배포 시 주의사항

#### ⚠️ 금지 사항
- ❌ 모든 서버 동시 재시작
- ❌ 헬스체크 없이 재시작
- ❌ DB 마이그레이션 중 배포

#### ✅ 권장 사항
- ✅ 롤링 업데이트 사용
- ✅ 헬스체크 확인
- ✅ 배포 후 SSE 연결 확인

---

## 3. 모니터링

### 3.1 핵심 메트릭

#### SSE 연결 메트릭

```python
# 추가 예정: Prometheus 메트릭
from prometheus_client import Gauge

sse_connections = Gauge('sse_connections', 'Number of SSE connections', ['server'])
sse_users = Gauge('sse_users', 'Number of connected users', ['server'])

# 사용
sse_connections.labels(server='app1').set(sse_manager.total_connections())
sse_users.labels(server='app1').set(len(sse_manager.get_connected_users()))
```

#### 폴링 메트릭

```python
polling_query_duration = Histogram('polling_query_duration', 'DB polling query duration')
notifications_sent = Counter('notifications_sent', 'Total notifications sent', ['event_type'])
```

### 3.2 로그 모니터링

#### 중요 로그 패턴

```bash
# SSE 연결
grep "SSE 연결 추가" app.log
grep "SSE 연결 해제" app.log

# 폴링
grep "NotificationPoller started" app.log
grep "Found .* new notifications" app.log

# 에러
grep "ERROR" app.log | grep -E "SSE|polling|notification"
```

#### 로그 레벨 설정

```python
# logging.conf
[loggers]
keys=root,notification

[logger_notification]
level=INFO  # 운영: INFO, 개발: DEBUG
handlers=console,file
qualname=src.domains.notification
```

### 3.3 Grafana 대시보드 (예시)

```json
{
  "dashboard": {
    "title": "SSE Notification System",
    "panels": [
      {
        "title": "SSE Connections",
        "targets": [
          {"expr": "sse_connections"}
        ]
      },
      {
        "title": "Connected Users",
        "targets": [
          {"expr": "sse_users"}
        ]
      },
      {
        "title": "Polling Query Duration",
        "targets": [
          {"expr": "histogram_quantile(0.95, polling_query_duration)"}
        ]
      },
      {
        "title": "Notifications Sent",
        "targets": [
          {"expr": "rate(notifications_sent[5m])"}
        ]
      }
    ]
  }
}
```

---

## 4. 트러블슈팅

### 4.1 알림이 도착하지 않음

#### 증상
- 클라이언트에서 알림을 수신하지 못함

#### 진단 절차

```bash
# 1. SSE 연결 확인
# 브라우저 개발자 도구 > Network 탭 > stream 확인
# Type: eventsource
# Status: pending (연결 유지 중)

# 2. 서버 로그 확인
docker-compose logs app1 | grep "SSE 연결"

# 3. 폴링 작동 확인
docker-compose logs app1 | grep "NotificationPoller"

# 4. DB에 알림 저장 확인
psql -h localhost -U postgres -d fastapi -c "SELECT * FROM notification ORDER BY created_at DESC LIMIT 10;"
```

#### 해결 방법

| 문제 | 원인 | 해결 |
|------|------|------|
| SSE 연결 안 됨 | 토큰 만료 | 재로그인 |
| SSE 연결 안 됨 | NGINX 설정 | `proxy_buffering off` 확인 |
| 폴링 작동 안 함 | 서버 미시작 | `await notification_poller.start()` 확인 |
| DB에 알림 없음 | 알림 생성 로직 오류 | `create_notification()` 호출 확인 |

### 4.2 연결이 자주 끊김

#### 증상
- SSE 연결이 30초마다 끊김

#### 원인
- NGINX timeout 설정

#### 해결
```nginx
# NGINX 설정
proxy_read_timeout 300s;  # 5분

# Heartbeat 전송 확인
# 30초마다 "event: heartbeat" 전송되는지 확인
```

### 4.3 중복 알림 수신

#### 증상
- 같은 알림을 여러 번 수신

#### 원인
- 다중 탭 지원 (정상 동작)
- 각 탭마다 독립적으로 SSE 연결

#### 해결
- 의도된 동작이므로 조치 불필요
- 원하지 않으면 클라이언트에서 중복 제거 로직 추가

```javascript
const receivedNotificationIds = new Set();

eventSource.addEventListener('notification', (e) => {
  const notification = JSON.parse(e.data);

  if (receivedNotificationIds.has(notification.id)) {
    return; // 중복 무시
  }

  receivedNotificationIds.add(notification.id);
  // UI 업데이트
});
```

### 4.4 DB 부하 증가

#### 증상
- DB CPU 사용률 증가
- 폴링 쿼리가 느려짐

#### 진단
```sql
-- 폴링 쿼리 성능 확인
EXPLAIN ANALYZE
SELECT * FROM notification
WHERE created_at > NOW() - INTERVAL '10 seconds'
  AND user_id IN (1, 2, 3)
ORDER BY created_at ASC;

-- 인덱스 확인
\d notification
```

#### 해결
```sql
-- 인덱스 재생성
DROP INDEX IF EXISTS ix_notification_user_created;
CREATE INDEX ix_notification_user_created ON notification(user_id, created_at);

-- 통계 업데이트
ANALYZE notification;
```

### 4.5 메모리 누수

#### 증상
- 서버 메모리 사용량 지속 증가

#### 진단
```python
# sse_manager.py에 디버깅 추가
import logging
logger = logging.getLogger(__name__)

def get_stats(self):
    stats = {
        "connected_users": len(self._connections),
        "total_connections": self.total_connections(),
    }
    logger.info(f"SSE Stats: {stats}")
    return stats
```

#### 해결
- 연결 해제 로직 확인 (`disconnect` 호출 확인)
- Queue 누적 확인 (timeout으로 제거)

---

## 5. 성능 튜닝

### 5.1 폴링 간격 조정

#### 기본값
```python
# notification_poller.py
notification_poller = NotificationPoller(interval=1.5)  # 1.5초
```

#### 튜닝 기준

| 사용자 수 | 권장 간격 | DB QPS | 실시간성 |
|----------|----------|--------|----------|
| < 1000 | 0.5초 | 360 | 매우 높음 |
| 1000-5000 | 1.5초 | 120 | 높음 |
| > 5000 | 3.0초 | 60 | 보통 |

#### 동적 조정 (향후)
```python
class NotificationPoller:
    def adjust_interval(self):
        users = len(sse_manager.get_connected_users())
        if users < 100:
            self.interval = 0.5
        elif users < 1000:
            self.interval = 1.5
        else:
            self.interval = 3.0
```

### 5.2 DB 연결 풀 최적화

#### 권장 설정
```bash
# 서버당 연결 풀
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# 계산 방법
# 동시 요청 수: 100 req/sec
# 평균 쿼리 시간: 10ms
# 필요 연결 수: 100 * 0.01 = 1
# 여유분: 20 (버스트 대응)
```

### 5.3 Heartbeat 간격 조정

#### 기본값
```python
# router.py
await asyncio.wait_for(queue.get(), timeout=30.0)  # 30초
```

#### 튜닝 기준
- NGINX timeout보다 짧게 설정
- 권장: NGINX timeout의 50-70%

```python
# NGINX timeout = 300s → Heartbeat = 150-210s
await asyncio.wait_for(queue.get(), timeout=180.0)
```

---

## 6. 체크리스트

### 6.1 배포 전 체크리스트

- [ ] NGINX 설정 확인 (`proxy_buffering off`)
- [ ] 환경 변수 설정
- [ ] DB 인덱스 생성 (`ix_notification_user_created`)
- [ ] 헬스체크 엔드포인트 확인
- [ ] 로그 레벨 설정 (INFO)

### 6.2 배포 후 체크리스트

- [ ] SSE 연결 테스트 (브라우저)
- [ ] 알림 생성 → 수신 테스트
- [ ] 다중 탭 테스트
- [ ] 재연결 테스트 (서버 재시작)
- [ ] Fallback 테스트 (SSE 차단)
- [ ] 로그 확인 (에러 없음)
- [ ] DB 쿼리 성능 확인

### 6.3 일일 모니터링 체크리스트

- [ ] SSE 연결 수 확인
- [ ] DB 부하 확인 (QPS)
- [ ] 에러 로그 확인
- [ ] 알림 전송 성공률 확인

---

## 7. 긴급 상황 대응

### 7.1 SSE 완전 장애

#### 즉시 조치
```javascript
// frontend/src/lib/notification.js
const SSE_ENABLED = false;  // SSE 비활성화
```

#### 결과
- 모든 클라이언트가 폴링 모드로 자동 전환
- 서비스 정상 유지

### 7.2 DB 부하 급증

#### 즉시 조치
```python
# notification_poller.py
notification_poller = NotificationPoller(interval=5.0)  # 간격 증가
```

#### 재시작
```bash
docker-compose restart app1 app2 app3
```

---

## 8. 참고 자료

### 8.1 관련 문서
- [SSE 아키텍처](./NOTIFICATION_SSE_ARCHITECTURE.md)
- [API 명세](./API_SPECIFICATION.md)
- [알림 시스템 개요](./NOTIFICATION_SYSTEM.md)

### 8.2 외부 참고
- [NGINX SSE Configuration](https://www.nginx.com/blog/nginx-1-7-5/)
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)

---

## 9. 문의

### 기술 지원
- 이슈: GitHub Issues
- 문서: `/docs` 디렉토리

### 긴급 연락
- 운영팀: ops@example.com
- 개발팀: dev@example.com
