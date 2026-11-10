# Kubernetes — 백엔드 개발자 몫

[study/README.md](./README.md) 의 한 주제. 실습은 [apps/consign](../apps/consign/README.md) 의 `k8s/`, 과제는 [CATALOG.md](../apps/consign/CATALOG.md) #10~12.

클러스터 운영이 아니라 **내 코드가 k8s 에서 어떻게 사는지** 아는 것이 목표다.

- 객체: Deployment · Service · Ingress · ConfigMap · Secret · Job · CronJob · HPA
- probe: liveness 는 가볍게(DB 검사를 넣으면 DB 장애로 전 Pod 재시작), readiness 는 lifespan 초기화 뒤 통과
- graceful shutdown: SIGTERM 뒤 처리 중 요청 마무리. `preStop`·`terminationGracePeriodSeconds`
- resource: requests/limits, CPU throttling, OOMKilled. 보통 Pod 당 uvicorn 1프로세스, replica 로 확장
- CronJob: crontab 의 자리. `concurrencyPolicy` 없으면 겹쳐 돌고, 놓친 실행은 `startingDeadlineSeconds` 에 따른다 → **멱등성 필수**
- 디버깅: SSH 대신 `kubectl logs/describe/exec`·이벤트. 로그는 stdout JSON

## 자료

- 『Kubernetes in Action』
