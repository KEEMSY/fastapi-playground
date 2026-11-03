# ③ 이벤트 vs 작업큐

## 목표
같은 요구사항을 보고 Celery task로 처리할지 도메인 이벤트로 발행할지 근거를 갖고 판단할 수 있고, RabbitMQ와 Avro의 기본 운영 개념을 이해한다.

## 핵심 비교

| | 작업큐 (Celery) | 이벤트 (RabbitMQ + Avro) |
|---|---|---|
| 의미 | "이걸 해라" (Command) | "이런 일이 일어났다" (Fact) |
| 소비자 | 보통 1종류 | 여러 서비스가 각자 구독 (fan-out) |
| 결합도 | 발행자가 누가 처리할지 앎 | 발행자는 누가 받는지 모름 |
| 실패 책임 | 발행자가 결과를 신경 씀 | 각 소비자가 책임짐 |
| 예시 | 이메일 발송, 리포트 생성 | `OrderCreated`, `UserSignedUp` |

## 학습 체크리스트

### 개념: RabbitMQ
- [ ] exchange, queue, binding, routing key
- [ ] exchange 타입: direct / topic / fanout / headers
- [ ] 소비자(서비스)별 queue를 두는 이유
- [ ] `ack` / `nack` / `reject`, `prefetch_count`
- [ ] DLX(Dead Letter Exchange)와 재시도 큐 설계
- [ ] durable queue, persistent message, publisher confirms

### 개념: Celery
- [ ] broker와 result backend의 역할
- [ ] `acks_late`, `task_reject_on_worker_lost`
- [ ] `autoretry_for`, `retry_backoff`, `max_retries`
- [ ] 워커 동시성 모델(prefork, gevent 등)과 `prefetch_multiplier`
- [ ] k8s에서 워커 종료(SIGTERM) 시 처리 중이던 작업은 어떻게 되는가

### 개념: Avro
- [ ] 스키마 정의와 직렬화/역직렬화 (`fastavro`)
- [ ] 스키마 진화: backward / forward / full 호환
- [ ] 필드 추가·삭제·이름 변경 시 지켜야 할 규칙 (default 값의 역할)
- [ ] 스키마를 어디서 관리하고 버전을 어떻게 붙이는가

### 실습
- [ ] 루트 `docker-compose.yml`에 `rabbitmq:3-management` 추가
- [ ] Celery 워커 서비스 추가, 간단한 task 실행
- [ ] 같은 기능(예: 답변 등록 후 후처리)을 Celery task 방식과 이벤트 발행 방식으로 각각 구현
- [ ] topic exchange 하나에 consumer 두 개를 붙여 fan-out 확인
- [ ] Avro 스키마로 이벤트를 직렬화하고, 필드를 추가한 v2 스키마로 v1 메시지 읽어보기
- [ ] consumer에서 예외를 내 DLQ로 가는지 확인

## 설명할 수 있어야 할 질문
1. "회원가입 후 환영 메일 발송"은 task인가, 이벤트인가? 둘 다라면 어떻게 나누는가?
2. Celery도 RabbitMQ를 broker로 쓰는데, 그럼 Celery와 직접 RabbitMQ 이벤트를 쓰는 것의 차이는?
3. consumer가 메시지를 처리하던 중 Pod가 죽으면 그 메시지는 어떻게 되는가?
4. Avro 스키마에 필수 필드를 추가하면 어떤 문제가 생기는가?

## 내 판단 기준 정리


## 노트


## 참고 자료
- RabbitMQ 공식 튜토리얼 (Python, 1~5번)
- Celery 문서: Tasks, Optimizing
- Apache Avro 명세: Schema Resolution
