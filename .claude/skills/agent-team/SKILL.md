---
name: agent-team
description: This skill should be used when the user wants to execute a feature plan using the full agent team (staff engineer, senior developer, code reviewer, pessimistic reviewer, planner/tester, UI/UX designer, frontend developer). Triggers on: "에이전트 팀", "agent team", "팀으로 구현", "전체 팀 실행", "기획 구현해줘".
version: 1.0.0
---

# Agent Team Orchestrator

기획서를 받아 **7개 전문 에이전트 팀**이 협력하여 기능을 구현합니다.
각 에이전트는 자신의 전문 영역을 담당하며, 단계별로 산출물을 다음 에이전트에게 전달합니다.

## 팀 구성

| 에이전트 | 역할 | 산출물 |
|---------|------|--------|
| `staff-engineer` | 기술 설계 및 태스크 분해 | 기술 설계 문서, 태스크 목록 |
| `planner-tester` | 유스케이스 정의 및 테스트 작성 | 유스케이스, 테스트 코드 |
| `ui-ux-designer` | 화면 설계 및 인터랙션 정의 | 와이어프레임, 컴포넌트 스펙 |
| `senior-developer` | 백엔드 코드 구현 | 완성된 백엔드 코드 |
| `frontend-developer` | 프론트엔드 코드 구현 | 완성된 프론트엔드 코드 |
| `code-reviewer` | 전체 코드 품질 리뷰 | 품질 점수, 개선 사항 |
| `pessimistic-reviewer` | 잠재 문제 및 리스크 분석 | 위험 목록, P1/P2/P3 분류 |

## 실행 모드

### 모드 A: 전체 팀 실행 (기본)
모든 에이전트가 순서대로 실행됩니다.

### 모드 B: 백엔드만
staff-engineer → planner-tester → senior-developer → code-reviewer → pessimistic-reviewer

### 모드 C: 프론트엔드만
ui-ux-designer → frontend-developer → code-reviewer

### 모드 D: 리뷰만
code-reviewer + pessimistic-reviewer (병렬)

## 실행 플로우

### 시작 전: 기획 입력 확인

사용자가 기획을 전달하면 다음을 먼저 확인합니다:

```
1. 기획 범위: 백엔드만? 프론트엔드만? 풀스택?
2. 우선순위: MVP 범위가 있는가?
3. 기존 코드: 새 기능인가, 기존 기능 수정인가?
4. 제약 사항: 기술 스택, 마감 등
```

모호한 경우 AskUserQuestion으로 확인 후 진행합니다.

---

### Phase 1: 설계 (병렬 실행 가능)

**1-A: Staff Engineer — 기술 설계**

staff-engineer 에이전트를 호출합니다:
```
다음 기획을 분석하고 기술 설계 문서와 태스크 목록을 작성해주세요:

{기획 내용}
```

산출물 확인:
- [ ] 기술 설계 문서 (아키텍처, 데이터 모델, API 스펙)
- [ ] 태스크 목록 (Phase별 분류)
- [ ] 수용 기준 (Acceptance Criteria)

**1-B: Planner-Tester — 유스케이스 정의** (1-A와 병렬)

planner-tester 에이전트를 호출합니다:
```
다음 기획의 유스케이스를 정의하고 테스트 계획을 작성해주세요:

{기획 내용}
```

산출물 확인:
- [ ] 유스케이스 목록
- [ ] 테스트 매트릭스
- [ ] 테스트 코드 초안

**1-C: UI/UX Designer — 화면 설계** (UI 포함 기능인 경우)

ui-ux-designer 에이전트를 호출합니다:
```
다음 기획을 바탕으로 UI/UX를 설계해주세요:

{기획 내용}
{staff-engineer 산출물의 API 스펙}
```

산출물 확인:
- [ ] 사용자 여정 맵
- [ ] 화면별 와이어프레임
- [ ] 컴포넌트 스펙
- [ ] API 연동 스펙

---

### Phase 1 완료 체크포인트

사용자에게 Phase 1 결과를 요약하여 보고합니다:

```markdown
## Phase 1 완료: 설계

### Staff Engineer 결과
{핵심 설계 결정사항 요약}

### Planner-Tester 결과
{유스케이스 N개, 테스트 케이스 N개 식별}

### UI/UX Designer 결과 (해당 시)
{화면 N개, 컴포넌트 N개 설계}

---
다음 단계(구현)를 진행할까요?
변경이 필요한 부분이 있으면 말씀해 주세요.
```

**사용자 승인 후 Phase 2로 진행합니다.**

---

### Phase 2: 구현 (병렬 실행 가능)

**2-A: Senior Developer — 백엔드 구현**

senior-developer 에이전트를 호출합니다:
```
다음 설계 문서를 바탕으로 백엔드를 구현해주세요:

{staff-engineer 기술 설계 문서}
{planner-tester 유스케이스 및 테스트 계획}
```

구현 순서:
1. models.py (데이터 모델)
2. schemas.py (Pydantic 스키마)
3. service.py (비즈니스 로직)
4. router.py (API 엔드포인트)
5. main.py 라우터 등록
6. 테스트 코드

**2-B: Frontend Developer — 프론트엔드 구현** (2-A와 병렬, UI 기능인 경우)

frontend-developer 에이전트를 호출합니다:
```
다음 UI/UX 설계와 API 스펙을 바탕으로 프론트엔드를 구현해주세요:

{ui-ux-designer 설계 문서}
{staff-engineer API 스펙}
```

---

### Phase 3: 리뷰 (병렬 실행)

**3-A: Code Reviewer — 코드 품질 리뷰**

code-reviewer 에이전트를 호출합니다:
```
다음 구현된 코드를 전체적인 품질 관점에서 리뷰해주세요.
conventions.yaml 규칙을 기준으로 평가해 주세요.
```

**3-B: Pessimistic Reviewer — 리스크 분석** (3-A와 병렬)

pessimistic-reviewer 에이전트를 호출합니다:
```
다음 구현에서 발생할 수 있는 잠재적 문제와 리스크를 분석해주세요.
```

---

### Phase 4: 최종 보고

모든 에이전트 실행 완료 후 종합 보고서를 작성합니다:

```markdown
## 에이전트 팀 작업 완료 보고

### 구현 요약

#### 생성/수정된 파일
- {파일 목록}

#### API 엔드포인트
- {엔드포인트 목록}

---

### 코드 리뷰 결과 (code-reviewer)

| 영역 | 점수 |
|------|------|
| 가독성 | {N}/5 |
| 컨벤션 | {N}/5 |
| 견고성 | {N}/5 |
| 유지보수성 | {N}/5 |
| 성능 | {N}/5 |

**필수 수정 {N}건:**
{수정 필요 목록}

---

### 리스크 분석 결과 (pessimistic-reviewer)

- P1 (즉시 대응 필요): {N}건
- P2 (계획적 대응): {N}건
- P3 (모니터링): {N}건

**P1 위험 목록:**
{P1 목록}

---

### 테스트 현황 (planner-tester)

- 작성된 테스트: {N}개
- 커버리지: 정상/{에러}/{권한} 케이스

---

### 다음 단계 권고

1. **즉시**: {Code Reviewer P1 수정 사항}
2. **단기**: {Pessimistic Reviewer P1 리스크 대응}
3. **중기**: {P2 리스크 대응}

---

### 배포 준비 상태

- [ ] 코드 리뷰 필수 수정 완료
- [ ] P1 리스크 대응 완료
- [ ] DB 마이그레이션 준비 (`/db-migrate`)
- [ ] 테스트 통과 (`pytest tests/ -v`)
```

## 에이전트 호출 방식

각 Phase에서 에이전트를 호출할 때 Agent 도구를 사용합니다:

```
Agent(
  subagent_type="{agent-name}",
  description="{이 에이전트가 할 작업 요약}",
  prompt="{에이전트에게 전달할 전체 컨텍스트 + 지시사항}"
)
```

**컨텍스트 전달 원칙:**
- 이전 에이전트의 산출물을 다음 에이전트의 프롬프트에 포함합니다
- 기획 원문을 모든 에이전트에게 전달합니다
- 에이전트 간 결정사항은 명시적으로 전달합니다

## 사용 예시

```
사용자: /agent-team

아래 기획을 에이전트 팀에게 전달해서 구현해줘:

## 북마크 기능 기획

### 개요
사용자가 질문(Question)을 북마크로 저장할 수 있는 기능

### 기능 요구사항
1. 북마크 추가/제거 (토글 방식)
2. 내 북마크 목록 조회
3. 북마크 여부 표시 (목록/상세 화면)

### 기술 스택
- 백엔드: FastAPI (기존 프로젝트에 추가)
- 프론트엔드: React (기존 프로젝트에 추가)
```

→ 에이전트 팀이 Phase 1부터 순차 실행하여 구현합니다.

## 주의사항

1. 각 Phase 완료 후 **사용자 확인**을 받습니다 — 방향이 틀렸을 때 빠르게 수정합니다
2. 에이전트 산출물이 충돌할 경우 **staff-engineer 결정**을 따릅니다
3. 기획이 모호하면 실행 전 AskUserQuestion으로 명확화합니다
4. 각 에이전트는 **독립적으로 실행**됩니다 — 이전 에이전트의 코드를 직접 수정하지 않습니다
5. 컨텍스트가 커질 경우 **Agent 도구**를 사용하여 메인 컨텍스트를 보호합니다
