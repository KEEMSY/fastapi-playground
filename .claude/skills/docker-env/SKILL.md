---
name: docker-env
description: This skill should be used when the user asks to "switch environment", "change docker", "환경 전환", "개발환경 변경", "운영환경 실행", or wants to manage Docker Compose environments.
version: 1.0.0
---

# Docker Environment Manager

여러 Docker Compose 환경을 빠르고 안전하게 전환하고 관리합니다.

## 사용 시점

- 개발/운영 환경 전환
- 성능 테스트 환경 실행
- 모니터링 스택 관리
- 환경별 로그 확인

## 프로젝트 환경 구성

```yaml
사용 가능한 환경:

1. dev (개발)
   파일: docker-compose-dev.yml
   구성: FastAPI(1) + MySQL + Redis
   용도: 로컬 개발

2. prod (운영)
   파일: docker-compose-prod.yml
   구성: FastAPI(3) + MySQL + Redis + Nginx
   용도: 프로덕션 배포

3. loadbalance (로드밸런싱)
   파일: docker-compose-loadbalance.yml
   구성: FastAPI(다중) + Nginx + MySQL + Redis
   용도: 부하 분산 테스트

4. monitoring (모니터링)
   파일: docker-compose-monitoring.yml
   구성: Prometheus + Grafana + Exporters
   용도: 메트릭 수집 및 시각화

5. test-single (성능 테스트 - 단일)
   파일: docker-compose-test-single-w1.yml, w4.yml
   구성: 단일 인스턴스 + 부하 생성기
   용도: 단일 인스턴스 성능 측정

6. test-multi (성능 테스트 - 멀티)
   파일: docker-compose-test-multi-w1.yml, w4.yml
   구성: 다중 인스턴스 + 부하 생성기
   용도: 수평 확장 성능 측정

7. massive (대규모 테스트)
   파일: docker-compose-massive.yml
   구성: 10+ 인스턴스 + Nginx
   용도: 대규모 부하 테스트
```

---

## 실행 플로우

### 1. 환경 전환 (`/docker-env switch {env}`)

#### 1.1 현재 환경 감지

```bash
🔍 현재 실행 중인 환경 확인 중...

실행 중:
  ✅ docker-compose-loadbalance.yml
    - fastapi-app-1 (Up 2 hours)
    - fastapi-app-2 (Up 2 hours)
    - fastapi-app-3 (Up 2 hours)
    - mysql (Up 2 hours)
    - redis (Up 2 hours)
    - nginx (Up 2 hours)

  ✅ docker-compose-monitoring.yml
    - prometheus (Up 2 hours)
    - grafana (Up 2 hours)
```

**감지 방법:**
```bash
$ docker ps --format '{{.Names}}\t{{.Status}}' | grep "fastapi\|mysql\|redis"
```

#### 1.2 환경 전환 확인

```bash
다음 작업을 수행합니다:

🛑 중지할 환경:
  - loadbalance (6개 컨테이너)

🚀 시작할 환경:
  - prod (5개 컨테이너)

⚠️  주의사항:
  - 실행 중인 API 요청이 중단됩니다
  - MySQL/Redis는 데이터 볼륨이 유지됩니다
  - 환경별 .env 설정이 적용됩니다

계속하시겠습니까? [Y/n]: _______
```

#### 1.3 기존 환경 정리

```bash
📦 기존 환경 정리 중...

$ docker-compose -f docker-compose-loadbalance.yml down

Stopping fastapi-app-3 ... done
Stopping nginx ... done
Stopping fastapi-app-2 ... done
Stopping fastapi-app-1 ... done
Stopping redis ... done
Stopping mysql ... done
Removing containers... done

✅ 정리 완료 (네트워크 및 볼륨 유지)
```

**옵션:**
- `--volumes`: 볼륨도 삭제 (데이터 초기화)
- `--rmi`: 이미지도 삭제 (디스크 공간 확보)

#### 1.4 새 환경 실행

```bash
🚀 prod 환경 시작 중...

$ docker-compose -f docker-compose-prod.yml up -d

Creating network "fastapi-prod" ... done
Creating mysql ... done
Creating redis ... done
Creating fastapi-app-1 ... done
Creating fastapi-app-2 ... done
Creating fastapi-app-3 ... done
Creating nginx ... done

⏳ 헬스체크 대기 중...
  ⏳ mysql (1/30s)
  ⏳ redis (1/30s)
  ⏳ fastapi-app-1 (1/30s)
  ...

  ✅ mysql (Ready)
  ✅ redis (Ready)
  ✅ fastapi-app-1 (Ready)
  ✅ fastapi-app-2 (Ready)
  ✅ fastapi-app-3 (Ready)
  ✅ nginx (Ready)

✨ 환경 전환 완료!
```

#### 1.5 환경 정보 출력

```markdown
✅ prod 환경 실행 중

접속 정보:
  - API: http://localhost:7777
  - API 문서: http://localhost:7777/docs
  - Nginx: http://localhost:80
  - MySQL: localhost:3306 (root/1234)
  - Redis: localhost:6379

실행 중인 서비스:
  - fastapi-app-1: 192.168.1.10:8000
  - fastapi-app-2: 192.168.1.11:8000
  - fastapi-app-3: 192.168.1.12:8000
  - nginx: 로드밸런서 (least_conn)

설정:
  - DB_POOL_SIZE: 15
  - Worker Processes: 1
  - Replicas: 3

다음 단계:
  1. 헬스체크: curl http://localhost:7777/
  2. 모니터링 연동: /docker-env start monitoring
  3. 로그 확인: /docker-env logs app
```

---

### 2. 환경 상태 확인 (`/docker-env status`)

```bash
📊 Docker 환경 상태

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
현재 환경: prod
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

서비스 상태:
┌─────────────────┬──────────┬─────────────┬─────────┐
│ 서비스          │ 상태     │ 실행 시간   │ 포트    │
├─────────────────┼──────────┼─────────────┼─────────┤
│ fastapi-app-1   │ Up ✅    │ 10 minutes  │ 8000    │
│ fastapi-app-2   │ Up ✅    │ 10 minutes  │ 8001    │
│ fastapi-app-3   │ Up ✅    │ 10 minutes  │ 8002    │
│ nginx           │ Up ✅    │ 10 minutes  │ 80      │
│ mysql           │ Up ✅    │ 2 hours     │ 3306    │
│ redis           │ Up ✅    │ 2 hours     │ 6379    │
└─────────────────┴──────────┴─────────────┴─────────┘

리소스 사용량:
┌─────────────────┬─────────┬──────────┬────────────┐
│ 서비스          │ CPU     │ 메모리   │ 네트워크   │
├─────────────────┼─────────┼──────────┼────────────┤
│ fastapi-app-1   │ 12%     │ 145 MB   │ 1.2 MB/s   │
│ fastapi-app-2   │ 10%     │ 142 MB   │ 1.1 MB/s   │
│ fastapi-app-3   │ 11%     │ 148 MB   │ 1.0 MB/s   │
│ nginx           │ 2%      │ 8 MB     │ 3.5 MB/s   │
│ mysql           │ 25%     │ 512 MB   │ 2.8 MB/s   │
│ redis           │ 3%      │ 32 MB    │ 0.5 MB/s   │
└─────────────────┴─────────┴──────────┴────────────┘

볼륨:
  - mysql-data: 2.3 GB
  - redis-data: 145 MB

네트워크:
  - fastapi-prod: 172.20.0.0/16
```

**명령어:**
```bash
# 서비스 상태
docker-compose -f docker-compose-prod.yml ps

# 리소스 사용량
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# 볼륨 크기
docker system df -v
```

---

### 3. 로그 확인 (`/docker-env logs {service}`)

#### 3.1 서비스 선택

```bash
로그를 확인할 서비스를 선택하세요:

1. app (모든 FastAPI 인스턴스)
2. app-1 (fastapi-app-1만)
3. nginx
4. mysql
5. redis
6. all (전체)

선택 [1-6]: _______
```

#### 3.2 로그 옵션

```bash
로그 옵션:

1. 실시간 추적 (tail -f)
2. 최근 100줄
3. 특정 시간 범위
4. 에러만 필터링

선택 [1-4]: _______
```

#### 3.3 로그 출력

```bash
📋 fastapi-app-1 로그 (실시간)

2026-02-15 14:45:23 | INFO     | Uvicorn running on http://0.0.0.0:8000
2026-02-15 14:45:24 | INFO     | Application startup complete
2026-02-15 14:45:30 | INFO     | GET /api/question/list - 200 OK (42ms)
2026-02-15 14:45:31 | INFO     | POST /api/answer/create - 204 No Content (128ms)
2026-02-15 14:45:35 | WARNING  | DB connection pool at 80% capacity (16/20)
2026-02-15 14:45:40 | ERROR    | Failed to fetch user: User not found
2026-02-15 14:45:40 | INFO     | POST /api/user/login - 401 Unauthorized (5ms)

[Ctrl+C to exit]
```

**명령어:**
```bash
# 실시간
docker-compose -f docker-compose-prod.yml logs -f fastapi-app-1

# 최근 N줄
docker-compose -f docker-compose-prod.yml logs --tail=100 fastapi-app-1

# 시간 범위
docker-compose -f docker-compose-prod.yml logs --since="2026-02-15T14:00:00" --until="2026-02-15T15:00:00"

# 에러만
docker-compose -f docker-compose-prod.yml logs fastapi-app-1 | grep -i "error\|exception"
```

---

### 4. 환경 재시작 (`/docker-env restart {service}`)

#### 4.1 재시작 범위 선택

```bash
무엇을 재시작하시겠습니까?

1. 전체 환경
2. 애플리케이션만 (FastAPI)
3. 특정 서비스

선택 [1-3]: 2
```

#### 4.2 재시작 실행

```bash
🔄 FastAPI 서비스 재시작 중...

Stopping fastapi-app-3 ... done
Stopping fastapi-app-2 ... done
Stopping fastapi-app-1 ... done

Starting fastapi-app-1 ... done
Starting fastapi-app-2 ... done
Starting fastapi-app-3 ... done

⏳ 헬스체크 대기 중...
  ✅ fastapi-app-1 (Ready in 3s)
  ✅ fastapi-app-2 (Ready in 3s)
  ✅ fastapi-app-3 (Ready in 4s)

✅ 재시작 완료!

다음 단계:
  - API 테스트: curl http://localhost:7777/
  - 로그 확인: /docker-env logs app
```

**코드 변경 시 빠른 재시작:**
```bash
# 이미지 재빌드 + 재시작
$ docker-compose -f docker-compose-prod.yml up -d --build app

Building app... done
Recreating fastapi-app-1 ... done
Recreating fastapi-app-2 ... done
Recreating fastapi-app-3 ... done
```

---

### 5. 환경 정리 (`/docker-env clean`)

```bash
🧹 환경 정리 옵션:

1. 현재 환경만 중지
2. 모든 환경 중지
3. 중지 + 이미지 삭제
4. 완전 초기화 (볼륨 포함)

선택 [1-4]: _______
```

#### 완전 초기화 선택 시

```bash
⚠️  완전 초기화 경고!

다음 항목이 삭제됩니다:
  - 모든 컨테이너
  - 모든 네트워크
  - 모든 이미지
  - 모든 볼륨 (DB 데이터 포함!)

백업 상태:
  - 마지막 DB 백업: 2026-02-15 10:30 (5시간 전)
  - 백업 파일: ./backups/db_backup_20260215_1030.sql

'CLEAN ALL'을 입력하여 확인: _______
```

```bash
$ docker-compose down --volumes --rmi all
$ docker system prune -a --volumes

✅ 정리 완료

삭제된 항목:
  - 컨테이너: 12개
  - 이미지: 8개 (1.2 GB)
  - 볼륨: 4개 (2.5 GB)
  - 네트워크: 3개

확보된 공간: 3.7 GB
```

---

## 환경별 가이드

### Dev 환경 (개발)

```yaml
특징:
  - 단일 FastAPI 인스턴스
  - 로컬 MySQL/Redis
  - 핫 리로드 활성화
  - 디버그 모드

사용 시나리오:
  - 새 기능 개발
  - 로컬 테스트
  - 디버깅

명령어:
  /docker-env switch dev
```

### Prod 환경 (운영)

```yaml
특징:
  - 3개 FastAPI 레플리카
  - Nginx 로드밸런서
  - 최적화된 DB 풀 설정
  - 프로덕션 레벨 설정

사용 시나리오:
  - 프로덕션 배포 시뮬레이션
  - 실전 부하 테스트
  - 최종 검증

명령어:
  /docker-env switch prod
```

### Loadbalance 환경

```yaml
특징:
  - 가변 인스턴스 수
  - Nginx least_conn 알고리즘
  - 성능 모니터링 통합

사용 시나리오:
  - 로드밸런싱 전략 테스트
  - 인스턴스 확장 실험
  - 부하 분산 검증

명령어:
  /docker-env switch loadbalance
```

### Monitoring 환경

```yaml
특징:
  - Prometheus + Grafana
  - MySQL/Redis Exporter
  - Nginx Exporter

사용 시나리오:
  - 메트릭 수집
  - 대시보드 모니터링
  - 성능 분석

명령어:
  /docker-env start monitoring  # 추가 실행 (기존 환경 유지)
  /docker-env stop monitoring   # 모니터링만 중지

URL:
  - Prometheus: http://localhost:9090
  - Grafana: http://localhost:3000 (admin/admin)
```

---

## 고급 기능

### 1. 환경 변수 동적 변경

```bash
환경 변수를 변경하시겠습니까?

현재 설정 (prod):
  DB_POOL_SIZE=15
  WORKER_PROCESSES=1
  LOG_LEVEL=INFO

변경할 변수: DB_POOL_SIZE
새 값: 20

적용 방법:
1. .env 파일 업데이트
2. 서비스 재시작

실행하시겠습니까? [Y/n]: _______
```

**업데이트:**
```bash
$ sed -i '' 's/DB_POOL_SIZE=15/DB_POOL_SIZE=20/' .env
$ docker-compose -f docker-compose-prod.yml up -d --force-recreate app

✅ DB_POOL_SIZE 변경 완료 (15 → 20)
```

### 2. 다중 환경 동시 실행

```bash
여러 환경을 동시에 실행하시겠습니까?

선택된 환경:
  ✅ prod (애플리케이션)
  ✅ monitoring (모니터링)

포트 충돌 확인:
  ✅ 포트 중복 없음

시작하시겠습니까? [Y/n]: _______
```

```bash
$ docker-compose -f docker-compose-prod.yml up -d
$ docker-compose -f docker-compose-monitoring.yml up -d

✅ 2개 환경 실행 중:
  - prod: 6개 컨테이너
  - monitoring: 4개 컨테이너
```

### 3. 성능 벤치마크

```bash
성능 테스트를 실행하시겠습니까?

환경: prod
도구: Apache Bench (ab)

테스트 설정:
  - 요청 수: 10,000
  - 동시성: 100
  - 엔드포인트: GET /api/question/list

시작하시겠습니까? [Y/n]: _______
```

```bash
$ ab -n 10000 -c 100 http://localhost:7777/api/question/list

결과:
  - 처리량: 1,234 req/s
  - 평균 응답: 81 ms
  - 95% 응답: 145 ms
  - 실패율: 0%

비교 (이전 테스트):
  - 처리량: +15% ⬆️
  - 응답 시간: -12% ⬇️

📊 성능 리포트: ./performance_tests/results/report_20260215_1445.md
```

---

## 트러블슈팅

### 포트 충돌

```bash
❌ 환경 시작 실패!

오류: Port 7777 is already in use

해결 방법:
1. 기존 프로세스 종료
   $ lsof -ti:7777 | xargs kill -9

2. 포트 변경
   .env: API_PORT=7778

3. 충돌 서비스 확인
   $ docker ps | grep 7777

선택 [1-3]: _______
```

### 컨테이너 헬스체크 실패

```bash
⚠️  fastapi-app-1 헬스체크 실패 (30s timeout)

로그 확인:
  $ docker logs fastapi-app-1 --tail=50

일반적인 원인:
  1. DB 연결 실패 → MySQL 상태 확인
  2. 의존성 오류 → requirements.txt 확인
  3. 포트 충돌 → 포트 사용 확인

자동 진단 실행 중...
```

### 볼륨 권한 문제

```bash
❌ MySQL 시작 실패: Permission denied

해결 방법:
  $ sudo chown -R $(id -u):$(id -g) ./mysql-data

또는 볼륨 재생성:
  $ docker volume rm mysql-data
  $ docker-compose up -d mysql

주의: 볼륨 삭제 시 데이터 손실!
```

---

## 모범 사례

1. **환경 전환 전 백업**
   ```bash
   /db-migrate backup
   /docker-env switch prod
   ```

2. **모니터링과 함께 실행**
   ```bash
   /docker-env switch prod
   /docker-env start monitoring
   ```

3. **정기적인 로그 확인**
   ```bash
   /docker-env logs app | grep ERROR
   ```

4. **리소스 정리**
   ```bash
   /docker-env clean unused
   docker system prune
   ```
