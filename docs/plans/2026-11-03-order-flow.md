# Order Flow 구현 계획 및 진행 결과

**목표:** async FastAPI/SQLAlchemy, Transactional Outbox, RabbitMQ와 Avro, Celery, 멱등성을 한 주문 처리 앱에서 실습한다.

**구조:** `apps/order-flow/`는 독립 Compose 프로젝트다. API, relay, consumer, Celery worker는 같은 Python 앱의 서로 다른 프로세스이며 MySQL과 RabbitMQ는 이 앱 전용 컨테이너와 볼륨을 사용한다.

## 구현 단위

### 1. 독립 실행 환경

- [x] 앱 전용 패키지와 Dockerfile 구성
- [x] 루트 스택과 충돌하지 않는 포트 및 별도 DB volume 설정
- [x] MySQL, RabbitMQ health check 및 API health endpoint 구성

### 2. Async 주문 API와 요청 멱등성

- [x] 요청별 `AsyncSession`과 Alembic 스키마 구성
- [x] 주문·Idempotency-Key 응답·Outbox 이벤트를 하나의 트랜잭션으로 저장
- [x] 동일 키/동일 본문 재요청은 기존 응답, 다른 본문은 `409` 반환
- [x] API 저장과 요청 키 시나리오 테스트

### 3. Avro 이벤트와 Outbox relay

- [x] `OrderCreated` v1/v2 스키마와 v1→v2 reader 호환 테스트 추가
- [x] 미발행 행을 잠그고 persistent message를 발행
- [x] Publisher confirm 뒤에만 Outbox 상태 갱신
- [x] RabbitMQ에서 확인 가능한 durable exchange와 두 queue 구성

### 4. RabbitMQ consumer와 Inbox 멱등성

- [x] `orders.audit`, `orders.receipts` 독립 큐를 topic exchange에 binding
- [x] `(consumer_name, message_id)` unique key로 중복 전달 방지
- [x] 처리 성공 후 ack하고 예외 시 재전달하는 consumer 흐름 구성
- [x] 한 이벤트가 두 consumer에 각각 기록되는 테스트 추가

### 5. Celery receipt task

- [x] `orders.receipts` consumer에서 task 발행
- [x] `order.tasks` queue를 듣는 worker를 별도 컨테이너로 실행
- [x] `order_id` 기준 영수증 기록 멱등성 및 task retry/late-ack 정책 구성
- [x] 실제 Compose 주문 흐름 및 같은 task 재실행에서 receipt row 한 건 확인

### 6. 문서와 최종 검증

- [x] Order Flow 가이드에 흐름도, 실행·확인 방법, 요청/SQL 예시와 알려진 한계 기록
- [x] 루트 README 및 study 문서에서 실행 앱과 학습 체크리스트 연결
- [x] 설계 문서와 구현 결과를 현재 동작에 맞게 정리
- [x] 단위 테스트, Ruff, Compose 구성을 검증하고 컨테이너 end-to-end 확인

## 학습 단계에서 직접 확인할 항목

코드와 실행 환경이 준비되어도 학습 항목이 자동으로 완료되는 것은 아니다. 아래는 사용자가 직접 결과를 확인하고 설명한 뒤 체크할 수 있다.

- RabbitMQ consumer 처리 실패와 재전달, DLQ 확장 설계
- relay가 confirm 직후 종료될 때 재발행과 Inbox 중복 방지
- Inbox commit과 Celery enqueue 사이 장애 및 task-dispatch Outbox 필요성
- Avro 스키마 호환성 및 Celery broker/retry/ack 설정의 운영상 의미
