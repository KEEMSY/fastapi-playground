#!/bin/bash
# DB 세션 풀 크기 및 인스턴스 수에 따른 성능 분석 자동화 스크립트
# Usage: ./scripts/analyze_pool_vs_instances.sh

set -e

# 결과 저장 경로
RESULTS_BASE="performance_tests/results/experiment_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_BASE"

# 실험 매트릭스 정의
# (인스턴스_수 풀_크기 케이스명)
experiments=(
    "1 5  A1_Single_SmallPool"
    "1 20 A2_Single_LargePool"
    "3 5  B1_Multi_SmallPool"
    "3 20 B2_Multi_LargePool"
)

echo "=========================================================="
echo " DB Session Pool vs Instances Performance Experiment"
echo "=========================================================="
echo "Results will be saved to: $RESULTS_BASE"

for exp in "${experiments[@]}"; do
    read -r instances pool_size name <<< "$exp"
    
    echo ""
    echo ">>> Running Test Case: $name (Instances: $instances, Pool: $pool_size)"
    
    # 1. 환경 정리
    docker-compose -f docker-compose-test-multi-w4.yml down -v > /dev/null 2>&1 || true
    
    # 2. 환경 변수 설정 및 실행
    export DB_POOL_SIZE=$pool_size
    if [ "$instances" -eq 1 ]; then
        COMPOSE_FILE="docker-compose-test-single-w4.yml"
        docker-compose -f "$COMPOSE_FILE" up -d --build
    else
        COMPOSE_FILE="docker-compose-test-multi-w4.yml"
        docker-compose -f "$COMPOSE_FILE" up -d --build --scale app=$instances
    fi
    
    echo "Waiting for containers to be ready..."
    sleep 15
    
    # 3. 부하 테스트 실행
    TEST_DIR="$RESULTS_BASE/$name"
    mkdir -p "$TEST_DIR"
    
    locust -f performance_tests/locustfile_db.py \
        --host=http://localhost:7777 \
        --users 100 \
        --spawn-rate 10 \
        --run-time 1m \
        --headless \
        --csv "$TEST_DIR/result" \
        --html "$TEST_DIR/report.html"
        
    echo "Test Case $name completed."
    
    # 4. 환경 종료
    docker-compose -f "$COMPOSE_FILE" down -v > /dev/null 2>&1
done

echo ""
echo "=========================================================="
echo " All experiments completed!"
echo " Summary of results available in: $RESULTS_BASE"
echo "=========================================================="
