# apps/consign — 작업 규칙

학습 문서는 [study/README.md](../../study/README.md) 의 진행 규칙을 따른다. **`apps/api` 코딩 규칙(204 응답·`_` 접두사·Python 3.9 타입 힌트 등)은 여기에 적용하지 않는다.**

## 읽는 순서

[README.md](README.md)(구조·실행) → [ROADMAP.md](ROADMAP.md)(단계) → [CATALOG.md](CATALOG.md)(실수 카탈로그) → [LOG.md](LOG.md) 마지막 줄

## 환경

- Python 3.13 · uv (`uv sync`, `uv run ...`). 루트의 `venv/` 를 쓰지 않는다
- Postgres 16 · Redis 7 — `docker compose up -d`
- 테스트: `make test` (로컬 Postgres 필요). 클러스터 전체 동작은 `make up` 후 콘솔 http://localhost:8001/ 시나리오

## 규칙

- 판매는 조건부 `UPDATE … RETURNING` 으로 확인과 변경을 한 문장에. 생성 201, 이미 팔림 409
- DB 커밋과 메시지 발행을 따로 하지 않는다 — Outbox. 소비자는 멱등(`sale_id` PK)으로, ACK 는 DB 커밋 뒤
- 새 실수 카탈로그 항목은 `app/static/index.html` 의 `SCENARIOS` 에 시나리오를 하나 더한다 — 실수를 켜면 ❌, 고치면 ✅
- 카탈로그 과제는 표준 참고(GitHub·공식 문서)를 먼저 읽고 비교한 뒤 만든다
- 끝나면 [CATALOG.md](CATALOG.md) 상태와 [LOG.md](LOG.md) 를 고친다
