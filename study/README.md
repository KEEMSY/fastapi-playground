# 입사 전 학습 플랜

> 회사 스택: FastAPI / Pydantic · Celery · RabbitMQ + Avro · Docker / k8s / Helm / Terraform · Jenkins / ArgoCD
>
> 요청받은 학습 범위: **async/await**, **비동기 DB 세션 관리**, **이벤트 vs 작업큐 역할 차이**, **메시지 발행 멱등성 설계**

## 학습 순서

다음 실습은 빠진 hands-on 항목을 보완하기 위해 **Avro부터** 시작한다. 그 뒤 기존 async/DB 학습을 이어가고, RabbitMQ·Celery·멱등성 실습을 통합한다.

```
⓪ Avro  →  ① async/await  →  ② 비동기 DB 세션  →  ③ 이벤트 vs 작업큐  →  ④ 멱등성 설계
 (바이너리·스키마) (런타임 이해) (리소스·트랜잭션)     (메시징 구조)          (앞 단계를 합친 문제)
```

Avro 실습: [`study/labs/avro/`](./labs/avro/README.md). Order Flow의 Avro 구현과 별도로, 학습자가 직렬화와 Reader/Writer Schema 해석을 직접 완성한다.

④는 "DB 커밋과 메시지 발행이 따로 실패할 수 있다"는 문제라서 ②와 ③을 먼저 알아야 합니다. 네 주제를 연결하는 실행 프로젝트는 [`apps/order-flow/`](../apps/order-flow/README.md)에 있으며, 기존 API·웹 스택과 별도 Compose로 실행합니다.

## 진행 현황

| # | 주제 | 예상 기간 | 상태 | 노트 |
|---|------|----------|------|------|
| 0 | Apache Avro | 1~2일 | ⬜ 실습 랩 준비됨 · 직접 구현 전 | [Avro Lab](./labs/avro/README.md) |
| 1 | async/await | 2~3일 | 🟨 실습 환경 준비됨 · 개념 확인 필요 | [01-async-await.md](./01-async-await.md) |
| 2 | 비동기 DB 세션 관리 | 3~4일 | 🟨 실습 환경 준비됨 · 세션 흐름 확인 필요 | [02-async-db-session.md](./02-async-db-session.md) |
| 3 | 이벤트 vs 작업큐 | 3~4일 | 🟨 이벤트와 Celery 경로 실행 가능 · 학습 중 | [03-event-vs-task-queue.md](./03-event-vs-task-queue.md) |
| 4 | 메시지 발행 멱등성 | 4~5일 | 🟨 API·Outbox·consumer·task 구현 · 장애 실습 남음 | [04-idempotency.md](./04-idempotency.md) |

상태 표기: ⬜ 시작 전 / 🟨 진행 중 / ✅ 완료

## 실행 프로젝트

- [Order Flow Lab](../apps/order-flow/README.md): 비동기 주문 API → Outbox → Avro/RabbitMQ → 멱등 consumer → Celery 작업
- [Consign Lab](../apps/consign/README.md): 위탁 판매 정산 2서비스(판매·정산). Outbox → Redis Streams 또는 RabbitMQ → 멱등 원장, kind 배포와 관찰용 콘솔. 서버 한 대에서 여러 Pod 로 옮길 때 깨지는 가정을 확인한다. 재시도·DLQ·Avro 같은 메시징 패턴은 Order Flow 를 기준 구현으로 삼는다.
- 기능 단위 권장 커밋 경계: `order API와 요청 멱등성`, `Avro와 Outbox relay`, `consumer 중복 처리`, `Celery 작업큐`, `학습 문서와 로컬 실행 안내`
- 구현 완료와 학습 완료를 구분한다. 체크리스트는 직접 실행하고 설명할 수 있을 때만 완료로 표시한다.
- 한 기능을 실행하고 결과를 기록한 뒤 시간을 두고 다음 기능으로 넘어간다. 진행 코드와 실습 명령은 Order Flow 가이드에서 확인한다.

## 진행 규칙

1. **질문부터 정한다**: 각 주제 파일에 있는 "설명할 수 있어야 할 질문"에 내 말로 답을 적을 수 있으면 완료로 본다.
2. **코드와 문서를 분리한다**: `study/`에는 학습 계획, 개념 정리, 결과 기록만 둔다. 실행 코드는 해당 앱 디렉터리(`apps/order-flow/`)에 두고, 문서에서 코드와 측정 결과를 링크한다.
3. **입사 후 비교한다**: 회사 코드를 설명 들은 뒤 "내 구현과 다른 점" 섹션을 채운다.

## 그 밖의 학습 주제

입사 전 플랜 밖에서 이어 온 주제다. 실행 코드는 `apps/` 아래에, 정리 문서는 `docs/` 또는 이 폴더에 둔다. 진행 기록은 실습 앱의 `LOG.md` 에 쓰고 이 표에는 상태만 고친다.

| 주제 | 상태 | 문서 | 코드 |
|---|---|---|---|
| FastAPI 기본 관례 (구조·Pydantic·의존성·설정·Alembic) | ✅ | [README.md](../apps/api/README.md) §1~18 | `apps/api/src/` · `apps/api/src/domains/standard` |
| 동기 vs 비동기 엔드포인트 성능 | ✅ | [fastapi-sync-async-performance.md](../docs/fastapi-sync-async-performance.md) | `apps/api/src/domains/sync_example` · `async_example` |
| 비동기 FastAPI 심화 (async DB·풀·외부 호출·Pydantic v2) | 🟨 | [async-fastapi.md](./async-fastapi.md) | [apps/consign](../apps/consign/README.md) |
| 동시성 (asyncio · threading · multiprocessing · 멀티 인스턴스) | 🟨 | — | `apps/api/src/domains/concurrency` |
| DB 세션 풀과 인스턴스 확장 | ✅ | [README_ANALYSIS.md](../performance_tests/README_ANALYSIS.md) · [STRATEGY_ANALYSIS_REPORT.md](../performance_tests/STRATEGY_ANALYSIS_REPORT.md) | `performance_tests/` · `docker-compose-perf-*.yml` |
| 실시간 알림 (SSE·폴링) | ✅ | [NOTIFICATION_SYSTEM.md](../docs/NOTIFICATION_SYSTEM.md) · [결정 가이드](../docs/NOTIFICATION_SYSTEM_DECISION_GUIDE.md) · [SSE 아키텍처](../docs/NOTIFICATION_SSE_ARCHITECTURE.md) · [SSE 가이드](../docs/SSE_COMPLETE_GUIDE.md) · [SSE 운영](../docs/SSE_OPERATIONS_GUIDE.md) · [폴링 비교](../docs/POLLING_COMPARISON.md) · [정직한 폴링 비교](../docs/HONEST_POLLING_COMPARISON.md) | `apps/api/src/domains/notification` |
| Redis 커리큘럼 | ✅ | [REDIS_CURRICULUM.md](../docs/REDIS_CURRICULUM.md) | `apps/api/src/domains/redis` |
| 배치 (BackgroundTasks vs APScheduler) | ✅ | [batch-tradeoffs.md](../docs/batch-tradeoffs.md) | `apps/api/src/domains/batch` |
| 스케줄러 (DB 관리 스케줄·작업 레지스트리) | 🟨 | — | `apps/api/src/domains/scheduler` |
| 운영 환경 구성 (단일 EC2) | ✅ | [PRODUCTION_SETUP_GUIDE.md](../docs/PRODUCTION_SETUP_GUIDE.md) | `docker-compose-prod.yml` · `nginx/` |
| 서버 한 대 → 여러 Pod 로 바뀔 때 깨지는 가정 | 🟨 | [single-to-multi-pod.md](./single-to-multi-pod.md) | [apps/consign](../apps/consign/README.md) |
| Kubernetes — 백엔드 개발자 몫 | 🟨 | [k8s-for-backend.md](./k8s-for-backend.md) | `apps/consign/k8s` |
| MSA — Outbox·멱등 소비자·Saga | 🟨 | [msa.md](./msa.md) | [apps/consign](../apps/consign/README.md) |
| 메시지 브로커 — RabbitMQ (ack·prefetch·DLX 지연 재시도) | ⬜ | [CATALOG.md](../apps/consign/CATALOG.md) #16~18 | [apps/consign](../apps/consign/README.md) 3b 단계 |
| 자동화 워크플로우 (CI/CD·Helm·GitOps) | ⬜ | [workflow-automation.md](./workflow-automation.md) | [apps/consign](../apps/consign/README.md) 5·5a·5b 단계 · CATALOG #20~21 |

## 입사 후 확인할 질문 (모아두기)

- [ ] 
