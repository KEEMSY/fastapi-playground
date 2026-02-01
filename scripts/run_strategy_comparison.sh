#!/bin/bash
# 두 가지 확장 전략 비교 테스트 스크립트: 수직 확장(Pool 60) vs 수평 확장(3 Inst x 20 Pool)

set -e

# 결과 저장 폴더
COMP_DIR="performance_tests/results/comparison_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$COMP_DIR"

echo "=========================================================="
echo " 전략 비교 시작: 수직 확장 vs 수평 확장"
echo "=========================================================="

# 시나리오 1: 수직 확장 (Single Instance, Large Pool)
echo ">>> [1/2] 시나리오 1 실행: 단일 인스턴스, Pool 60"
export DB_POOL_SIZE=60
docker-compose -f docker-compose-test-single-w4.yml down -v > /dev/null 2>&1 || true
docker-compose -f docker-compose-test-single-w4.yml up -d --build

echo "Waiting for environment to stabilize..."
sleep 15

locust -f performance_tests/locustfile_db.py \
    --host=http://localhost:7777 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 1m \
    --headless \
    --csv "$COMP_DIR/case1_vertical" \
    --html "$COMP_DIR/case1_report.html"

docker-compose -f docker-compose-test-single-w4.yml down -v

echo "----------------------------------------------------------"

# 시나리오 2: 수평 확장 (Multiple Instances, Balanced Pool)
echo ">>> [2/2] 시나리오 2 실행: 3개 인스턴스, 각 Pool 20 (Total 60)"
export DB_POOL_SIZE=20
docker-compose -f docker-compose-test-multi-w4.yml down -v > /dev/null 2>&1 || true
docker-compose -f docker-compose-test-multi-w4.yml up -d --build --scale app1=1 --scale app2=1 --scale app3=1

echo "Waiting for environment to stabilize..."
sleep 15

locust -f performance_tests/locustfile_db.py \
    --host=http://localhost:7777 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 1m \
    --headless \
    --csv "$COMP_DIR/case2_horizontal" \
    --html "$COMP_DIR/case2_report.html"

docker-compose -f docker-compose-test-multi-w4.yml down -v

# 결과 분석 Python 실행
if [ -f "scripts/analyze_comparison.py" ]; then
    python3 scripts/analyze_comparison.py "$COMP_DIR"
fi
