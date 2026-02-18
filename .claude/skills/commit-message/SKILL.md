---
name: commit-message
description: This skill should be used when the user asks to "create commit message", "write commit message", "커밋 메시지 작성", "git commit", or wants to commit changes with an appropriate message.
version: 1.0.0
---

# Commit Message Generator

프로젝트 컨벤션을 따르는 의미 있는 커밋 메시지를 자동으로 생성합니다.

## 사용 시점

- Git 변경사항을 커밋하기 전
- 커밋 메시지 작성이 고민될 때
- 프로젝트 스타일에 맞는 메시지가 필요할 때

## 실행 플로우

### 1단계: 변경사항 분석

```bash
🔍 변경사항 분석 중...

[Git 상태 확인]
$ git status
$ git diff --stat
$ git log --oneline -5  # 기존 커밋 스타일 참조
```

**분석 항목:**
- 수정된 파일 (modified)
- 추가된 파일 (untracked)
- 삭제된 파일
- 파일별 변경 라인 수

**변경사항 분류:**
```
카테고리 자동 판단:
1. 새 기능 추가 (Add)
   - 새 도메인/파일 추가
   - 새 엔드포인트 추가
   - 새 기능 구현

2. 기능 개선 (Update)
   - 기존 기능 향상
   - 성능 최적화
   - 리팩토링

3. 버그 수정 (Fix)
   - 에러 수정
   - 버그 패치

4. 문서 (Docs)
   - README 업데이트
   - 주석 추가

5. 설정 (Config)
   - 환경 설정 변경
   - Docker 설정

6. 테스트 (Test)
   - 테스트 코드 추가/수정
```

### 2단계: 프로젝트 커밋 스타일 파악

이 프로젝트의 커밋 메시지 컨벤션:

```yaml
구조:
  - 첫 줄: "카테고리: 메인 제목"
  - 두 번째 줄: 빈 줄
  - 본문: 섹션별 상세 설명

카테고리:
  - Add: 새 기능 추가
  - Update: 기능 개선
  - Fix: 버그 수정
  - Edit: 파일 수정
  - Docs: 문서 작성

메인 제목:
  - 한글 사용
  - 핵심 내용 요약 (100자 이내)
  - 무엇을 왜 했는지 명확히

본문 구조:
  [대분류 카테고리]
  - 세부 항목 나열
    · 하위 항목 (선택)
    · 구체적인 변경 내용

  [또 다른 카테고리]
  - 항목...

  [주요 효과/인사이트]
  - 변경으로 인한 효과
  - 성능 개선 수치
  - 중요한 인사이트

마지막:
  Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**기존 커밋 예시 분석:**
```
ea29476 Add: DB 성능 분석 자동화 도구, 분석 리포트 및 AWS 최적화 운영 환경 구축

[DB 성능 분석 및 최적화]
- DB 세션 풀 크기 및 인스턴스 수에 따른 성능 측정 자동화 스크립트 추가
- 수직 확장(Vertical) vs 수평 확장(Horizontal) 전략 비교 분석 도구
...

[운영 환경 구축]
- AWS t3.medium 환경에 최적화된 docker-compose-prod.yml 추가
...

[주요 인사이트]
- 파이썬 GIL 한계 극복을 위한 멀티 컨테이너 아키텍처 채택
...
```

### 3단계: 변경사항 그룹핑

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 변경사항 분석 결과
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

그룹 1: 새 기능 추가
  📁 src/domains/review/
    ├─ models.py (새 파일, 25줄)
    ├─ schemas.py (새 파일, 49줄)
    ├─ service.py (새 파일, 82줄)
    └─ router.py (새 파일, 78줄)

  영향: Review 도메인 전체 구현

그룹 2: DB 스키마 변경
  📄 alembic/versions/abc123_add_review.py (새 파일)

  영향: review, review_voter 테이블 추가

그룹 3: 라우터 등록
  📝 src/main.py (+3줄)

  영향: Review API 활성화

그룹 4: 문서
  📄 docs/REVIEW_SYSTEM.md (새 파일)

  영향: 리뷰 시스템 설계 문서
```

### 4단계: 커밋 메시지 생성

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 생성된 커밋 메시지
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Add: 상품 리뷰 시스템 구현 (별점, 댓글, 투표 기능)

[Review 도메인 추가]
- Review 모델 및 스키마 정의 (product_id, rating, content)
  · SQLAlchemy 모델: review, review_voter 테이블
  · Pydantic 스키마: 6개 (Review, ReviewList, ReviewCreate 등)
  · 표준 필드 자동 포함 (create_date, modify_date, user_id)
- Review 서비스 레이어 구현
  · get_review_list: 페이징, 검색 지원
  · CRUD 기본 기능: create/update/delete
  · vote_review: 좋아요 기능 + 이벤트 발행
- Review API 엔드포인트 (7개)
  · GET /api/review/list - 리뷰 목록 조회
  · GET /api/review/detail/{id} - 상세 조회
  · POST /api/review/create - 리뷰 작성 (인증)
  · PUT /api/review/update - 수정 (권한 검증)
  · DELETE /api/review/delete - 삭제 (권한 검증)
  · POST /api/review/vote - 좋아요 (인증)
  · GET /api/review/average-rating/{product_id} - 평균 별점

[데이터베이스]
- Alembic 마이그레이션 추가 (abc123)
  · review 테이블: 리뷰 본문 및 별점
  · review_voter 테이블: Many-to-Many 관계
  · 외래키: user_id, product_id

[통합]
- main.py에 review 라우터 등록
- API 문서 자동 생성 (/docs)

[문서]
- 리뷰 시스템 설계 문서 작성 (docs/REVIEW_SYSTEM.md)
  · ERD 및 API 명세
  · 사용 예시 및 제약사항

[주요 기능]
- 1-5점 별점 시스템
- 텍스트 리뷰 작성 및 수정
- 리뷰에 대한 좋아요 (투표)
- 상품별 평균 별점 조회
- 작성자 본인만 수정/삭제 가능 (권한 검증)
- 이벤트 기반 알림 연동 준비

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 5단계: 사용자 확인 및 수정

```
생성된 커밋 메시지를 사용하시겠습니까?

1. 그대로 사용
2. 제목만 수정
3. 전체 수정
4. 취소

선택 [1-4]: _____
```

**선택 2: 제목만 수정**
```
현재 제목:
"Add: 상품 리뷰 시스템 구현 (별점, 댓글, 투표 기능)"

새 제목을 입력하세요:
입력: _____
```

**선택 3: 전체 수정**
```
편집기로 열기:
$ $EDITOR commit_message.txt

[편집 후 저장하면 계속]
```

### 6단계: 커밋 실행

```
커밋을 실행하시겠습니까? [Y/n]: _____
```

**Yes 선택 시:**
```bash
$ git commit -m "$(cat <<'EOF'
Add: 상품 리뷰 시스템 구현 (별점, 댓글, 투표 기능)

[Review 도메인 추가]
...

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"

[main abc1234] Add: 상품 리뷰 시스템 구현
 7 files changed, 234 insertions(+)
 create mode 100644 src/domains/review/models.py
 create mode 100644 src/domains/review/schemas.py
 create mode 100644 src/domains/review/service.py
 create mode 100644 src/domains/review/router.py
 create mode 100644 alembic/versions/abc123_add_review.py
 create mode 100644 docs/REVIEW_SYSTEM.md

✅ 커밋 완료!

다음 단계:
- git log -1 --stat : 커밋 확인
- git push : 원격 저장소에 푸시
```

---

## 커밋 메시지 템플릿

### Add (새 기능)

```
Add: [메인 기능 설명] (부가 설명)

[카테고리 1]
- 항목 1
  · 세부 내용
- 항목 2

[카테고리 2]
- 항목...

[주요 효과]
- 효과 설명

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Update (개선)

```
Update: [무엇을 개선했는지]

[개선 내용]
- 변경 사항

[성능 향상]
- 이전: X
- 이후: Y (+Z% 개선)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Fix (버그 수정)

```
Fix: [어떤 버그를 수정했는지]

[문제 상황]
- 증상 및 재현 방법

[원인]
- 버그 원인 분석

[해결 방법]
- 수정 내용

[영향 범위]
- 영향받는 기능

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## 커밋 메시지 작성 원칙

### 제목 (첫 줄)

1. **카테고리 명시**
   ```
   ✅ Add: 리뷰 시스템 추가
   ✅ Fix: 로그인 버그 수정
   ❌ 리뷰 시스템 (카테고리 없음)
   ```

2. **한글 사용**
   ```
   ✅ Add: 상품 리뷰 시스템 구현
   ❌ Add: Implement product review system
   ```

3. **명확하고 구체적**
   ```
   ✅ Add: 상품 리뷰 시스템 구현 (별점, 댓글, 투표)
   ❌ Add: 새 기능 추가
   ```

4. **100자 이내**
   ```
   ✅ Add: Review 도메인 구현 및 평균 별점 API 추가
   ❌ Add: Review 도메인을 추가하고 CRUD 전체 구현하고 별점 기능도 넣고 투표도 되고...
   ```

### 본문

1. **섹션으로 분류**
   ```
   [도메인 추가]
   [데이터베이스]
   [API 엔드포인트]
   [주요 효과]
   ```

2. **계층 구조 사용**
   ```
   - 대항목
     · 중항목
     · 중항목
   - 대항목
   ```

3. **구체적인 변경 내용**
   ```
   ✅ - Review 모델 정의 (product_id, rating, content)
   ❌ - 모델 추가
   ```

4. **수치 포함 (성능 개선 시)**
   ```
   ✅ - 응답 시간 80% 단축 (250ms → 50ms)
   ❌ - 성능 개선
   ```

### Co-Authored-By

```
항상 마지막 줄에 추가:
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## 변경사항별 예시

### 도메인 추가

```
Add: Product 도메인 구현 (상품 관리 시스템)

[Product 도메인]
- Product 모델 (name, price, stock, description)
- CRUD 서비스 레이어 (6개 함수)
- REST API 엔드포인트 (5개)
  · GET /api/product/list - 상품 목록
  · POST /api/product/create - 상품 등록
  · ...

[데이터베이스]
- product 테이블 마이그레이션 (abc123)
- 외래키: category_id, user_id

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### 엔드포인트 추가

```
Add: Question 도메인에 조회수 집계 API 추가

[새 엔드포인트]
- GET /api/question/popular - 조회수 TOP 10
  · 최근 7일 기준 집계
  · 캐싱 적용 (Redis, TTL 5분)

[서비스 로직]
- get_popular_questions() 함수 추가
- 조회수 기준 정렬 및 페이징

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### 성능 개선

```
Update: DB 커넥션 풀 최적화 및 쿼리 성능 개선

[DB 최적화]
- 커넥션 풀 크기 조정 (20 → 15)
- selectinload로 N+1 문제 해결

[쿼리 최적화]
- Question 목록 조회 시 인덱스 활용
- 불필요한 JOIN 제거

[성능 향상]
- 목록 조회: 250ms → 50ms (80% 개선)
- 처리량: 800 req/s → 1,200 req/s (+50%)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### 버그 수정

```
Fix: 리뷰 수정 시 권한 검증 누락 문제 해결

[문제 상황]
- 다른 사용자의 리뷰를 수정할 수 있는 보안 취약점
- /api/review/update 엔드포인트에서 발생

[원인]
- router.py의 review_update 함수에서
- current_user.id != review.user_id 검증 로직 누락

[해결 방법]
- 권한 검증 로직 추가
- HTTPException(400, "수정 권한이 없습니다") 반환

[영향 범위]
- Review 수정 API만 해당
- 조회/삭제 API는 정상 작동

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Docker/환경 설정

```
Config: 운영 환경 Docker Compose 설정 최적화

[컨테이너 구성]
- FastAPI 레플리카: 3개
- Nginx 로드밸런서 추가 (least_conn)
- DB 풀 크기: 15 (환경 변수로 조정 가능)

[설정 파일]
- docker-compose-prod.yml 생성
- nginx/nginx-prod.conf 추가

[환경 변수]
- DB_POOL_SIZE: 15
- WORKER_PROCESSES: 1

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## 자동 감지 규칙

### 파일 패턴 분석

```python
파일 패턴별 카테고리:
  "src/domains/*/models.py": "도메인 모델"
  "src/domains/*/schemas.py": "Pydantic 스키마"
  "src/domains/*/service.py": "비즈니스 로직"
  "src/domains/*/router.py": "API 엔드포인트"
  "alembic/versions/*.py": "DB 마이그레이션"
  "docker-compose*.yml": "Docker 설정"
  "docs/*.md": "문서"
  ".claude/skills/*": "개발 도구"
```

### 변경 라인 수 기준

```
라인 수별 중요도:
  1-10줄: 소규모 수정
  11-50줄: 중간 규모 변경
  51-100줄: 큰 변경
  100줄+: 주요 기능 추가

커밋 메시지 상세도 조절:
  - 소규모: 간단히
  - 중대규모: 상세히
  - 대규모: 매우 상세히
```

---

## 주의사항

1. **민감 정보 제외**
   - 비밀번호, API 키 등은 메시지에 포함하지 않음

2. **Co-Authored-By 항상 포함**
   - Claude가 작성한 코드임을 명시

3. **이슈 번호 참조 (선택)**
   ```
   Fix: 로그인 버그 수정 (#123)
   ```

4. **Breaking Changes 명시**
   ```
   Update: API 응답 형식 변경 (Breaking Change)

   [주의]
   - 기존 클라이언트 업데이트 필요
   - /api/v1/* → /api/v2/* 로 마이그레이션
   ```

---

## 통합 워크플로우

```bash
# 1. 변경사항 확인
git status
git diff

# 2. SKILL 사용
/commit-message

# 3. 생성된 메시지 확인 및 수정

# 4. 스테이징
git add .

# 5. 커밋
git commit -m "생성된 메시지"

# 6. 푸시
git push
```
