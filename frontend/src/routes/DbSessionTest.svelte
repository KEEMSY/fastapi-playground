<script>
    import { onMount } from 'svelte';
    import { performanceMetrics, TestScenarios, runScenario } from '../lib/dbTest'
    import Chart from 'chart.js/auto';
    
    let charts = {};
    let results = [];  // 여러 결과를 저장하기 위한 배열
    let selectedScenario = null;
    
    // DB 세션 시나리오만 필터링 (시나리오 7-9)
    const dbScenarios = TestScenarios.slice(0, 3); // 임시 3개만 실행

    function updateCombinedDbMetricsChart() {
        const canvasId = 'combinedDbMetricsChart';
        
        if (charts[canvasId]) {
            charts[canvasId].destroy();
        }

        const ctx = document.getElementById(canvasId)?.getContext('2d');
        if (!ctx) return;

        const colors = [
            { main: 'rgb(75, 192, 192)', light: 'rgba(75, 192, 192, 0.2)' },
            { main: 'rgb(255, 99, 132)', light: 'rgba(255, 99, 132, 0.2)' },
            { main: 'rgb(54, 162, 235)', light: 'rgba(54, 162, 235, 0.2)' }
        ];

        const datasets = results.flatMap((result, idx) => [
            {
                label: `${result.scenarioName} - 총 연결 수`,
                data: result.dbMetrics.session.timeline.map(m => m.total_connections),
                borderColor: colors[idx].main,
                backgroundColor: colors[idx].light,
                borderWidth: 2,
                tension: 0.4,
                pointRadius: 3,
                pointHoverRadius: 6,
                fill: false
            },
            {
                label: `${result.scenarioName} - 활성 연결 수`,
                data: result.dbMetrics.session.timeline.map(m => m.active_connections),
                borderColor: colors[idx].main,
                backgroundColor: colors[idx].light,
                borderWidth: 2,
                borderDash: [5, 5],
                tension: 0.4,
                pointRadius: 3,
                pointHoverRadius: 6,
                fill: false
            },
            {
                label: `${result.scenarioName} - 가용 연결 수`,
                data: result.dbMetrics.pool.timeline.map(m => m.available_connections),
                borderColor: colors[idx].main,
                backgroundColor: colors[idx].light,
                borderWidth: 2,
                borderDash: [2, 2],
                tension: 0.4,
                pointRadius: 3,
                pointHoverRadius: 6,
                fill: false
            }
        ]);

        charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: results[0]?.dbMetrics.session.timeline.map(m => m.iterationNumber) || [],
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                plugins: {
                    title: {
                        display: true,
                        text: '시나리오 비교 - DB 연결 메트릭스',
                        font: {
                            size: 16,
                            weight: 'bold'
                        },
                        padding: 20
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.9)',
                        titleColor: '#000',
                        titleFont: {
                            size: 14,
                            weight: 'bold'
                        },
                        bodyColor: '#000',
                        bodyFont: {
                            size: 13
                        },
                        borderColor: '#ddd',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true,
                        callbacks: {
                            title: (tooltipItems) => {
                                return `반복 횟수: ${tooltipItems[0].label}`;
                            },
                            label: (context) => {
                                return ` ${context.dataset.label}: ${context.parsed.y}개`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: '반복 횟수',
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: '연결 수',
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    }
                }
            }
        });
    }

    async function executeAllScenarios() {
        results = []; // 결과 초기화
        for (const scenario of dbScenarios) {
            const result = await runScenario(scenario);
            results = [...results, result];
        }
        // 모든 시나리오 실행 후 통합 차트 업데이트
        setTimeout(() => {
            updateCombinedDbMetricsChart();
        }, 0);
    }

    async function executeScenario(scenario) {
        const result = await runScenario(scenario);
        // 동일한 시나리오가 있다면 제거
        results = results.filter(r => r.scenarioName !== result.scenarioName);
        // 새로운 결과 추가
        results = [...results, result];
        // 차트 업데이트
        setTimeout(() => {
            updateCombinedDbMetricsChart();
        }, 0);
    }

    function updateDbMetricsChart(metrics, scenarioName) {
        const canvasId = `dbMetricsChart-${scenarioName}`;
        
        if (charts[canvasId]) {
            charts[canvasId].destroy();
        }

        const ctx = document.getElementById(canvasId)?.getContext('2d');
        if (!ctx) return;

        charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: metrics.dbMetrics.session.timeline.map(m => m.iterationNumber),
                datasets: [
                    {
                        label: '총 연결 수',
                        data: metrics.dbMetrics.session.timeline.map(m => m.total_connections),
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    },
                    {
                        label: '활성 연결 수',
                        data: metrics.dbMetrics.session.timeline.map(m => m.active_connections),
                        borderColor: 'rgb(255, 99, 132)',
                        tension: 0.1
                    },
                    {
                        label: '가용 연결 수',
                        data: metrics.dbMetrics.pool.timeline.map(m => m.available_connections),
                        borderColor: 'rgb(54, 162, 235)',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'DB 연결 메트릭스'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    function showScenarioDetails(result) {
        selectedScenario = result;
        // 모달이 표시된 후 차트 생성을 위해 setTimeout 사용
        setTimeout(() => {
            updateModalChart(result);
        }, 0);
    }

    function updateModalChart(result) {
        const canvasId = `dbMetricsChart-modal-${result.scenarioName}`;
        
        if (charts[canvasId]) {
            charts[canvasId].destroy();
        }

        const ctx = document.getElementById(canvasId)?.getContext('2d');
        if (!ctx) return;

        charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: result.dbMetrics.session.timeline.map(m => m.iterationNumber),
                datasets: [
                    {
                        label: '총 연결 수',
                        data: result.dbMetrics.session.timeline.map(m => m.total_connections),
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 3,
                        pointHoverRadius: 6
                    },
                    {
                        label: '활성 연결 수',
                        data: result.dbMetrics.session.timeline.map(m => m.active_connections),
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 3,
                        pointHoverRadius: 6
                    },
                    {
                        label: '가용 연결 수',
                        data: result.dbMetrics.pool.timeline.map(m => m.available_connections),
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 3,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    title: {
                        display: true,
                        text: `${result.scenarioName} - DB 연결 메트릭스`,
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.9)',
                        titleColor: '#000',
                        bodyColor: '#000',
                        borderColor: '#ddd',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true,
                        callbacks: {
                            title: (tooltipItems) => {
                                return `반복 횟수: ${tooltipItems[0].label}`;
                            },
                            label: (context) => {
                                return ` ${context.dataset.label}: ${context.parsed.y}개`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: '반복 횟수'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: '연결 수'
                        }
                    }
                }
            }
        });
    }

    function closeScenarioDetails() {
        selectedScenario = null;
    }
</script>

<div class="container mt-4">
    <!-- 시나리오 목록 -->
    <div class="scenarios mb-4">
        <div class="card mb-3">
            <div class="card-body">
                <h5 class="card-title">모든 DB 세션 테스트 실행</h5>
                <button class="btn btn-primary" on:click={executeAllScenarios}>
                    전체 실행
                </button>
            </div>
        </div>
        {#each dbScenarios as scenario}
            <div class="card mb-3">
                <div class="card-body">
                    <h5 class="card-title">{scenario.name}</h5>
                    <p class="card-text">{scenario.description}</p>
                    <button class="btn btn-primary" on:click={() => executeScenario(scenario)}>
                        실행
                    </button>
                </div>
            </div>
        {/each}
    </div>

    <!-- 통합 결과 차트 -->
    {#if results.length > 0}
        <div class="card mb-4">
            <div class="card-header">
                <h5>시나리오 비교</h5>
            </div>
            <div class="card-body">
                <div class="chart-container" style="position: relative; height:60vh; width:100%">
                    <canvas id="combinedDbMetricsChart"></canvas>
                </div>
            </div>
        </div>

        <!-- 통합 결과 테이블 -->
        <div class="card mb-4">
            <div class="card-header">
                <h5>시나리오 결과 비교</h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>시나리오</th>
                                <th>평균 총 연결 수</th>
                                <th>평균 활성 연결 수</th>
                                <th>평균 가용 연결 수</th>
                                <th>최대 연결 스레드</th>
                                <th>최대 실행 스레드</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each results as result}
                                <tr class="cursor-pointer" on:click={() => showScenarioDetails(result)}>
                                    <td>{result.scenarioName}</td>
                                    <td>{result.dbMetrics.session.averageTotalConnections?.toFixed(0) || '0'}</td>
                                    <td>{result.dbMetrics.session.averageActiveConnections?.toFixed(0) || '0'}</td>
                                    <td>{result.dbMetrics.pool.averageAvailableConnections?.toFixed(0) || '0'}</td>
                                    <td>{result.dbMetrics.session.maxThreadsConnected || '0'}</td>
                                    <td>{result.dbMetrics.session.maxThreadsRunning || '0'}</td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    {/if}

    <!-- 개별 결과 카드들 제거 -->
</div>

<!-- 시나리오 상세 정보 모달 -->
{#if selectedScenario}
    <div class="modal-backdrop" on:click={closeScenarioDetails}></div>
    <div class="modal-container">
        <div class="modal-content">
            <div class="modal-header">
                <h4>{selectedScenario.scenarioName} 상세 정보</h4>
                <button type="button" class="btn-close" on:click={closeScenarioDetails}></button>
            </div>
            <div class="modal-body">
                <div class="row">
                    <!-- 세션 정보 카드 -->
                    <div class="col-md-6 mb-4">
                        <div class="card h-100">
                            <div class="card-header bg-light">
                                <h6 class="mb-0">세션 정보</h6>
                            </div>
                            <div class="card-body">
                                <div class="info-grid">
                                    <div class="info-item">
                                        <span class="label">총 연결 수</span>
                                        <span class="value">{selectedScenario.dbMetrics.session.averageTotalConnections?.toFixed(0) || '0'}</span>
                                    </div>
                                    <div class="info-item">
                                        <span class="label">활성 연결 수</span>
                                        <span class="value">{selectedScenario.dbMetrics.session.averageActiveConnections?.toFixed(0) || '0'}</span>
                                    </div>
                                    <div class="info-item">
                                        <span class="label">연결 스레드</span>
                                        <span class="value">{selectedScenario.dbMetrics.session.maxThreadsConnected || '0'}</span>
                                    </div>
                                    <div class="info-item">
                                        <span class="label">실행 스레드</span>
                                        <span class="value">{selectedScenario.dbMetrics.session.maxThreadsRunning || '0'}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 풀 정보 카드 -->
                    <div class="col-md-6 mb-4">
                        <div class="card h-100">
                            <div class="card-header bg-light">
                                <h6 class="mb-0">커넥션 풀 정보</h6>
                            </div>
                            <div class="card-body">
                                <div class="info-grid">
                                    <div class="info-item">
                                        <span class="label">최대 연결 수</span>
                                        <span class="value">{selectedScenario.dbMetrics.pool.maxConnections || '0'}</span>
                                    </div>
                                    <div class="info-item">
                                        <span class="label">현재 연결 수</span>
                                        <span class="value">{selectedScenario.dbMetrics.pool.averageCurrentConnections?.toFixed(0) || '0'}</span>
                                    </div>
                                    <div class="info-item">
                                        <span class="label">가용 연결 수</span>
                                        <span class="value">{selectedScenario.dbMetrics.pool.averageAvailableConnections?.toFixed(0) || '0'}</span>
                                    </div>
                                    <div class="info-item">
                                        <span class="label">대기 시간 제한</span>
                                        <span class="value">{selectedScenario.dbMetrics.pool.waitTimeout || '0'}s</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- 모달 차트 -->
                <div class="modal-chart-container">
                    <canvas id="dbMetricsChart-modal-{selectedScenario.scenarioName}"></canvas>
                </div>
            </div>
        </div>
    </div>
{/if}

<style>
    .chart-container {
        margin: 20px 0;
        padding: 10px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
        background: #fff;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }

    .card-header {
        background-color: #f8f9fa;
        border-bottom: 1px solid rgba(0,0,0,0.125);
        padding: 1rem;
    }

    .card-header h5 {
        margin: 0;
        color: #495057;
    }

    .card-body {
        padding: 1.25rem;
    }

    .cursor-pointer {
        cursor: pointer;
    }
    
    .cursor-pointer:hover {
        background-color: #f8f9fa;
    }

    .modal-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
        z-index: 1000;
    }

    .modal-container {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 90%;
        max-width: 1200px;
        max-height: 90vh;
        overflow-y: auto;
        z-index: 1001;
    }

    .modal-content {
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }

    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem;
        border-bottom: 1px solid #dee2e6;
    }

    .modal-body {
        padding: 1.5rem;
    }

    .modal-chart-container {
        height: 400px;
        margin-top: 2rem;
        padding: 1rem;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .info-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 0.5rem;
    }

    .info-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem;
        background-color: #f8f9fa;
        border-radius: 4px;
    }

    .info-item .label {
        color: #666;
        font-size: 0.9rem;
    }

    .info-item .value {
        font-weight: bold;
        color: #333;
    }
</style> 