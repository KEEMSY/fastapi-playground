#!/bin/bash

# Multi 인스턴스 테스트 스크립트
# 사용법: ./scripts/run_multi_test.sh [users] [spawn-rate] [run-time]

set -e

USERS=${1:-100}
SPAWN_RATE=${2:-10}
RUN_TIME=${3:-2m}

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="$PROJECT_DIR/performance_tests/results/multi_$TIMESTAMP"
mkdir -p "$RESULTS_DIR"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

wait_for_health() {
    local max_attempts=60
    local attempt=1
    log_info "Waiting for application to be healthy..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:7777/health > /dev/null 2>&1; then
            log_success "Application is healthy!"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo ""
    log_error "Application failed to become healthy"
    return 1
}

run_test() {
    local case_name=$1
    local compose_file=$2
    local test_dir="$RESULTS_DIR/$case_name"
    mkdir -p "$test_dir"

    echo ""
    echo "=============================================="
    log_info "Testing: $case_name"
    echo "=============================================="

    # 기존 환경 정리
    docker-compose -f "$compose_file" down -v --remove-orphans 2>/dev/null || true

    # 환경 시작
    log_info "Starting environment..."
    docker-compose -f "$compose_file" up -d --build

    if ! wait_for_health; then
        log_error "Failed to start $case_name"
        docker-compose -f "$compose_file" logs > "$test_dir/docker_logs.txt"
        docker-compose -f "$compose_file" down -v
        return 1
    fi

    # 워커 정보 확인
    log_info "Checking instances..."
    for i in 1 2 3; do
        curl -s http://localhost:7777/api/v1/standard/sync-test 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'  Instance: {d.get(\"worker_name\", \"N/A\")}')" || true
    done

    sleep 5

    # Simple 테스트
    log_info "Running simple response test..."
    locust -f performance_tests/locustfile_simple.py \
        --host=http://localhost:7777 \
        --users=$USERS \
        --spawn-rate=$SPAWN_RATE \
        --run-time=$RUN_TIME \
        --headless \
        --csv="$test_dir/simple" \
        --html="$test_dir/simple_report.html" \
        2>&1 | tee "$test_dir/simple_output.log"

    # I/O 테스트
    log_info "Running I/O test..."
    locust -f performance_tests/locustfile_io.py \
        --host=http://localhost:7777 \
        --users=$((USERS / 2)) \
        --spawn-rate=$((SPAWN_RATE / 2)) \
        --run-time=$RUN_TIME \
        --headless \
        --csv="$test_dir/io" \
        --html="$test_dir/io_report.html" \
        2>&1 | tee "$test_dir/io_output.log"

    # 환경 종료
    log_info "Stopping environment..."
    docker-compose -f "$compose_file" down -v

    log_success "Completed: $case_name"
}

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Multi Instance Performance Test                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
log_info "Users: $USERS, Spawn Rate: $SPAWN_RATE, Run Time: $RUN_TIME"
log_info "Results: $RESULTS_DIR"
echo ""

# 기존 테스트 환경 정리
docker-compose -f docker-compose-test-multi-w1.yml down -v --remove-orphans 2>/dev/null || true
docker-compose -f docker-compose-test-multi-w4.yml down -v --remove-orphans 2>/dev/null || true

# 테스트 실행
run_test "multi_w1" "docker-compose-test-multi-w1.yml"
sleep 10
run_test "multi_w4" "docker-compose-test-multi-w4.yml"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Test Complete!                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
log_success "Results: $RESULTS_DIR"
