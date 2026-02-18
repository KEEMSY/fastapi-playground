# 이벤트 기반 In-App 실시간 알림 시스템

질문/답변 도메인에서 투표, 답변 작성 등의 이벤트가 발생하면 콘텐츠 작성자에게 SSE(Server-Sent Events)로 실시간 알림을 전달한다.

## 1. 설계 원칙

- **이벤트 버스**: 인프로세스 asyncio 기반 Pub/Sub. 질문/답변 서비스는 알림 도메인의 존재를 모른다.
- **fire-and-forget**: `asyncio.create_task`로 알림 처리를 비동기 실행하여 원래 API 응답을 지연시키지 않는다.
- **SSE**: WebSocket보다 단순한 단방향 스트리밍. 브라우저 `EventSource`의 자동 재연결을 활용한다.

## 2. 전체 흐름

```
userB가 userA의 질문에 투표

  vote_question() → db.commit()
      ↓
  event_bus.publish(DomainEvent)     ← 원래 요청은 여기서 바로 응답 반환
      ↓ asyncio.create_task
  event_handler
      ├─ DB에 Notification 저장     (별도 AsyncSession)
      └─ sse_manager.send_to_user() → userA의 Queue에 push
                                          ↓
                                    SSE event_generator() → yield
                                          ↓
                                    userA 브라우저에서 실시간 수신
```

## 3. 파일 구조

```
src/common/events.py                     # EventBus, DomainEvent, EventType 정의
src/domains/notification/
├── models.py                            # Notification DB 모델
├── schemas.py                           # Pydantic 요청/응답 스키마
├── service.py                           # 알림 CRUD (생성, 목록 조회, 읽음 처리)
├── sse_manager.py                       # SSE 연결 관리 (user_id → asyncio.Queue)
├── event_handlers.py                    # 이벤트 수신 → 알림 저장 → SSE 푸시
└── router.py                            # REST API + SSE 스트리밍 엔드포인트
```

## 4. 핵심 구조

### 4.1 이벤트 버스 (`src/common/events.py`)

| 이벤트 타입 | 트리거 | 알림 대상 |
|-------------|--------|-----------|
| `question.voted` | 질문에 투표 | 질문 작성자 |
| `answer.created` | 답변 작성 | 질문 작성자 |
| `answer.voted` | 답변에 투표 | 답변 작성자 |

- async 서비스에서는 `await event_bus.publish(event)` 사용
- sync 라우터에서는 `event_bus.publish_sync(event)` 사용 (`loop.call_soon_threadsafe`로 메인 이벤트 루프에 예약)
- `actor_user_id == target_user_id`인 경우 알림을 생성하지 않음 (자기 행동에 대한 자기 알림 방지)

### 4.2 SSE 매니저 (`sse_manager.py`)

- `dict[int, set[asyncio.Queue]]` 구조로 user_id별 연결 관리
- `set`으로 관리하여 한 사용자의 **다중 탭** 지원 (탭 3개 열면 Queue 3개)
- 현재 단일 인스턴스 기준. 멀티 인스턴스 시 Redis Pub/Sub를 이 파일에만 추가하면 됨

### 4.3 이벤트 핸들러 (`event_handlers.py`)

- `asyncio.create_task`로 실행되므로 원래 요청의 DB 세션이 이미 닫혀 있을 수 있음
- 따라서 `AsyncSessionPrimary()`로 **별도 DB 세션**을 생성하여 알림 저장

## 5. API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/api/notification/list?page=0&size=20` | 알림 목록 (total, unread_count 포함) |
| `PUT` | `/api/notification/read` | 특정 알림 읽음 처리 (`{notification_ids: [1,2]}`) |
| `PUT` | `/api/notification/read-all` | 전체 읽음 처리 |
| `GET` | `/api/notification/stream?token=<jwt>` | SSE 실시간 스트림 |

- REST API는 `Authorization: Bearer <token>` 헤더 인증
- SSE 엔드포인트는 `?token=<jwt>` 쿼리 파라미터 인증 (브라우저 EventSource가 커스텀 헤더를 지원하지 않으므로)

### SSE 이벤트 타입

| event 필드 | 설명 |
|------------|------|
| `connected` | 연결 성공 시 1회 발생 |
| `notification` | 새 알림 도착 |
| `heartbeat` | 30초 간격. NGINX idle timeout 방지용 |

### 응답 예시

```json
// GET /api/notification/list
{
  "total": 1,
  "unread_count": 1,
  "notifications": [{
    "id": 1,
    "actor_username": "userB",
    "event_type": "question.voted",
    "resource_type": "question",
    "resource_id": 1,
    "message": "userB님이 회원님의 질문에 투표했습니다.",
    "is_read": false,
    "created_at": "2026-02-13T15:08:59.872946"
  }]
}
```

```
// GET /api/notification/stream (SSE)
event: connected
data: {"user_id": 1}

event: notification
data: {"id": 1, "event_type": "question.voted", "message": "userB님이 회원님의 질문에 투표했습니다.", ...}
```

## 6. DB 스키마

```sql
CREATE TABLE notification (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    actor_user_id   INTEGER NOT NULL REFERENCES users(id),
    event_type      VARCHAR(50) NOT NULL,
    resource_type   VARCHAR(50) NOT NULL,
    resource_id     INTEGER NOT NULL,
    message         TEXT NOT NULL,
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP NOT NULL
);

CREATE INDEX ix_notification_user_is_read  ON notification(user_id, is_read);
CREATE INDEX ix_notification_user_created  ON notification(user_id, created_at);
```

## 7. 기존 코드 변경 사항

| 파일 | 변경 |
|------|------|
| `question/service.py` | `vote_question()` 끝에 `await event_bus.publish(...)` 1줄 추가 |
| `answer/router.py` | `answer_create()`, `answer_vote()` 끝에 `event_bus.publish_sync(...)` 각 1줄 추가 |
| `main.py` | lifespan에 `register_event_handlers()` 호출 + 라우터 등록 |
| `alembic/env.py` | `Notification` 모델 import 추가 |

## 8. 클라이언트 연동

```javascript
const es = new EventSource(`/api/notification/stream?token=${jwt}`);

es.addEventListener('notification', (e) => {
    const data = JSON.parse(e.data);
    showToast(data.message);       // 토스트 알림
    updateBadge(data.unread_count); // 뱃지 카운트
});
```

## 9. 확장 포인트

| 요구사항 | 변경 위치 |
|----------|-----------|
| 멀티 인스턴스 | `sse_manager.py`에 Redis Pub/Sub 추가 |
| Slack/Email | `event_handlers.py`에 채널별 핸들러 추가 |
| 새 이벤트 타입 | `EventType` Enum 추가 + 해당 서비스에 `publish` 1줄 |
| 알림 설정 (on/off) | `notification/settings` 모델 + 핸들러에서 필터 |
