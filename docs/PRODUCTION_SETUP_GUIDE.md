# 🚀 AWS t3.medium 최적화 운영 환경 구축 가이드

본 문서는 성능 분석 실험 결과(S1~S4)를 바탕으로, AWS `t3.medium` (2 vCPU, 4GiB RAM) 환경에서 FastAPI 애플리케이션의 성능을 극대화하기 위한 아키텍처 설정을 가이드합니다.

## 1. 아키텍처 설계 원칙

### 1.1 수평 확장 (Multiple Containers)
- **전략**: 단일 인스턴스 내에서 3개의 컨테이너 복제본(Replicas) 운영.
- **이유**: 파이썬의 GIL(Global Interpreter Lock)로 인해 프로세스 하나는 코어 1개만 사용 가능합니다. 컨테이너를 3개로 나누어 OS가 2개의 vCPU 코어에 부하를 분산하게 함으로써 CPU 자원을 100% 활용합니다.

### 1.2 작고 효율적인 커넥션 풀 (Optimized DB Pool)
- **설정**: 인스턴스당 `DB_POOL_SIZE=20`, `DB_MAX_OVERFLOW=5`.
- **이유**: 1개의 이벤트 루프가 너무 많은 DB 응답을 처리하면 '루프 정체(Starvation)'가 발생합니다. 실험 결과, 인스턴스당 20개의 풀을 유지하는 것이 응답 속도와 처리량 면에서 가장 안정적이었습니다.

## 2. 구성 요소 상세 (Deployment Details)

### 2.1 애플리케이션 계층 (App Layer)
- **이미지**: Multi-stage build 최적화 이미지.
- **리소스 제한**: 
  - CPU: 컨테이너당 0.6 (총 1.8 코어 사용하여 OS 여유분 확보)
  - Memory: 컨테이너당 1GB (총 3GB 사용하여 OOM 방지)
- **환경 변수**: `WORKERS=1` (컨테이너 내부 멀티 워커보다 컨테이너 복제가 관리 및 격리에 유리).

### 2.2 로드밸런서 계층 (Nginx Layer)
- **알고리즘**: `least_conn` (연결 수가 가장 적은 컨테이너로 요청 배분).
- **최적화**: `keepalive` 설정을 통해 Nginx-App 간 연결 재사용 효율 증대.

## 3. 실행 방법 (How to Run)

```bash
# 1. 운영 환경용 스택 실행
docker-compose -f docker-compose-prod.yml up -d

# 2. 인스턴스 상태 및 로그 확인
docker-compose -f docker-compose-prod.yml ps
docker-compose -f docker-compose-prod.yml logs -f --tail=100
```

## 4. 기대 효과 (Expected Performance)
- **초당 처리량 (RPS)**: 약 40~50 req/s (pg_sleep 및 무거운 쿼리 포함 기준)
- **평균 응답 시간**: 1초 내외 (부하 상황 시)
- **가용성**: 컨테이너 1개 장애 시에도 서비스 중단 없이 나머지 2개가 요청 처리.

---
*본 문서는 [Sisyphus] 에이전트의 성능 분석 실험 데이터를 기반으로 작성되었습니다.*
