<script>
    import { onMount } from 'svelte';
    import { performanceMetrics } from '../lib/apiGateway';
    import { TestScenarios, runScenario } from '../lib/apiGateway';
    import Chart from 'chart.js/auto';
    
    let testResults = [];
    let isRunning = false;
    let currentScenario = null;
    let progress = 0;
    let chart;

    // DB 세션 시나리오만 필터링 (시나리오 7-15)
    const dbScenarios = TestScenarios.slice(6);
    
    async function runTests() {
        if (isRunning) return;
        
        isRunning = true;
        testResults = [];
        progress = 0;
        
        const totalScenarios = dbScenarios.length;
        
        try {
            for (let i = 0; i < dbScenarios.length; i++) {
                currentScenario = dbScenarios[i];
                const result = await runScenario(dbScenarios[i]);
                testResults = [...testResults, result];
                progress = ((i + 1) / totalScenarios) * 100;
            }
        } catch (error) {
            console.error('테스트 실행 중 오류:', error);
        } finally {
            isRunning = false;
            currentScenario = null;
            updateChart();
        }
    }

    function updateChart() {
        const ctx = document.getElementById('dbPerformanceChart');
        if (!ctx) return;
        
        if (chart) {
            chart.destroy();
        }

        const data = testResults.map(result => ({
            name: result.scenarioName,
            totalTime: result.totalTime / 1000,
            avgTime: result.averageRequestTime / 1000,
            successRate: result.successRate * 100
        }));

        chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.map(d => d.name),
                datasets: [
                    {
                        label: '총 실행시간 (초)',
                        data: data.map(d => d.totalTime),
                        backgroundColor: 'rgba(54, 162, 235, 0.5)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    },
                    {
                        label: '평균 요청시간 (초)',
                        data: data.map(d => d.avgTime),
                        backgroundColor: 'rgba(255, 99, 132, 0.5)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: '시간 (초)'
                        }
                    }
                }
            }
        });
    }
</script>

<div class="container mt-4">
    <div class="card mb-4">
        <div class="card-header">
            <h4>🔍 DB 세션 성능 테스트</h4>
        </div>
        <div class="card-body">
            <!-- DB 세션 테스트 설명 -->
            <div class="alert alert-info mb-4">
                <h5>📊 DB 세션 테스트 시나리오</h5>
                <div class="row mt-3">
                    <div class="col-md-4">
                        <div class="test-type-card">
                            <h6>기본 DB 세션 테스트 (시나리오 7-9)</h6>
                            <ul class="small">
                                <li>동기 메서드 + 동기 DB</li>
                                <li>비동기 메서드 + 동기 DB</li>
                                <li>비동기 메서드 + 비동기 DB</li>
                            </ul>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="test-type-card">
                            <h6>대규모 요청 테스트 (시나리오 10-12)</h6>
                            <ul class="small">
                                <li>50개 동시 요청</li>
                                <li>각 패턴별 성능 비교</li>
                                <li>동시성 처리 효율 측정</li>
                            </ul>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="test-type-card">
                            <h6>초대규모 요청 테스트 (시나리오 13-15)</h6>
                            <ul class="small">
                                <li>100개 동시 요청</li>
                                <li>시스템 한계 테스트</li>
                                <li>패턴별 확장성 비교</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 실행 버튼 -->
            <button 
                class="btn btn-primary mb-4" 
                on:click={runTests} 
                disabled={isRunning}
            >
                {#if isRunning}
                    <span class="spinner-border spinner-border-sm me-2" role="status"></span>
                    테스트 실행 중...
                {:else}
                    DB 세션 테스트 시작
                {/if}
            </button>

            <!-- 진행 상황 -->
            {#if isRunning}
                <div class="progress mb-4">
                    <div 
                        class="progress-bar" 
                        role="progressbar" 
                        style="width: {progress}%" 
                        aria-valuenow={progress} 
                        aria-valuemin="0" 
                        aria-valuemax="100"
                    >
                        {progress.toFixed(0)}%
                    </div>
                </div>
            {/if}

            <!-- 차트 -->
            <div class="row mb-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h5>📊 성능 비교 차트</h5>
                        </div>
                        <div class="card-body">
                            <div class="chart-container">
                                <canvas id="dbPerformanceChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 결과 테이블 -->
            {#if testResults.length > 0}
                <div class="row">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <h5>📋 상세 테스트 결과</h5>
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-hover">
                                        <thead class="table-light">
                                            <tr>
                                                <th>시나리오</th>
                                                <th class="text-center">총 실행시간</th>
                                                <th class="text-center">평균 요청시간</th>
                                                <th class="text-center">성공률</th>
                                                <th class="text-center">효율성</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {#each testResults as result}
                                                <tr>
                                                    <td>{result.scenarioName}</td>
                                                    <td class="text-center">
                                                        <span class="badge bg-primary">
                                                            {(result.totalTime / 1000).toFixed(2)}s
                                                        </span>
                                                    </td>
                                                    <td class="text-center">
                                                        <span class="badge bg-info">
                                                            {(result.averageRequestTime / 1000).toFixed(2)}s
                                                        </span>
                                                    </td>
                                                    <td class="text-center">
                                                        <span class="badge bg-success">
                                                            {(result.successRate * 100).toFixed(1)}%
                                                        </span>
                                                    </td>
                                                    <td class="text-center">
                                                        <span class="badge bg-warning text-dark">
                                                            {result.efficiency.toFixed(1)}%
                                                        </span>
                                                    </td>
                                                </tr>
                                            {/each}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            {/if}
        </div>
    </div>
</div>

<style>
    .chart-container {
        height: 400px;
        position: relative;
        margin: 1rem 0;
    }

    .test-type-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .test-type-card h6 {
        color: #0d6efd;
        margin-bottom: 0.5rem;
    }

    .test-type-card ul {
        padding-left: 1.2rem;
        margin-bottom: 0;
    }

    .test-type-card li {
        margin-bottom: 0.2rem;
    }

    .badge {
        font-size: 0.9rem;
        padding: 0.5em 1em;
    }

    .table th {
        font-weight: 600;
    }

    .card {
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    .card-header {
        background-color: #f8f9fa;
        border-bottom: 1px solid rgba(0,0,0,0.125);
    }

    .card-header h5 {
        margin: 0;
        color: #495057;
    }
</style> 