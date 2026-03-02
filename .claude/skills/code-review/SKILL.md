---
name: code-review
description: This skill should be used when the user asks to "code review", "review code", "코드 리뷰", "리뷰해줘", "코드 검토", or wants to review changed files against project conventions before a PR.
version: 1.0.0
---

# Code Review

변경된 파일을 `conventions.yaml` 기준으로 리뷰하여 PR 전 셀프 리뷰를 자동화합니다.

## 사용 시점

- PR 생성 전 코드 품질 점검
- 새 도메인 / 엔드포인트 추가 후 컨벤션 확인
- 예: "/code-review", "변경된 코드 리뷰해줘"

## 실행 플로우

### 1단계: 변경 파일 파악

```bash
# 기준 브랜치 대비 변경된 파일 목록
git diff main...HEAD --name-only --diff-filter=ACM

# 변경된 내용
git diff main...HEAD
```

기준 브랜치 기본값: `main` (사용자가 다른 브랜치를 지정하면 그것 사용)

### 2단계: 파일별 리뷰

각 변경 파일에 대해 아래 체크리스트를 실행합니다.

#### 공통 체크리스트

- [ ] **네이밍**: snake_case 변수·함수, PascalCase 클래스
- [ ] **async/await**: `async def` 함수 내에서 blocking I/O 호출 없음
- [ ] **하드코딩 금지**: 매직 넘버, 하드코딩된 URL/문자열 없음
- [ ] **타입 힌팅**: 함수 파라미터·반환값 타입 힌팅 존재

#### router.py 체크리스트

- [ ] 함수명: `{domain}_{action}` 패턴 (`question_list`, `question_create`)
- [ ] `prefix="/api/{domain}"` 설정
- [ ] create/update/delete/vote 엔드포인트에 `get_current_user_with_async` 인증 의존성
- [ ] 권한 검증: update/delete에서 `current_user.id != model.user_id` 체크
- [ ] CUD 응답: `status.HTTP_204_NO_CONTENT`
- [ ] 파라미터명: `_{domain}_create` 형식 (언더스코어 접두사)
- [ ] 에러 메시지: 한글 사용 (예: "데이터를 찾을 수 없습니다.")

#### service.py 체크리스트

- [ ] 함수명: `{action}_{domain}` 패턴 (`get_question`, `create_question`)
- [ ] `selectinload`로 관계 로딩 (N+1 쿼리 방지)
- [ ] 명시적 `await db.commit()` 호출
- [ ] 이벤트 발행: vote 액션 시 `event_bus.publish(DomainEvent(...))`
- [ ] `datetime.now()` 사용으로 `create_date`/`modify_date` 설정

#### models.py 체크리스트

- [ ] `__tablename__` 소문자 단수형
- [ ] 필수 필드: `id`, `create_date`, `modify_date`, `user_id`
- [ ] `user` relationship 포함
- [ ] Many-to-many 테이블명: `{domain}_voter`

#### schemas.py 체크리스트

- [ ] 응답 스키마: `{Domain}`, `{Domain}List`
- [ ] 요청 스키마: `{Domain}Create`, `{Domain}Update`, `{Domain}Delete`
- [ ] `field_validator`로 필수 필드 빈값 검증
- [ ] 에러 메시지: "필드를 입력해주세요"
- [ ] `Union[Type, None]` 타입 힌팅 (nullable 필드)

### 3단계: 고급 분석

#### N+1 쿼리 탐지

```python
# 위험 패턴 — selectinload 없이 관계 접근
for item in items:
    print(item.user.username)  # N+1 발생!

# 올바른 패턴
query.options(selectinload(Model.user))
```

#### 비동기 컨텍스트 오용 탐지

```python
# 위험 패턴 — async 함수 내 동기 I/O
async def my_func():
    time.sleep(1)           # 블로킹!
    requests.get(url)       # 블로킹!
    open("file.txt").read() # 블로킹!
```

#### 보안 기본 체크

- 인증 없는 데이터 변경 엔드포인트
- 권한 체크 없이 타인 데이터 수정 가능한 경우
- SQL 인젝션 가능성 (raw query 사용 시)

### 4단계: 리뷰 리포트 출력

```markdown
## 코드 리뷰 결과 — {브랜치명}

변경된 파일: {N}개

### ❌ 수정 필요

**src/domains/question/router.py**
- L23: `question_delete` 함수에 인증 의존성 누락
- L45: 에러 메시지 영문 사용 → 한글로 변경

**src/domains/question/service.py**
- L67: `selectinload` 없이 `.voter` 관계 접근 → N+1 위험

### ⚠️ 권고사항 (선택적 수정)

- `create_question`: 반환값 타입 힌팅 없음

### ✅ 통과 항목

- 네이밍 컨벤션: 모두 통과
- 필수 필드: 모두 존재
- async/await 올바른 사용

### 종합 평가

위험도: 🔴 높음 / 🟡 중간 / 🟢 낮음
PR 준비 상태: 수정 후 재검토 필요
```

## 참고사항

- 자동 수정은 하지 않으며 문제 목록만 제공합니다
- 수정이 필요한 경우 `/add-endpoint` 또는 직접 수정 후 재실행
- 보안 관련 이슈는 Critical Code Analyst Agent에 추가 분석 요청 권장
