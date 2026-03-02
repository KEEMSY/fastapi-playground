# FastAPI 코딩 스타일 규칙

이 파일은 매 세션 자동으로 로드됩니다. 아래 규칙을 항상 준수하세요.

## 네이밍 규칙

- **router 함수명**: `{domain}_{action}` 패턴 필수
  - 올바른 예: `question_list`, `question_create`, `question_update`
  - 잘못된 예: `list_questions`, `get_questions`, `createQuestion`

- **service 함수명**: `{action}_{domain}` 패턴 필수
  - 올바른 예: `get_question`, `create_question`, `update_question`
  - 잘못된 예: `question_get`, `question_create`, `getQuestion`

- **파라미터 이름**: 언더스코어 접두사 필수
  - 올바른 예: `_question_create`, `_user_update`
  - 잘못된 예: `question_create`, `question_data`

## HTTP 응답 규칙

- **Create/Update/Delete 응답**: 반드시 `status.HTTP_204_NO_CONTENT` 사용
  - 숫자 `204` 직접 사용 금지
  - `200` 반환 금지 (CUD 작업에)

- **상태코드**: 숫자 대신 `status.HTTP_XXX` 상수 사용
  - 올바른 예: `status.HTTP_200_OK`, `status.HTTP_404_NOT_FOUND`
  - 잘못된 예: `200`, `404`

## 에러 처리

- **에러 메시지**: 항상 한글로 작성
  - 올바른 예: `"데이터를 찾을 수 없습니다"`, `"권한이 없습니다"`
  - 잘못된 예: `"Not found"`, `"Forbidden"`

- **에러 응답**: `str(e)` 직접 반환 금지 → 내부 정보 노출 방지
  - `HTTPException`의 `detail`에 내부 예외 메시지 그대로 넣지 말 것

## 데이터베이스

- **관계 로딩**: 반드시 `selectinload` 사용 (N+1 방지)
  - `lazy loading` 또는 `joinedload` 사용 금지 (특별한 이유 없이)

## 인증

- **인증 의존성**: `create`, `update`, `delete`, `vote` 작업에 반드시 `get_current_user_with_async` 추가
  - 누락 시 보안 취약점

## 비동기 규칙

- **async def 내 blocking I/O 절대 금지**:
  - `time.sleep()` → `await asyncio.sleep()` 사용
  - `requests.get()` → `httpx.AsyncClient` 또는 `aiohttp` 사용
  - 동기 `open()` → `aiofiles` 사용

## 코드 구조

- 도메인 파일 위치: `src/domains/{domain}/{router,service,models,schemas}.py`
- DB 세션: `get_async_db` 의존성 사용
- 이벤트: `src/common/events.py`의 `event_bus` 사용
