# SSE(Server-Sent Events) 완전 가이드

## 목차
1. [SSE란 무엇인가?](#1-sse란-무엇인가)
2. [SSE vs WebSocket vs Polling](#2-sse-vs-websocket-vs-polling)
3. [SSE 동작 원리](#3-sse-동작-원리)
4. [EventSource API 사용법](#4-eventsource-api-사용법)
5. [서버 측 구현 방식](#5-서버-측-구현-방식)
6. [현재 구현된 로직 상세 설명](#6-현재-구현된-로직-상세-설명)
7. [전체 데이터 흐름](#7-전체-데이터-흐름)
8. [코드 레벨 설명](#8-코드-레벨-설명)

---

## 1. SSE란 무엇인가?

### 1.1 정의

**SSE(Server-Sent Events)**는 서버에서 클라이언트로 **실시간 데이터를 푸시**하는 웹 기술입니다.

### 1.2 핵심 개념

```
일반적인 HTTP 요청/응답:
┌─────────┐  요청 →  ┌─────────┐
│ 클라이언트 │ ←──────── │  서버   │
└─────────┘  ← 응답   └─────────┘
   (연결 종료)

SSE:
┌─────────┐  연결 유지 → ┌─────────┐
│ 클라이언트 │ ←────────── │  서버   │
└─────────┘  ← 데이터 푸시 └─────────┘
   (계속 연결 유지, 서버가 필요할 때마다 데이터 전송)
```

### 1.3 특징

1. **단방향 통신**: 서버 → 클라이언트만 가능 (클라이언트 → 서버는 별도 HTTP 요청 필요)
2. **자동 재연결**: 연결이 끊어지면 브라우저가 자동으로 재연결 시도
3. **HTTP 기반**: 기존 HTTP 프로토콜 사용 (특별한 프로토콜 불필요)
4. **텍스트 기반**: UTF-8 텍스트 데이터만 전송 가능 (보통 JSON 사용)
5. **이벤트 타입**: 여러 종류의 이벤트를 구분하여 전송 가능

### 1.4 주요 사용 사례

- ✅ **알림 시스템** (우리의 경우)
- ✅ 실시간 뉴스 피드
- ✅ 주식 가격 업데이트
- ✅ 소셜 미디어 라이브 업데이트
- ✅ 서버 모니터링 대시보드
- ✅ 채팅 (읽기 전용, 예: 공지사항)

---

## 2. SSE vs WebSocket vs Polling

### 2.1 비교표

| 특징 | Polling | SSE | WebSocket |
|------|---------|-----|-----------|
| **통신 방향** | 양방향 (매번 새 요청) | 단방향 (서버→클라이언트) | 양방향 (실시간) |
| **프로토콜** | HTTP | HTTP | WebSocket (ws://) |
| **재연결** | 매번 연결/해제 | 자동 재연결 | 수동 재연결 |
| **서버 부하** | 높음 (주기적 요청) | 낮음 (연결 유지) | 낮음 (연결 유지) |
| **실시간성** | 낮음 (폴링 간격) | 높음 (즉시 푸시) | 매우 높음 (즉시 양방향) |
| **구현 복잡도** | 매우 쉬움 | 쉬움 | 중간 |
| **브라우저 지원** | 모든 브라우저 | 대부분 (IE 제외) | 대부분 |
| **방화벽 통과** | 쉬움 | 쉬움 | 어려움 (일부 차단) |
| **적합한 용도** | 단순 조회 | 서버→클라이언트 푸시 | 실시간 양방향 통신 |

### 2.2 시각적 비교

#### Polling (10초 간격)
```
Time: 0s    10s    20s    30s    40s    50s
      ↓     ↓      ↓      ↓      ↓      ↓
┌─────┐   ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
│ 요청 │   │ 요청 │ │ 요청 │ │ 요청 │ │ 요청 │ │ 요청 │
└─────┘   └─────┘ └─────┘ └─────┘ └─────┘ └─────┘
  ↓ 응답    ↓      ↓      ↓      ↓      ↓
  (연결종료) (연결종료) (연결종료) (연결종료) (연결종료) (연결종료)

문제점:
- 데이터가 없어도 계속 요청
- 최대 10초 지연
- 불필요한 HTTP 오버헤드
```

#### SSE (연결 유지)
```
Time: 0s    10s    20s    30s    40s    50s
      ↓                   ↓            ↓
┌─────────────────────────────────────────┐
│         연결 유지 (keep-alive)           │
└─────────────────────────────────────────┘
                        ↓            ↓
                    새 데이터 푸시  새 데이터 푸시

장점:
- 데이터가 있을 때만 전송
- 즉시 전송 (지연 없음)
- HTTP 오버헤드 1회만
```

#### WebSocket (양방향)
```
Time: 0s    10s    20s    30s    40s    50s
      ↓     ↑ ↓    ↑     ↓      ↑ ↓    ↑
┌─────────────────────────────────────────┐
│    양방향 실시간 통신 (full-duplex)        │
└─────────────────────────────────────────┘

장점:
- 양방향 실시간 통신
- 매우 낮은 지연
- 바이너리 데이터 지원
```

### 2.3 왜 SSE를 선택했는가?

우리의 알림 시스템에 SSE가 적합한 이유:

1. **단방향 통신 충분**: 알림은 서버→클라이언트만 필요
2. **간단한 구현**: WebSocket보다 훨씬 쉬움
3. **자동 재연결**: 브라우저가 알아서 처리
4. **HTTP 기반**: 기존 인프라 그대로 사용 가능
5. **폴링보다 효율적**: 불필요한 요청 제거

---

## 3. SSE 동작 원리

### 3.1 HTTP 연결 유지 메커니즘

#### 일반 HTTP 요청/응답
```http
# 클라이언트 → 서버
GET /api/data HTTP/1.1
Host: example.com

# 서버 → 클라이언트
HTTP/1.1 200 OK
Content-Type: application/json

{"data": "hello"}
# 연결 종료
```

#### SSE 연결
```http
# 클라이언트 → 서버 (연결 시작)
GET /api/notification/stream?token=abc123 HTTP/1.1
Host: example.com
Accept: text/event-stream

# 서버 → 클라이언트 (연결 유지)
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

# 데이터 전송 (연결 유지된 상태에서 계속 전송)
data: {"message": "hello"}\n\n

# 30초 후
data: {"message": "heartbeat"}\n\n

# 새 알림 발생 시
data: {"id": 1, "message": "new notification"}\n\n

# ... 연결 계속 유지 ...
```

### 3.2 SSE 메시지 형식

SSE는 특정 형식을 따라야 합니다:

```
event: 이벤트타입
data: 데이터내용
id: 메시지ID (선택)
retry: 재연결간격 (선택)

(빈 줄로 메시지 종료)
```

#### 예시

```
event: connected
data: {"user_id": 1}

event: notification
data: {"id": 1, "message": "새 알림"}

event: heartbeat
data: {"type": "ping"}

```

**중요**:
- 각 줄은 `\n`으로 끝남
- 메시지는 `\n\n` (빈 줄)로 구분
- `data:` 뒤에는 반드시 공백 필요

### 3.3 재연결 메커니즘

SSE는 연결이 끊어지면 **자동으로 재연결**합니다:

```
1. 클라이언트가 연결 시작
   ↓
2. 서버가 데이터 전송
   ↓
3. [연결 끊김] (네트워크 오류, 서버 재시작 등)
   ↓
4. 브라우저가 자동으로 재연결 시도 (기본 3초 후)
   ↓
5. 연결 성공 → 다시 데이터 수신
```

#### Last-Event-ID

재연결 시 마지막으로 받은 메시지 ID를 전송:

```http
# 재연결 요청
GET /api/notification/stream?token=abc123 HTTP/1.1
Last-Event-ID: 123

# 서버는 ID 123 이후 데이터부터 전송
```

---

## 4. EventSource API 사용법

### 4.1 기본 사용법

```javascript
// SSE 연결 생성
const eventSource = new EventSource('http://localhost:8000/api/notification/stream?token=abc123');

// 연결 성공 (onopen)
eventSource.onopen = () => {
  console.log('✅ 연결 성공');
};

// 메시지 수신 (message 이벤트)
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('📩 메시지:', data);
};

// 에러 처리 (onerror)
eventSource.onerror = (error) => {
  console.error('❌ 에러:', error);

  if (eventSource.readyState === EventSource.CLOSED) {
    console.log('연결 종료됨');
  }
};

// 연결 종료
eventSource.close();
```

### 4.2 커스텀 이벤트 처리

```javascript
const eventSource = new EventSource('/api/notification/stream?token=abc123');

// 'connected' 이벤트 리스너
eventSource.addEventListener('connected', (e) => {
  const data = JSON.parse(e.data);
  console.log('연결됨:', data);
});

// 'notification' 이벤트 리스너
eventSource.addEventListener('notification', (e) => {
  const notification = JSON.parse(e.data);
  console.log('🔔 새 알림:', notification);

  // UI 업데이트
  showNotification(notification);
});

// 'heartbeat' 이벤트 리스너
eventSource.addEventListener('heartbeat', (e) => {
  console.log('💓 Heartbeat');
});
```

### 4.3 readyState 상태

```javascript
// EventSource 연결 상태
console.log(eventSource.readyState);

// 가능한 값:
// 0 = EventSource.CONNECTING (연결 중)
// 1 = EventSource.OPEN (연결됨)
// 2 = EventSource.CLOSED (연결 종료)
```

### 4.4 실전 예제 (재연결 로직 포함)

```javascript
let eventSource = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000;

function connectSSE() {
  const token = localStorage.getItem('access_token');
  const url = `http://localhost:8000/api/notification/stream?token=${token}`;

  eventSource = new EventSource(url);

  eventSource.addEventListener('connected', (e) => {
    console.log('✅ SSE 연결 성공');
    reconnectAttempts = 0; // 재연결 카운터 초기화
  });

  eventSource.addEventListener('notification', (e) => {
    const notification = JSON.parse(e.data);
    console.log('🔔 새 알림:', notification);
  });

  eventSource.onerror = (error) => {
    console.error('❌ SSE 에러');

    if (eventSource.readyState === EventSource.CLOSED) {
      // 재연결 시도
      if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        console.log(`🔄 재연결 시도 ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}...`);

        setTimeout(() => {
          connectSSE();
        }, RECONNECT_DELAY);
      } else {
        console.error('⚠️ 재연결 실패, 폴링 모드로 전환');
        startPolling(); // fallback
      }
    }
  };
}

function disconnectSSE() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
    console.log('🛑 SSE 연결 종료');
  }
}
```

---

## 5. 서버 측 구현 방식

### 5.1 FastAPI StreamingResponse

FastAPI에서 SSE를 구현하는 방법:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

@app.get("/stream")
async def event_stream():
    async def event_generator():
        # 연결 성공 이벤트
        yield "event: connected\ndata: {\"status\": \"ok\"}\n\n"

        # 무한 루프로 데이터 전송
        count = 0
        while True:
            await asyncio.sleep(5)  # 5초마다

            # 데이터 전송
            data = f'{{"count": {count}}}'
            yield f"event: message\ndata: {data}\n\n"

            count += 1

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

### 5.2 핵심 개념

1. **Generator 함수**: `yield`로 데이터를 조금씩 전송
2. **StreamingResponse**: 연결을 유지하면서 데이터 스트리밍
3. **무한 루프**: 연결이 끊어질 때까지 계속 실행
4. **비동기**: `async`/`await`로 다른 요청 처리 가능

### 5.3 SSE 형식 준수

```python
# ❌ 잘못된 형식
yield '{"data": "hello"}'

# ✅ 올바른 형식
yield 'data: {"data": "hello"}\n\n'

# ✅ 이벤트 타입 포함
yield 'event: notification\ndata: {"id": 1}\n\n'
```

---

## 6. 현재 구현된 로직 상세 설명

### 6.1 전체 아키텍처 개요

```
┌──────────────────────────────────────────────────────┐
│                   프론트엔드                          │
│  ┌─────────────────────────────────────────────┐    │
│  │  Navigation.svelte (컴포넌트)                │    │
│  │  - 로그인 시 SSE 연결 시작                    │    │
│  │  - 로그아웃 시 SSE 연결 종료                  │    │
│  └─────────────────────────────────────────────┘    │
│                      ↓                               │
│  ┌─────────────────────────────────────────────┐    │
│  │  notification.js (SSE 클라이언트)            │    │
│  │  - startNotificationSSE()                   │    │
│  │  - EventSource 생성 및 관리                  │    │
│  │  - 재연결 로직                               │    │
│  │  - Fallback to polling                      │    │
│  └─────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
                      ↓ SSE 연결
       GET /api/notification/stream?token=...
                      ↓
┌──────────────────────────────────────────────────────┐
│                  백엔드 (FastAPI)                     │
│  ┌─────────────────────────────────────────────┐    │
│  │  router.py (SSE 엔드포인트)                  │    │
│  │  - JWT 인증 (query parameter)                │    │
│  │  - StreamingResponse 반환                    │    │
│  │  - event_generator() 실행                    │    │
│  └─────────────────────────────────────────────┘    │
│                      ↓                               │
│  ┌─────────────────────────────────────────────┐    │
│  │  sse_manager.py (연결 관리자)                │    │
│  │  - connect(user_id) → Queue 생성             │    │
│  │  - send_to_user(user_id, data)               │    │
│  │  - disconnect(user_id, queue)                │    │
│  └─────────────────────────────────────────────┘    │
│                      ↑                               │
│  ┌─────────────────────────────────────────────┐    │
│  │  notification_poller.py (폴링 시스템)        │    │
│  │  - 1.5초마다 DB 폴링                         │    │
│  │  - 새 알림 감지 → SSE 푸시                   │    │
│  └─────────────────────────────────────────────┘    │
│                      ↓ DB 조회                       │
│  ┌─────────────────────────────────────────────┐    │
│  │  service.py (비즈니스 로직)                  │    │
│  │  - get_new_notifications_since()             │    │
│  └─────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
                      ↓
              ┌──────────────┐
              │ PostgreSQL DB │
              │  notification │
              └──────────────┘
```

### 6.2 각 컴포넌트 역할

#### 6.2.1 프론트엔드: notification.js

**역할**: SSE 연결 관리 및 재연결 로직

```javascript
// 핵심 로직
export function startNotificationSSE() {
  // 1. 로그인 확인
  if (!get(is_login)) return;

  // 2. 토큰 확인
  const token = get(access_token);
  if (!token) {
    startNotificationPolling(); // fallback
    return;
  }

  // 3. EventSource 생성
  const url = `${baseUrl}/api/notification/stream?token=${token}`;
  eventSource = new EventSource(url);

  // 4. 이벤트 리스너 등록
  eventSource.addEventListener('notification', (e) => {
    const notification = JSON.parse(e.data);

    // 상태 업데이트 (Svelte store)
    notifications.update(list => [notification, ...list]);
    unread_count.update(count => count + 1);
  });

  // 5. 에러 처리 및 재연결
  eventSource.onerror = () => {
    handleSSEReconnect(); // 최대 5회 재시도
  };
}
```

#### 6.2.2 백엔드: router.py (SSE 엔드포인트)

**역할**: SSE 연결 수립 및 메시지 전송

```python
@router.get("/stream")
async def notification_stream(
    request: Request,
    current_user: User = Depends(get_current_user_for_sse)
):
    async def event_generator():
        # 1. SSE 연결 등록
        queue = await sse_manager.connect(current_user.id)

        try:
            # 2. 연결 성공 이벤트 전송
            yield f"event: connected\ndata: {{\"user_id\": {current_user.id}}}\n\n"

            # 3. 무한 루프 (연결 유지)
            while True:
                try:
                    # 4. Queue에서 데이터 대기 (30초 타임아웃)
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # 5. 새 알림 전송
                    yield f"event: notification\ndata: {data}\n\n"

                except asyncio.TimeoutError:
                    # 6. 타임아웃 시 Heartbeat 전송
                    yield "event: heartbeat\ndata: {\"type\": \"ping\"}\n\n"

        finally:
            # 7. 연결 해제
            await sse_manager.disconnect(current_user.id, queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

#### 6.2.3 백엔드: sse_manager.py (연결 관리자)

**역할**: 사용자별 Queue 관리

```python
class SSEConnectionManager:
    def __init__(self):
        # user_id → set[Queue] (다중 탭 지원)
        self._connections: Dict[int, Set[asyncio.Queue]] = {}

    async def connect(self, user_id: int) -> asyncio.Queue:
        """새 연결 등록"""
        queue = asyncio.Queue()

        if user_id not in self._connections:
            self._connections[user_id] = set()

        self._connections[user_id].add(queue)
        return queue

    async def send_to_user(self, user_id: int, data: str):
        """해당 사용자의 모든 연결(탭)에 전송"""
        if user_id not in self._connections:
            return

        for queue in self._connections[user_id]:
            await queue.put(data)  # Queue에 데이터 추가
```

**핵심**:
- `Queue`는 파이프와 같음 (한쪽에서 넣으면 다른쪽에서 꺼냄)
- `event_generator()`는 `queue.get()`으로 대기
- `send_to_user()`는 `queue.put()`으로 데이터 전송

#### 6.2.4 백엔드: notification_poller.py (폴링 시스템)

**역할**: DB를 주기적으로 확인하여 새 알림 푸시

```python
class NotificationPoller:
    async def _poll_loop(self):
        """메인 폴링 루프"""
        while self.running:
            await asyncio.sleep(1.5)  # 1.5초 대기
            await self._check_and_push_notifications()

    async def _check_and_push_notifications(self):
        # 1. 연결된 사용자 확인
        connected_users = sse_manager.get_connected_users()
        if not connected_users:
            return  # 연결 없으면 쿼리 생략

        # 2. DB에서 새 알림 조회
        new_notifications = await notification_service.get_new_notifications_since(
            db,
            since=self.last_check,
            user_ids=list(connected_users)
        )

        # 3. user_id별 그룹핑
        for notif in new_notifications:
            # 4. SSE로 푸시
            payload = NotificationResponse.from_orm_with_actor(notif).model_dump_json()
            await sse_manager.send_to_user(notif.user_id, payload)
```

---

## 7. 전체 데이터 흐름

### 7.1 연결 수립 과정

```
Step 1: 사용자 로그인
┌──────────┐
│ 사용자 A  │ 로그인 → JWT 토큰 발급 (abc123)
└──────────┘

Step 2: SSE 연결 시작
┌──────────┐
│ 브라우저  │ new EventSource('/stream?token=abc123')
└──────────┘
     ↓ HTTP GET /api/notification/stream?token=abc123
┌──────────┐
│  서버    │ JWT 검증 → user_id=1 확인
└──────────┘
     ↓
┌──────────┐
│sse_manager│ connect(user_id=1) → Queue 생성
└──────────┘
     ↓
     Queue ← event_generator()가 대기 중

Step 3: 연결 성공 이벤트
┌──────────┐
│  서버    │ yield "event: connected\ndata: {\"user_id\": 1}\n\n"
└──────────┘
     ↓
┌──────────┐
│ 브라우저  │ 'connected' 이벤트 수신
└──────────┘
     console.log('✅ SSE 연결 성공')
```

### 7.2 알림 생성 및 전송 과정

```
Step 1: 사용자 B가 사용자 A의 질문에 투표
┌──────────┐
│ 사용자 B  │ POST /api/question/1/vote
└──────────┘
     ↓
┌──────────┐
│question   │ vote_question() 실행
│service   │
└──────────┘
     ↓
┌──────────┐
│notification│ create_notification(
│service    │   user_id=A의 ID,
└──────────┘   actor_user_id=B의 ID,
     ↓          event_type="question_voted"
     ↓        )
┌──────────┐
│    DB    │ INSERT INTO notification ...
└──────────┘

Step 2: NotificationPoller가 감지 (최대 1.5초 후)
┌──────────┐
│  Poller  │ 1.5초마다 실행
└──────────┘
     ↓ SELECT * FROM notification WHERE created_at > last_check
┌──────────┐
│    DB    │ 새 알림 반환 (user_id=A, ...)
└──────────┘
     ↓
┌──────────┐
│  Poller  │ 새 알림 발견!
└──────────┘
     ↓
┌──────────┐
│sse_manager│ send_to_user(user_id=A, data=알림JSON)
└──────────┘
     ↓ queue.put(data)

Step 3: event_generator()가 Queue에서 데이터 꺼냄
┌──────────┐
│event_gen │ data = await queue.get()  ← Queue에서 꺼냄
└──────────┘
     ↓ yield f"event: notification\ndata: {data}\n\n"
┌──────────┐
│  서버    │ SSE로 전송
└──────────┘
     ↓
┌──────────┐
│ 브라우저  │ 'notification' 이벤트 수신
│(사용자 A) │
└──────────┘
     notifications.update(list => [notification, ...list])
     🔔 새 알림 표시!
```

### 7.3 Heartbeat 전송 과정

```
30초 동안 새 알림 없음
┌──────────┐
│event_gen │ await asyncio.wait_for(queue.get(), timeout=30.0)
└──────────┘
     ↓ 30초 타임아웃
     asyncio.TimeoutError 발생
     ↓
┌──────────┐
│event_gen │ yield "event: heartbeat\ndata: {\"type\": \"ping\"}\n\n"
└──────────┘
     ↓
┌──────────┐
│ 브라우저  │ 'heartbeat' 이벤트 수신
└──────────┘
     console.log('💓 Heartbeat')

     다시 queue.get() 대기...
```

### 7.4 연결 종료 및 재연결

```
서버 재시작 또는 네트워크 오류
┌──────────┐
│  서버    │ 연결 종료
└──────────┘
     ↓
┌──────────┐
│ 브라우저  │ onerror 이벤트 발생
└──────────┘
     console.error('❌ SSE 에러')
     ↓
     reconnectAttempts = 1
     ↓
     3초 대기
     ↓
┌──────────┐
│ 브라우저  │ new EventSource(...) ← 재연결 시도
└──────────┘
     ↓
┌──────────┐
│  서버    │ 새로운 연결 수립
└──────────┘
     ✅ 연결 성공
```

---

## 8. 코드 레벨 설명

### 8.1 프론트엔드 코드 상세 분석

#### notification.js

```javascript
// 1. SSE 연결 상태 변수
let eventSource = null;              // EventSource 객체
let reconnectAttempts = 0;           // 재연결 시도 횟수
const MAX_RECONNECT_ATTEMPTS = 5;    // 최대 재연결 횟수
const RECONNECT_DELAY = 3000;        // 재연결 대기 시간 (3초)
const SSE_ENABLED = true;            // SSE 기능 활성화 플래그

// 2. SSE 연결 시작 함수
export function startNotificationSSE() {
  // 2-1. 로그인 확인
  if (!get(is_login) || !SSE_ENABLED) {
    startNotificationPolling();  // 미로그인 또는 SSE 비활성화 시 폴링 모드
    return;
  }

  // 2-2. 토큰 확인
  const token = get(access_token);
  if (!token) {
    console.warn('⚠️ 토큰 없음, 폴링 모드로 전환');
    startNotificationPolling();
    return;
  }

  // 2-3. 기존 연결 종료
  stopNotificationSSE();      // 기존 SSE 연결 종료
  stopNotificationPolling();  // 기존 폴링 중지

  // 2-4. EventSource 생성
  try {
    const baseUrl = import.meta.env.VITE_SERVER_URL || 'http://localhost:8000';
    const url = `${baseUrl}/api/notification/stream?token=${token}`;

    eventSource = new EventSource(url);  // ← SSE 연결 시작

    // 2-5. 'connected' 이벤트 리스너
    eventSource.addEventListener('connected', (e) => {
      const data = JSON.parse(e.data);
      console.log('✅ SSE 연결 성공', data);
      reconnectAttempts = 0;  // 재연결 카운터 초기화

      // 초기 알림 목록 로드
      fetchNotifications();
    });

    // 2-6. 'notification' 이벤트 리스너
    eventSource.addEventListener('notification', (e) => {
      const notification = JSON.parse(e.data);
      console.log('🔔 새 알림:', notification);

      // Svelte store 업데이트
      notifications.update(list => [notification, ...list]);  // 맨 앞에 추가
      unread_count.update(count => count + 1);                // 미읽음 +1
      total_count.update(count => count + 1);                 // 총 개수 +1
    });

    // 2-7. 'heartbeat' 이벤트 리스너
    eventSource.addEventListener('heartbeat', () => {
      console.log('💓 Heartbeat');
      // 연결 유지 확인용, 특별한 처리 불필요
    });

    // 2-8. 에러 처리
    eventSource.onerror = (error) => {
      console.error('❌ SSE 에러:', error);

      // 연결이 종료된 경우
      if (eventSource.readyState === EventSource.CLOSED) {
        handleSSEReconnect();  // 재연결 시도
      }
    };

  } catch (error) {
    console.error('❌ SSE 연결 실패:', error);
    startNotificationPolling();  // fallback
  }
}

// 3. 재연결 로직
function handleSSEReconnect() {
  // 3-1. 최대 재연결 횟수 초과 확인
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    console.warn('⚠️ SSE 재연결 실패, 폴링 모드로 전환');
    stopNotificationSSE();
    startNotificationPolling();  // fallback
    return;
  }

  // 3-2. 재연결 시도
  reconnectAttempts++;
  console.log(`🔄 SSE 재연결 시도 ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}...`);

  // 3-3. 3초 후 재연결
  setTimeout(() => {
    if (get(is_login)) {
      startNotificationSSE();
    }
  }, RECONNECT_DELAY);
}

// 4. SSE 연결 종료
export function stopNotificationSSE() {
  if (eventSource) {
    eventSource.close();  // EventSource 연결 종료
    eventSource = null;
    console.log('🛑 SSE 연결 종료');
  }
  reconnectAttempts = 0;
}
```

### 8.2 백엔드 코드 상세 분석

#### router.py - SSE 엔드포인트

```python
# 1. SSE 전용 인증 함수
async def get_current_user_for_sse(
    token: str = Query(..., description="JWT access token"),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """SSE용 토큰 인증 (query parameter 사용)

    EventSource API는 커스텀 헤더를 지원하지 않으므로
    query parameter로 토큰을 받습니다.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        # JWT 디코딩
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # DB에서 사용자 조회
    user = await user_service.get_user_async(db, username=username)
    if user is None:
        raise credentials_exception

    return user


# 2. SSE 스트리밍 엔드포인트
@router.get("/stream")
async def notification_stream(
    request: Request,
    current_user: User = Depends(get_current_user_for_sse)
):
    """SSE 실시간 알림 스트림"""

    # 2-1. Generator 함수 정의
    async def event_generator():
        # 2-2. SSE 연결 등록 (Queue 생성)
        queue = await sse_manager.connect(current_user.id)

        try:
            # 2-3. 연결 성공 이벤트 전송
            yield f"event: connected\ndata: {{\"user_id\": {current_user.id}}}\n\n"
            logger.info(f"SSE connection established: user_id={current_user.id}")

            # 2-4. 무한 루프 (연결 유지)
            while True:
                try:
                    # 2-5. Queue에서 데이터 대기 (30초 타임아웃)
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # 2-6. 새 알림 전송
                    yield f"event: notification\ndata: {data}\n\n"

                except asyncio.TimeoutError:
                    # 2-7. 클라이언트 연결 확인
                    if await request.is_disconnected():
                        logger.info(f"SSE client disconnected: user_id={current_user.id}")
                        break

                    # 2-8. Heartbeat 전송 (연결 유지)
                    yield "event: heartbeat\ndata: {\"type\": \"ping\"}\n\n"

        except Exception as e:
            logger.error(f"SSE stream error: user_id={current_user.id}, error={e}")

        finally:
            # 2-9. 연결 해제
            await sse_manager.disconnect(current_user.id, queue)
            logger.info(f"SSE connection closed: user_id={current_user.id}")

    # 2-10. StreamingResponse 반환
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",  # SSE 미디어 타입
        headers={
            "Cache-Control": "no-cache",     # 캐싱 비활성화
            "Connection": "keep-alive",       # 연결 유지
            "X-Accel-Buffering": "no"         # NGINX 버퍼링 비활성화
        }
    )
```

#### sse_manager.py - 연결 관리자

```python
class SSEConnectionManager:
    def __init__(self):
        # user_id → set[Queue] 매핑
        # 한 사용자가 여러 탭을 열 수 있으므로 set 사용
        self._connections: Dict[int, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()  # 동시성 제어

    async def connect(self, user_id: int) -> asyncio.Queue:
        """새 SSE 연결 등록"""
        async with self._lock:  # 락 획득 (동시성 제어)
            # 1. 새 Queue 생성
            queue = asyncio.Queue()

            # 2. user_id가 없으면 빈 set 생성
            if user_id not in self._connections:
                self._connections[user_id] = set()

            # 3. Queue를 set에 추가
            self._connections[user_id].add(queue)

            logger.info(
                f"SSE 연결 추가: user_id={user_id}, "
                f"총 연결 수={len(self._connections[user_id])}"
            )

            return queue

    async def disconnect(self, user_id: int, queue: asyncio.Queue) -> None:
        """SSE 연결 해제"""
        async with self._lock:
            if user_id in self._connections:
                # 1. Queue 제거
                self._connections[user_id].discard(queue)

                # 2. 해당 사용자의 모든 연결이 끊어졌으면 딕셔너리에서 제거
                if not self._connections[user_id]:
                    del self._connections[user_id]

                logger.info(
                    f"SSE 연결 해제: user_id={user_id}, "
                    f"남은 연결 수={len(self._connections.get(user_id, []))}"
                )

    async def send_to_user(self, user_id: int, data: str) -> None:
        """해당 사용자의 모든 연결(탭)에 메시지 전송"""
        if user_id not in self._connections:
            return

        # 복사하여 iteration 중 수정 방지
        queues = self._connections[user_id].copy()

        # 모든 Queue에 데이터 추가
        for queue in queues:
            try:
                await queue.put(data)  # ← event_generator()가 queue.get()으로 받음
            except Exception as e:
                logger.error(f"SSE 메시지 전송 실패: user_id={user_id}, error={e}")

    def get_connected_users(self) -> Set[int]:
        """현재 연결된 사용자 ID 목록 (폴링 최적화용)"""
        return set(self._connections.keys())

    def total_connections(self) -> int:
        """총 연결 수 (모니터링용)"""
        return sum(len(queues) for queues in self._connections.values())
```

#### notification_poller.py - 폴링 시스템

```python
class NotificationPoller:
    def __init__(self, interval: float = 1.5):
        self.interval = interval              # 폴링 간격
        self.last_check: datetime = datetime.utcnow()  # 마지막 확인 시각
        self.running = False                  # 실행 상태
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """앱 시작 시 백그라운드 태스크로 실행"""
        if self.running:
            return

        self.running = True
        self.last_check = datetime.utcnow()

        # 백그라운드 태스크 생성
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"NotificationPoller started (interval={self.interval}s)")

    async def _poll_loop(self):
        """메인 폴링 루프"""
        while self.running:
            try:
                # 1. 1.5초 대기
                await asyncio.sleep(self.interval)

                # 2. 새 알림 확인 및 푸시
                await self._check_and_push_notifications()

            except Exception as e:
                logger.error(f"폴링 에러: {e}", exc_info=True)

    async def _check_and_push_notifications(self):
        """새 알림 확인 및 SSE 푸시"""
        # 1. 연결된 사용자만 조회 (최적화)
        connected_users = sse_manager.get_connected_users()
        if not connected_users:
            return  # 연결된 사용자 없으면 쿼리 생략

        # 2. DB에서 새 알림 조회
        try:
            async with AsyncSessionPrimary() as db:
                new_notifications = await notification_service.get_new_notifications_since(
                    db,
                    since=self.last_check,       # 마지막 확인 이후
                    user_ids=list(connected_users)  # 연결된 사용자만
                )
        except Exception as e:
            logger.error(f"DB 조회 에러: {e}")
            return

        # 3. 시간 업데이트
        if new_notifications:
            self.last_check = max(n.created_at for n in new_notifications)
            logger.info(f"Found {len(new_notifications)} new notifications")
        else:
            self.last_check = datetime.utcnow()

        # 4. user_id별로 그룹핑
        user_notifications: dict[int, list] = {}
        for notif in new_notifications:
            if notif.user_id not in user_notifications:
                user_notifications[notif.user_id] = []
            user_notifications[notif.user_id].append(notif)

        # 5. 각 사용자에게 SSE 푸시
        for user_id, notifications in user_notifications.items():
            for notif in notifications:
                try:
                    # JSON 직렬화
                    payload = NotificationResponse.from_orm_with_actor(notif).model_dump_json()

                    # SSE로 푸시
                    await sse_manager.send_to_user(user_id, payload)

                except Exception as e:
                    logger.error(f"SSE 푸시 에러: user_id={user_id}, error={e}")
```

#### service.py - 새 알림 조회

```python
async def get_new_notifications_since(
    db: AsyncSession,
    since: datetime,
    user_ids: list[int] | None = None
) -> list[Notification]:
    """마지막 확인 이후 새 알림 조회 (폴링용)"""

    # 1. 기본 쿼리
    stmt = (
        select(Notification)
        .where(Notification.created_at > since)  # 마지막 확인 이후
        .options(selectinload(Notification.actor))  # actor 정보 함께 로드
        .order_by(Notification.created_at.asc())
    )

    # 2. 연결된 사용자만 필터링 (최적화)
    if user_ids:
        stmt = stmt.where(Notification.user_id.in_(user_ids))

    # 3. 실행
    result = await db.execute(stmt)
    return list(result.scalars().all())
```

---

## 9. 핵심 개념 정리

### 9.1 Queue의 역할

**Queue는 파이프와 같습니다**:

```python
# router.py (event_generator)
queue = await sse_manager.connect(user_id)

# 무한 대기
data = await queue.get()  # ← 데이터가 들어올 때까지 대기
yield f"data: {data}\n\n"  # ← 데이터 전송

# notification_poller.py
await sse_manager.send_to_user(user_id, payload)
  ↓
await queue.put(payload)  # ← queue.get()에게 전달
```

**비유**:
- `queue.get()`: 우체통을 기다리는 사람
- `queue.put()`: 우체통에 편지 넣는 사람
- Queue: 우체통

### 9.2 asyncio.wait_for()의 역할

```python
# 30초 동안 대기
try:
    data = await asyncio.wait_for(queue.get(), timeout=30.0)
    # 데이터가 들어오면 여기 실행
except asyncio.TimeoutError:
    # 30초 동안 데이터 없으면 여기 실행
    yield "event: heartbeat\n\n"
```

**왜 필요한가?**:
- 새 알림이 없으면 무한 대기 → NGINX timeout (연결 끊김)
- 30초마다 heartbeat 전송 → 연결 유지

### 9.3 StreamingResponse의 역할

```python
# 일반 응답
return {"data": "hello"}  # ← 즉시 반환, 연결 종료

# StreamingResponse
return StreamingResponse(event_generator())
# ↓ generator가 yield할 때마다 조금씩 전송
# ↓ 연결 유지
# ↓ generator가 끝날 때까지 계속
```

---

## 10. 자주 묻는 질문 (FAQ)

### Q1. SSE와 WebSocket의 차이는?

**SSE**: 서버 → 클라이언트 (단방향)
- 알림, 뉴스 피드 등
- HTTP 기반, 구현 쉬움

**WebSocket**: 서버 ↔ 클라이언트 (양방향)
- 채팅, 게임 등
- 별도 프로토콜, 구현 복잡

### Q2. 왜 1.5초마다 폴링하나요?

**Trade-off**:
- 간격 짧음 (0.5초): 실시간성 ↑, DB 부하 ↑
- 간격 김 (5초): 실시간성 ↓, DB 부하 ↓

**1.5초 선택 이유**:
- 실시간성: 충분함 (알림은 2초 지연 허용 가능)
- DB 부하: 낮음 (120 QPS)

### Q3. Redis 없이 어떻게 멀티 인스턴스에서 동작하나요?

**각 서버가 독립적으로 동작**:
- 서버 1: 자신에게 연결된 클라이언트만 관리
- 서버 2: 자신에게 연결된 클라이언트만 관리
- 서버 3: 자신에게 연결된 클라이언트만 관리

**모두 DB를 폴링**:
- 새 알림이 DB에 저장되면
- 각 서버가 독립적으로 감지
- 자신의 클라이언트에게만 푸시

### Q4. 한 사용자가 여러 탭을 열면?

**다중 탭 지원**:
```python
self._connections = {
    1: {queue1, queue2},  # user_id=1이 2개 탭 오픈
    2: {queue3}           # user_id=2가 1개 탭 오픈
}
```

**모든 탭에 전송**:
```python
for queue in self._connections[user_id]:
    await queue.put(data)  # 각 탭에 전송
```

### Q5. 재연결은 언제 일어나나요?

**자동 재연결 상황**:
1. 서버 재시작
2. 네트워크 일시 끊김
3. NGINX timeout (heartbeat로 방지)

**재연결 로직**:
- 브라우저가 자동으로 재연결 시도
- 우리 코드에서 수동 재연결도 지원 (최대 5회)

---

## 11. 실습 예제

### 예제 1: 간단한 SSE 서버 (Python)

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

@app.get("/time")
async def stream_time():
    async def time_generator():
        import datetime

        while True:
            current_time = datetime.datetime.now().isoformat()
            yield f"data: {current_time}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        time_generator(),
        media_type="text/event-stream"
    )
```

### 예제 2: SSE 클라이언트 (JavaScript)

```javascript
const eventSource = new EventSource('http://localhost:8000/time');

eventSource.onmessage = (event) => {
  console.log('현재 시각:', event.data);
};
```

### 예제 3: 이벤트 타입 구분

**서버**:
```python
async def multi_event_generator():
    yield "event: greeting\ndata: Hello!\n\n"
    await asyncio.sleep(1)
    yield "event: farewell\ndata: Goodbye!\n\n"
```

**클라이언트**:
```javascript
const eventSource = new EventSource('/events');

eventSource.addEventListener('greeting', (e) => {
  console.log('인사:', e.data);
});

eventSource.addEventListener('farewell', (e) => {
  console.log('작별:', e.data);
});
```

---

## 12. 참고 자료

### 공식 문서
- [MDN - Server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [MDN - EventSource API](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)
- [FastAPI - Custom Response](https://fastapi.tiangolo.com/advanced/custom-response/)

### 관련 문서
- [SSE 아키텍처](./NOTIFICATION_SSE_ARCHITECTURE.md)
- [API 명세](./API_SPECIFICATION.md)
- [운영 가이드](./SSE_OPERATIONS_GUIDE.md)

---

## 요약

### SSE란?
서버에서 클라이언트로 실시간 데이터를 푸시하는 기술 (HTTP 기반, 단방향)

### 핵심 구성
1. **클라이언트**: EventSource API
2. **서버**: StreamingResponse + Generator
3. **연결 관리**: Queue를 사용한 메시지 전달

### 동작 과정
1. 클라이언트가 SSE 연결 요청
2. 서버가 Queue 생성 및 대기
3. 새 알림 발생 → Queue에 추가
4. event_generator가 Queue에서 꺼내서 전송
5. 클라이언트가 실시간으로 수신

### 장점
- ✅ 실시간 푸시
- ✅ 자동 재연결
- ✅ 간단한 구현
- ✅ HTTP 기반 (기존 인프라 활용)

### 단점
- ❌ 단방향만 가능
- ❌ 텍스트만 전송 가능
- ❌ IE 미지원
