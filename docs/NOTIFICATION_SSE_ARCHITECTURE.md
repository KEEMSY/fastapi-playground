# SSE 기반 실시간 알림 시스템 아키텍처

## 1. 개요

### 목적
기존 REST API 폴링 방식(10초 간격)의 단점을 개선하여 실시간 알림 시스템을 구현합니다.

### 핵심 특징
- **Primary**: SSE (Server-Sent Events)
- **Fallback**: REST API 폴링 (10초 간격)
- **실시간성**: 최대 1.5초 지연
- **멀티 인스턴스 지원**: Redis 없이 동작
- **다중 탭 지원**: 한 사용자가 여러 탭을 열어도 정상 동작

---

## 2. Database Polling + SSE Hybrid 아키텍처

### 2.1 동작 원리

```
[Client A] ←SSE→ [Server 1] ↘
[Client B] ←SSE→ [Server 2] → [PostgreSQL DB] (1.5초마다 폴링)
[Client C] ←SSE→ [Server 3] ↗

각 서버는 독립적으로:
1. 1.5초마다 DB 폴링 (마지막 확인 이후 새 알림 조회)
2. 연결된 사용자만 필터링 (최적화)
3. 새 알림을 해당 서버의 SSE 클라이언트에게만 푸시
```

### 2.2 왜 이 방식을 선택했는가?

#### 과거 이력
- 과거에 이벤트 기반 SSE가 구현되었으나 멀티 인스턴스 환경의 복잡도로 인해 제거됨 (commit 0742360)
- 제거된 컴포넌트: EventBus, SSEConnectionManager, event_handlers

#### 제약사항
- **멀티 인스턴스 환경**: 3개 서버 + 로드밸런서
- **Redis 도입 어려움**: 인프라 복잡도 증가 우려
- **하위 호환성**: 기존 폴링 시스템 유지 필요

#### 선택한 이유
1. **간단한 구조**: 각 서버가 독립적으로 동작, 서버 간 통신 불필요
2. **로드밸런서 설정 변경 불필요**: Sticky Session 등 불필요
3. **Redis 불필요**: DB만으로 동작
4. **자동 복구**: 서버 장애/배포 시 클라이언트가 다른 서버로 재연결
5. **허용 가능한 지연**: 알림 특성상 1-2초 지연은 문제없음

---

## 3. 시스템 구성 요소

### 3.1 백엔드 컴포넌트

#### SSEConnectionManager (`sse_manager.py`)
- **역할**: SSE 연결 관리
- **기능**:
  - user_id별 asyncio.Queue 관리
  - 다중 탭 지원 (set[Queue] 사용)
  - 메시지 전송 (send_to_user)
  - 연결 통계 (get_stats)

#### NotificationPoller (`notification_poller.py`)
- **역할**: DB 폴링 및 SSE 푸시
- **기능**:
  - 1.5초마다 DB 폴링
  - 연결된 사용자만 조회 (최적화)
  - 새 알림을 user_id별로 그룹핑
  - SSE를 통해 실시간 푸시
- **라이프사이클**: 앱 시작/종료 시 자동 시작/중지

#### SSE 엔드포인트 (`router.py`)
- **경로**: `GET /api/notification/stream?token={JWT_TOKEN}`
- **인증**: Query parameter (EventSource는 커스텀 헤더 미지원)
- **이벤트 타입**:
  - `connected`: 연결 성공
  - `notification`: 새 알림
  - `heartbeat`: 연결 유지 (30초 간격)

### 3.2 프론트엔드 컴포넌트

#### SSE 클라이언트 (`notification.js`)
- **연결 관리**: EventSource API 사용
- **재연결 로직**: 최대 5회 재시도 (3초 간격)
- **Fallback**: 재연결 실패 시 자동으로 폴링 모드 전환
- **상태 관리**: Svelte store (notifications, unread_count, total_count)

#### Navigation 컴포넌트
- **라이프사이클**: 로그인 시 SSE 연결, 로그아웃 시 연결 해제
- **다중 탭**: 각 탭마다 독립적으로 연결

---

## 4. 데이터 흐름

### 4.1 알림 생성 흐름

```
1. 사용자 A가 질문에 투표
   ↓
2. question_service에서 notification_service.create_notification() 호출
   ↓
3. DB에 알림 저장 (user_id, actor_user_id, event_type, ...)
   ↓
4. NotificationPoller가 1.5초 이내에 감지
   ↓
5. 해당 user_id에 연결된 SSE 클라이언트에게 푸시
   ↓
6. 프론트엔드에서 실시간으로 알림 표시
```

### 4.2 SSE 연결 흐름

```
1. 클라이언트: startNotificationSSE() 호출
   ↓
2. EventSource 생성: GET /api/notification/stream?token={JWT}
   ↓
3. 서버: JWT 검증 → SSEConnectionManager에 Queue 등록
   ↓
4. 'connected' 이벤트 전송
   ↓
5. 30초마다 'heartbeat' 전송 (NGINX timeout 방지)
   ↓
6. NotificationPoller가 새 알림 감지 시 'notification' 이벤트 전송
```

---

## 5. 성능 및 확장성

### 5.1 DB 부하 분석

#### 폴링 쿼리
```sql
SELECT * FROM notification
WHERE created_at > :last_check
  AND user_id IN (:connected_user_ids)
ORDER BY created_at ASC
```

#### 부하 계산
- 서버 인스턴스: 3대
- 폴링 간격: 1.5초
- QPS: 3 × (60 / 1.5) = **120 queries/sec**
- 인덱스: `ix_notification_user_created (user_id, created_at)`
- **결론**: 인덱스 스캔으로 부하 미미

#### 최적화
- **연결된 사용자만 조회**: `WHERE user_id IN (connected_users)`
- **마지막 확인 이후만 조회**: `WHERE created_at > last_check`
- 연결된 사용자가 없으면 쿼리 생략

### 5.2 메모리 사용량

- SSE 연결당 메모리: ~1-2KB (Queue + 메타데이터)
- 1000명 동시 접속: ~1-2MB
- **결론**: 단일 서버에서 1000명 이상 수용 가능

### 5.3 확장성

#### 현재 구조 (3서버)
- 동시 접속자 3000명 가능
- DB 부하: 120 QPS (매우 낮음)

#### 수평 확장
- 서버 추가 시 DB 부하는 선형 증가
- 10서버까지 확장 가능 (400 QPS, 여전히 낮음)

---

## 6. 멀티 인스턴스 대응

### 6.1 현재 아키텍처

#### 장점
- **로드밸런서 설정 변경 불필요**: 기존 라운드로빈 방식 유지
- **Redis 불필요**: DB만으로 동작
- **서버 장애 시 자동 복구**: 클라이언트 재연결 → 다른 서버
- **배포 시 롤링 업데이트 가능**: 무중단 배포

#### 단점
- **1-2초 지연**: 폴링 간격만큼 지연 발생
- **중복 쿼리**: 각 서버가 독립적으로 DB 폴링

### 6.2 지연 최소화 방법

#### Option 1: 폴링 간격 단축
- 1.5초 → 0.5초 (QPS 3배 증가)
- DB 부하 증가 (120 → 360 QPS, 여전히 낮음)

#### Option 2: Sticky Session (향후)
```nginx
upstream app_servers {
    ip_hash;  # IP 기반 세션 고정
    server app1:8000;
    server app2:8000;
    server app3:8000;
}
```
- **장점**: 같은 클라이언트는 항상 같은 서버로 연결
- **단점**: 서버 장애 시 재연결 필요

#### Option 3: Redis Pub/Sub (향후)
```python
# sse_manager.py에 Redis Pub/Sub 추가
async def subscribe_redis():
    async for message in redis.subscribe('notifications'):
        data = json.loads(message['data'])
        await sse_manager.send_to_user(data['user_id'], data['payload'])

# 알림 발생 시
await redis.publish('notifications', json.dumps({
    'user_id': user_id,
    'payload': notification_json
}))
```
- **장점**: 지연 최소화 (<100ms), 중복 쿼리 제거
- **단점**: Redis 인프라 필요

---

## 7. SSE 이벤트 타입

### 7.1 connected
```
event: connected
data: {"user_id": 1}
```
- **시점**: SSE 연결 성공 직후 (1회)
- **목적**: 연결 확인, 초기화

### 7.2 notification
```
event: notification
data: {"id": 1, "event_type": "question_voted", "message": "...", ...}
```
- **시점**: 새 알림 발생 시 (실시간)
- **payload**: NotificationResponse JSON

### 7.3 heartbeat
```
event: heartbeat
data: {"type": "ping"}
```
- **시점**: 30초마다
- **목적**: NGINX/proxy timeout 방지, 연결 유지

---

## 8. Fallback 전략

### 8.1 자동 Fallback

```javascript
// SSE 연결 시도
startNotificationSSE()
  ↓
실패 시 3초 후 재연결 (최대 5회)
  ↓
재연결 모두 실패 시
  ↓
자동으로 폴링 모드로 전환
```

### 8.2 수동 비활성화

```javascript
// notification.js
const SSE_ENABLED = false; // 폴링 모드로 강제 전환
```

### 8.3 Fallback 시나리오

| 상황 | 동작 |
|------|------|
| 로그인 안 됨 | 폴링 시작 안 함 |
| 토큰 없음 | 폴링 모드로 전환 |
| SSE 연결 실패 | 재연결 시도 → 폴링 |
| SSE 연결 끊김 | 재연결 시도 |
| 서버 재시작 | 재연결 → 다른 서버 |
| NGINX timeout | Heartbeat로 방지 |

---

## 9. 보안

### 9.1 인증

#### SSE 엔드포인트
- **방식**: JWT token (query parameter)
- **이유**: EventSource API는 커스텀 헤더 미지원
- **주의**: 토큰이 URL에 노출되므로 **HTTPS 필수**

#### 보안 권장사항
1. **HTTPS 사용**: 토큰 노출 방지
2. **로그 관리**: 토큰이 로그에 기록되지 않도록 주의
3. **Rate limiting**: 연결 시도 제한 (DDoS 방지)
4. **토큰 만료**: 짧은 만료 시간 설정

### 9.2 권한 검증

- user_id는 JWT에서 추출 (서버 측)
- 클라이언트는 자신의 알림만 수신
- 다른 사용자의 알림은 절대 수신 불가

---

## 10. 모니터링

### 10.1 핵심 메트릭

#### SSE 연결 수
```python
stats = sse_manager.get_stats()
# {
#   "connected_users": 100,
#   "total_connections": 150,  # 다중 탭 포함
#   "users": {1: 2, 2: 1, ...}
# }
```

#### 폴링 성능
- 폴링 쿼리 응답 시간 (DB 메트릭)
- 새 알림 감지 빈도
- 알림 전송 성공/실패율

#### 알림 지연
- 알림 생성 시각 → 클라이언트 수신 시각
- 목표: < 2초

### 10.2 로그

#### 연결 이벤트
```
SSE 연결 추가: user_id=1, 총 연결 수=2
SSE 연결 해제: user_id=1, 남은 연결 수=1
```

#### 폴링 이벤트
```
NotificationPoller started (interval=1.5s)
Found 3 new notifications
Pushed notification 123 to user 1
```

#### 에러
```
SSE 메시지 전송 실패: user_id=1, error=...
DB 조회 에러: ...
```

---

## 11. 운영 가이드

### 11.1 배포 시 주의사항

#### 롤링 업데이트
1. 서버 1 재시작 → 연결된 클라이언트 재연결 → 서버 2 또는 3
2. 서버 2 재시작 → 연결된 클라이언트 재연결 → 서버 1 또는 3
3. 서버 3 재시작 → 연결된 클라이언트 재연결 → 서버 1 또는 2

**결과**: 무중단 배포 가능

#### 주의사항
- 동시에 모든 서버 재시작 금지
- 재연결 로직 동작 확인

### 11.2 문제 해결

#### 알림이 도착하지 않음
1. SSE 연결 상태 확인 (브라우저 Network 탭)
2. NotificationPoller 로그 확인
3. DB에 알림 저장 확인
4. 폴링 모드로 전환하여 테스트

#### 연결이 자주 끊김
1. NGINX timeout 설정 확인 (`proxy_read_timeout`)
2. Heartbeat 전송 확인 (30초 간격)
3. 네트워크 안정성 확인

#### 중복 알림 수신
- 정상 동작 (다중 탭 지원)
- 각 탭마다 독립적으로 수신

---

## 12. 향후 개선 방안

### 12.1 단기 (1-3개월)
- [ ] Prometheus 메트릭 수집
- [ ] Grafana 대시보드 구축
- [ ] 알림 전송 성공/실패 추적

### 12.2 중기 (3-6개월)
- [ ] Redis Pub/Sub 도입 (지연 최소화)
- [ ] Sticky Session 적용 (선택적)
- [ ] 알림 우선순위 시스템

### 12.3 장기 (6개월 이상)
- [ ] WebSocket 전환 검토
- [ ] 푸시 알림 통합 (FCM, APNs)
- [ ] 알림 설정 UI (타입별 on/off)

---

## 13. 참고 자료

### 13.1 관련 문서
- [알림 시스템 개요](./NOTIFICATION_SYSTEM.md)
- [API 명세](./API_SPECIFICATION.md)
- [SSE 운영 가이드](./SSE_OPERATIONS_GUIDE.md)

### 13.2 기술 스택
- **SSE**: Server-Sent Events (EventSource API)
- **FastAPI**: StreamingResponse
- **PostgreSQL**: 알림 저장 및 폴링
- **Svelte**: 프론트엔드 상태 관리

### 13.3 외부 참고
- [MDN - Server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [FastAPI - Custom Response](https://fastapi.tiangolo.com/advanced/custom-response/)
- [EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
