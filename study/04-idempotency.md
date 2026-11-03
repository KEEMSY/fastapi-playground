# ④ 메시지 발행 멱등성 설계

## 목표
"메시지는 중복되거나 유실될 수 있다"는 전제에서 발행 측과 소비 측 모두 안전한 구조를 설계하고, 실패 시나리오를 테스트로 검증할 수 있다.

## 학습 체크리스트

### 개념
- [ ] 전달 보장 수준: at-most-once / at-least-once / exactly-once (그리고 exactly-once가 사실상 어려운 이유)
- [ ] **Dual write 문제**: DB 커밋과 메시지 발행이 원자적이지 않음
  - 커밋 성공 → 발행 실패: 이벤트 유실
  - 발행 성공 → 커밋 실패: 존재하지 않는 데이터에 대한 이벤트
- [ ] **Transactional Outbox 패턴**: 같은 트랜잭션에서 outbox 테이블에 저장하고 relay가 발행
- [ ] Outbox relay 방식: polling vs CDC(Debezium 등)
- [ ] relay가 발행 후 상태 업데이트 전에 죽으면 → 중복 발행 → 그래서 consumer 멱등성이 필요함
- [ ] **Consumer 멱등성**
  - Inbox / processed_message 테이블 (`message_id` unique 제약)
  - 비즈니스 로직과 processed 기록을 같은 트랜잭션에 넣기
  - 상태 전이 체크 (이미 `PAID`면 무시)
  - upsert / 조건부 업데이트
- [ ] 메시지 순서 보장 문제와 대응 (버전 필드, 단일 consumer 등)
- [ ] RabbitMQ publisher confirms와 mandatory flag
- [ ] **API 레벨 멱등성**: `Idempotency-Key` 헤더 + Redis/DB 저장, 처리 중 상태 처리
- [ ] Celery task 멱등성: `acks_late` 환경에서 같은 task가 두 번 실행될 때

### 실습
- [ ] Alembic 마이그레이션으로 `outbox` 테이블 추가 (id, aggregate_type, aggregate_id, event_type, payload, status, created_at)
- [ ] 도메인 로직 + outbox insert를 한 트랜잭션으로 묶기
- [ ] outbox relay 워커 구현 (polling, `SELECT ... FOR UPDATE SKIP LOCKED`)
- [ ] consumer에 `processed_message` 테이블 기반 중복 처리 방지 구현
- [ ] pytest로 실패 시나리오 검증
  - [ ] 같은 메시지를 두 번 보내도 결과가 한 번만 반영되는지
  - [ ] relay가 발행 직후 죽는 상황을 흉내 내도 최종 상태가 맞는지
  - [ ] consumer 처리 중 예외 발생 시 롤백 및 재처리되는지
- [ ] `Idempotency-Key` 기반 POST API 구현

### Order Flow Lab 진행

- [ ] 같은 `Idempotency-Key`와 같은 본문으로 재요청해 동일 응답 확인
- [ ] 같은 키에 다른 본문을 보내 `409` 확인
- [ ] 주문 row와 Outbox row가 함께 저장되는지 확인
- [ ] Outbox relay 재시작 후 중복 발행 가능성과 consumer의 `processed_messages` 중복 방지 확인
- [ ] 같은 consumer queue에서 동일 이벤트를 재전달해도 Inbox 기록이 한 건인지 확인
- [ ] 서로 다른 consumer 두 개가 같은 `message_id`를 각각 기록하는 이유 설명
- [ ] Celery task를 같은 주문 ID로 여러 번 실행해도 `order_receipts` row가 한 건인지 확인
- [ ] Inbox 기록 이후 Celery 발행 전에 장애가 나면 작업이 누락될 수 있는 dual-write 구간을 설명

요청 키 재사용은 수량 누적을 뜻하지 않는다. 같은 키와 같은 요청은 같은 주문 응답을 재생하며, 별도 주문은 별도 키가 필요하다. 한 주문의 수량 변경은 별도의 API 동작으로 구현해야 한다.

## 실패 시나리오 표 (직접 채우기)

| 시점 | 장애 | 결과 | 대응 |
|------|------|------|------|
| DB 커밋 직후, 발행 전 | API Pod OOMKilled | | |
| relay 발행 후, status 업데이트 전 | relay 재시작 | | |
| consumer 처리 후, ack 전 | consumer Pod 종료 | | |
| consumer 처리 중 | DB 일시 장애 | | |
| 클라이언트 | 타임아웃 후 재요청 | | |

## 설명할 수 있어야 할 질문
1. outbox 패턴을 써도 consumer 멱등성이 여전히 필요한 이유는?
2. `processed_message` 체크를 비즈니스 로직과 다른 트랜잭션에서 하면 어떤 문제가 생기는가?
3. outbox 테이블이 계속 커지면 어떻게 관리하는가?
4. 멱등 키는 누가 만들어야 하는가? (클라이언트, 발행자, 메시지 브로커)

## 내 설계안


## 노트


## 참고 자료
- microservices.io: Transactional Outbox, Idempotent Consumer
- Stripe API 문서: Idempotent Requests
