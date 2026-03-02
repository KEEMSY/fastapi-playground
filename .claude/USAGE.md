# Claude Code 사용 가이드 — FastAPI-Playground

---

## 핵심 철학: Context Bloat 방지

> **많이 넣을수록 나빠진다.** — Context Bloat은 Claude의 집중력을 분산시키는 가장 큰 적이다.

### 레이어드 컴포지션 원칙

```
Rules (.claude/rules/)    ← 항상 자동 주입 (최소 핵심 규칙만)
    ↓ 필요시 선택적 로드
Skills (/slash-command)   ← 특정 작업 시에만 로드
    ↓ 분석/판단 필요시
Agents (Task tool)        ← 복잡한 판단이 필요할 때만
```

**원칙**:
- Rules에는 항상 지켜야 할 최소 핵심 규칙만 (10줄 이내 권장)
- Skills는 해당 작업 시에만 컨텍스트 추가
- Agents는 단순 작업에는 오버킬 — 필요한 경우에만

### `.claude/` 파일 Git 관리

`.claude/` 디렉토리 전체를 Git으로 버전 관리하세요:
```bash
git add .claude/
git commit -m "Update Claude Code settings"
# → 팀원과 설정 공유, 롤백 가능
```

---

## 구조 개요 (2-tier Architecture)

```
~/.claude/                          ← 모든 프로젝트 자동 사용 (Global)
├── agents/
│   ├── critical-analyst.md         범용 버전 (conventions.yaml 자동 감지)
│   ├── security-reviewer.md        OWASP Top 10 기반, 언어 무관
│   ├── test-generator.md           pytest/jest/go test 자동 감지
│   └── documentation.md            범용 버전
└── skills/
    └── commit-message/SKILL.md     완전 범용 커밋 메시지 생성

project/.claude/                    ← FastAPI-Playground 특화 (Project)
├── rules/                          ← 매 세션 자동 주입 (AI 지시사항)
│   ├── code-style.md               FastAPI 네이밍, async, 응답 코드 규칙
│   └── security.md                 .env 보호, 시크릿 하드코딩 금지 등
├── skills/
│   ├── new-domain/                 FastAPI CRUD 스캐폴드
│   ├── add-endpoint/               FastAPI 특화 엔드포인트 추가
│   ├── add-test/                   pytest + FastAPI 특화
│   ├── code-review/                conventions.yaml 참조
│   ├── db-migrate/                 Alembic 특화
│   ├── docker-env/                 Docker Compose 특화
│   └── perf-check/                 Prometheus + FastAPI 특화
└── settings.local.json             Python hooks + 권한
```

**우선순위**: Global agents + Global commit-message는 모든 프로젝트에서 자동 사용
**같은 이름이면**: Global이 Project보다 우선

---

## Rules vs Hooks — 핵심 구분

| 구분 | Rules (`.claude/rules/*.md`) | Hooks (`settings.local.json`) |
|------|------------------------------|-------------------------------|
| **형식** | 자연어 마크다운 | 셸 스크립트 |
| **실행 주체** | AI (Claude) | 운영체제 (bash) |
| **실행 시점** | 매 세션 시작 시 자동 로드 | Pre/PostToolUse 이벤트 발생 시 |
| **용도** | AI에게 "어떻게 코드를 작성해야 하는가" 지시 | 파일 저장 후 자동 포매팅, 린팅 등 |
| **예시** | "async def 내 blocking I/O 금지" | `black {file} && isort {file}` |

**현재 설정된 Rules:**
- `code-style.md`: 네이밍, 응답 코드, 비동기 규칙
- `security.md`: .env 보호, SQL 인젝션 방지, 에러 노출 금지

---

## 빠른 참조 (키워드 → 도구 매핑)

| 상황 | 도구 | 트리거 |
|------|------|--------|
| 새 도메인 CRUD 전체 | `/new-domain` | "새 도메인 만들어줘" |
| 기존 도메인에 API 추가 | `/add-endpoint` | "엔드포인트 추가" |
| DB 스키마 변경 | `/db-migrate` | "마이그레이션 만들어줘" |
| 환경 전환 (dev/prod) | `/docker-env` | "운영환경으로 전환" |
| 테스트 스캐폴드 | `/add-test` | "테스트 추가해줘" |
| PR 전 컨벤션 체크 | `/code-review` | "코드 리뷰해줘" |
| 성능/에러율 확인 | `/perf-check` | "API 느려졌어" |
| 커밋 메시지 생성 | `/commit-message` | "커밋 메시지 만들어줘" |
| 버그/취약점 탐색 | `critical-analyst` agent | "비판적으로 봐줘" |
| 보안 감사 | `security-reviewer` agent | "보안 검토해줘" |
| 엣지케이스 테스트 | `test-generator` agent | "엣지케이스 테스트 만들어줘" |
| 문서 업데이트 | `documentation` agent | "docs 업데이트해줘" |

---

## 시나리오 1: 새 기능 개발 플로우

**"Question 게시판 같은 새 도메인을 추가하고 싶어요"**

```
1. /new-domain
   → 도메인명, 필드, 관계 입력
   → models.py, schemas.py, service.py, router.py, migration 자동 생성

2. (구현 확인 후) /code-review
   → conventions.yaml 기준 자동 검증
   → 함수명 패턴, 인증 의존성, 응답 코드 체크

3. critical-analyst agent
   → "비판적으로 봐줘"
   → N+1 쿼리, 권한 검증 누락, 예외 처리 공백 탐지

4. /db-migrate
   → Alembic 마이그레이션 생성 및 적용

5. /commit-message
   → 변경사항 분석 후 컨벤션 맞는 커밋 메시지 생성
```

**기대 결과**: 컨벤션 준수, 보안 취약점 없음, DB 반영 완료

---

## 시나리오 2: PR 직전 품질 점검

**"이 브랜치 PR 올리기 전에 점검하고 싶어요"**

```
1. /code-review
   → git diff main...HEAD 기준 변경 파일 자동 감지
   → conventions.yaml 항목 전체 체크
   → 위반 목록 출력

2. critical-analyst agent
   → "비판적으로 봐줘" 또는 "버그 찾아줘"
   → 구현 편향 없이 반대 입장에서 분석
   → 즉시 수정 필요 / 수정 권고 / 컨벤션 위반 분류

3. (인증/보안 코드 변경이 있을 경우) security-reviewer agent
   → "보안 검토해줘"
   → JWT, 비밀번호, CORS, SQL Injection 체크
   → Critical/High/Medium 등급 분류
```

**기대 결과**: 리뷰어가 컨벤션 위반 지적 없음, 보안 이슈 없음

---

## 시나리오 3: 테스트 커버리지 확보

**"이 도메인 테스트가 너무 부족해요"**

```
1. /add-test {domain}
   → 기본 pytest 스캐폴드 생성
   → Happy path 케이스 포함
   → conftest.py 픽스처 설정

2. test-generator agent
   → "엣지케이스 테스트 만들어줘"
   → 경계값, 인증/인가, 상태 전이 케이스 추가
   → Happy path보다 실패 경로 우선

3. 실행 및 확인
   pytest tests/domains/test_{domain}.py -v --cov=src/domains/{domain}
```

**기대 결과**: 커버리지 80% 이상, 실패 경로 포함

---

## 시나리오 4: "갑자기 느려졌어요" 디버깅

**"특정 API가 갑자기 응답이 느려졌어요"**

```
1. /perf-check
   → Prometheus 메트릭 조회
   → 느린 엔드포인트 TOP 5, 에러율 높은 엔드포인트 출력
   → 비정상 지표 하이라이트

2. critical-analyst agent
   → 해당 서비스 파일 지정: "service.py 비판적으로 봐줘"
   → N+1 쿼리 탐지 (selectinload 누락)
   → 비동기 컨텍스트 오용 탐지 (동기 I/O)
   → 불필요한 데이터 로딩 탐지

3. 수정 후 /perf-check 재실행으로 개선 확인
```

**기대 결과**: 병목 지점 식별 및 수정, 지표 개선 확인

---

## 시나리오 5: 신규 팀원 온보딩

**"새로 합류했는데 이 프로젝트 어떻게 사용하나요?"**

```
1. 이 파일(USAGE.md) 읽기

2. 구조 파악
   cat README.md
   ls src/domains/  # 기존 도메인 파악

3. 환경 설정
   /docker-env  → 개발 환경 실행

4. 첫 기능 추가
   /new-domain  → 가이드를 따라 도메인 생성

5. 더 자세한 설정 방법
   cat .claude/NEW-PROJECT-SETUP.md
```

---

## Hooks 동작 설명 (자동 실행)

`.claude/settings.local.json`에 설정된 자동 실행 항목:

### 파일 저장 시 (PostToolUse: Write)

**.py 파일 저장 시:**
```bash
# 자동 실행 (수동 조작 불필요)
black {파일}      # 코드 포매팅
isort {파일}      # import 정렬
```

**모든 저장 시 컨벤션 검증:**
```bash
python scripts/validate_conventions.py {파일}
# conventions.yaml 기준 네이밍 위반 즉시 출력
```

### 대화 종료 시 (Stop hook)

```bash
alembic check
# 모델 변경 후 마이그레이션 누락 시 경고 출력
# → /db-migrate 실행 권장
```

---

## Agent Teams (실험적 기능)

> **참고**: 현재 Claude Code settings 스키마에서 `experiments.agentTeams` 필드가 공식 지원되지 않습니다.
> 향후 공식 지원 시 `settings.local.json`에 `"experiments": { "agentTeams": true }` 추가 예정.

Agent Teams는 여러 Claude 인스턴스가 병렬로 동작하는 기능입니다.

**적합한 작업 유형:**
- 리서치 + 리뷰 병렬 실행 (조사하면서 동시에 리뷰)
- 크로스 레이어 동시 수정 (router, service, tests 동시 작업)
- 대규모 리팩토링 (여러 파일 병렬 처리)

**주의사항:**
- 토큰 사용량이 크게 증가
- 동일 파일 동시 수정 시 충돌 가능
- 단순 작업에는 오버킬

---

## npx skills 생태계

커뮤니티 제작 skills를 설치해 기능을 확장할 수 있습니다.

```bash
# 커뮤니티 스킬 검색
npx skills find "code review"

# 스킬 설치 예시
npx skills add obra/superpowers

# 포탈: skills.sh
```

**기사에서 추천한 커뮤니티 스킬:**
- `obra/superpowers` — 일반 생산성 향상
- `humanizer` — 출력 스타일 자연스럽게
- `ui-ux-pro-max` — UI/UX 특화 리뷰
- `vercel-labs/skills` — Vercel 배포 워크플로우

> **현재 프로젝트**: Python/FastAPI 특화이므로 위 npm 기반 스킬보다 `.claude/skills/` 직접 작성 방식 권장

---

## 자주 묻는 질문

**Q: agents와 skills의 차이는?**

- **Skills** (`/slash-command`): 정해진 절차를 단계별로 실행. 예: `/new-domain`은 파일 생성 → 라우터 등록까지 자동화
- **Agents**: 분석/판단이 필요한 작업. 코드를 읽고 상황에 맞게 판단. 예: `critical-analyst`는 어떤 파일이든 문제점을 찾아냄

**Q: Rules와 Hooks의 차이는?**

- **Rules** (`.claude/rules/*.md`): 자연어 → Claude가 읽고 코드 작성 시 적용. 매 세션 자동 로드
- **Hooks** (`settings.local.json`): 셸 스크립트 → 파일 저장 등 이벤트 시 자동 실행

**Q: `/code-review`와 `critical-analyst`의 차이는?**

- `/code-review`: conventions.yaml 체크리스트 기반 **규칙 준수** 검사
- `critical-analyst`: 동작 여부와 무관하게 **"왜 틀렸는가"** 관점의 심층 분석

**Q: global agent가 제대로 동작하는지 확인하는 방법은?**

```bash
ls ~/.claude/agents/
# critical-analyst.md, security-reviewer.md, test-generator.md, documentation.md
```

대화에서 "비판적으로 봐줘" → `critical-analyst` agent 자동 실행
