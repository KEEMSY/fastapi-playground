<script>
    import { onDestroy } from 'svelte';

    const BASE_URL = import.meta.env.VITE_SERVER_URL || 'http://127.0.0.1:7777';

    // ── 실험 설정 ────────────────────────────────────────────────────────
    let concurrencyType = 'asyncio';
    let taskType = 'io';
    let taskCount = 8;
    let workerCount = 4;
    let complexity = 3;

    const concurrencyOptions = [
        { value: 'asyncio',        label: 'asyncio',         desc: '이벤트 루프 + Semaphore' },
        { value: 'threading',      label: 'Threading',       desc: 'ThreadPoolExecutor + run_in_executor' },
        { value: 'multiprocessing',label: 'Multiprocessing', desc: 'ProcessPoolExecutor + run_in_executor' },
        { value: 'multi_instance', label: 'Multi Instance',  desc: '다중 프로세스 인스턴스 분산' },
    ];

    const taskTypeOptions = [
        { value: 'io',  label: 'I/O Bound', desc: 'sleep으로 네트워크/디스크 대기 시뮬레이션' },
        { value: 'cpu', label: 'CPU Bound', desc: '소수 계산 (GIL 영향 관찰 가능)' },
    ];

    // ── 실험 상태 ────────────────────────────────────────────────────────
    let isRunning = false;
    let experimentId = null;
    let status = 'idle'; // idle | running | completed | error
    let totalElapsed = null;
    let throughput = null;
    let errorMessage = null;

    // 태스크 결과 (task_id → { worker_id, start_time, end_time, elapsed })
    let taskResults = {};
    let taskStarts = {}; // task_id → start_time (시작했지만 완료 안 된 것)

    // 이력
    let history = [];

    // SSE 연결
    let eventSource = null;

    // ── Canvas 타임라인 ──────────────────────────────────────────────────
    let canvas;
    const COLORS = [
        '#4CAF50', '#2196F3', '#FF9800', '#9C27B0',
        '#F44336', '#00BCD4', '#CDDC39', '#FF5722',
    ];

    function drawTimeline() {
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const W = canvas.width;
        const H = canvas.height;
        ctx.clearRect(0, 0, W, H);

        const results = Object.values(taskResults);
        if (results.length === 0 && Object.keys(taskStarts).length === 0) {
            ctx.fillStyle = '#888';
            ctx.font = '14px monospace';
            ctx.textAlign = 'center';
            ctx.fillText('실험을 실행하면 타임라인이 표시됩니다', W / 2, H / 2);
            return;
        }

        // 시간 범위 계산
        const maxTime = totalElapsed || Math.max(
            ...results.map(r => r.end_time),
            ...Object.values(taskStarts),
            0.1
        ) * 1.1;

        const paddingLeft = 60;
        const paddingRight = 20;
        const paddingTop = 30;
        const paddingBottom = 30;
        const chartW = W - paddingLeft - paddingRight;
        const chartH = H - paddingTop - paddingBottom;
        const rowH = Math.min(28, chartH / workerCount);

        // 배경 그리드
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 1;
        const gridCount = 5;
        for (let i = 0; i <= gridCount; i++) {
            const x = paddingLeft + (chartW / gridCount) * i;
            ctx.beginPath();
            ctx.moveTo(x, paddingTop);
            ctx.lineTo(x, H - paddingBottom);
            ctx.stroke();

            // 시간 레이블
            ctx.fillStyle = '#666';
            ctx.font = '11px monospace';
            ctx.textAlign = 'center';
            const t = (maxTime / gridCount) * i;
            ctx.fillText(t.toFixed(2) + 's', x, H - paddingBottom + 15);
        }

        // Worker 레이블
        for (let w = 0; w < workerCount; w++) {
            const y = paddingTop + w * rowH + rowH / 2;
            ctx.fillStyle = '#333';
            ctx.font = '11px monospace';
            ctx.textAlign = 'right';
            ctx.fillText(`W${w}`, paddingLeft - 6, y + 4);
        }

        // 완료된 태스크 바
        for (const r of results) {
            const x = paddingLeft + (r.start_time / maxTime) * chartW;
            const w = Math.max(2, ((r.end_time - r.start_time) / maxTime) * chartW);
            const y = paddingTop + r.worker_id * rowH + 2;
            const h = rowH - 4;

            ctx.fillStyle = COLORS[r.worker_id % COLORS.length];
            ctx.beginPath();
            ctx.roundRect(x, y, w, h, 3);
            ctx.fill();

            // task_id 레이블 (너비 충분할 때만)
            if (w > 20) {
                ctx.fillStyle = '#fff';
                ctx.font = `${Math.min(11, rowH - 6)}px monospace`;
                ctx.textAlign = 'center';
                ctx.fillText(`T${r.task_id}`, x + w / 2, y + h / 2 + 4);
            }
        }

        // 진행 중 태스크 바 (점선)
        const now = totalElapsed || (Date.now() / 1000);
        for (const [taskId, startTime] of Object.entries(taskStarts)) {
            const r = taskResults[taskId];
            if (r) continue; // 이미 완료됨
            const wid = (parseInt(taskId)) % workerCount;
            const x = paddingLeft + (startTime / maxTime) * chartW;
            const currentEnd = Math.min(now, maxTime);
            const w = Math.max(2, ((currentEnd - startTime) / maxTime) * chartW);
            const y = paddingTop + wid * rowH + 2;
            const h = rowH - 4;

            ctx.fillStyle = COLORS[wid % COLORS.length] + '55';
            ctx.setLineDash([4, 3]);
            ctx.strokeStyle = COLORS[wid % COLORS.length];
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.roundRect(x, y, w, h, 3);
            ctx.fill();
            ctx.stroke();
            ctx.setLineDash([]);
        }

        // 현재 시간 선 (실행 중일 때)
        if (status === 'running' && totalElapsed === null) {
            ctx.strokeStyle = '#f44336';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([4, 3]);
            ctx.beginPath();
            ctx.moveTo(paddingLeft, paddingTop);
            ctx.lineTo(paddingLeft, H - paddingBottom);
            ctx.stroke();
            ctx.setLineDash([]);
        }
    }

    $: {
        taskResults; taskStarts; totalElapsed; status; workerCount;
        if (typeof requestAnimationFrame !== 'undefined') {
            requestAnimationFrame(drawTimeline);
        }
    }

    // ── 실험 실행 ────────────────────────────────────────────────────────
    async function runExperiment() {
        if (isRunning) return;
        isRunning = true;
        status = 'running';
        taskResults = {};
        taskStarts = {};
        totalElapsed = null;
        throughput = null;
        errorMessage = null;
        experimentId = null;

        // 기존 SSE 연결 정리
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }

        try {
            const res = await fetch(`${BASE_URL}/api/concurrency/run`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    concurrency_type: concurrencyType,
                    task_type: taskType,
                    task_count: taskCount,
                    worker_count: workerCount,
                    complexity,
                }),
            });

            if (!res.ok) {
                let errMsg = '실험 시작 실패';
                try { const err = await res.json(); errMsg = err.detail || errMsg; } catch {}
                throw new Error(errMsg);
            }

            const data = await res.json();
            experimentId = data.experiment_id;

            // SSE 연결
            connectSSE(experimentId);
        } catch (e) {
            status = 'error';
            errorMessage = e.message;
            isRunning = false;
        }
    }

    function connectSSE(id) {
        eventSource = new EventSource(`${BASE_URL}/api/concurrency/stream/${id}`);

        eventSource.addEventListener('task_start', (e) => {
            const d = JSON.parse(e.data);
            taskStarts[d.task_id] = d.start_time;
            taskStarts = taskStarts;
            requestAnimationFrame(drawTimeline);
        });

        eventSource.addEventListener('task_complete', (e) => {
            const d = JSON.parse(e.data);
            taskResults[d.task_id] = {
                worker_id: d.worker_id,
                start_time: d.start_time,
                end_time: d.end_time,
                elapsed: d.elapsed,
            };
            taskResults = taskResults;
            delete taskStarts[d.task_id];
            taskStarts = taskStarts;
            requestAnimationFrame(drawTimeline);
        });

        eventSource.addEventListener('completed', (e) => {
            const d = JSON.parse(e.data);
            totalElapsed = d.total_elapsed;
            throughput = d.throughput;
            status = 'completed';
            isRunning = false;
            eventSource.close();
            loadHistory();
            requestAnimationFrame(drawTimeline);
        });

        eventSource.addEventListener('error', (e) => {
            try {
                const d = JSON.parse(e.data);
                errorMessage = d.message;
            } catch {
                errorMessage = '알 수 없는 오류가 발생했습니다.';
            }
            status = 'error';
            isRunning = false;
            eventSource.close();
        });

        eventSource.onerror = () => {
            if (status !== 'completed' && status !== 'error') {
                errorMessage = 'SSE 연결이 끊어졌습니다.';
                status = 'error';
                isRunning = false;
            }
        };
    }

    // ── 이력 ────────────────────────────────────────────────────────────
    async function loadHistory() {
        try {
            const res = await fetch(`${BASE_URL}/api/concurrency/history`);
            if (res.ok) history = await res.json();
        } catch {}
    }

    async function clearHistory() {
        await fetch(`${BASE_URL}/api/concurrency/clear`, { method: 'DELETE' });
        history = [];
    }

    loadHistory();

    onDestroy(() => {
        if (eventSource) eventSource.close();
    });

    // ── 헬퍼 ────────────────────────────────────────────────────────────
    function typeColor(type) {
        const map = { asyncio: '#4CAF50', threading: '#2196F3', multiprocessing: '#FF9800', multi_instance: '#9C27B0' };
        return map[type] || '#888';
    }
</script>

<div class="container-fluid py-3">
    <h4 class="mb-1">동시성 프로그래밍 실험</h4>
    <p class="text-muted small mb-3">asyncio / threading / multiprocessing / multi-instance 성능을 실시간으로 비교합니다.</p>

    <div class="row g-3">
        <!-- 설정 패널 -->
        <div class="col-md-3">
            <div class="card h-100">
                <div class="card-header py-2"><strong>실험 설정</strong></div>
                <div class="card-body">
                    <!-- 동시성 타입 -->
                    <label class="form-label fw-bold small">동시성 방식</label>
                    {#each concurrencyOptions as opt}
                        <div class="form-check mb-1">
                            <input class="form-check-input" type="radio" id="ct_{opt.value}"
                                   bind:group={concurrencyType} value={opt.value} disabled={isRunning}>
                            <label class="form-check-label" for="ct_{opt.value}">
                                <span class="fw-semibold">{opt.label}</span>
                                <br><span class="text-muted" style="font-size:11px">{opt.desc}</span>
                            </label>
                        </div>
                    {/each}

                    <hr class="my-2">

                    <!-- 태스크 타입 -->
                    <label class="form-label fw-bold small">작업 유형</label>
                    {#each taskTypeOptions as opt}
                        <div class="form-check mb-1">
                            <input class="form-check-input" type="radio" id="tt_{opt.value}"
                                   bind:group={taskType} value={opt.value} disabled={isRunning}>
                            <label class="form-check-label" for="tt_{opt.value}">
                                <span class="fw-semibold">{opt.label}</span>
                                <br><span class="text-muted" style="font-size:11px">{opt.desc}</span>
                            </label>
                        </div>
                    {/each}

                    <hr class="my-2">

                    <!-- 슬라이더 -->
                    <label class="form-label fw-bold small d-flex justify-content-between">
                        태스크 수 <span class="badge bg-secondary">{taskCount}</span>
                    </label>
                    <input type="range" class="form-range" min="2" max="32" step="2"
                           bind:value={taskCount} disabled={isRunning}>

                    <label class="form-label fw-bold small d-flex justify-content-between mt-2">
                        워커 수 <span class="badge bg-secondary">{workerCount}</span>
                    </label>
                    <input type="range" class="form-range" min="1" max="8"
                           bind:value={workerCount} disabled={isRunning}>

                    <label class="form-label fw-bold small d-flex justify-content-between mt-2">
                        복잡도 <span class="badge bg-secondary">{complexity}</span>
                    </label>
                    <input type="range" class="form-range" min="1" max="10"
                           bind:value={complexity} disabled={isRunning}>
                    <div class="text-muted" style="font-size:11px">
                        {#if taskType === 'io'}예상 태스크 시간: {(complexity * 0.2).toFixed(1)}s{:else}소수 계산 한계: {complexity * 3000}
                        {/if}
                    </div>

                    <button class="btn btn-primary w-100 mt-3"
                            on:click={runExperiment} disabled={isRunning}>
                        {#if isRunning}
                            <span class="spinner-border spinner-border-sm me-1"></span>실행 중...
                        {:else}
                            ▶ 실험 시작
                        {/if}
                    </button>
                </div>
            </div>
        </div>

        <!-- 타임라인 + 결과 -->
        <div class="col-md-9">
            <!-- 상태 배너 -->
            {#if status === 'running'}
                <div class="alert alert-info py-2 mb-2">
                    <strong>실행 중</strong> — experiment_id: <code>{experimentId}</code>
                    &nbsp;|&nbsp; 완료: {Object.keys(taskResults).length} / {taskCount}
                </div>
            {:else if status === 'completed'}
                <div class="alert alert-success py-2 mb-2">
                    <strong>완료</strong> &nbsp;|&nbsp;
                    총 시간: <strong>{totalElapsed}s</strong> &nbsp;|&nbsp;
                    처리량: <strong>{throughput} tasks/s</strong> &nbsp;|&nbsp;
                    <span class="badge" style="background:{typeColor(concurrencyType)}">{concurrencyType}</span>
                </div>
            {:else if status === 'error'}
                <div class="alert alert-danger py-2 mb-2">
                    <strong>오류</strong>: {errorMessage}
                </div>
            {/if}

            <!-- 타임라인 캔버스 -->
            <div class="card mb-3">
                <div class="card-header py-2 d-flex justify-content-between align-items-center">
                    <strong>작업 타임라인</strong>
                    <small class="text-muted">각 행 = Worker, 각 블록 = 태스크</small>
                </div>
                <div class="card-body p-2">
                    <canvas bind:this={canvas}
                            width="900"
                            height={Math.max(120, workerCount * 32 + 60)}
                            style="width:100%; height:auto; display:block">
                    </canvas>
                </div>
            </div>

            <!-- 결과 테이블 -->
            {#if Object.keys(taskResults).length > 0}
                <div class="card mb-3">
                    <div class="card-header py-2">
                        <strong>태스크 결과</strong>
                        <span class="badge bg-secondary ms-2">{Object.keys(taskResults).length}개 완료</span>
                    </div>
                    <div class="card-body p-0" style="max-height:220px; overflow-y:auto">
                        <table class="table table-sm table-hover mb-0">
                            <thead class="table-light sticky-top">
                                <tr>
                                    <th>Task ID</th>
                                    <th>Worker</th>
                                    <th>시작(s)</th>
                                    <th>종료(s)</th>
                                    <th>소요(s)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each Object.entries(taskResults).sort((a,b) => a[1].start_time - b[1].start_time) as [tid, r]}
                                    <tr>
                                        <td>T{tid}</td>
                                        <td>
                                            <span class="badge" style="background:{COLORS[r.worker_id % COLORS.length]}">
                                                W{r.worker_id}
                                            </span>
                                        </td>
                                        <td>{r.start_time.toFixed(3)}</td>
                                        <td>{r.end_time.toFixed(3)}</td>
                                        <td>{r.elapsed.toFixed(3)}</td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>
                </div>
            {/if}

            <!-- 학습 포인트 -->
            <div class="card">
                <div class="card-header py-2"><strong>학습 포인트</strong></div>
                <div class="card-body py-2">
                    <div class="row g-2">
                        <div class="col-sm-6">
                            <div class="p-2 rounded" style="background:#e8f5e9; font-size:13px">
                                <strong style="color:#2e7d32">asyncio (I/O Best)</strong><br>
                                이벤트 루프가 await 시점에 다른 코루틴 실행.
                                I/O 대기 시간을 0에 가깝게 활용. 단일 스레드로 높은 동시성 달성.
                            </div>
                        </div>
                        <div class="col-sm-6">
                            <div class="p-2 rounded" style="background:#e3f2fd; font-size:13px">
                                <strong style="color:#1565c0">threading (I/O OK)</strong><br>
                                GIL은 CPU 코드만 제한. sleep/socket 등 I/O 중에는 GIL 해제되어
                                실제 병렬 I/O 가능. CPU 작업은 순차 실행과 유사.
                            </div>
                        </div>
                        <div class="col-sm-6">
                            <div class="p-2 rounded" style="background:#fff3e0; font-size:13px">
                                <strong style="color:#e65100">multiprocessing (CPU Best)</strong><br>
                                별도 프로세스 → GIL 없음. CPU 코어 수만큼 선형 성능 향상.
                                프로세스 생성/통신 오버헤드 있음.
                            </div>
                        </div>
                        <div class="col-sm-6">
                            <div class="p-2 rounded" style="background:#f3e5f5; font-size:13px">
                                <strong style="color:#6a1b9a">multi_instance (Scale-out)</strong><br>
                                Nginx + Gunicorn + uvicorn worker 구조.
                                각 인스턴스가 독립 프로세스로 CPU-bound도 병렬화.
                                실제 운영 환경 스케일-아웃 패턴.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- 실험 이력 -->
    {#if history.length > 0}
        <div class="card mt-3">
            <div class="card-header py-2 d-flex justify-content-between align-items-center">
                <strong>실험 이력</strong>
                <button class="btn btn-sm btn-outline-danger" on:click={clearHistory}>이력 삭제</button>
            </div>
            <div class="card-body p-0">
                <table class="table table-sm table-hover mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>ID</th>
                            <th>방식</th>
                            <th>작업</th>
                            <th>태스크</th>
                            <th>워커</th>
                            <th>복잡도</th>
                            <th>상태</th>
                            <th>총 시간(s)</th>
                            <th>처리량</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each history as h}
                            <tr>
                                <td><code>{h.experiment_id}</code></td>
                                <td>
                                    <span class="badge" style="background:{typeColor(h.concurrency_type)}">
                                        {h.concurrency_type}
                                    </span>
                                </td>
                                <td>{h.task_type}</td>
                                <td>{h.task_count}</td>
                                <td>{h.worker_count}</td>
                                <td>{h.complexity}</td>
                                <td>
                                    {#if h.status === 'completed'}
                                        <span class="badge bg-success">완료</span>
                                    {:else if h.status === 'running'}
                                        <span class="badge bg-primary">실행 중</span>
                                    {:else}
                                        <span class="badge bg-danger">오류</span>
                                    {/if}
                                </td>
                                <td>{h.total_elapsed ?? '-'}</td>
                                <td>{h.throughput ?? '-'}</td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        </div>
    {/if}
</div>
