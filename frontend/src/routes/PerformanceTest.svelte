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
    let chartView = 'basic';
    let filteredResults = [];
    
    // 일반 성능 테스트 시나리오만 필터링 (시나리오 1-6)
    const generalScenarios = TestScenarios.slice(0, 6);
    
    function initChart() {
        const ctx = document.getElementById('performanceChart');
        if (!ctx) return;
        
        if (chart) {
            chart.destroy();
        }

        filteredResults = testResults.filter(result => 
            chartView === 'basic' ? 
                result.scenarioName.includes('반복') : 
                result.scenarioName.includes('50개')
        );
        
        const chartData = {
            labels: filteredResults.map(r => {
                const name = r.scenarioName.split(':')[1].trim();
                return name
                    .replace(' (3회 반복)', '')
                    .replace(' (50개)', '')
                    .replace('비동기 메서드 + ', '')
                    .replace('동기 메서드 + ', '');
            }),
            datasets: [
                {
                    label: '실제 실행 시간',
                    data: filteredResults.map(r => r.totalTime / 1000),
                    backgroundColor: filteredResults.map(r => {
                        if (r.efficiency >= 90) return 'rgba(40, 167, 69, 0.7)';
                        if (r.efficiency >= 50) return 'rgba(255, 193, 7, 0.7)';
                        return 'rgba(220, 53, 69, 0.7)';
                    }),
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 1,
                    barPercentage: 0.7
                },
                {
                    label: '이론적 실행 시간',
                    data: filteredResults.map(r => r.totalTheoreticalTime / 1000),
                    backgroundColor: 'rgba(54, 162, 235, 0.7)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1,
                    barPercentage: 0.7
                }
            ]
        };
        
        chart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: true,
                indexAxis: 'x',
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    tooltip: {
                        enabled: true,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleFont: { size: 14 },
                        bodyFont: { size: 13 },
                        callbacks: {
                            beforeTitle: function(context) {
                                const dataIndex = context[0].dataIndex;
                                const result = filteredResults[dataIndex];
                                return result?.scenarioName || '';
                            },
                            label: function(context) {
                                const dataIndex = context.dataIndex;
                                const result = filteredResults[dataIndex];
                                if (!result) return '';

                                if (context.datasetIndex === 0) {
                                    return [
                                        `실제 실행 시간: ${(result.totalTime / 1000).toFixed(2)}초`,
                                        `총 요청 수: ${result.totalRequests}개`,
                                        `효율성: ${result.efficiency.toFixed(1)}%`,
                                        `반복 횟수: ${result.iterations}회`
                                    ];
                                } else {
                                    return [`이론적 실행 시간: ${(result.totalTheoreticalTime / 1000).toFixed(2)}초`];
                                }
                            }
                        }
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            font: { size: 12 }
                        }
                    },
                    title: {
                        display: true,
                        text: chartView === 'basic' ? 
                            '기본 시나리오 성능 비교 (3회 반복)' : 
                            '대규모 동시 요청 성능 비교 (50개 요청)',
                        font: { size: 16 }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: '시나리오',
                            font: { size: 12 }
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: '실행 시간 (초)',
                            font: { size: 12 }
                        },
                        beginAtZero: true
                    }
                }
            }
        });
    }

    function updateChart() {
        if (!chart || testResults.length === 0) {
            initChart();
            return;
        }

        filteredResults = testResults.filter(result => 
            chartView === 'basic' ? 
                result.scenarioName.includes('반복') : 
                result.scenarioName.includes('50개')
        );

        chart.data.labels = filteredResults.map(r => {
            const name = r.scenarioName.split(':')[1].trim();
            return name
                .replace(' (3회 반복)', '')
                .replace(' (50개)', '')
                .replace('비동기 메서드 + ', '')
                .replace('동기 메서드 + ', '');
        });

        chart.data.datasets[0].data = filteredResults.map(r => r.totalTime / 1000);
        chart.data.datasets[1].data = filteredResults.map(r => r.totalTheoreticalTime / 1000);
        chart.data.datasets[0].backgroundColor = filteredResults.map(r => {
            if (r.efficiency >= 90) return 'rgba(40, 167, 69, 0.7)';
            if (r.efficiency >= 50) return 'rgba(255, 193, 7, 0.7)';
            return 'rgba(220, 53, 69, 0.7)';
        });

        chart.options.plugins.title.text = chartView === 'basic' ? 
            '기본 시나리오 성능 비교 (3회 반복)' : 
            '대규모 동시 요청 성능 비교 (50개 요청)';

        chart.update();
    }

    function formatDuration(ms) {
        if (ms < 1000) return `${ms.toFixed(1)}ms`;
        return `${(ms/1000).toFixed(2)}초`;
    }

    function formatPercentage(value) {
        return `${(value * 100).toFixed(1)}%`;
    }

    async function runTests() {
        if (isRunning) return;
        
        isRunning = true;
        testResults = [];
        progress = 0;
        
        const totalScenarios = generalScenarios.length;
        
        try {
            for (let i = 0; i < generalScenarios.length; i++) {
                currentScenario = generalScenarios[i];
                const result = await runScenario(generalScenarios[i]);
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

    onMount(() => {
        if (testResults.length > 0) {
            initChart();
        }
    });

    $: if (testResults.length > 0) {
        updateChart();
    }

    $: if (chartView) {
        updateChart();
    }
</script>

<div class="container mt-4">
    <div class="card mb-4">
        <div class="card-header bg-primary text-white">
            <h2 class="mb-0">동기/비동기 성능 테스트 대시보드</h2>
        </div>
        <div class="card-body">
            <div class="alert alert-info">
                <h5>📊 성능 지표 설명</h5>
                <ul class="mb-0">
                    <li><strong>효율성</strong>: (이론적 처리 시간 / 실제 처리 시간) × 100%
                        <ul>
                            <li>100% = 이론값과 동일한 성능</li>
                            <li>100% 초과 = 이론값보다 빠른 처리</li>
                            <li>100% 미만 = 이론값보다 느린 처리</li>
                        </ul>
                    </li>
                    <li><strong>이론적 시간</strong>: 가장 긴 대기 시간 (동시 실행 가정)</li>
                    <li><strong>실제 시간</strong>: 모든 요청이 완료될 때까지의 시간</li>
                </ul>
            </div>
            <div class="alert alert-secondary mt-3">
                <h5>🔄 테스트 시나리오</h5>
                <ul class="mb-0">
                    <li><strong>기본 시나리오 (1-3)</strong>
                        <ul>
                            <li>10개 동시 요청을 3회 반복</li>
                            <li>각 요청은 1~3초의 대기 시간</li>
                            <li>처리 방식별 성능 비교</li>
                        </ul>
                    </li>
                    <li><strong>대규모 동시 요청 (4-5)</strong>
                        <ul>
                            <li>50개 요청을 단일 시점에 실행</li>
                            <li>모든 요청은 2초의 대기 시간</li>
                            <li>동기/비동기 방식 비교</li>
                        </ul>
                    </li>
                </ul>
            </div>
            <button 
                class="btn btn-lg btn-primary mt-3" 
                on:click={runTests} 
                disabled={isRunning}>
                {#if isRunning}
                    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    테스트 실행 중...
                {:else}
                    성능 테스트 시작
                {/if}
            </button>
        </div>
    </div>

    {#if isRunning}
        <div class="progress mb-4" style="height: 25px;">
            <div class="progress-bar progress-bar-striped progress-bar-animated"
                role="progressbar" 
                style="width: {progress}%" 
                aria-valuenow={progress} 
                aria-valuemin="0" 
                aria-valuemax="100">
                {progress.toFixed(0)}% - {currentScenario?.name || '준비 중...'}
            </div>
        </div>
    {/if}

    {#if testResults.length > 0}
        <div class="card mb-4">
            <div class="card-header">
                <h3 class="mb-0">📊 성능 비교 차트</h3>
            </div>
            <div class="card-body">
                <div class="row mb-3">
                    <div class="col">
                        <div class="btn-group">
                            <button class="btn btn-outline-primary" 
                                    class:active={chartView === 'basic'}
                                    on:click={() => chartView = 'basic'}>
                                기본 시나리오 (1-3)
                            </button>
                            <button class="btn btn-outline-primary" 
                                    class:active={chartView === 'massive'}
                                    on:click={() => chartView = 'massive'}>
                                대규모 요청 (4-6)
                            </button>
                        </div>
                    </div>
                </div>
                <div style="height: 400px">
                    <canvas id="performanceChart"></canvas>
                </div>
            </div>
        </div>

        <div class="card mb-4">
            <div class="card-header">
                <h3 class="mb-0">📈 전체 테스트 요약</h3>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-body text-center">
                                <h6 class="card-title">총 요청 수</h6>
                                <h3 class="card-text">
                                    {testResults.reduce((acc, result) => acc + result.totalRequests, 0)}개
                                </h3>
                                <small class="text-muted">
                                    시나리오당 {testResults[0]?.totalRequests}개
                                </small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-body text-center">
                                <h6 class="card-title">총 실행 시간</h6>
                                <h3 class="card-text">
                                    {formatDuration(testResults.reduce((acc, result) => acc + result.totalTime, 0))}
                                </h3>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-body text-center">
                                <h6 class="card-title">평균 성공률</h6>
                                <h3 class="card-text">
                                    {formatPercentage(testResults.reduce((acc, result) => acc + result.successRate, 0) / testResults.length)}
                                </h3>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-body text-center">
                                <h6 class="card-title">시나리오 수</h6>
                                <h3 class="card-text">
                                    {testResults.length}개
                                </h3>
                                <small class="text-muted">
                                    각 {testResults[0]?.iterations}회 반복
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card mb-3">
            <div class="card-header">
                <h5 class="mb-0">📝 상세 결과 테이블 가이드</h5>
            </div>
            <div class="card-body">
                <ul class="mb-0">
                    <li><strong>반복</strong>: 현재 실행 회차</li>
                    <li><strong>요청 유형</strong>: API 엔드포인트의 처리 방식</li>
                    <li><strong>대기 시간</strong>: 서버에 설정된 의도적인 대기 시간</li>
                    <li><strong>실제 소요 시간</strong>: 요청부터 응답까지 실제 걸린 시간(대기 시간 + 네트워크 지연 + 서버 처리 시간 등이 포함)</li>
                    <li><strong>반복 내 총시간</strong>: 해당 반복의 10개 요청이 모두 완료되는데 걸린 시간</li>
                    <li><strong>개별 요청 평균</strong>: 각 요청이 완료되는데 걸린 시간의 평균값 (병렬 처리 시 총시간보다 작음)</li>
                    <li><strong>상태</strong>: 요청의 성공/실패 여부</li>
                </ul>
            </div>
        </div>

        <div class="accordion mb-5" id="testResults">
            {#each testResults as result, i}
                <div class="accordion-item">
                    <h2 class="accordion-header">
                        <button class="accordion-button {i === testResults.length - 1 ? '' : 'collapsed'}" 
                                type="button" 
                                data-bs-toggle="collapse" 
                                data-bs-target="#collapse{i}">
                            <div class="w-100">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <strong>{result.scenarioName}</strong>
                                        <br/>
                                        <small class="text-muted">{result.description}</small>
                                    </div>
                                    <div class="text-end">
                                        <span class="badge {result.efficiency > 100 ? 'bg-success' : 'bg-warning'}">
                                            효율성: {result.efficiency.toFixed(1)}%
                                        </span>
                                        <br/>
                                        <small class="text-muted">
                                            요청 수: {result.totalRequests}개
                                        </small>
                                    </div>
                                </div>
                            </div>
                        </button>
                    </h2>
                    <div id="collapse{i}" 
                         class="accordion-collapse collapse {i === testResults.length - 1 ? 'show' : ''}" 
                         data-bs-parent="#testResults">
                        <div class="accordion-body">
                            <div class="row mb-3">
                                <div class="col-md-4">
                                    <div class="card">
                                        <div class="card-body">
                                            <h6 class="card-title">실제 실행 시간</h6>
                                            <p class="card-text">
                                                <strong>전체:</strong> {formatDuration(result.totalTime)}<br/>
                                                <strong>1회당:</strong> {formatDuration(result.totalTime / result.iterations)}<br/>
                                                <small class="text-muted">
                                                    총 {result.iterations}회 반복 실행
                                                </small>
                                            </p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="card">
                                        <div class="card-body">
                                            <h6 class="card-title">이론적 실행 시간</h6>
                                            <p class="card-text">
                                                <strong>전체:</strong> {formatDuration(result.totalTheoreticalTime)}<br/>
                                                <strong>1회당:</strong> {formatDuration(result.theoreticalTimePerIteration)}<br/>
                                                <small class="text-muted">
                                                    동시 실행 시 예상 시간
                                                </small>
                                            </p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="card">
                                        <div class="card-body">
                                            <h6 class="card-title">효율성 분석</h6>
                                            <p class="card-text">
                                                <strong>효율성:</strong> {result.efficiency.toFixed(1)}%<br/>
                                                <strong>추가시간:</strong> {formatDuration(result.overhead)}<br/>
                                                <small class="text-muted">
                                                    효율성 = (이론 시간 / 실제 시간) × 100<br/>
                                                    추가시간 = 실제 시간 - 이론 시간
                                                </small>
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- 반복 회차별 아코디언 추가 -->
                            <div class="accordion" id="iterationAccordion{i}">
                                {#each Array(result.iterations) as _, iterIndex}
                                    {@const iterationResults = result.endpointResults.filter(er => er.iterationNumber === iterIndex + 1)}
                                    <div class="accordion-item">
                                        <h2 class="accordion-header">
                                            <button class="accordion-button collapsed" 
                                                    type="button" 
                                                    data-bs-toggle="collapse" 
                                                    data-bs-target="#iteration{i}-{iterIndex}">
                                                <div class="w-100 d-flex justify-content-between align-items-center">
                                                    <span>
                                                        <strong>{iterIndex + 1}회차</strong> 실행 결과
                                                    </span>
                                                    <span>
                                                        <span class="badge bg-secondary me-2">
                                                            총 소요시간: {formatDuration(result.iterationTimes[iterIndex])}
                                                        </span>
                                                        <span class="badge bg-info">
                                                            요청 수: {iterationResults.length}개
                                                        </span>
                                                    </span>
                                                </div>
                                            </button>
                                        </h2>
                                        <div id="iteration{i}-{iterIndex}" 
                                             class="accordion-collapse collapse" 
                                             data-bs-parent="#iterationAccordion{i}">
                                            <div class="accordion-body">
                                                <div class="table-responsive">
                                                    <table class="table table-sm table-hover">
                                                        <thead class="table-light">
                                                            <tr>
                                                                <th>요청 유형</th>
                                                                <th>엔드포인트</th>
                                                                <th>대기 시간</th>
                                                                <th>실제 소요 시간</th>
                                                                <th>상태</th>
                                                                <th>처리 방식</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {#each iterationResults as er}
                                                                <tr>
                                                                    <td>{er.endpoint}</td>
                                                                    <td>
                                                                        <small class="text-muted">
                                                                            <code>/api/v1/standard/{er.path}</code>
                                                                            {#if er.timeout}
                                                                                <span class="text-nowrap">
                                                                                    <code>?timeout={er.timeout}</code>
                                                                                </span>
                                                                            {/if}
                                                                        </small>
                                                                        <button class="btn btn-sm btn-outline-secondary ms-2"
                                                                                title="전체 URL 복사"
                                                                                on:click={() => {
                                                                                    navigator.clipboard.writeText(
                                                                                        `http://localhost:7777/api/v1/standard/${er.path}${er.timeout ? `?timeout=${er.timeout}` : ''}`
                                                                                    );
                                                                                }}>
                                                                            <i class="bi bi-clipboard"></i>
                                                                        </button>
                                                                    </td>
                                                                    <td>{er.timeout}초</td>
                                                                    <td>{formatDuration(er.time)}</td>
                                                                    <td>
                                                                        {#if er.success}
                                                                            <span class="badge bg-success">성공</span>
                                                                        {:else}
                                                                            <span class="badge bg-danger">실패</span>
                                                                        {/if}
                                                                    </td>
                                                                    <td>
                                                                        {#if er.path.includes('async')}
                                                                            <span class="badge bg-info">비동기</span>
                                                                        {:else}
                                                                            <span class="badge bg-warning text-dark">동기</span>
                                                                        {/if}
                                                                    </td>
                                                                </tr>
                                                                {#if er.data?.data?.message}
                                                                    <tr class="table-light">
                                                                        <td colspan="6">
                                                                            <small class="text-muted">
                                                                                <i class="bi bi-arrow-return-right"></i> 
                                                                                응답: {er.data.data.message}
                                                                            </small>
                                                                        </td>
                                                                    </tr>
                                                                {/if}
                                                            {/each}
                                                            <tr class="table-secondary">
                                                                <td colspan="3"><strong>회차 총계</strong></td>
                                                                <td colspan="3">
                                                                    <strong>총 소요시간:</strong> {formatDuration(result.iterationTimes[iterIndex])}
                                                                    <br/>
                                                                    <small class="text-muted">
                                                                        평균 요청 시간: {formatDuration(iterationResults.reduce((acc, r) => acc + r.time, 0) / iterationResults.length)}
                                                                    </small>
                                                                </td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                {/each}
                            </div>

                            <!-- 전체 요약 테이블 -->
                            <div class="card mt-3">
                                <div class="card-header">
                                    <h6 class="mb-0">전체 실행 요약</h6>
                                </div>
                                <div class="card-body">
                                    <div class="table-responsive">
                                        <table class="table table-sm">
                                            <thead class="table-light">
                                                <tr>
                                                    <th>회차</th>
                                                    <th>총 소요시간</th>
                                                    <th>개별 요청 평균</th>
                                                    <th>성공률</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {#each result.iterationTimes as time, idx}
                                                    {@const iterResults = result.endpointResults.filter(er => er.iterationNumber === idx + 1)}
                                                    <tr>
                                                        <td>{idx + 1}회차</td>
                                                        <td>{formatDuration(time)}</td>
                                                        <td>{formatDuration(iterResults.reduce((acc, r) => acc + r.time, 0) / iterResults.length)}</td>
                                                        <td>{formatPercentage(iterResults.filter(r => r.success).length / iterResults.length)}</td>
                                                    </tr>
                                                {/each}
                                                <tr class="table-secondary">
                                                    <td><strong>전체 평균</strong></td>
                                                    <td>{formatDuration(result.averageIterationTime)}</td>
                                                    <td>{formatDuration(result.averageRequestTime)}</td>
                                                    <td>{formatPercentage(result.successRate)}</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>

<style>
    .card {
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .accordion-button:not(.collapsed) {
        background-color: #f8f9fa;
    }
    
    .table-responsive {
        margin-top: 1rem;
    }
    
    .badge {
        font-size: 0.9em;
    }

    .card-text {
        margin-bottom: 0.5rem;
    }

    .card-text strong {
        display: inline-block;
        width: 4.5rem;
    }

    .accordion-button.collapsed {
        background-color: #f8f9fa;
    }
    
    .accordion-button:not(.collapsed) {
        background-color: #e9ecef;
    }
    
    .table-secondary {
        background-color: #f8f9fa;
    }

    code {
        background-color: #f8f9fa;
        padding: 2px 4px;
        border-radius: 4px;
        font-size: 0.9em;
    }
    
    .text-nowrap {
        white-space: nowrap;
    }
    
    .btn-outline-secondary {
        padding: 0.25rem 0.5rem;
        font-size: 0.875rem;
        line-height: 1;
    }
    
    .table td {
        vertical-align: middle;
    }

    .alert ul {
        margin-bottom: 0.5rem;
    }
    
    .alert ul:last-child {
        margin-bottom: 0;
    }
    
    .badge {
        font-size: 0.9em;
        padding: 0.4em 0.6em;
    }

    .btn-group {
        margin-bottom: 1rem;
    }
    
    .btn-outline-primary.active {
        background-color: #0d6efd;
        color: white;
    }

    canvas {
        min-height: 300px;
    }

    .card-body {
        overflow: hidden;
    }
</style> 