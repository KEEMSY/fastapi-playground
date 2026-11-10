# MSA — 서비스 분리와 메시지

[study/README.md](./README.md) 의 한 주제. 실습은 [apps/consign](../apps/consign/README.md)(판매 / 정산 2서비스 + Outbox + Redis Stream), 과제는 [CATALOG.md](../apps/consign/CATALOG.md) #2~8·#13~14.

- 통신: 동기 HTTP vs 비동기 메시지
- 분산 트랜잭션: **Outbox**(DB 쓰기와 메시지 발행을 원자적으로) · **Saga**(보상 트랜잭션)
- 메시지는 at-least-once → **소비자 멱등 처리**. 중복 결제 방지와 같은 사고방식
- 분산 추적: OpenTelemetry, trace ID 를 서비스 경계 너머로

## 자료

- microservices.io — Transactional Outbox, Saga
