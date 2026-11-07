# Order Flow Learning Curriculum Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the existing Order Flow lab into a staged learning curriculum that first reviews current behavior, then adds reliability capabilities in individually verified and committed steps.

**Architecture:** Keep the isolated `apps/order-flow` app and add a learner-facing guide beside its operational README. Add a Task Outbox written atomically with each receipt Inbox record, then dispatch commands asynchronously with at-least-once semantics. Follow with derived order status and correlated logs, bounded consumer retries with a DLQ, and explicit Avro compatibility exercises.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy asyncio, Alembic, MySQL, RabbitMQ, Avro, Celery, pytest, Docker Compose.

---

## Commit checkpoints

1. `docs: 주문 이벤트 학습 커리큘럼 설계 기록` — design already committed as `cdc98b0`.
2. `docs: 주문 이벤트 현재 흐름 복습 자료 추가` — stage 0 learning guide.
3. `feature: 영수증 작업 전달에 Task Outbox 적용` — stage 1 schema, code, tests, exercise.
4. `feature: 주문 처리 상태 조회와 추적 정보 추가` — stage 2 API, logs, tests, exercise.
5. `feature: RabbitMQ consumer 재시도와 DLQ 구성` — stage 3 retry/DLQ, recovery guide and tests.
6. `docs: Avro 이벤트 스키마 진화 학습 단계 추가` — stage 4 compatibility rules and contract exercises/tests.

Every checkpoint must have a clean worktree after commit. Do not combine a later stage into an earlier commit.

## Task 0: Review existing flow and document it

**Files:**
- Create: `apps/order-flow/LEARNING_GUIDE.md`
- Modify: `apps/order-flow/README.md` (link the learning guide and mark learner-owned checklist items)

**Steps:**
1. Trace `api.py`, `models.py`, `relay.py`, `consumer.py`, `processing.py`, `dispatch.py`, `tasks.py`, `receipts.py`, and the existing tests.
2. Write a sequence diagram showing idempotency replay/conflict branches and asynchronous processing.
3. Explain each table (`orders`, `idempotency_records`, `outbox_events`, `processed_messages`, `order_receipts`), the process responsible for it, and each deduplication key.
4. Document local run commands, one request, SQL queries, expected observations, and failure-window exercises.
5. Add learner checkboxes and short recall questions; do not pre-check them.
6. Review every technical statement against current code and docs; run Markdown/link or repository checks if available.
7. Commit only the stage-0 documentation files.

## Task 1: Add durable task dispatch with a Task Outbox

**Files:**
- Modify: `apps/order-flow/src/order_flow/models.py`
- Create: `apps/order-flow/migrations/versions/0002_task_dispatch_outbox.py`
- Modify: `apps/order-flow/src/order_flow/dispatch.py`
- Create: `apps/order-flow/src/order_flow/task_relay.py`
- Modify: `apps/order-flow/src/order_flow/compose.yaml`
- Modify: `apps/order-flow/tests/test_consumer_dispatch.py`
- Create: `apps/order-flow/tests/test_task_relay.py`
- Modify: `apps/order-flow/LEARNING_GUIDE.md`
- Modify: `apps/order-flow/README.md`

**Steps:**
1. Write a failing test that a new receipt delivery stores both its Inbox row and one task-outbox row; a duplicate delivery stores neither a second Inbox nor a second task-outbox row.
2. Run the targeted test and confirm the missing model/table behavior causes failure.
3. Add a task-dispatch outbox model with unique event identity, order ID, pending/dispatched status, attempts, and timestamps; create an Alembic migration.
4. Change receipt dispatch to insert the task-outbox record in the same transaction as the Inbox record. Audit consumer behavior remains task-free.
5. Verify the targeted test passes and add assertions for atomic rollback or duplicate semantics.
6. Write failing relay tests for pending dispatch, successful status update, deterministic Celery task ID, and duplicate-safe retry after enqueue-before-status crash.
7. Implement a separate async task relay that submits a deterministic task ID and only marks a row dispatched after broker publish returns successfully. Document that this is at-least-once; task business effect remains idempotent by `order_id`.
8. Add the task relay process to Compose and ensure it starts after DB, broker, and API readiness.
9. Run targeted tests, the full order-flow suite, migration upgrade checks, and Compose config validation.
10. Add a learning exercise for stopping the relay around publish/status update and observing duplicate submission without duplicate receipt rows.
11. Commit only Task Outbox code, migration, tests, Compose, and relevant learning docs.

## Task 2: Add order status and correlated trace fields

**Files:**
- Modify: `apps/order-flow/src/order_flow/api.py`
- Modify: `apps/order-flow/src/order_flow/schemas.py`
- Modify: `apps/order-flow/src/order_flow/relay.py`
- Modify: `apps/order-flow/src/order_flow/consumer.py`
- Modify: `apps/order-flow/src/order_flow/task_relay.py`
- Modify: `apps/order-flow/src/order_flow/tasks.py`
- Create or modify: `apps/order-flow/tests/test_order_status.py`
- Modify: `apps/order-flow/LEARNING_GUIDE.md`

**Steps:**
1. Write failing API tests for unknown order (404) and existing order with pending/published/receipt-recorded stages.
2. Implement a read-only `GET /orders/{order_id}` status response derived from existing order, event, consumer, and receipt rows. Avoid storing redundant lifecycle states.
3. Add tests for partial progress states and final state.
4. Add structured log context carrying `order_id`, `event_id`/`message_id`, and deterministic `task_id` through the relay, consumer, and task boundaries.
5. Verify logs can be correlated for a single order and the full suite passes.
6. Document a status polling and log tracing exercise.
7. Commit this stage independently.

## Task 3: Bound consumer retries and route poison messages to a DLQ

**Files:**
- Modify: `apps/order-flow/src/order_flow/consumer.py`
- Modify: `apps/order-flow/compose.yaml`
- Modify: `apps/order-flow/tests/test_consumer.py`
- Modify: `apps/order-flow/LEARNING_GUIDE.md`
- Modify: `apps/order-flow/README.md`

**Steps:**
1. Define a bounded retry policy and dead-letter topology (retry delay queue with TTL, then a durable parking/DLQ queue); make limits configurable with safe local defaults.
2. Write tests for retry headers/attempt counts, successful redelivery, and dead-lettering after the configured maximum.
3. Implement explicit message rejection/routing so a poison event cannot requeue forever. Preserve manual ack after durable Inbox processing.
4. Declare durable queues/exchanges and bindings in consumer startup; ensure relay's domain-event bindings remain correct.
5. Validate topology through tests and `docker compose config`, then run an end-to-end failure exercise if Compose is available.
6. Document inspecting and manually replaying a DLQ message, including the duplicate-safety caveat.
7. Commit the DLQ stage independently.

## Task 4: Make Avro schema evolution rules explicit

**Files:**
- Modify: `apps/order-flow/src/order_flow/events.py`
- Modify: `apps/order-flow/schemas/order-created.avsc`
- Modify: `apps/order-flow/schemas/order-created-v2.avsc`
- Modify: `apps/order-flow/tests/test_events.py`
- Modify: `apps/order-flow/LEARNING_GUIDE.md`
- Modify: `apps/order-flow/README.md`

**Steps:**
1. Record current writer/reader behavior and choose a concrete compatibility policy for the lab (default: backward-compatible optional additions with defaults).
2. Write contract tests for old-writer/new-reader and new-writer/old-reader scenarios as required by the chosen policy, including missing-field defaults and incompatible type/removal examples.
3. Confirm each new test fails for the intended incompatibility before changing schemas or codecs.
4. Implement only schema/codec changes needed to meet the selected policy.
5. Run event tests and full suite; document a safe producer/consumer deployment order and schema-change exercise.
6. Commit this stage independently.

## Final review

- Run the complete `apps/order-flow` tests and static checks available in the project.
- Validate the Compose file and migration chain.
- Compare every guarantee in README and LEARNING_GUIDE to code and tests.
- Confirm each stage has its own commit and a clean working tree.
- Keep learner checklists unchecked until the user performs the exercise or explains the concept.
