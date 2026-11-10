# 서버 한 대 → 여러 Pod: 큰 틀은 같아도 미리 알면 좋은 차이

[study/README.md](./README.md) 의 한 주제.

1. **롤링 배포 중 구·신 코드가 동시에 돈다** → 마이그레이션은 expand → 배포 → contract. 컬럼 이름 변경·NOT NULL 추가를 한 번에 하면 장애. 마이그레이션 실행 위치(Job·initContainer·CI)를 확인 — [CATALOG.md](../apps/consign/CATALOG.md) #11
2. **Pod 가 여러 개** → 메모리·로컬 파일 상태가 공유되지 않는다. heartbeat 파일·메모리 캐시·프로세스 내 락은 Redis/DB 로
3. 설정은 환경변수·Secret 으로 주입된다
4. 장애 분석은 로그·메트릭·트레이스 대시보드. 위치를 먼저 알아 둔다

## 새 환경에서 처음 읽을 것

CI 워크플로우 yaml · Dockerfile · k8s 매니페스트/Helm 차트 · 마이그레이션 실행 위치 · sync/async 비율 · DB 드라이버 · 큐 종류 · 런북
