# k8s 연습 환경. 처음엔 make up, 코드를 고친 뒤엔 make deploy
CLUSTER := consign
CTX := --context kind-$(CLUSTER)

up:
	kind get clusters | grep -qx $(CLUSTER) || kind create cluster --config k8s/kind.yaml
	$(MAKE) deploy

deploy:
	docker build -t consign:dev .
	kind load docker-image consign:dev --name $(CLUSTER)
	kubectl $(CTX) apply -k k8s
	kubectl $(CTX) rollout restart deploy/consign deploy/settlement
	kubectl $(CTX) rollout status deploy/consign deploy/settlement --timeout=180s

demo:  # 판매 1건 → 정산 서비스에 반영되는지
	@ID=$$(curl -s -XPOST localhost:8001/items -H 'content-type: application/json' \
	  -d '{"seller_id":7,"name":"demo","price":100000,"commission_rate":30}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])'); \
	curl -s -XPOST localhost:8001/items/$$ID/sell; echo; sleep 2; \
	echo "consign   :" $$(curl -s localhost:8001/sellers/7/settlement); \
	echo "settlement:" $$(curl -s localhost:8002/sellers/7/settlement)

reset:  # DB·Redis·RabbitMQ 를 비운다(emptyDir 라 Pod 를 지우면 데이터도 사라진다). 모델을 바꿨는데 create_all 이 기존 테이블을 안 고칠 때
	kubectl $(CTX) delete pod -l 'app in (postgres,redis,rabbitmq)' --wait
	kubectl $(CTX) wait --for=condition=ready pod -l app=postgres --timeout=60s
	$(MAKE) deploy

test:  # 로컬 docker compose 의 Postgres 로 pytest. 클러스터 동작 확인은 콘솔의 시나리오로
	docker compose up -d --wait
	uv run pytest -q

status:
	kubectl $(CTX) get pods -o wide

mq-ui:  # RabbitMQ 관리 UI → http://localhost:55673 (guest/guest). compose 와 같은 포트. kind 포트를 늘리면 클러스터를 다시 만들어야 해서 port-forward
	kubectl $(CTX) port-forward svc/rabbitmq 55673:15672

logs:
	kubectl $(CTX) logs -l app=settlement --tail=20 --prefix

down:
	kind delete cluster --name $(CLUSTER)

.PHONY: up deploy reset demo test status mq-ui logs down
