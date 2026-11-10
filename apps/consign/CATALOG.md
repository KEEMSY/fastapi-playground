# 실수 카탈로그 — 위탁 정산에서 실제로 터지는 문제를 화면에서 깨 보고 고친다

코드·실행법은 [README.md](README.md), 학습 목록은 [study/README.md](../../study/README.md).

원칙 (2026-10-28 정함)
- **비즈니스 로직에서 실제로 마주칠 실수**만 다룬다. 인프라 연습도 "그래서 판매자 정산이 어떻게 틀어지나"로 끝맺는다
- **콘솔에서 보여야 한다.** 과제마다 ① 실수를 켜는 스위치(환경변수나 `/ops/faults`) ② 콘솔의 어느 칸에 어떤 증상이 보이는지 ③ 고친 뒤 그 칸이 어떻게 바뀌는지를 정해 두고 시작한다
- **표준을 먼저 찾아 읽는다.** 아래 참고는 GitHub·공식 문서 중 2026-10-28에 존재를 확인한 것이다. 직접 만들기 전에 그 구현과 비교한다

| # | 상황 → 실수 | 판매자에게 생기는 일 | 콘솔에서 보이는 증상 | 고치는 법 | 표준 참고 | 상태 |
|---|---|---|---|---|---|---|
| 1 | 같은 상품에 동시 구매 → SELECT 후 UPDATE | 한 물건이 두 번 팔림, 정산 2건 | ② 동시 20건: 201 이 2건 이상 또는 500 | 조건부 `UPDATE … WHERE status='ON_SALE' RETURNING` + unique | — (돌연변이 테스트로 확인) | ✅ |
| 2 | 응답이 끊겨 앱이 판매를 **재시도** | 첫 요청은 성공했는데 재시도가 409 → 구매자는 실패로 보고 다시 결제 시도 | ⑤ 같은 판매에 201 다음 409 | `Idempotency-Key` 헤더, 키별 첫 응답을 저장해 재시도엔 같은 응답 | [Stripe 멱등 요청](https://docs.stripe.com/idempotency) · [brandur: Postgres 로 Stripe식 멱등 키](https://brandur.org/idempotency-keys) · [brandur/rocket-rides-atomic](https://github.com/brandur/rocket-rides-atomic) | ⬜ |
| 3 | 판매 커밋 뒤 Redis 에 **직접** 발행, 발행 실패 (이중 쓰기) | 팔렸는데 정산이 영원히 안 옴 | ④ "따라잡는 중"이 끝나지 않음, ⓪ ③ 선에 점이 안 흐름 | Transactional Outbox (지금 구조) — 스위치로 직접 발행판을 켜 비교 | [microservices.io 를 따라 만든 relay 예제 bakhoraliev/message-relay](https://github.com/bakhoraliev/message-relay) · [DBOS outbox 예제](https://github.com/dbos-inc/dbos-demo-apps) | 🟡 고친 쪽만 있음 |
| 4 | 같은 이벤트가 두 번 도착 (at-least-once) | 정산이 두 번 잡힘 | ④ settlement 합계 > consign 합계 | 소비자 멱등: `sale_id` PK + `ON CONFLICT DO NOTHING` | 위 outbox 예제들의 소비자 쪽 | 🟡 방어만 있음 — 중복을 일부러 만들어 볼 것 |
| 5 | 정산 Pod 가 처리 중에 죽음 | 그 판매의 정산이 무기한 대기 | ③ 회색 소비자에 pending 이 남음, ④ "따라잡는 중" 고정 | `XAUTOCLAIM` 으로 오래된 pending 회수 | [Redis 공식: redis-py 스트리밍](https://redis.io/docs/latest/develop/use-cases/streaming/redis-py/) | ⬜ |
| 6 | 깨진 이벤트(독 메시지)를 계속 재시도 | 그 건은 영원히 실패, 로그만 쌓임 | ③ 같은 pending 이 계속 회수됐다 실패 | 배달 횟수 상한 → dead-letter 스트림으로 옮기고 XACK | 위 Redis 공식 문서 (deletedMessages·dead-letter 절) | ⬜ |
| 7 | 정산 서비스가 금액을 **다시 계산** (float·반올림 규칙 다름) | 1원씩 어긋남, 월말 대사에서 발견 | ④ 일치 대신 1원 차이 | 금액은 판매 시점에 한 곳에서 정수로 확정해 이벤트로 보낸다(지금 구조) | 표준 참고 미조사 | 🟡 고친 쪽만 있음 |
| 8 | 일마감 집계를 UTC 날짜로 묶음 | 밤 9시 이후(KST) 판매가 다음 날 정산으로 밀림 | 일별 정산 표에서 날짜가 하루 어긋남 | `AT TIME ZONE 'Asia/Seoul'` 로 묶기, CronJob `timeZone` | 표준 참고 미조사 | ⬜ (일별 표 필요) |
| 9 | `async def` 판매 API 안에 동기 호출(`time.sleep`·`requests`) | 판매 하나가 느리면 그 Pod 의 모든 요청이 멈춤 | ⑤ 상관없는 요청의 ms 까지 같이 튐 | `await` 가능한 라이브러리, 안 되면 `def` 또는 `to_thread` | [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) §async routes · [FastAPI 공식 async](https://fastapi.tiangolo.com/async/) | ⬜ |
| 10 | 배포 중 Pod 가 요청을 받다 꺼짐 (preStop 없음) | 배포할 때마다 결제 몇 건 실패 | `make deploy` 동안 ⑤ 에 실패 요청 | `preStop` sleep + SIGTERM 처리, grace period 예산 | [Kubernetes graceful shutdown 정리](https://jorijn.com/en/knowledge-base/kubernetes/troubleshooting/kubernetes-graceful-shutdown-sigterm-pod-termination/) | 🟡 preStop 있음 — 빼서 비교할 것 |
| 11 | 롤링 중 컬럼 이름 변경 | 구버전 Pod 가 500 → 그 사이 판매 실패 | ⑤ 500 | expand → 배포 → contract, Alembic | [ankane/strong_migrations](https://github.com/ankane/strong_migrations) 위험 작업 목록 (Rails 지만 목록이 표준) | ⬜ |
| 12 | 앱이 Postgres 보다 먼저 뜸 | 배포 직후 잠깐 판매 불가 | `make status` RESTARTS 2 | readiness + 시작 시 재시도 또는 initContainer | 표준 참고 미조사 | ⬜ |
| 13 | 판매가 몰릴 때(세일·라이브 직후) Outbox 를 폴링 relay 하나로 비움 | 판매는 1초 만에 끝났는데 정산 반영은 그 뒤로 밀림 — 량이 늘면 지연이 선형으로 커진다 | 콘솔 시나리오 「판매 1000건」 그래프: outbox 대기가 먼저 솟았다 내려오고 정산 미도착이 뒤따라 0 | 배치 크기·폴링 간격 조정, relay 를 Pod 마다 병렬(SKIP LOCKED, 지금 구조), 더 크면 CDC(Debezium outbox) | [microservices.io Polling publisher](https://microservices.io/patterns/data/polling-publisher.html) · [debezium/debezium](https://github.com/debezium/debezium) [Outbox Event Router](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html) | 🟡 관찰만 — 고친 판 없음 |
| 14 | 정산이 느리다고 **소비자 Pod 부터 늘림** | 비용만 늘고 정산 지연은 그대로 | 시나리오 「소비자 2→4」: 1.2s → 1.3s, 적체는 outbox 343 / Redis lag 30 (2026-10-29, 이 kind 클러스터) | 먼저 줄이 어디에 섰는지(outbox 대기 vs Redis lag) 보고 병목 단계를 늘린다 | [Redis Streams 공식 — 소비자 그룹](https://redis.io/docs/latest/develop/data-types/streams/) | ✅ 재현·판별 |
| 15 | 느린 쿼리(리포트·대사)를 판매와 같은 커넥션 풀에서 몰아 돌림 | 판매 API 가 풀 빈자리를 기다리며 수 초 지연, 더 길면 `QueuePool limit … reached` 타임아웃 | 시나리오 「커넥션 풀」: 300ms 쿼리 100개 → 가장 늦은 2,138ms(7번에 나눠 처리), 끼어든 `SELECT 1` 1,776ms | 동시 개수 제한(Semaphore)·별도 풀·읽기 복제본, `statement_timeout`, 짧은 `pool_timeout` 으로 빨리 실패. 풀 확대는 Pod 수 × 풀 ≤ `max_connections` 확인 → PgBouncer | [SQLAlchemy 커넥션 풀](https://docs.sqlalchemy.org/en/20/core/pooling.html) · [SQLAlchemy 오류: QueuePool limit](https://docs.sqlalchemy.org/en/20/errors.html) · [pgbouncer/pgbouncer](https://github.com/pgbouncer/pgbouncer) | 🟡 재현만 — 고친 판 없음 |
| 16 | 정산 소비자가 auto-ack 로 받고 처리 중에 Pod 가 죽음 (RabbitMQ) | 브로커는 전달이 끝났다고 보고 메시지를 지운다 → 그 판매의 정산이 영원히 없음 | ④ consign 합계 > settlement 합계에서 멈추고 따라잡지 않음 | manual ack, DB 커밋 뒤에 ack (Redis Streams 의 XACK 순서와 같다) | [RabbitMQ: Consumer Acknowledgements and Publisher Confirms](https://www.rabbitmq.com/docs/confirms) · [mosquito/aio-pika](https://github.com/mosquito/aio-pika) | ⬜ |
| 17 | prefetch 제한 없이 소비 (RabbitMQ) | 느린 Pod 하나가 메시지를 잔뜩 쥐고 있어 다른 Pod 는 놀고 정산은 밀림. 그 Pod 가 죽으면 쥐고 있던 메시지가 한꺼번에 재전달 | ③ 소비자별 unacked 수가 한쪽으로 쏠림 | `basic_qos(prefetch_count=N)`. N 을 바꿔 가며 처리량과 쏠림을 잰다 | [RabbitMQ: Consumer Prefetch](https://www.rabbitmq.com/docs/consumer-prefetch) | ⬜ |
| 18 | 처리 실패를 바로 `nack(requeue=True)` (RabbitMQ) | 깨진 이벤트 하나가 큐 앞에서 끝없이 돌고 정산 서비스 CPU 만 쓴다. 일시 오류도 쉴 틈 없이 재시도 | ③ 같은 메시지의 재전달 횟수만 계속 늘어남 | 일시 오류는 TTL 대기 큐 + DLX 로 지연 재시도. 재시도 횟수(`x-death`)가 상한을 넘거나 영구 오류면 dead-letter 큐로. Redis Streams 판 #6 과 비교 | [RabbitMQ: Dead Letter Exchanges](https://www.rabbitmq.com/docs/dlx) · [RabbitMQ: TTL](https://www.rabbitmq.com/docs/ttl) · [RabbitMQ: Quorum Queues](https://www.rabbitmq.com/docs/quorum-queues) (배달 횟수 상한) | ⬜ |
| 19 | 판매 이벤트의 필드 이름을 바꾸고(`settlement_amount` → `payout_amount`) consign 을 먼저 배포 | 구버전 settlement 가 `KeyError` 로 실패 → 롤링 동안 들어온 판매의 정산이 멈춤 | ③ pending·재시도 증가, ④ "따라잡는 중" 고정 | 이벤트도 expand/contract: 새 필드를 더하기만 하고 소비자를 먼저 배포한 뒤 옛 필드를 뺀다. 이벤트에 `schema_version` | [Avro 명세: Schema Resolution](https://avro.apache.org/docs/1.12.0/specification/) · [Confluent: Schema Evolution and Compatibility](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html) | ⬜ |
| 20 | 환경마다 다른 값(replicas·리소스·DB 주소)을 매니페스트 한 벌에 박아 두고 손으로 고쳐 배포 | dev 설정이 다른 환경에 그대로 나가 정산 Pod 가 모자라거나 엉뚱한 DB 를 본다 | `make status` 의 replicas·환경변수가 의도와 다름 | Helm 차트 + `values-local.yaml`·`values-dev.yaml`, `helm template` 으로 렌더링 결과 비교, 잘못 나가면 `helm rollback` | [Helm: Values Files](https://helm.sh/docs/chart_template_guide/values_files/) | ⬜ |
| 21 | 장애 중에 급해서 `kubectl edit`·`scale` 로 클러스터를 직접 고침 | self-heal 이 켜져 있으면 Argo CD 가 몇 분 뒤 되돌려 같은 장애가 다시 난다. 꺼져 있으면 Git 과 클러스터가 어긋난 채 남는다 | Argo CD 화면 OutOfSync → Synced, settlement replicas 가 원래대로 돌아감 | 수정은 Git 커밋으로만, 롤백은 `git revert`. 자동 sync 와 수동 sync 를 언제 쓰는지 정리 | [Argo CD: Automated Sync Policy](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/) · [argoproj/argocd-example-apps](https://github.com/argoproj/argocd-example-apps) | ⬜ |

나중에(사내 구조를 본 뒤): Pod 늘릴 때 `max_connections` 초과(HPA × 풀), 일마감 CronJob 겹침(`concurrencyPolicy`), 취소 이벤트가 판매 이벤트보다 먼저 도착하는 순서 역전.

#16~18 은 3b(RabbitMQ), #19 는 회사 구조(이벤트 스키마·소비자 먼저 배포), #20~21 은 5a·5b 단계 과제다. 참고 링크는 2026-11-10 에 존재를 확인했다.

#16~19 의 메시징 패턴은 [apps/order-flow](../order-flow/README.md) 에 먼저 구현돼 있다(소비자별 지연 재시도 큐·DLQ, `schema-version` 헤더). consign 에서는 같은 실수를 여러 Pod·k8s 환경에서 재현하고 고친 판은 order-flow 구현과 비교한다.
