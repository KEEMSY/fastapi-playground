# 새 프로젝트에 Claude Code 설정 적용하기

---

## 빠른 시작 체크리스트 (전체 스택 공통)

```bash
# Step 1: 기본 구조 생성 (1분)
mkdir -p .claude/{agents,skills,rules,commands}

# Step 2: rules/ 작성 (5분)
# → code-style.md: 언어별 네이밍/응답 규칙
# → security.md: 시크릿 하드코딩 금지, SQL 인젝션 방지

# Step 3: hooks 설정 (2분)
# → settings.local.json: 포매터/린터 자동 실행

# Step 4: npx skills 설치 (선택사항, 3분)
# npx skills add obra/superpowers
# npx skills find "code review"
```

---

## 전제: 글로벌 Agents 자동 사용

`~/.claude/agents/`에 이미 4개가 설치되어 있으므로 **모든 프로젝트에서 자동으로 사용 가능**합니다.

```bash
ls ~/.claude/agents/
# critical-analyst.md  security-reviewer.md  test-generator.md  documentation.md
```

별도 설치 없이 어느 프로젝트에서나 즉시 사용:
- "비판적으로 봐줘" → `critical-analyst`
- "보안 검토해줘" → `security-reviewer`
- "테스트 만들어줘" → `test-generator`
- "docs 업데이트해줘" → `documentation`

---

## Case A: FastAPI (동일 스택)

이 프로젝트와 동일한 스택 (FastAPI + SQLAlchemy + MySQL + Docker Compose).

### 1. 기본 구조 생성

```bash
mkdir -p .claude/{skills,rules}
```

### 2. rules/ 설정 (자동 로드되는 AI 지시사항)

**`.claude/rules/code-style.md`** 생성:
```markdown
# FastAPI 코딩 규칙
- router 함수명: {domain}_{action} (question_list, question_create)
- service 함수명: {action}_{domain} (get_question, create_question)
- CUD 응답: 항상 status.HTTP_204_NO_CONTENT
- 관계 로딩: selectinload 필수 (N+1 방지)
- 인증: create/update/delete/vote에 get_current_user_with_async
- 파라미터 접두사: _ (_question_create)
- 에러 메시지: 한글
- async def 내 blocking I/O 금지 (time.sleep, requests.get)
```

**`.claude/rules/security.md`** 생성:
```markdown
# 보안 규칙
- .env 파일 내용 절대 출력/커밋 금지
- SECRET_KEY, API_KEY 하드코딩 금지 → 환경변수
- SQL raw query에 사용자 입력 직접 삽입 금지
- 에러 응답에 str(e) 직접 반환 금지
- 비밀번호, 토큰 로그 출력 금지
```

### 3. skills 폴더 복사

```bash
cp -r /path/to/FastAPI-Playground/.claude/skills/ /path/to/new-project/.claude/skills/
cp /path/to/FastAPI-Playground/scripts/validate_conventions.py /path/to/new-project/scripts/
```

### 4. conventions.yaml 도메인 규칙 수정

`.claude/skills/new-domain/conventions.yaml` 수정:

```yaml
# 수정 필요 항목
router:
  prefix: "/api/{your-domain}"  # 기본 라우터 prefix

naming:
  router_function: "{domain}_{action}"  # 그대로 유지 권장
  service_function: "{action}_{domain}"  # 그대로 유지 권장

# 에러 메시지 언어 변경 (한글 → 영어 등)
error_messages:
  language: "korean"  # "english"로 변경 가능
```

### 5. settings.local.json 절대경로 수정

`.claude/settings.local.json`에서 **2개의 절대경로**만 수정:

```json
{
  "permissions": { ... },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "cd /path/to/NEW-PROJECT && black {file} && isort {file}"
          },
          {
            "type": "command",
            "command": "cd /path/to/NEW-PROJECT && python scripts/validate_conventions.py {file}"
          }
        ]
      }
    ]
  }
}
```

### 6. 검증

```bash
# Docker 환경 실행
/docker-env

# 새 도메인 생성 테스트
/new-domain

# .py 파일 저장 후 black/isort 자동 실행 확인
```

### MCP 서버 연동 (선택사항)

`.claude/settings.local.json`에 추가:
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"]
    },
    "postgres": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-postgres", "postgresql://user:pass@localhost/db"]
    }
  }
}
```

---

## Case B: Next.js / TypeScript

글로벌 agents는 자동 사용 가능. 스택별 skills 새로 구성 필요.

### 1. 기본 구조 생성

```bash
mkdir -p .claude/{skills,rules}
```

### 2. rules/ 설정 (TypeScript 버전)

**`.claude/rules/code-style.md`** 생성:
```markdown
# TypeScript/Next.js 코딩 규칙
- TypeScript strict 모드 필수, any 타입 사용 금지
- 컴포넌트명: PascalCase (MyComponent)
- 훅 이름: use{Name} (useMyHook)
- API 라우트: kebab-case (/api/my-route)
- console.log 대신 구조화된 로거 사용
- 새 컴포넌트 생성 시 테스트 파일 함께 생성
- Props는 항상 TypeScript interface로 타입 정의
```

**`.claude/rules/security.md`** 생성:
```markdown
# 보안 규칙
- .env.local 파일 내용 절대 출력/커밋 금지
- API 키 하드코딩 금지 → 환경변수 (NEXT_PUBLIC_ 주의)
- eval() 사용 금지
- dangerouslySetInnerHTML 사용 시 반드시 DOMPurify로 sanitize
- fetch 호출 시 에러 처리 필수
```

### 3. 글로벌 agents 동작 확인

```bash
# 이미 동작함 — 추가 설정 불필요
# "비판적으로 봐줘" → critical-analyst (TypeScript 패턴 자동 감지)
# "보안 검토해줘" → security-reviewer (JWT, CORS 등)
# "테스트 만들어줘" → test-generator (Jest/Vitest 자동 감지)
```

### 4. 새 skills 구성

`.claude/skills/` 디렉토리에 Next.js 특화 skill 생성:

```
.claude/skills/
├── new-component/      # React 컴포넌트 스캐폴드
│   └── SKILL.md
├── add-api-route/      # Next.js API Route 추가
│   └── SKILL.md
└── db-migrate/         # Prisma 마이그레이션
    └── SKILL.md
```

**new-component/SKILL.md 예시:**
```markdown
---
name: new-component
description: Use when user asks to "create component", "add component", "컴포넌트 추가"
---
# New Component Scaffold

1. src/components/{ComponentName}/
   - index.tsx
   - {ComponentName}.stories.tsx (Storybook 있으면)
   - {ComponentName}.test.tsx

2. 스타일: Tailwind CSS / CSS Modules
3. Props 타입 정의 (TypeScript interface)
```

### 5. hooks: prettier/eslint로 교체

`.claude/settings.local.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "cd /path/to/project && npx prettier --write {file} && npx eslint --fix {file}"
          }
        ]
      }
    ]
  }
}
```

### 6. conventions.yaml (선택사항)

```yaml
naming:
  component: "PascalCase"           # MyComponent
  hook: "use{Name}"                 # useMyHook
  api_route: "kebab-case"           # /api/my-route
  util_function: "camelCase"        # myUtilFunction
  constant: "UPPER_SNAKE_CASE"      # MY_CONSTANT

file_structure:
  component_dir: "src/components/{ComponentName}/"
  api_dir: "src/app/api/{route}/"
  hook_dir: "src/hooks/"

rules:
  no_default_export_for_utils: true
  always_type_props: true
```

### MCP 서버 연동 (선택사항)

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/path/to/project"]
    }
  }
}
```

---

## Case C: Go / Gin

글로벌 agents 자동 사용. Go 특화 설정 필요.

### 1. 기본 구조 생성

```bash
mkdir -p .claude/{skills,rules}
```

### 2. rules/ 설정 (Go 버전)

**`.claude/rules/code-style.md`** 생성:
```markdown
# Go/Gin 코딩 규칙
- error 반환값 무시 금지 (_, err = 패턴 금지)
- context.Context를 DB 함수 첫 번째 파라미터로 전달
- handler에서 panic 금지
- handler 함수명: {Domain}{Action}Handler (UserCreateHandler)
- service 함수명: {Action}{Domain} (CreateUser)
- 에러는 항상 상위로 전파하거나 명시적으로 처리
```

**`.claude/rules/security.md`** 생성:
```markdown
# 보안 규칙
- .env 파일 내용 절대 출력/커밋 금지
- DB 비밀번호, API 키 하드코딩 금지 → 환경변수
- SQL 쿼리에 fmt.Sprintf로 사용자 입력 삽입 금지 → 파라미터 바인딩
- gin.Context에서 에러 직접 노출 금지
- JWT 시크릿 하드코딩 금지
```

### 3. 글로벌 agents 동작 확인

```bash
# 자동 동작 — Go 패턴 자동 감지
# critical-analyst: N+1 쿼리, 에러 무시 패턴 탐지
# security-reviewer: JWT, SQL Injection (Go 패턴)
# test-generator: go test 스타일 생성
```

### 4. hooks: gofmt/golint로 교체

`.claude/settings.local.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "cd /path/to/project && gofmt -w {file} && golangci-lint run {file}"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "cd /path/to/project && go build ./... 2>&1 | grep -E 'error|warning' || echo '빌드 정상'"
          }
        ]
      }
    ]
  }
}
```

### 5. Go 특화 skills

```
.claude/skills/
├── new-handler/        # Gin 핸들러 + 라우트 등록
│   └── SKILL.md
├── add-middleware/     # Gin 미들웨어 추가
│   └── SKILL.md
└── db-migrate/         # golang-migrate 관리
    └── SKILL.md
```

### 6. conventions.yaml (Go)

```yaml
naming:
  handler_func: "{Domain}{Action}Handler"   # UserCreateHandler
  service_func: "{Action}{Domain}"          # CreateUser
  model: "PascalCase"                       # UserModel
  constant: "UPPER_SNAKE_CASE"

file_structure:
  handler: "handler/{domain}.go"
  service: "service/{domain}.go"
  model: "model/{domain}.go"
  repository: "repository/{domain}.go"

rules:
  always_handle_error: true        # err 반환값 무시 금지
  use_context_in_db: true          # DB 함수에 ctx 전달
  no_panic_in_handler: true        # handler에서 panic 금지
```

### MCP 서버 연동 (선택사항)

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"]
    },
    "postgres": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-postgres", "postgresql://user:pass@localhost/db"]
    }
  }
}
```

---

## conventions.yaml 커스터마이징 가이드

현재 파일 위치: `.claude/skills/new-domain/conventions.yaml`

### 주요 항목 설명

```yaml
# ① 네이밍 패턴 — {domain}, {action} 플레이스홀더 사용
naming:
  router_function: "{domain}_{action}"
  # 예: question_list, question_create
  # → 위반 시 critical-analyst/code-review가 탐지

  service_function: "{action}_{domain}"
  # 예: get_question, create_question

  parameter_prefix: "_"
  # 예: _question_create (언더스코어 접두사)

# ② HTTP 응답 규칙
responses:
  cud_status_code: "status.HTTP_204_NO_CONTENT"
  # Create/Update/Delete는 항상 204 반환
  # → 200 반환 시 code-review에서 경고

# ③ DB 쿼리 규칙
database:
  relationship_loading: "selectinload"
  # N+1 방지를 위해 selectinload 강제
  # → 누락 시 critical-analyst가 탐지

# ④ 인증 규칙
auth:
  required_for: ["create", "update", "delete", "vote"]
  dependency: "get_current_user_with_async"
  # → 누락 시 critical-analyst가 탐지

# ⑤ 에러 메시지
errors:
  language: "korean"
  # 한글 에러 메시지 강제
  example: "데이터를 찾을 수 없습니다"
```

### 수정 방법

1. 항목 변경 후 저장
2. `.py` 파일 저장 시 `validate_conventions.py`가 자동 체크
3. `/code-review` 실행 시 새 규칙 기준으로 검토

---

## 체크리스트: 새 프로젝트 설정 완료 여부

- [ ] `~/.claude/agents/` — 4개 파일 존재 확인
- [ ] `~/.claude/skills/commit-message/SKILL.md` 존재 확인
- [ ] `.claude/rules/code-style.md` — 언어별 네이밍/응답 규칙
- [ ] `.claude/rules/security.md` — 시크릿, SQL 인젝션 방지
- [ ] `.claude/skills/` — 스택별 skills 구성
- [ ] `.claude/settings.local.json` — hooks 절대경로 수정
- [ ] `scripts/validate_conventions.py` 복사 (Python 스택)
- [ ] `conventions.yaml` 프로젝트 규칙으로 수정
- [ ] 동작 검증: 파일 저장 시 포매터 자동 실행 확인
- [ ] `.claude/` 디렉토리 Git에 커밋 (팀 공유)
