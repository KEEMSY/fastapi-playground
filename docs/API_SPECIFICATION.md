# API 명세서

## 개요

FastAPI-Playground 프로젝트의 API 명세서입니다.

---

## 알림 시스템 API

### 1. 알림 목록 조회 (REST)

#### Endpoint
```
GET /api/notification/list
```

#### Authentication
- Header: `Authorization: Bearer {access_token}`

#### Query Parameters
| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| page | integer | No | 0 | 페이지 번호 (0부터 시작) |
| size | integer | No | 20 | 페이지 크기 |

#### Response
```json
{
  "total": 100,
  "unread_count": 5,
  "notifications": [
    {
      "id": 1,
      "user_id": 1,
      "actor_user_id": 2,
      "actor_username": "john",
      "event_type": "question_voted",
      "resource_type": "question",
      "resource_id": 10,
      "message": "john님이 질문에 투표했습니다",
      "is_read": false,
      "created_at": "2026-02-21T10:30:00"
    }
  ]
}
```

#### Event Types
- `question_voted`: 질문에 투표
- `answer_created`: 답변 작성
- `answer_voted`: 답변에 투표

---

### 2. 알림 읽음 처리

#### Endpoint
```
PUT /api/notification/read
```

#### Authentication
- Header: `Authorization: Bearer {access_token}`

#### Request Body
```json
{
  "notification_ids": [1, 2, 3]
}
```

#### Response
```
HTTP 204 No Content
```

---

### 3. 모든 알림 읽음 처리

#### Endpoint
```
PUT /api/notification/read-all
```

#### Authentication
- Header: `Authorization: Bearer {access_token}`

#### Response
```
HTTP 204 No Content
```

---

### 4. SSE 실시간 알림 스트림

#### Endpoint
```
GET /api/notification/stream?token={access_token}
```

#### Authentication
- **Query Parameter**: `token` (required)
- EventSource API는 커스텀 헤더를 지원하지 않으므로 query parameter로 토큰 전달
- **중요**: HTTPS 사용 필수 (토큰 노출 방지)

#### Query Parameters
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| token | string | Yes | JWT access token |

#### Response Headers
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

#### SSE Events

##### connected
연결 성공 이벤트 (1회)
```
event: connected
data: {"user_id": 1}
```

##### notification
새 알림 이벤트 (실시간)
```
event: notification
data: {"id": 1, "user_id": 1, "actor_user_id": 2, "actor_username": "john", "event_type": "question_voted", "resource_type": "question", "resource_id": 10, "message": "john님이 질문에 투표했습니다", "is_read": false, "created_at": "2026-02-21T10:30:00"}
```

##### heartbeat
연결 유지 이벤트 (30초 간격)
```
event: heartbeat
data: {"type": "ping"}
```

#### Error Codes
| 코드 | 설명 | 대응 방법 |
|------|------|-----------|
| 401 | 인증 실패 (토큰 없음/만료) | 로그인 페이지로 이동 |
| 403 | 권한 없음 | 접근 거부 |

#### 사용 예제 (JavaScript)

```javascript
const token = localStorage.getItem('access_token');
const baseUrl = 'http://localhost:8000';
const url = `${baseUrl}/api/notification/stream?token=${token}`;

const eventSource = new EventSource(url);

// 연결 성공
eventSource.addEventListener('connected', (e) => {
  const data = JSON.parse(e.data);
  console.log('✅ Connected:', data);
});

// 새 알림 수신
eventSource.addEventListener('notification', (e) => {
  const notification = JSON.parse(e.data);
  console.log('🔔 New notification:', notification);
  // UI 업데이트
});

// Heartbeat
eventSource.addEventListener('heartbeat', (e) => {
  console.log('💓 Heartbeat');
});

// 에러 처리
eventSource.onerror = (error) => {
  console.error('❌ SSE Error:', error);
  if (eventSource.readyState === EventSource.CLOSED) {
    // 재연결 로직
  }
};

// 연결 종료
eventSource.close();
```

#### 재연결 전략

1. **자동 재연결**: 브라우저의 EventSource API가 자동으로 재연결 시도
2. **수동 재연결**: 에러 발생 시 3초 후 재연결 (최대 5회)
3. **Fallback**: 재연결 실패 시 REST API 폴링 모드로 전환

#### 성능 특성

- **실시간성**: 최대 1.5초 지연
- **Heartbeat**: 30초 간격 (NGINX timeout 방지)
- **다중 탭 지원**: 각 탭마다 독립적 연결
- **멀티 인스턴스**: 로드밸런서 환경에서 정상 동작

---

## 에러 코드

### 공통 에러 코드

| 코드 | 설명 | HTTP Status |
|------|------|-------------|
| AUTH001 | 인증 실패 | 401 |
| AUTH002 | 권한 없음 | 403 |
| NOTIF001 | 알림 조회 실패 | 500 |
| NOTIF002 | 알림 생성 실패 | 500 |
| NOTIF003 | 알림 업데이트 실패 | 500 |

---

## 참고 사항

### Rate Limiting
- SSE 연결: 사용자당 최대 10개 연결 (다중 탭 고려)
- REST API: 사용자당 100 req/min

### 캐싱
- SSE: 캐싱 비활성화 (`Cache-Control: no-cache`)
- REST API: 캐싱 없음 (실시간 데이터)

### CORS
```python
origins = [
    "http://localhost:5173",
    "http://localhost:7777",
]
```

---

## 변경 이력

### 2026-02-21
- SSE 실시간 알림 스트림 엔드포인트 추가
- 기존 REST API 폴링 방식 유지 (fallback)

### 이전
- 알림 목록 조회, 읽음 처리 API 구현
