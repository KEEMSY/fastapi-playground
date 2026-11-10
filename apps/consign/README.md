# consign — 위탁 판매 정산 미니 플랫폼

학습 목록은 [study/README.md](../../study/README.md). 단계 계획은 [ROADMAP.md](ROADMAP.md), 과제는 [CATALOG.md](CATALOG.md), 진행 기록은 [LOG.md](LOG.md).

## 구조

```
[consign 서비스]  판매 → items·sales·outbox 를 한 트랜잭션에 기록
      │  relay(백그라운드 작업): outbox → Redis Stream "sales"   (at-least-once)
      ▼
[Redis Stream]  소비자 그룹 "settlement"
      ▼
[settlement 서비스]  원장 ledger(sale_id PK)에 멱등 기록 → 판매자별 정산 조회
```

- DB 는 서비스마다 따로다(`consign` / `settlement` 데이터베이스). settlement 는 consign DB 를 읽지 않고 이벤트로만 판매를 안다
- consign 의 `/sellers/{id}/settlement` 는 1단계 흔적이다. settlement 쪽 값과 결국 같아지는지(최종 일관성) 비교용으로 남겼다

## 로컬 (테스트)

```bash
docker compose up -d --wait   # Postgres 16 :55432 (consign·settlement DB), Redis 7 :56379, RabbitMQ 4 :55672 (관리 UI :55673)
uv sync
uv run pytest -v              # 실제 Postgres·RabbitMQ 에 붙는다. Redis 는 쓰지 않는다
```

판매 이벤트 브로커는 환경변수 `BROKER` 로 고른다. 기본은 `redis`(Streams)이고, `rabbitmq` 면 topic exchange `sales` → 큐 `settlement.sales` 로 간다. 콘솔 기록(trace)은 어느 쪽이든 Redis 에 남는다. k8s 에서는 `k8s/apps.yaml` 의 두 Secret 에서 `BROKER` 를 같이 바꾸고 `make deploy`, 관리 UI 는 `make mq-ui`. 콘솔의 이벤트 흐름 탭은 아직 Redis Stream 만 보여 준다(3b 2단계에서 RabbitMQ 큐를 붙인다).

## k8s (kind)

```bash
make up       # 클러스터 생성 + 이미지 빌드·적재 + 배포 (consign 2개, settlement 2개, postgres, redis, rabbitmq)
make demo     # 판매 1건 → 두 서비스의 정산 합계 비교
make status   # Pod 목록
make logs     # settlement 로그
make deploy   # 코드 고친 뒤 다시 배포 (롤링)
make mq-ui    # RabbitMQ 관리 UI → http://localhost:55673 (port-forward)
make reset    # DB·Redis·RabbitMQ 비우고 재배포 (모델을 바꿨을 때 — create_all 은 기존 테이블을 고치지 않는다)
make down     # 클러스터 삭제
```

**콘솔: http://localhost:8001/** — consign 이 직접 내려주는 화면 한 장(`app/static/index.html`, 빌드 없음). API 문서: consign `:8001/docs` · settlement `:8002/docs`

한 화면에 **왼쪽 = 하는 것(시나리오), 오른쪽 = 보이는 것(구성도 + 상세 탭)** 을 둔다. 버튼을 누르고 스크롤 없이 결과를 본다.

| 영역 | 무엇을 하나 / 보여 주나 | 데이터 출처 |
|---|---|---|
| 시나리오 (왼쪽) | 버튼 하나로 정해진 단계를 실행하고, **단계마다 판정(✅/❌)·근거·걸린 시간**을 남긴다. "자동 시나리오 전부 실행" = 클러스터를 상대로 한 눈에 보이는 테스트. 터미널이 필요한 단계는 명령과 복사 버튼을 보여 주고, 실행 결과가 화면에 나타나면 알아서 다음 단계로 넘어간다 | 아래 엔드포인트 전부 |
| 구성도 (오른쪽 위) | 6개 노드를 선으로 잇고, 서버가 받은 요청·relay 발행·정산 소비마다 경로를 따라 점이 흐른다(1초 사이 건수는 ×n). 노드엔 살아 있는 Pod·outbox 대기·pending·lag. 서비스가 응답하지 않으면 빨갛게. 단계 설명의 주소는 consign 의 실제 설정값 | `/ops/topology` · 아래 전부 |
| 탭: 판매 여정 | sale 별로 커밋 → Redis 발행 → 원장 기록 시각과 구간별 소요 | `/ops/outbox` + `/ops/settlement/ledger` |
| 탭: 상품 · 직접 조작 | 등록·판매·동시 20건을 손으로 | consign `/items` · `/ops/items` |
| 탭: 이벤트 흐름 | Outbox → Redis Stream(길이·pending·lag·소비자) → 정산 원장 | `/ops/outbox` · `/ops/stream`(XINFO) · `/ops/settlement/ledger` |
| 탭: 정산 비교 | 판매자별 consign 합계 vs settlement 합계 — "따라잡는 중" → "일치" | `/ops/sellers` · `/ops/settlement/sellers` |
| 탭: 요청 기록 | 두 서비스의 **모든 Pod** 가 받은 HTTP 요청(콘솔·curl·k8s probe)과 내부 이동(relay XADD 배치, 정산 XREADGROUP 배치)을 한 줄로. 콘솔 1초 갱신(`x-poll` 헤더)만 뺀다. probe 는 체크로 숨김 | `/ops/trace` ← Redis 스트림 `trace`(최근 2000건). 미들웨어·relay·소비자가 쓴다 |

| 시나리오 | 확인하는 것 | 실행 |
|---|---|---|
| 판매 1건이 정산까지 도착한다 | Outbox → Redis → 원장, 판매자 합계 일치 | 자동 |
| 같은 상품 동시 구매 20건 → 1건만 팔린다 | 실수 카탈로그 #1. 두 Pod 에 나뉜 요청끼리도 막히는지 | 자동 |
| 정산 서비스가 꺼져도 판매는 된다 | 정산을 0개로 줄여도 판매 201, 이벤트는 Redis 에 쌓였다가(lag) 다시 켜면 따라잡는다 | 터미널 2번(명령 복사) |
| 판매 1000건이 한꺼번에 몰린다 | 카탈로그 #13. 부하는 서버 안(`/ops/burst`)에서 만든다 — 브라우저는 한 주소에 동시 연결 6개라 1000건을 화면에서 보내면 브라우저가 병목. outbox 대기·Redis lag·정산 미도착 추이 그래프 | 자동 |
| 정산 소비자를 2→4개로 늘리면 빨라지나 | 카탈로그 #14. 같은 500건 전후 비교, 두 그래프를 같은 축으로 | 터미널 2번 |
| 느린 쿼리가 커넥션 풀을 다 잡으면 판매도 줄 선다 | 카탈로그 #15. `/ops/pool` 이 한 Pod 안에서 `pg_sleep` 쿼리 n개 + 끼어든 `SELECT 1` 을 잰다. 완료 시간 계단 그래프 | 자동 |

**새 실수 카탈로그 항목을 만들 때는 시나리오 하나를 `index.html` 의 `SCENARIOS` 에 더한다** — 실수를 켠 상태에서 ❌, 고친 뒤 ✅ 가 나오게.

- 브라우저는 consign 하나에만 붙는다. 정산 데이터는 consign 이 **settlement 를 HTTP 로 호출**해 가져온다(`/ops/settlement/*`, 클러스터 안에선 `http://settlement:8000`). 정산 DB 를 직접 읽지 않는다
- 1초마다 갱신. 끄려면 오른쪽 위 체크
- 단위 테스트(pytest)는 `make test` — 로컬 Postgres 로 돈다. 클러스터 전체 동작은 콘솔 시나리오로 본다

처음 `make up` 하면 앱 Pod 가 Postgres 보다 먼저 떠서 2번쯤 재시작된다(RESTARTS 2). lifespan 의 테이블 생성이 실패해 죽고, k8s 가 다시 띄운다. 일부러 막지 않았다 — [CATALOG.md](CATALOG.md) #12.

## 파일

| 파일 | 무엇 |
|---|---|
| `app/db.py` · `models.py` · `main.py` | consign: 설정·엔진, `Item`·`Sale`·`Outbox`, API·probe·lifespan |
| `app/relay.py` | Outbox → Redis. `FOR UPDATE SKIP LOCKED` 로 Pod 여러 개가 같은 행을 집지 않게 |
| `app/console.py` · `app/static/index.html` | 관찰용 콘솔: 화면 + `/ops/*` 조회 엔드포인트 |
| `settlement/main.py` | 정산 서비스 한 파일: 소비자 그룹, 멱등 기록, 정산 조회, 종료 시 소비자 정리 |
| `k8s/kind.yaml` | 노드 1개 클러스터, NodePort 30001·30002 → localhost 8001·8002 |
| `k8s/infra.yaml` · `apps.yaml` | Postgres·Redis / Secret·Deployment(probe·preStop·resources)·Service |
| `Dockerfile` · `Makefile` | 두 서비스가 한 이미지를 쓰고 실행 명령만 다르다 |
