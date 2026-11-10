# 자동화된 워크플로우

[study/README.md](./README.md) 의 한 주제. 실습은 [apps/consign ROADMAP](../apps/consign/ROADMAP.md) 5단계.

어느 쪽 자동화인지 먼저 확인한다.

- 배포 파이프라인: GitHub Actions(테스트 → 이미지 빌드 → 레지스트리) → Helm/Kustomize → ArgoCD 같은 GitOps
- 데이터 파이프라인: Airflow·Dagster 류
