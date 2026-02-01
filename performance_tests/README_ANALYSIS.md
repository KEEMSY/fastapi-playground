# DB 세션 풀 및 인스턴스 확장 성능 분석 가이드

이 문서는 DB 세션 풀 크기와 애플리케이션 인스턴스 수에 따른 시스템의 성공률 및 응답 속도를 분석하는 방법과 관련 설정을 설명합니다.

## 1. 개요
시스템 부하 상황에서 DB 커넥션 병목 현상을 파악하고, 최적의 인스턴스 수와 세션 풀 크기 조합을 도출하기 위한 실험 환경을 제공합니다.

## 2. 주요 설정 (Dynamic DB Configuration)
`src/database/database.py`에서 다음 환경 변수를 통해 DB 엔진 설정을 조절할 수 있습니다.

- `DB_POOL_SIZE`: 기본 커넥션 수 (Default: 20)
- `DB_MAX_OVERFLOW`: 최대 추가 허용 커넥션 수 (Default: 30)
- `DB_POOL_TIMEOUT`: 커넥션 획득 대기 시간 (Default: 10초)

## 3. 실험 자동화 스크립트
`scripts/analyze_pool_vs_instances.sh`를 통해 다양한 시나리오를 자동으로 실행할 수 있습니다.

### 실험 매트릭스
| 케이스 | 인스턴스 수 | 풀 크기 | 비고 |
|:---:|:---:|:---:|:---|
| A1 | 1 | 5 | 소규모 풀 병목 테스트 |
| A2 | 1 | 20 | 단일 인스턴스 표준 성능 |
| B1 | 3 | 5 | 수평 확장 시 병목 완화 확인 |
| B2 | 3 | 20 | 전체 시스템 최대 가용량 |

### 실행 방법
```bash
./scripts/analyze_pool_vs_instances.sh
```

## 4. 테스트 도구 및 실행
- **기능 테스트 (Pytest)**: `pytest`
- **부하 테스트 (Locust)**: `locust -f performance_tests/locustfile_db.py --host=http://localhost:7777`
- **통합 검증**: `./test.sh` (Lint + Pytest)

## 5. 결과 분석
실험 완료 후 `performance_tests/results/experiment_[TIMESTAMP]/` 폴더 내의 CSV 및 HTML 보고서를 통해 다음 지표를 분석합니다.
- **Failures**: 세션 풀 고갈로 인한 요청 실패 수
- **Average Response Time**: 커넥션 대기로 인한 지연 시간 증가 여부
- **TPS (Transactions Per Second)**: 인스턴스 수 증가에 따른 처리량 향상 비율
