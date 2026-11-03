# Order Flow 학습 프로젝트 설계

## 목적

`study/01`부터 `study/04`까지의 개념을 하나의 주문 처리 흐름에서 관찰한다. 기존 `apps/api`, `apps/web`, 루트 Compose 스택은 유지하고 실행 실습은 독립 앱 `apps/order-flow/`에서 제공한다. 구현 완료를 학습 완료로 간주하지 않으며, 각 체크리스트는 직접 실행하고 설명할 수 있을 때 완료한다.

## 구조

`apps/order-flow/compose.yaml`은 API, Outbox relay, RabbitMQ consumer, Celery worker, MySQL, RabbitMQ를 각각 별도 컨테이너로 실행한다. API와 worker 프로세스는 같은 Python 패키지를 사용하지만 실행 역할과 broker 경로는 분리한다. Avro 스키마는 앱 내부 `schemas/` 디렉터리에서 관리한다.

## 주요 흐름

1. `POST /orders`는 필수 `Idempotency-Key`와 JSON 본문을 검증한다. 주문, 동일 요청의 재생 응답, Outbox 이벤트를 하나의 비동기 DB 트랜잭션에 저장한다. 같은 키와 같은 본문은 기존 응답을 돌려주며, 같은 키의 다른 본문은 `409`를 반환한다.
2. Outbox relay는 미발행 행을 `FOR UPDATE SKIP LOCKED`로 가져와 Avro 이벤트를 RabbitMQ topic exchange에 persistent message로 발행한다. Publisher confirm 이후에만 행을 `published`로 갱신한다.
3. `orders.audit`와 `orders.receipts`는 같은 이벤트를 독립적으로 받는다. 각 consumer는 `(consumer_name, message_id)` Inbox 고유 키를 기록하고, 기록이 끝난 뒤 메시지를 ack한다.
4. 새 `orders.receipts` 이벤트는 Celery의 `order.tasks` queue에 receipt command를 보낸다. worker는 `order_id`를 고유 키로 영수증 기록을 저장하고, late ack와 backoff retry를 사용한다.

## 보장 범위와 실패 구간

Outbox relay는 RabbitMQ confirm을 받았으나 MySQL 상태 갱신 전에 종료될 경우 이벤트를 다시 발행할 수 있다. consumer Inbox 키와 receipt primary key는 각 단계의 중복 효과를 막는다.

Inbox 트랜잭션과 Celery task 발행은 하나의 원자적 트랜잭션이 아니다. consumer가 Inbox를 커밋한 직후 Celery 발행 전에 종료되면 task가 누락될 수 있다. 현재 실습은 이 dual-write 한계를 의도적으로 드러내며, task-dispatch Outbox를 확장 과제로 남긴다. Compose에는 consumer 실패 메시지를 위한 DLQ를 구성하지 않았으므로 DLQ 실습도 후속 과제다.

## 확인 방법

독립 Compose 스택에서 API 응답과 요청 키 재사용을 확인하고, RabbitMQ 관리 화면에서 exchange, bindings, queue, consumer를 본다. MySQL의 `orders`, `outbox_events`, `processed_messages`, `order_receipts` 행을 주문 ID와 이벤트 ID로 연결해 결과를 확인한다. Celery worker 로그에서 receipt task 성공 및 중복 실행 결과를 확인한다. 앱 README에 실행 명령, 요청 예시, SQL, 제한사항을 기록한다.

## 범위 밖

기존 API와 웹 앱의 모노레포 구조를 다시 바꾸거나, Kubernetes/Helm/Terraform/Jenkins/ArgoCD 구성까지 복제하지 않는다. 이번 앱은 로컬에서 async DB, 이벤트 전달, 작업큐, 멱등성과 실패 구간을 학습하는 데 집중한다.
