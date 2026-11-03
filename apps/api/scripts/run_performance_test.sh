#!/bin/bash
# FastAPI 동기/비동기 성능 비교 테스트 스크립트
#
# 사용법:
#   ./scripts/run_performance_test.sh [single|multi] [scenario] [users]
#
# 예시:
#   ./scripts/run_performance_test.sh single simple 100
#   ./scripts/run_performance_test.sh multi mixed 500
#   ./scripts/run_performance_test.sh single all 200

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 기본값
ENV_TYPE=${1:-single}
SCENARIO=${2:-mixed}
USERS=${3:-100}
SPAWN_RATE=${4:-10}
RUN_TIME=${5:-5m}
HOST="http://localhost:7777"

# 결과 디렉토리
RESULTS_DIR="performance_tests/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE} FastAPI 성능 테스트 실행${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""
echo -e "환경: ${GREEN}${ENV_TYPE}${NC}"
echo -e "시나리오: ${GREEN}${SCENARIO}${NC}"
echo -e "사용자 수: ${GREEN}${USERS}${NC}"
echo -e "Spawn Rate: ${GREEN}${SPAWN_RATE}/s${NC}"
echo -e "실행 시간: ${GREEN}${RUN_TIME}${NC}"
echo ""

# 결과 디렉토리 생성
mkdir -p ${RESULTS_DIR}

# 함수: 환경 시작
start_environment() {
    echo -e "${YELLOW}환경 시작 중...${NC}"

    if [ "$ENV_TYPE" == "single" ]; then
        docker-compose -f docker-compose-perf-single.yml up -d
    else
        docker-compose -f docker-compose-perf-multi.yml up -d
    fi

    # 서비스 준비 대기
    echo -e "${YELLOW}서비스 준비 대기 중 (30초)...${NC}"
    sleep 30

    # 헬스체크
    echo -e "${YELLOW}헬스체크 중...${NC}"
    for i in {1..10}; do
        if curl -s -o /dev/null -w "%{http_code}" ${HOST}/api/v1/standard/sync-test | grep -q "200"; then
            echo -e "${GREEN}서비스 준비 완료!${NC}"
            return 0
        fi
        echo "대기 중... ($i/10)"
        sleep 5
    done

    echo -e "${RED}서비스 시작 실패${NC}"
    exit 1
}

# 함수: 테스트 데이터 생성
generate_test_data() {
    echo -e "${YELLOW}테스트 데이터 확인 중...${NC}"

    # 데이터 존재 여부 확인 (curl로 bulk-read 호출)
    RESPONSE=$(curl -s "${HOST}/api/v1/standard/sync-bulk-read?limit=1" 2>/dev/null || echo '{"data":{"total_count":0}}')
    COUNT=$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('total_count',0))" 2>/dev/null || echo "0")

    if [ "$COUNT" -lt "10000" ]; then
        echo -e "${YELLOW}테스트 데이터 생성 중 (10만 건)...${NC}"

        if [ "$ENV_TYPE" == "single" ]; then
            docker exec perf_single_app python scripts/generate_test_data.py --records=100000 --clear
        else
            docker exec perf_app_1 python scripts/generate_test_data.py --records=100000 --clear
        fi

        echo -e "${GREEN}테스트 데이터 생성 완료!${NC}"
    else
        echo -e "${GREEN}테스트 데이터 존재 (${COUNT}건)${NC}"
    fi
}

# 함수: Locust 테스트 실행
run_locust_test() {
    local SCENARIO_NAME=$1
    local LOCUST_FILE=$2

    echo ""
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE} 테스트 실행: ${SCENARIO_NAME}${NC}"
    echo -e "${BLUE}============================================${NC}"

    local RESULT_PREFIX="${RESULTS_DIR}/${ENV_TYPE}_${SCENARIO_NAME}_${USERS}_${TIMESTAMP}"

    cd performance_tests

    locust -f ${LOCUST_FILE} \
        --host=${HOST} \
        --users=${USERS} \
        --spawn-rate=${SPAWN_RATE} \
        --run-time=${RUN_TIME} \
        --headless \
        --csv=../${RESULT_PREFIX} \
        --html=../${RESULT_PREFIX}.html \
        --only-summary

    cd ..

    echo ""
    echo -e "${GREEN}결과 저장: ${RESULT_PREFIX}${NC}"
    echo -e "  - CSV: ${RESULT_PREFIX}_stats.csv"
    echo -e "  - HTML: ${RESULT_PREFIX}.html"
}

# 함수: 환경 정리
cleanup_environment() {
    echo ""
    echo -e "${YELLOW}환경 정리 중...${NC}"

    if [ "$ENV_TYPE" == "single" ]; then
        docker-compose -f docker-compose-perf-single.yml down
    else
        docker-compose -f docker-compose-perf-multi.yml down
    fi

    echo -e "${GREEN}정리 완료${NC}"
}

# 함수: 결과 요약
print_summary() {
    echo ""
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE} 테스트 결과 요약${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
    echo -e "결과 파일 위치: ${GREEN}${RESULTS_DIR}/${NC}"
    echo ""

    # 최신 결과 파일 목록
    echo "생성된 결과 파일:"
    ls -la ${RESULTS_DIR}/*${TIMESTAMP}* 2>/dev/null || echo "결과 파일 없음"

    echo ""
    echo -e "${YELLOW}분석 방법:${NC}"
    echo "  1. HTML 리포트 열기: open ${RESULTS_DIR}/*.html"
    echo "  2. CSV 분석: cat ${RESULTS_DIR}/*_stats.csv"
    echo ""
}

# 메인 실행
main() {
    # 의존성 확인
    if ! command -v locust &> /dev/null; then
        echo -e "${RED}Locust가 설치되어 있지 않습니다.${NC}"
        echo "설치: pip install locust"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}docker-compose가 설치되어 있지 않습니다.${NC}"
        exit 1
    fi

    # 환경 시작
    start_environment

    # 테스트 데이터 생성
    generate_test_data

    # 시나리오별 테스트 실행
    case $SCENARIO in
        simple)
            run_locust_test "simple" "locustfile_simple.py"
            ;;
        io)
            run_locust_test "io" "locustfile_io.py"
            ;;
        db)
            run_locust_test "db" "locustfile_db.py"
            ;;
        mixed)
            run_locust_test "mixed" "locustfile_mixed.py"
            ;;
        all)
            run_locust_test "simple" "locustfile_simple.py"
            run_locust_test "io" "locustfile_io.py"
            run_locust_test "db" "locustfile_db.py"
            run_locust_test "mixed" "locustfile_mixed.py"
            ;;
        *)
            echo -e "${RED}알 수 없는 시나리오: ${SCENARIO}${NC}"
            echo "사용 가능한 시나리오: simple, io, db, mixed, all"
            exit 1
            ;;
    esac

    # 결과 요약
    print_summary

    # 사용자에게 정리 여부 확인
    echo ""
    read -p "환경을 정리하시겠습니까? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cleanup_environment
    else
        echo -e "${YELLOW}환경이 계속 실행 중입니다.${NC}"
        echo "수동 정리: docker-compose -f docker-compose-perf-${ENV_TYPE}.yml down"
    fi
}

# 스크립트 실행
main
