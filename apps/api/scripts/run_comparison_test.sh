#!/bin/bash

# 동기/비동기 컨텍스트 성능 비교 테스트 스크립트
# 워커 수와 인스턴스 수에 따른 성능 차이 측정
#
# 사용법:
#   ./scripts/run_comparison_test.sh [users] [spawn-rate] [run-time]
#
# 예시:
#   ./scripts/run_comparison_test.sh 100 10 2m
#   ./scripts/run_comparison_test.sh 200 20 5m

set -e

# 기본값 설정
USERS=${1:-100}
SPAWN_RATE=${2:-10}
RUN_TIME=${3:-2m}

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 프로젝트 루트 디렉토리
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# 결과 디렉토리
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="$PROJECT_DIR/performance_tests/results/comparison_$TIMESTAMP"
mkdir -p "$RESULTS_DIR"

# 테스트 케이스 정의 (macOS bash 3.x 호환)
TEST_CASE_NAMES="single_w1 single_w4 multi_w1 multi_w4"

# compose 파일 매핑 함수
get_compose_file() {
    case "$1" in
        single_w1) echo "docker-compose-test-single-w1.yml" ;;
        single_w4) echo "docker-compose-test-single-w4.yml" ;;
        multi_w1)  echo "docker-compose-test-multi-w1.yml" ;;
        multi_w4)  echo "docker-compose-test-multi-w4.yml" ;;
    esac
}

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 환경 정리 함수
cleanup_all() {
    log_info "Cleaning up all test environments..."
    for case_name in $TEST_CASE_NAMES; do
        compose_file=$(get_compose_file "$case_name")
        docker-compose -f "$compose_file" down -v --remove-orphans 2>/dev/null || true
    done
    # 기존 성능 테스트 환경도 정리
    docker-compose -f docker-compose-perf-single.yml down -v --remove-orphans 2>/dev/null || true
    docker-compose -f docker-compose-perf-multi.yml down -v --remove-orphans 2>/dev/null || true
}

# 헬스 체크 함수
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
    log_error "Application failed to become healthy after $max_attempts attempts"
    return 1
}

# 테스트 데이터 생성 함수
generate_test_data() {
    log_info "Generating test data..."

    # Docker 컨테이너 내에서 실행
    docker exec -it $(docker ps -qf "name=_app" | head -1) \
        python scripts/generate_test_data.py --records=10000 --batch=5000 --clear 2>/dev/null || {
        log_warning "Could not generate test data in container, trying locally..."
        python scripts/generate_test_data.py --records=10000 --batch=5000 --clear 2>/dev/null || true
    }
}

# 단일 테스트 실행 함수
run_single_test() {
    local case_name=$1
    local compose_file=$2
    local test_results_dir="$RESULTS_DIR/$case_name"

    mkdir -p "$test_results_dir"

    echo ""
    echo "=============================================="
    log_info "Testing: $case_name"
    log_info "Compose file: $compose_file"
    echo "=============================================="

    # 환경 시작
    log_info "Starting environment..."
    docker-compose -f "$compose_file" up -d --build

    # 헬스 체크
    if ! wait_for_health; then
        log_error "Failed to start environment for $case_name"
        docker-compose -f "$compose_file" logs > "$test_results_dir/docker_logs.txt"
        docker-compose -f "$compose_file" down -v
        return 1
    fi

    # 워커 정보 확인
    log_info "Worker configuration:"
    curl -s http://localhost:7777/api/v1/standard/sync-test | python -m json.tool 2>/dev/null || true

    # 테스트 데이터 생성 (첫 번째 케이스에서만)
    if [[ "$case_name" == "single_w1" ]]; then
        generate_test_data
    fi

    sleep 5  # 안정화 대기

    # Locust 테스트 실행 - Simple (sync vs async 기본 비교)
    log_info "Running simple response test..."
    locust -f performance_tests/locustfile_simple.py \
        --host=http://localhost:7777 \
        --users=$USERS \
        --spawn-rate=$SPAWN_RATE \
        --run-time=$RUN_TIME \
        --headless \
        --csv="$test_results_dir/simple" \
        --html="$test_results_dir/simple_report.html" \
        2>&1 | tee "$test_results_dir/simple_output.log"

    # Locust 테스트 실행 - I/O (동기/비동기 I/O 비교)
    log_info "Running I/O test..."
    locust -f performance_tests/locustfile_io.py \
        --host=http://localhost:7777 \
        --users=$((USERS / 2)) \
        --spawn-rate=$((SPAWN_RATE / 2)) \
        --run-time=$RUN_TIME \
        --headless \
        --csv="$test_results_dir/io" \
        --html="$test_results_dir/io_report.html" \
        2>&1 | tee "$test_results_dir/io_output.log"

    # 환경 종료
    log_info "Stopping environment..."
    docker-compose -f "$compose_file" down -v

    log_success "Completed test for $case_name"
}

# 결과 요약 생성 함수
generate_summary() {
    local summary_file="$RESULTS_DIR/summary.md"

    echo "# 동기/비동기 컨텍스트 성능 비교 결과" > "$summary_file"
    echo "" >> "$summary_file"
    echo "테스트 일시: $(date '+%Y-%m-%d %H:%M:%S')" >> "$summary_file"
    echo "테스트 설정: Users=$USERS, Spawn Rate=$SPAWN_RATE, Run Time=$RUN_TIME" >> "$summary_file"
    echo "" >> "$summary_file"

    echo "## ASGI에서 동기 함수 처리 방식" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "FastAPI/Starlette(ASGI)는 동기 함수(\`def\`)를 호출할 때 **ThreadPoolExecutor**를 사용합니다:" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "\`\`\`python" >> "$summary_file"
    echo "# Starlette 내부 동작 (개념)" >> "$summary_file"
    echo "if asyncio.iscoroutinefunction(func):" >> "$summary_file"
    echo "    response = await func()  # 이벤트 루프에서 직접 실행" >> "$summary_file"
    echo "else:" >> "$summary_file"
    echo "    response = await run_in_executor(None, func)  # ThreadPool에서 실행" >> "$summary_file"
    echo "\`\`\`" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "이로 인해:" >> "$summary_file"
    echo "- 동기 함수도 이벤트 루프를 **블로킹하지 않음**" >> "$summary_file"
    echo "- I/O가 없는 단순 응답에서는 동기/비동기 성능 차이가 **미미**" >> "$summary_file"
    echo "- 차이가 나는 경우: I/O 바운드 작업, 동시 요청 수가 스레드풀 크기 초과 시" >> "$summary_file"
    echo "" >> "$summary_file"

    echo "## 테스트 환경 구성" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "| 케이스 | 인스턴스 수 | 워커 수 | 총 워커 |" >> "$summary_file"
    echo "|--------|------------|---------|---------|" >> "$summary_file"
    echo "| single_w1 | 1 | 1 | 1 |" >> "$summary_file"
    echo "| single_w4 | 1 | 4 | 4 |" >> "$summary_file"
    echo "| multi_w1 | 3 | 1 | 3 |" >> "$summary_file"
    echo "| multi_w4 | 3 | 4 | 12 |" >> "$summary_file"
    echo "" >> "$summary_file"

    echo "## 테스트 결과 요약" >> "$summary_file"
    echo "" >> "$summary_file"

    echo "### Simple Response Test (단순 응답)" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "| 케이스 | RPS | 평균 응답시간 (ms) | 중앙값 (ms) | 95% (ms) | 실패율 |" >> "$summary_file"
    echo "|--------|-----|-------------------|-------------|----------|--------|" >> "$summary_file"

    for case_name in single_w1 single_w4 multi_w1 multi_w4; do
        stats_file="$RESULTS_DIR/$case_name/simple_stats.csv"
        if [ -f "$stats_file" ]; then
            # CSV에서 Aggregated 행 추출
            agg_line=$(grep "Aggregated" "$stats_file" 2>/dev/null | tail -1)
            if [ -n "$agg_line" ]; then
                rps=$(echo "$agg_line" | cut -d',' -f10)
                avg=$(echo "$agg_line" | cut -d',' -f6)
                median=$(echo "$agg_line" | cut -d',' -f7)
                p95=$(echo "$agg_line" | cut -d',' -f12)
                fail_count=$(echo "$agg_line" | cut -d',' -f4)
                total=$(echo "$agg_line" | cut -d',' -f3)
                fail_rate=$(echo "scale=2; $fail_count * 100 / $total" | bc 2>/dev/null || echo "N/A")
                echo "| $case_name | $rps | $avg | $median | $p95 | ${fail_rate}% |" >> "$summary_file"
            else
                echo "| $case_name | N/A | N/A | N/A | N/A | N/A |" >> "$summary_file"
            fi
        else
            echo "| $case_name | N/A | N/A | N/A | N/A | N/A |" >> "$summary_file"
        fi
    done

    echo "" >> "$summary_file"
    echo "### I/O Wait Test (I/O 대기)" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "| 케이스 | RPS | 평균 응답시간 (ms) | 중앙값 (ms) | 95% (ms) | 실패율 |" >> "$summary_file"
    echo "|--------|-----|-------------------|-------------|----------|--------|" >> "$summary_file"

    for case_name in single_w1 single_w4 multi_w1 multi_w4; do
        stats_file="$RESULTS_DIR/$case_name/io_stats.csv"
        if [ -f "$stats_file" ]; then
            agg_line=$(grep "Aggregated" "$stats_file" 2>/dev/null | tail -1)
            if [ -n "$agg_line" ]; then
                rps=$(echo "$agg_line" | cut -d',' -f10)
                avg=$(echo "$agg_line" | cut -d',' -f6)
                median=$(echo "$agg_line" | cut -d',' -f7)
                p95=$(echo "$agg_line" | cut -d',' -f12)
                fail_count=$(echo "$agg_line" | cut -d',' -f4)
                total=$(echo "$agg_line" | cut -d',' -f3)
                fail_rate=$(echo "scale=2; $fail_count * 100 / $total" | bc 2>/dev/null || echo "N/A")
                echo "| $case_name | $rps | $avg | $median | $p95 | ${fail_rate}% |" >> "$summary_file"
            else
                echo "| $case_name | N/A | N/A | N/A | N/A | N/A |" >> "$summary_file"
            fi
        else
            echo "| $case_name | N/A | N/A | N/A | N/A | N/A |" >> "$summary_file"
        fi
    done

    echo "" >> "$summary_file"
    echo "## 분석 및 결론" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "### 예상 결과" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "1. **Simple Response**: 동기/비동기 차이 미미 (ThreadPoolExecutor 덕분)" >> "$summary_file"
    echo "2. **I/O Wait**: 비동기가 유리 (이벤트 루프 효율성)" >> "$summary_file"
    echo "3. **워커 증가**: RPS 증가, 응답시간 감소" >> "$summary_file"
    echo "4. **인스턴스 증가**: RPS 증가, 부하 분산 효과" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "### 최적 환경 선택 가이드" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "| 워크로드 유형 | 권장 설정 | 이유 |" >> "$summary_file"
    echo "|--------------|----------|------|" >> "$summary_file"
    echo "| CPU 바운드 | 워커 증가 | CPU 병렬 처리 활용 |" >> "$summary_file"
    echo "| I/O 바운드 | 비동기 + 인스턴스 증가 | 이벤트 루프 효율성 + 수평 확장 |" >> "$summary_file"
    echo "| 혼합 | 다중 인스턴스 + 적정 워커 | 균형잡힌 리소스 활용 |" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "---" >> "$summary_file"
    echo "결과 디렉토리: \`$RESULTS_DIR\`" >> "$summary_file"

    log_success "Summary generated: $summary_file"
}

# 메인 실행
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║     동기/비동기 컨텍스트 성능 비교 테스트                      ║"
    echo "║     Sync/Async Context Performance Comparison Test           ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    log_info "Test Configuration:"
    log_info "  - Users: $USERS"
    log_info "  - Spawn Rate: $SPAWN_RATE"
    log_info "  - Run Time: $RUN_TIME"
    log_info "  - Results Directory: $RESULTS_DIR"
    echo ""

    # 기존 환경 정리
    cleanup_all

    # 각 테스트 케이스 실행
    for case_name in $TEST_CASE_NAMES; do
        compose_file=$(get_compose_file "$case_name")
        run_single_test "$case_name" "$compose_file" || {
            log_error "Test failed for $case_name, continuing with next..."
        }

        # 테스트 간 쿨다운
        log_info "Cooling down for 10 seconds..."
        sleep 10
    done

    # 결과 요약 생성
    generate_summary

    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    테스트 완료!                               ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    log_success "Results saved to: $RESULTS_DIR"
    log_info "View summary: cat $RESULTS_DIR/summary.md"
    log_info "View HTML reports in: $RESULTS_DIR/*/simple_report.html"
}

# 스크립트 실행
main "$@"
