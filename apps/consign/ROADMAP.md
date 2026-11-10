# consign 단계 계획

위탁 판매 정산을 주제로 "서버 한 대 + 동기"에서 "여러 Pod + 비동기"로 옮겨 가며 깨지는 가정을 직접 확인한다. 코드·실행법은 [README.md](README.md), 과제는 [CATALOG.md](CATALOG.md), 기록은 [LOG.md](LOG.md).

| 단계 | 할 것 | 끝난 기준 | 상태 |
|---|---|---|---|
| 1. 비동기 API | 최신 FastAPI + Pydantic v2 + async SQLAlchemy/asyncpg 로 상품 등록·판매·정산 조회 | pytest-asyncio 통과 | ✅ 10-27 |
| 2. 블로킹 실험 | `async def` 안에 `time.sleep`·`requests` 를 넣은 버전과 고친 버전을 k6/JMeter 로 비교 | 지연·처리량 차이를 **직접 잰 수치**로 기록 | ⬜ 실수 카탈로그 #9 |
| 3. 서비스 분리 | 주문 / 정산 서비스 + Outbox + Redis Streams(또는 RabbitMQ). 중복 메시지 멱등 처리 | 같은 이벤트 2번에도 정산 1건 | 🟡 10-27 골격 구축 — 실수 카탈로그 #2~8 남음 |
| 3b. 브로커 교체 | Redis Streams 자리에 RabbitMQ(aio-pika)를 넣고 같은 실수(#4~6)를 RabbitMQ 방식으로 다시 막는다. exchange·routing key·manual ack·prefetch·DLX | 실수 카탈로그 #16~18 재현과 해결, Redis Streams 와 비교표 | 🟡 11-10 1단계: `BROKER` 스위치·발행·manual ack 소비 — 카탈로그 #16~18 남음 |
| 4. 로컬 k8s | kind/k3d 배포, probe·graceful shutdown·정산 CronJob·HPA | 롤링 배포 중 부하에서 실패 요청 0, 마이그레이션 expand/contract | 🟡 10-27 kind 배포·probe·preStop — 실수 카탈로그 #10~12 남음 |
| 5. 자동화 | GitHub Actions 테스트 → 이미지 빌드 → 5a·5b 로 kind 에 반영. OpenTelemetry 로 서비스 간 trace | push 한 번에 kind 까지 반영 | ⬜ |
| 5a. Helm | kustomize 매니페스트를 Helm 차트로 옮기고 `values-local.yaml`·`values-dev.yaml` 로 환경을 나눈다. upgrade·rollback | 실수 카탈로그 #20, `helm rollback` 으로 이전 리비전 복구 | ⬜ |
| 5b. Argo CD | kind 에 Argo CD 를 설치하고 manifest 저장소 커밋으로 배포한다. 자동 sync·self-heal·수동 sync·revert 롤백 | 실수 카탈로그 #21, 커밋 하나로 배포와 롤백 | ⬜ |

3b·5a·5b 는 회사 구조(RabbitMQ·Helm·Argo CD)에 맞춰 더한 단계다 (2026-11-10).

consign 은 k8s·여러 Pod 실험을 맡는다. 재시도·DLQ·스키마 버전은 [apps/order-flow](../order-flow/README.md) 가 기준 구현이고 3b 는 그 구현과 비교하며 진행한다 (2026-11-10).

1~2단계를 먼저 끝낸다. 3~5는 실제 운영 구조를 본 뒤 맞춘다.

**과제는 [CATALOG.md](CATALOG.md) 로 한다** (2026-10-28 정함): 위탁 정산에서 실제로 터질 실수만, 콘솔에서 증상과 해결이 보이게, GitHub·공식 문서의 표준 구현을 먼저 읽고 비교한다.
