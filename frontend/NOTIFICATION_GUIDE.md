# 알림 시스템 사용 가이드

## 🎯 구현된 기능

### 1. 알림 벨 컴포넌트
- **위치**: 내비게이션 바 (로그인 시에만 표시)
- **기능**:
  - 🔔 알림 아이콘 + 읽지 않은 알림 개수 뱃지
  - 클릭 시 최근 5개 알림 드롭다운
  - 개별 알림 읽음 처리
  - "전체보기" 버튼으로 알림 목록 페이지 이동

### 2. 알림 목록 페이지
- **경로**: `/notifications`
- **기능**:
  - 전체 알림 목록 조회 (페이징)
  - 필터링: 전체 / 읽지 않음 / 읽음
  - 선택 읽음 처리
  - 전체 읽음 처리
  - 체크박스 선택 (개별/전체)
  - 알림 타입별 아이콘 및 색상
  - 상대 시간 표시 (방금 전, 5분 전 등)

### 3. 자동 폴링 시스템
- **간격**: 10초
- **동작**:
  - 로그인 시 자동 시작
  - 로그아웃 시 자동 중지
  - 백그라운드에서 자동 알림 확인
  - 실시간 뱃지 업데이트

---

## 🚀 실행 방법

### 1. 백엔드 실행

```bash
# 개발 환경
docker-compose -f docker-compose-dev.yml up -d

# 또는 운영 환경
docker-compose -f docker-compose-prod.yml up -d
```

### 2. 프론트엔드 실행

```bash
cd frontend

# 의존성 설치 (처음 한 번만)
npm install

# 개발 서버 실행
npm run dev
```

**접속**: http://localhost:5173

---

## 📋 테스트 시나리오

### 시나리오 1: 알림 생성 및 확인

1. **사용자 A 로그인**
   - http://localhost:5173/user-login
   - 계정: userA / password

2. **질문 작성**
   - 내비게이션 → "질문 등록"
   - 제목, 내용 작성 후 저장

3. **사용자 B 로그인** (다른 브라우저 or 시크릿 모드)
   - 계정: userB / password

4. **질문에 투표**
   - 홈에서 userA의 질문 클릭
   - "추천" 버튼 클릭

5. **사용자 A에서 알림 확인**
   - 10초 이내에 알림 벨에 숫자 1 표시
   - 알림 벨 클릭 → "userB님이 회원님의 질문에 투표했습니다."

### 시나리오 2: 답변 알림

1. **사용자 B가 답변 작성**
   - userA의 질문 상세 페이지
   - 답변 작성 후 저장

2. **사용자 A에서 알림 확인**
   - 알림 벨에 새 알림 표시
   - "userB님이 회원님의 질문에 답변했습니다."

### 시나리오 3: 답변 투표 알림

1. **사용자 A가 답변에 투표**
   - userB의 답변에서 "추천" 클릭

2. **사용자 B에서 알림 확인**
   - 알림 벨 업데이트
   - "userA님이 회원님의 답변에 투표했습니다."

### 시나리오 4: 알림 관리

1. **알림 목록 페이지 이동**
   - 알림 벨 드롭다운 → "전체보기" 클릭
   - 또는 직접 `/notifications` 접속

2. **필터링**
   - "읽지 않음" 탭 → 새 알림만 표시
   - "읽음" 탭 → 읽은 알림만 표시

3. **읽음 처리**
   - 개별: 알림 오른쪽 "✓ 읽음" 버튼
   - 선택: 체크박스 선택 → "선택 읽음 처리"
   - 전체: "전체 읽음 처리" 버튼

---

## 🎨 UI 미리보기

### 알림 벨 (읽지 않은 알림 있음)
```
🔔 (3)  ← 빨간 뱃지
```

### 알림 드롭다운
```
┌─────────────────────────────────────┐
│ 알림                    [전체보기]  │
├─────────────────────────────────────┤
│ 👍 5분 전                          │
│ userB님이 회원님의 질문에 투표했습니다. │
│                                  ✓  │
├─────────────────────────────────────┤
│ 💬 1시간 전                        │
│ userC님이 회원님의 질문에 답변했습니다. │
│                                  ✓  │
└─────────────────────────────────────┘
```

### 알림 목록 페이지
```
🔔 알림 (3)                    [🔄 새로고침]

[전체 (10)] [읽지 않음 (3)] [읽음 (7)]

[선택 읽음 처리 (0)] [전체 읽음 처리]

□ 전체 선택

□ 👍 question_voted NEW  5분 전
  userB님이 회원님의 질문에 투표했습니다.
  👤 userB  📌 question #1          [✓ 읽음]

□ 💬 answer_created NEW  1시간 전
  userC님이 회원님의 질문에 답변했습니다.
  👤 userC  📌 question #1          [✓ 읽음]
```

---

## 🔧 기술 스택

- **프레임워크**: Svelte 4
- **라우터**: svelte-spa-router
- **스타일**: Bootstrap 5
- **빌드**: Vite
- **상태 관리**: Svelte Stores
- **폴링**: setInterval (10초 간격)

---

## 📂 파일 구조

```
frontend/src/
├── lib/
│   ├── notification.js           # 알림 API 및 폴링 로직
│   ├── api.js                    # 기존 API 헬퍼
│   └── store.js                  # 전역 상태
│
├── components/
│   ├── NotificationBell.svelte   # 알림 벨 컴포넌트
│   └── Navigation.svelte         # 내비게이션 바
│
├── routes/
│   ├── Notifications.svelte      # 알림 목록 페이지
│   └── ... (기존 라우트)
│
└── App.svelte                    # 라우트 설정
```

---

## 🔌 API 엔드포인트

### 백엔드 API

```bash
# 알림 목록 조회
GET /api/notification/list?page=0&size=20
Authorization: Bearer <token>

응답:
{
  "total": 10,
  "unread_count": 3,
  "notifications": [
    {
      "id": 1,
      "event_type": "question_voted",
      "resource_type": "question",
      "resource_id": 1,
      "message": "userB님이 회원님의 질문에 투표했습니다.",
      "is_read": false,
      "created_at": "2026-02-18T10:30:00",
      "actor": {
        "id": 2,
        "username": "userB"
      }
    }
  ]
}

# 선택 알림 읽음 처리
PUT /api/notification/read
Authorization: Bearer <token>
Body: { "notification_ids": [1, 2, 3] }

# 전체 알림 읽음 처리
PUT /api/notification/read-all
Authorization: Bearer <token>
```

---

## 💡 주요 기능 설명

### 1. 자동 폴링

```javascript
// lib/notification.js
export function startNotificationPolling() {
  // 즉시 1회 실행
  fetchNotifications();

  // 10초마다 실행
  setInterval(() => {
    if (get(is_login)) {
      fetchNotifications();
    }
  }, 10000);
}
```

**장점**:
- 별도 설정 불필요
- 로그인 시 자동 시작
- 멀티 인스턴스 환경 완벽 지원

### 2. 읽음 처리 후 로컬 상태 즉시 업데이트

```javascript
export function markAsRead(notification_ids, callback) {
  fastapi('put', '/api/notification/read', { notification_ids }, () => {
    // 로컬 상태 즉시 업데이트 (서버 응답 기다릴 필요 없음)
    notifications.update(list =>
      list.map(n =>
        notification_ids.includes(n.id) ? { ...n, is_read: true } : n
      )
    );
    unread_count.update(count => count - notification_ids.length);
  });
}
```

**장점**:
- UI 즉시 반영
- 폴링 기다릴 필요 없음
- 사용자 경험 향상

### 3. 상대 시간 표시

```javascript
function formatDate(dateString) {
  const minutes = Math.floor((now - date) / 60000);

  if (minutes < 1) return "방금 전";
  if (minutes < 60) return `${minutes}분 전`;
  // ... 시간/일 계산
}
```

**표시 예시**:
- "방금 전"
- "5분 전"
- "2시간 전"
- "3일 전"
- "2026-02-18" (일주일 이상)

---

## 🎯 앞으로 추가 가능한 기능

### 단기 (쉬움)
- [ ] 알림 클릭 시 해당 질문/답변으로 이동
- [ ] 알림 삭제 기능
- [ ] 알림 개수 제한 (100개 이상 시 오래된 것 자동 삭제)
- [ ] 알림 사운드 (선택적)

### 중기 (보통)
- [ ] 알림 타입별 설정 (투표 알림 끄기 등)
- [ ] 알림 그룹핑 ("3명이 회원님의 질문에 투표했습니다")
- [ ] 무한 스크롤 (페이징)
- [ ] 알림 검색 기능

### 장기 (복잡)
- [ ] 웹 푸시 알림 (브라우저 알림)
- [ ] 이메일 알림
- [ ] 실시간 알림 (SSE/WebSocket 재검토)

---

## 🐛 트러블슈팅

### 알림이 표시되지 않음

**원인 1**: 백엔드가 실행 중이지 않음
```bash
# 확인
curl http://localhost:8000/

# 해결
docker-compose -f docker-compose-dev.yml up -d
```

**원인 2**: 로그인하지 않음
- 알림은 로그인한 사용자만 확인 가능
- 로그인 후 자동으로 폴링 시작

**원인 3**: CORS 오류
```bash
# 백엔드 로그 확인
docker-compose logs -f app
```

### 폴링이 작동하지 않음

**확인 방법**:
```javascript
// 브라우저 개발자 도구 → Console
// "✅ 알림 폴링 시작 (10초 간격)" 메시지 확인
```

**해결**:
- 페이지 새로고침
- 로그아웃 후 재로그인

### 알림 개수가 맞지 않음

**원인**: 캐시 문제
```javascript
// 수동으로 새로고침
클릭: 알림 목록 페이지 → 🔄 새로고침 버튼
```

---

## 📞 문의

추가 기능이 필요하거나 버그를 발견하셨다면 알려주세요!
