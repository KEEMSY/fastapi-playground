# Order Flow 학습 커리큘럼 설계

## 목표

`apps/order-flow`의 현재 구현을 학습자가 복습하고 설명할 수 있게 정리한 다음, 신뢰성 보강을 한 단계씩 추가한다. 각 완료 단계는 실행 가능한 확인 항목과 학습 노트를 포함하고, 독립된 Git 커밋으로 남긴다.

## 학습 원칙

- 구현 전에 현재 코드를 읽고 실제 데이터 흐름을 먼저 복습한다.
- 각 단계는 개념, 실패 시나리오, 코드 변경, 직접 확인할 방법, 복습 질문으로 구성한다.
- 한 단계의 변경과 문서만 검증한 뒤 커밋한다. 다음 단계는 이전 커밋 위에 쌓는다.
- 학습 완료는 코드 작성만으로 처리하지 않는다. 직접 설명하거나 실습 결과를 확인할 수 있도록 체크리스트를 둔다.

## 단계

### 0. 현재 시스템 복습

현재 동작을 바꾸지 않고 주문 API부터 receipt 저장까지의 요청, DB 트랜잭션, Outbox, RabbitMQ fan-out, Inbox, Celery 흐름을 학습 가이드로 기록한다. 각 테이블과 프로세스의 책임, 멱등성 키, 재전달 시나리오, 현재 dual-write 한계를 정리한다. 로컬 Compose 실행과 SQL 조회, 복습 질문 및 체크리스트를 제공한다.

### 1. Celery 제출을 위한 Task Outbox

`orders.receipts` consumer가 Inbox와 task-dispatch Outbox를 같은 DB 트랜잭션에서 기록하도록 한다. 별도 dispatcher가 pending task-outbox 행을 Celery broker에 제출하고 제출 상태를 갱신한다. dispatcher가 broker 수락 뒤 DB 갱신 전에 종료되면 같은 task가 다시 제출될 수 있으므로 at-least-once 전달을 명시하고, 결정적인 task ID와 기존 `order_id` 멱등성으로 효과 중복을 막는다. 이 단계는 기존 RabbitMQ domain-event Outbox와 task command Outbox의 역할 차이를 학습한다.

### 2. 주문 처리 상태와 요청 추적

주문 ID로 주문, 이벤트 발행, consumer 처리, 영수증 생성을 확인하는 읽기 전용 상태 조회를 추가한다. 기존 데이터 모델의 상태를 과도하게 중복 저장하지 않고, 관련 레코드로부터 현재 단계를 조합한다. 로그에 order ID, event ID, task ID를 연결해 장애 지점을 찾는다.

### 3. Consumer 재시도와 DLQ 복구

무한 재전달이 아닌 제한된 재시도와 dead-letter 경로를 설계한다. 일시 오류와 영구 오류를 구분하고, 실패 메시지 보관·관찰·수동 재처리 절차를 로컬 Compose에서 확인한다. 정상 처리와 중복 억제 흐름이 유지되도록 한다.

### 4. Avro 이벤트 스키마 진화

현재 v1/v2 스키마와 reader 호환 테스트를 복습한다. 호환성 규칙과 필드 추가 기본값, producer/consumer 배포 순서를 문서화하고 자동화된 계약 테스트로 확인한다.

## 주요 설계 결정

- 학습 문서는 `apps/order-flow/README.md`를 실행 안내로 유지하고, 상세 복습·실습은 `apps/order-flow/LEARNING_GUIDE.md`에 둔다.
- 단계 진행 현황은 학습 가이드 체크리스트와 `docs/plans` 구현 기록에 남긴다.
- 각 기능은 해당 단계의 코드, 마이그레이션, 테스트 및 학습 설명을 한 커밋에 포함한다.
- Task Outbox 전송은 at-least-once다. 외부 broker와 DB 사이에서 exactly-once를 주장하지 않는다.
- 필요 이상으로 루트 API/Web 스택을 변경하지 않는다.

## 완료 기준

- 학습자가 현재 흐름과 각 DB 테이블의 역할을 설명할 수 있는 복습 자료가 있다.
- Task Outbox를 포함한 각 기능 단계가 별도 커밋으로 기록된다.
- 각 단계에 자동화 검증 및 사용자가 직접 실행할 확인 방법이 있다.
- 문서의 보장 범위가 실제 코드 및 메시지 전달의 장애 구간과 일치한다.
