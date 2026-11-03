<script>
    import { onMount } from "svelte";
    import {
        productionMetrics,
        ProductionTestScenarios,
        runProductionTest,
        UserActions,
        CustomTestConfigurations,
        runCustomProductionTest,
    } from "../lib/productionTest";
    import Chart from "chart.js/auto";

    let testResults = [];
    let isRunning = false;
    let currentScenario = null;
    let progress = 0;
    let chart;
    let chartView = "basic";
    let activeTab = "predefined";

    // 차트 컬렉션
    let charts = {};

    // 사용자 정의 테스트 설정
    let customUserCount = 50;
    let selectedActions = [];
    let selectedTrafficPattern = CustomTestConfigurations.trafficPatterns[0];

    function initCharts(result) {
        // 이전 차트 정리
        Object.values(charts).forEach((chart) => {
            if (chart) chart.destroy();
        });
        charts = {};

        // 차트 컨테이너가 있는지 확인
        const container = document.getElementById("charts-container");
        if (!container) return;

        // 차트 컨테이너 초기화
        container.innerHTML = `
            <div class="row">
                <div class="col-md-6 mb-4">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0">페이지별 평균 로드 시간</h5>
                        </div>
                        <div class="card-body">
                            <canvas id="pageLoadTimeChart"></canvas>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 mb-4">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0">복잡도별 응답 시간</h5>
                        </div>
                        <div class="card-body">
                            <canvas id="complexityChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row">
                <div class="col-md-6 mb-4">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0">응답 시간 분포</h5>
                        </div>
                        <div class="card-body">
                            <canvas id="responseDistributionChart"></canvas>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 mb-4">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0">처리량 분석</h5>
                        </div>
                        <div class="card-body">
                            <canvas id="throughputChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 페이지별 로드 시간 차트
        renderPageLoadTimeChart(result);

        // 복잡도별 응답 시간 차트
        renderComplexityChart(result);

        // 응답 시간 분포 차트
        renderResponseDistributionChart(result);

        // 처리량 차트
        renderThroughputChart(result);
    }

    // 페이지별 로드 시간 차트
    function renderPageLoadTimeChart(result) {
        if (!result.pageAnalysis || !result.pageAnalysis.pageTimeline) return;

        const ctx = document.getElementById("pageLoadTimeChart");
        if (!ctx) return;

        const pageData = result.pageAnalysis.pageTimeline;

        charts.pageLoadTime = new Chart(ctx, {
            type: "bar",
            data: {
                labels: pageData.map((p) => p.name),
                datasets: [
                    {
                        label: "평균 로드 시간 (ms)",
                        data: pageData.map((p) => p.average),
                        backgroundColor: "rgba(54, 162, 235, 0.7)",
                        borderColor: "rgba(54, 162, 235, 1)",
                        borderWidth: 1,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return `${context.formattedValue} ms`;
                            },
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "시간 (ms)",
                        },
                    },
                },
            },
        });
    }

    // 복잡도별 응답 시간 차트
    function renderComplexityChart(result) {
        if (
            !result.complexityAnalysis ||
            !result.complexityAnalysis.averageComplexityTimes
        )
            return;

        const ctx = document.getElementById("complexityChart");
        if (!ctx) return;

        const complexData = result.complexityAnalysis.averageComplexityTimes;

        charts.complexity = new Chart(ctx, {
            type: "bar",
            data: {
                labels: ["낮음", "중간", "높음"],
                datasets: [
                    {
                        label: "평균 응답 시간 (ms)",
                        data: [
                            complexData.low || 0,
                            complexData.medium || 0,
                            complexData.high || 0,
                        ],
                        backgroundColor: [
                            "rgba(75, 192, 192, 0.7)",
                            "rgba(255, 159, 64, 0.7)",
                            "rgba(255, 99, 132, 0.7)",
                        ],
                        borderColor: [
                            "rgba(75, 192, 192, 1)",
                            "rgba(255, 159, 64, 1)",
                            "rgba(255, 99, 132, 1)",
                        ],
                        borderWidth: 1,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "시간 (ms)",
                        },
                    },
                },
            },
        });
    }

    // 응답 시간 분포 차트
    function renderResponseDistributionChart(result) {
        if (!result.responseTimeDistribution) return;

        const ctx = document.getElementById("responseDistributionChart");
        if (!ctx) return;

        const distribution = result.responseTimeDistribution;

        charts.responseDistribution = new Chart(ctx, {
            type: "bar",
            data: {
                labels: ["P50", "P90", "P95", "P99"],
                datasets: [
                    {
                        label: "응답 시간 (ms)",
                        data: [
                            distribution.p50,
                            distribution.p90,
                            distribution.p95,
                            distribution.p99,
                        ],
                        backgroundColor: "rgba(153, 102, 255, 0.7)",
                        borderColor: "rgba(153, 102, 255, 1)",
                        borderWidth: 1,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const label = context.dataset.label || "";
                                return `${label}: ${context.formattedValue} ms`;
                            },
                            footer: function (tooltipItems) {
                                const dataIndex = tooltipItems[0].dataIndex;
                                const labels = ["50%", "90%", "95%", "99%"];
                                return `${labels[dataIndex]}의 요청이 이 시간 내에 완료됨`;
                            },
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "시간 (ms)",
                        },
                    },
                },
            },
        });
    }

    // 처리량 차트
    function renderThroughputChart(result) {
        if (!result.throughput) return;

        const ctx = document.getElementById("throughputChart");
        if (!ctx) return;

        charts.throughput = new Chart(ctx, {
            type: "bar",
            data: {
                labels: ["초당 처리량"],
                datasets: [
                    {
                        label: "요청/초",
                        data: [result.throughput],
                        backgroundColor: "rgba(255, 206, 86, 0.7)",
                        borderColor: "rgba(255, 206, 86, 1)",
                        borderWidth: 1,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return `${context.formattedValue} 요청/초`;
                            },
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "요청/초",
                        },
                    },
                },
            },
        });
    }

    function formatDuration(ms) {
        if (ms < 1000) return `${ms.toFixed(1)}ms`;
        return `${(ms / 1000).toFixed(2)}초`;
    }

    function formatPercentage(value) {
        return `${(value * 100).toFixed(1)}%`;
    }

    async function runTest() {
        if (isRunning) return;

        isRunning = true;
        progress = 0;

        try {
            currentScenario = ProductionTestScenarios.find(
                (_, i) => document.getElementById("scenario-select").value == i,
            );

            if (!currentScenario) {
                alert("시나리오를 선택해주세요");
                isRunning = false;
                return;
            }

            const result = await runProductionTest(currentScenario);
            testResults = [result, ...testResults];
            initCharts(result);
        } catch (error) {
            console.error("테스트 실행 중 오류:", error);
            alert(`테스트 실행 중 오류가 발생했습니다: ${error.message}`);
        } finally {
            isRunning = false;
            currentScenario = null;
        }
    }

    // 사용자 정의 테스트 실행
    async function runCustomTest() {
        if (isRunning || selectedActions.length === 0) return;
        isRunning = true;
        progress = 0;

        try {
            const config = {
                userCount: customUserCount,
                actions: selectedActions,
                trafficPattern: selectedTrafficPattern,
            };

            const testResult = await runCustomProductionTest(config);
            testResults = [testResult, ...testResults];
            initCharts(testResult);
        } catch (error) {
            console.error("사용자 정의 테스트 실행 오류:", error);
            alert(`테스트 실행 중 오류가 발생했습니다: ${error.message}`);
        } finally {
            isRunning = false;
        }
    }

    // 액션 선택 토글
    function toggleAction(action) {
        if (selectedActions.includes(action)) {
            selectedActions = selectedActions.filter((a) => a !== action);
        } else {
            selectedActions = [...selectedActions, action];
        }
    }

    onMount(() => {
        // 초기 선택 설정
        const selectElement = document.getElementById("scenario-select");
        if (selectElement) {
            selectElement.value = "0";
            currentScenario = ProductionTestScenarios[0];
        }

        // 진행 상황 구독
        const unsubscribe = productionMetrics.subscribe((metrics) => {
            if (metrics.totalRequests > 0) {
                progress =
                    (metrics.currentProgress / metrics.totalRequests) * 100;
            }
        });

        return () => {
            // 컴포넌트 언마운트 시 구독 해제
            unsubscribe();
            // 차트 정리
            Object.values(charts).forEach((chart) => {
                if (chart) chart.destroy();
            });
        };
    });
</script>

<div class="container mt-4">
    <div class="card mb-4">
        <div class="card-header bg-primary text-white">
            <h2 class="mb-0">프로덕션 환경 부하 테스트 대시보드</h2>
        </div>
        <div class="card-body">
            <div class="alert alert-info">
                <h5>📊 프로덕션 환경 테스트 설명</h5>
                <ul class="mb-0">
                    <li>
                        <strong>목적</strong>: 실제 프로덕션 환경을
                        시뮬레이션하여 시스템의 성능과 안정성 평가
                    </li>
                    <li>
                        <strong>사용자 행동</strong>: 실제 사용자의 다양한
                        페이지 접근 시나리오 시뮬레이션
                    </li>
                    <li>
                        <strong>복잡도 분석</strong>: 다양한 API 요청의 복잡도별
                        성능 측정
                    </li>
                    <li>
                        <strong>확장성 테스트</strong>: 동시 접속자 수 증가에
                        따른 시스템 성능 변화 측정
                    </li>
                </ul>
            </div>

            <!-- 추가: 테스트 설계 배경 설명 -->
            <div class="alert alert-secondary mt-3">
                <h5>🧪 테스트 설계 배경</h5>
                <p>
                    이 테스트는 실제 사용자의 행동 패턴과 요청 분포를 현실적으로
                    시뮬레이션하기 위해 설계되었습니다:
                </p>

                <h6 class="mt-3">📌 사용자 행동 모델링</h6>
                <ul>
                    <li>
                        <strong>현실적인 시나리오</strong>: '상품 검색 및 조회',
                        '구매 프로세스', '관리자 작업'과 같은 실제 사용자 여정을
                        기반으로 정의
                    </li>
                    <li>
                        <strong>동기/비동기 처리</strong>: 전통적인 페이지
                        로딩과 현대적인 SPA 방식의 API 호출 패턴 모두 테스트
                    </li>
                    <li>
                        <strong>시퀀스 기반 접근</strong>: 사용자가 웹사이트를
                        탐색할 때 취하는 실제 경로를 재현
                    </li>
                </ul>

                <h6 class="mt-3">📌 페이지별 요청 가중치 설계</h6>
                <ul>
                    <li>
                        <strong>상품 목록 페이지</strong>: 70% 단순 조회, 30%
                        복잡 조회 - 사용자의 일반적인 검색 패턴 반영
                    </li>
                    <li>
                        <strong>상품 상세 페이지</strong>: 40% 단순 조회, 40%
                        복잡 조회, 20% 분석 데이터 - 상세 정보와 관련 콘텐츠
                        로딩 시뮬레이션
                    </li>
                    <li>
                        <strong>결제 페이지</strong>: 60% 쓰기 작업, 30% 단순
                        조회, 10% 복잡 조회 - 트랜잭션 처리 중심의 워크로드
                    </li>
                    <li>
                        <strong>관리자 대시보드</strong>: 60% 분석 작업, 40%
                        복잡 조회 - 데이터 집계 및 분석 중심의 무거운 워크로드
                    </li>
                </ul>

                <h6 class="mt-3">📌 테스트 결과 해석</h6>
                <p>
                    이러한 가중치 기반 테스트를 통해 얻은 결과는 실제 운영
                    환경에서 발생할 수 있는 부하 상황을 더 정확하게 예측하는데
                    도움이 됩니다. 단순히 동일한 요청을 반복하는 것이 아니라,
                    다양한 복잡도의 요청이 실제 사용 패턴에 따라 분포된
                    상황에서의 시스템 성능을 측정합니다.
                </p>
            </div>

            <ul class="nav nav-tabs mt-3" id="testTabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button
                        class="nav-link {activeTab === 'predefined'
                            ? 'active'
                            : ''}"
                        id="predefined-tab"
                        on:click={() => (activeTab = "predefined")}
                    >
                        사전 정의 시나리오
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button
                        class="nav-link {activeTab === 'custom'
                            ? 'active'
                            : ''}"
                        id="custom-tab"
                        on:click={() => (activeTab = "custom")}
                    >
                        커스텀 시나리오
                    </button>
                </li>
            </ul>

            <div class="tab-content mt-3" id="testTabContent">
                <!-- 사전 정의 시나리오 탭 -->
                <div
                    class="tab-pane fade {activeTab === 'predefined'
                        ? 'show active'
                        : ''}"
                    id="predefined"
                >
                    <div class="form-group">
                        <label for="scenario-select" class="form-label"
                            >테스트 시나리오 선택</label
                        >
                        <select id="scenario-select" class="form-select">
                            <option value="" selected disabled
                                >시나리오를 선택하세요</option
                            >
                            {#each ProductionTestScenarios as scenario, i}
                                <option value={i}
                                    >{scenario.name} - {scenario.description}</option
                                >
                            {/each}
                        </select>
                    </div>

                    <div class="mt-3">
                        <button
                            class="btn btn-lg btn-primary"
                            on:click={runTest}
                            disabled={isRunning}
                        >
                            {#if isRunning}
                                <span
                                    class="spinner-border spinner-border-sm me-2"
                                    role="status"
                                    aria-hidden="true"
                                ></span>
                                테스트 실행 중...
                            {:else}
                                시나리오 테스트 시작
                            {/if}
                        </button>
                    </div>
                </div>

                <!-- 커스텀 시나리오 탭 -->
                <div
                    class="tab-pane fade {activeTab === 'custom'
                        ? 'show active'
                        : ''}"
                    id="custom"
                >
                    <div class="row">
                        <div class="col-md-6">
                            <div class="form-group mb-3">
                                <label
                                    for="custom-user-count"
                                    class="form-label">동시 사용자 수</label
                                >
                                <input
                                    type="number"
                                    id="custom-user-count"
                                    class="form-control"
                                    bind:value={customUserCount}
                                    min="1"
                                    max="500"
                                />
                                <div class="form-text">
                                    테스트에 사용할 가상 사용자 수 (1~500명)
                                </div>
                            </div>
                        </div>

                        <div class="col-md-6">
                            <div class="form-group mb-3">
                                <label for="traffic-pattern" class="form-label"
                                    >트래픽 패턴</label
                                >
                                <select
                                    id="traffic-pattern"
                                    class="form-select"
                                    bind:value={selectedTrafficPattern}
                                >
                                    {#each CustomTestConfigurations.trafficPatterns as pattern}
                                        <option value={pattern}
                                            >{pattern.name}</option
                                        >
                                    {/each}
                                </select>
                                <div class="form-text">
                                    사용자 트래픽 패턴 (균일 분포, 점진적 증가,
                                    버스트 패턴)
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="form-group mb-3">
                        <label class="form-label">사용자 행동 선택</label>
                        <div class="row">
                            {#each Object.values(UserActions) as action}
                                <div class="col-md-4 mb-2">
                                    <div class="form-check">
                                        <input
                                            class="form-check-input"
                                            type="checkbox"
                                            id="action-{action.name}"
                                            checked={selectedActions.includes(
                                                action,
                                            )}
                                            on:change={() =>
                                                toggleAction(action)}
                                        />
                                        <label
                                            class="form-check-label"
                                            for="action-{action.name}"
                                        >
                                            {action.name}
                                            <small class="text-muted d-block"
                                                >{action.description}</small
                                            >
                                        </label>
                                    </div>
                                </div>
                            {/each}
                        </div>
                    </div>

                    <div class="mt-3">
                        <button
                            class="btn btn-lg btn-primary"
                            on:click={runCustomTest}
                            disabled={isRunning || selectedActions.length === 0}
                        >
                            {#if isRunning}
                                <span
                                    class="spinner-border spinner-border-sm me-2"
                                    role="status"
                                    aria-hidden="true"
                                ></span>
                                테스트 실행 중...
                            {:else}
                                커스텀 테스트 시작
                            {/if}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    {#if isRunning}
        <div class="progress mb-4" style="height: 25px;">
            <div
                class="progress-bar progress-bar-striped progress-bar-animated"
                role="progressbar"
                style="width: {progress}%"
                aria-valuenow={progress}
                aria-valuemin="0"
                aria-valuemax="100"
            >
                {progress.toFixed(0)}% - {currentScenario?.name || "준비 중..."}
            </div>
        </div>
    {/if}

    {#if testResults.length > 0}
        <!-- 차트 컨테이너 -->
        <div id="charts-container" class="mb-4"></div>

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
                                    {testResults[0].totalRequests}개
                                </h3>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-body text-center">
                                <h6 class="card-title">총 실행 시간</h6>
                                <h3 class="card-text">
                                    {formatDuration(testResults[0].totalTime)}
                                </h3>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-body text-center">
                                <h6 class="card-title">성공률</h6>
                                <h3 class="card-text">
                                    {formatPercentage(
                                        testResults[0].successRate,
                                    )}
                                </h3>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-body text-center">
                                <h6 class="card-title">처리량</h6>
                                <h3 class="card-text">
                                    {testResults[0].throughput?.toFixed(2) || 0}
                                    req/s
                                </h3>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="accordion mb-5" id="testResults">
            {#each testResults as result, i}
                <div class="accordion-item">
                    <h2 class="accordion-header">
                        <button
                            class="accordion-button {i === 0
                                ? ''
                                : 'collapsed'}"
                            type="button"
                            data-bs-toggle="collapse"
                            data-bs-target="#collapse{i}"
                        >
                            <div class="w-100">
                                <div
                                    class="d-flex justify-content-between align-items-center"
                                >
                                    <div>
                                        <strong>{result.scenarioName}</strong>
                                        <br />
                                        <small class="text-muted"
                                            >{result.description}</small
                                        >
                                    </div>
                                    <div class="text-end">
                                        <span class="badge bg-info">
                                            동시 사용자: {result.concurrentUsers}명
                                        </span>
                                        <br />
                                        <small class="text-muted">
                                            총 요청: {result.totalRequests}개
                                        </small>
                                    </div>
                                </div>
                            </div>
                        </button>
                    </h2>
                    <div
                        id="collapse{i}"
                        class="accordion-collapse collapse {i === 0
                            ? 'show'
                            : ''}"
                        data-bs-parent="#testResults"
                    >
                        <div class="accordion-body">
                            <div class="row mb-3">
                                <div class="col-md-4">
                                    <div class="card">
                                        <div class="card-body">
                                            <h6 class="card-title">
                                                응답 시간 분석
                                            </h6>
                                            <p class="card-text">
                                                <strong>평균:</strong>
                                                {formatDuration(
                                                    result.averageResponseTime,
                                                )}<br />
                                                <strong>최소:</strong>
                                                {formatDuration(
                                                    result.minResponseTime,
                                                )}<br />
                                                <strong>최대:</strong>
                                                {formatDuration(
                                                    result.maxResponseTime,
                                                )}<br />
                                                <strong>P95:</strong>
                                                {formatDuration(
                                                    result
                                                        .responseTimeDistribution
                                                        ?.p95 || 0,
                                                )}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="card">
                                        <div class="card-body">
                                            <h6 class="card-title">
                                                처리량 분석
                                            </h6>
                                            <p class="card-text">
                                                <strong>처리량:</strong>
                                                {result.throughput?.toFixed(
                                                    2,
                                                ) || 0} req/s<br />
                                                <strong>총 시간:</strong>
                                                {formatDuration(
                                                    result.totalTime,
                                                )}<br />
                                                <strong>총 요청:</strong>
                                                {result.totalRequests}개<br />
                                            </p>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="card">
                                        <div class="card-body">
                                            <h6 class="card-title">
                                                성공/실패 분석
                                            </h6>
                                            <p class="card-text">
                                                <strong>성공률:</strong>
                                                {formatPercentage(
                                                    result.successRate,
                                                )}<br />
                                                <strong>실패률:</strong>
                                                {formatPercentage(
                                                    result.failureRate || 0,
                                                )}<br />
                                                <strong>성공:</strong>
                                                {result.totalRequests *
                                                    result.successRate} 요청<br
                                                />
                                                <strong>실패:</strong>
                                                {result.totalRequests *
                                                    (result.failureRate || 0)} 요청
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- 페이지별 테이블 -->
                            <h5 class="mt-4">페이지별 성능</h5>
                            {#if result.pageAnalysis && result.pageAnalysis.pageTimeline}
                                <div class="table-responsive">
                                    <table class="table table-hover">
                                        <thead class="table-light">
                                            <tr>
                                                <th>페이지 유형</th>
                                                <th>평균 로드 시간</th>
                                                <th>최소 시간</th>
                                                <th>최대 시간</th>
                                                <th>요청 수</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {#each result.pageAnalysis.pageTimeline as page}
                                                <tr>
                                                    <td>{page.name}</td>
                                                    <td
                                                        >{formatDuration(
                                                            page.average,
                                                        )}</td
                                                    >
                                                    <td
                                                        >{formatDuration(
                                                            page.min,
                                                        )}</td
                                                    >
                                                    <td
                                                        >{formatDuration(
                                                            page.max,
                                                        )}</td
                                                    >
                                                    <td>{page.times.length}</td>
                                                </tr>
                                            {/each}
                                        </tbody>
                                    </table>
                                </div>
                            {:else}
                                <p class="alert alert-warning">
                                    페이지별 성능 데이터가 없습니다.
                                </p>
                            {/if}

                            <!-- 사용자 행동 분석 -->
                            <h5 class="mt-4">사용자 행동 분석</h5>
                            {#if result.userActions && result.userActions.length > 0}
                                <div
                                    class="accordion"
                                    id="userActionsAccordion{i}"
                                >
                                    {#each result.userActions as userAction, actionIndex}
                                        <div class="accordion-item">
                                            <h2 class="accordion-header">
                                                <button
                                                    class="accordion-button collapsed"
                                                    type="button"
                                                    data-bs-toggle="collapse"
                                                    data-bs-target="#userAction{i}-{actionIndex}"
                                                >
                                                    <div
                                                        class="w-100 d-flex justify-content-between align-items-center"
                                                    >
                                                        <span>
                                                            <strong
                                                                >사용자 {actionIndex +
                                                                    1}</strong
                                                            >: {userAction.actionName}
                                                        </span>
                                                        <span>
                                                            <span
                                                                class="badge bg-secondary me-2"
                                                            >
                                                                총 시간: {formatDuration(
                                                                    userAction.totalTime,
                                                                )}
                                                            </span>
                                                            <span
                                                                class="badge bg-info"
                                                            >
                                                                요청 수: {userAction.totalRequests}개
                                                            </span>
                                                        </span>
                                                    </div>
                                                </button>
                                            </h2>
                                            <div
                                                id="userAction{i}-{actionIndex}"
                                                class="accordion-collapse collapse"
                                                data-bs-parent="#userActionsAccordion{i}"
                                            >
                                                <div class="accordion-body">
                                                    <p>
                                                        <strong
                                                            >평균 응답 시간:</strong
                                                        >
                                                        {formatDuration(
                                                            userAction.averageResponseTime,
                                                        )}<br />
                                                        <strong>성공률:</strong>
                                                        {formatPercentage(
                                                            userAction.successRate,
                                                        )}
                                                    </p>
                                                    <h6>방문 페이지:</h6>
                                                    <div
                                                        class="table-responsive"
                                                    >
                                                        <table
                                                            class="table table-sm"
                                                        >
                                                            <thead
                                                                class="table-light"
                                                            >
                                                                <tr>
                                                                    <th
                                                                        >페이지</th
                                                                    >
                                                                    <th
                                                                        >로드
                                                                        시간</th
                                                                    >
                                                                    <th
                                                                        >요청 수</th
                                                                    >
                                                                    <th
                                                                        >성공률</th
                                                                    >
                                                                </tr>
                                                            </thead>
                                                            <tbody>
                                                                {#each userAction.pages as page}
                                                                    <tr>
                                                                        <td
                                                                            >{page.pageName}</td
                                                                        >
                                                                        <td
                                                                            >{formatDuration(
                                                                                page.totalTime,
                                                                            )}</td
                                                                        >
                                                                        <td
                                                                            >{page
                                                                                .requests
                                                                                .length}</td
                                                                        >
                                                                        <td
                                                                            >{formatPercentage(
                                                                                page.successRate,
                                                                            )}</td
                                                                        >
                                                                    </tr>
                                                                {/each}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    {/each}
                                </div>
                            {:else}
                                <p class="alert alert-warning">
                                    사용자 행동 분석 데이터가 없습니다.
                                </p>
                            {/if}
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    {:else if !isRunning}
        <div class="alert alert-secondary">
            <p class="mb-0">테스트를 시작하면 결과가 여기에 표시됩니다.</p>
        </div>
    {/if}
</div>

<style>
    .card {
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
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

    .nav-tabs .nav-link {
        cursor: pointer;
    }

    .nav-tabs .nav-link.active {
        font-weight: 500;
    }

    .form-text {
        font-size: 0.875em;
        color: #6c757d;
    }
</style>
