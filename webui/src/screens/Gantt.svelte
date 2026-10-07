<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchTimeline,
    fetchMemory,
    ZOOM_HOURS,
    DEFAULT_ZOOM_HOURS,
    runEndMs,
    memoryColor,
  } from '../lib/timeline';
  import type { JobRun } from '../lib/types';
  import { toastError, errMsg } from '../lib/toast.svelte';

  const W = 1000;
  const ROW_H = 40;
  const LEFT = 190;
  const TOP = 26;

  const HOUR_MS = 3_600_000;
  const DAYS_HOURS = 168;

  let runs = $state<JobRun[]>([]);
  let limitMb = $state<number | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let zoomHours = $state(DEFAULT_ZOOM_HOURS);
  let dataStartMs = $state(0);
  let dataEndMs = $state(0);
  let nowMs = $state(Date.now());
  let vStartMs = $state(0);

  onMount(async () => {
    nowMs = Date.now();
    dataStartMs = nowMs - DAYS_HOURS * HOUR_MS;
    dataEndMs = nowMs;
    vStartMs = dataEndMs - zoomHours * HOUR_MS;
    try {
      const [tl, mem] = await Promise.all([fetchTimeline(DAYS_HOURS), fetchMemory()]);
      runs = tl.logs ?? [];
      limitMb = tl.memory_limit_mb ?? mem.limit_mb ?? null;
    } catch (e) {
      error = errMsg(e);
      toastError(errMsg(e));
    } finally {
      loading = false;
    }
  });

  const vEndMs = $derived(vStartMs + zoomHours * HOUR_MS);
  const spanMs = $derived(vEndMs - vStartMs);
  const scrollMax = $derived(Math.max(0, dataEndMs - zoomHours * HOUR_MS));

  const rows = $derived.by(() => {
    const list: { job_id: number; job_name: string; runs: JobRun[] }[] = [];
    const byId = new Map<number, number>();
    for (const run of runs) {
      const s = new Date(run.started_at).getTime();
      const e = runEndMs(run, nowMs);
      const x0 = LEFT + ((s - vStartMs) / spanMs) * (W - LEFT);
      const x1 = LEFT + ((e - vStartMs) / spanMs) * (W - LEFT);
      if (Math.min(x1, W) <= Math.max(x0, LEFT)) continue; // entirely outside the bar area
      let idx = byId.get(run.job_id);
      if (idx == null) {
        idx = list.length;
        byId.set(run.job_id, idx);
        list.push({ job_id: run.job_id, job_name: run.job_name, runs: [] });
      }
      list[idx].runs.push(run);
    }
    return list;
  });

  const svgH = $derived(TOP + rows.length * ROW_H + 8);

  function setZoom(z: number) {
    zoomHours = z;
    vStartMs = Math.max(dataStartMs, dataEndMs - z * HOUR_MS);
  }

  function barGeometry(run: JobRun) {
    const s = new Date(run.started_at).getTime();
    const e = runEndMs(run, nowMs);
    const x0 = LEFT + ((s - vStartMs) / spanMs) * (W - LEFT);
    const x1 = LEFT + ((e - vStartMs) / spanMs) * (W - LEFT);
    const x = Math.max(x0, LEFT);
    return { x, w: Math.max(1, Math.min(x1, W) - x) };
  }

  const failed = (r: JobRun) => r.status !== 'completed' && r.status !== 'running';
  const runningBar = (r: JobRun) => r.status === 'running';

  function tooltip(run: JobRun) {
    const s = new Date(run.started_at).getTime();
    const e = runEndMs(run, nowMs);
    const mins = Math.round((e - s) / 60000);
    const running = run.finished_at == null;
    const peak = run.peak_memory_mb != null ? `${run.peak_memory_mb} MB` : 'unknown';
    const lim = limitMb != null ? ` (limit ${limitMb} MB)` : '';
    let tip = `${run.job_name} — ${new Date(s).toLocaleString()} → ${new Date(e).toLocaleString()} — ${mins}m — ${peak}${lim}`;
    if (running) tip += ' (running)';
    return tip;
  }
</script>

<div class="gantt">
  {#if loading}
    <div class="spinner" role="status"></div>
  {:else if error}
    <div class="empty-state">
      <b>Couldn’t load run data</b>
      <div class="muted small">{error}</div>
      <div class="muted small">
        If the backend predates this feature, restart it:
        <code>./stop_local.sh &amp;&amp; ./run_local.sh</code>
      </div>
    </div>
  {:else if runs.length === 0}
    <div class="empty-state">No backup runs in the last 7 days</div>
  {:else}
    <div class="toolbar">
      <div class="zooms">
        {#each ZOOM_HOURS as z}
          <button
            class="btn ghost"
            class:active={z === zoomHours}
            onclick={() => setZoom(z)}
          >
            {z}h
          </button>
        {/each}
      </div>
      <div class="readout muted small">
        {new Date(vStartMs).toLocaleString()} → {new Date(vEndMs).toLocaleString()}
      </div>
    </div>

    <input
      type="range"
      min={dataStartMs}
      max={scrollMax}
      step={900000}
      value={vStartMs}
      class="panner"
      style="width:{W}px"
      oninput={(e) => (vStartMs = Number((e.currentTarget as HTMLInputElement).value))}
    />

    <svg width={W} height={svgH} class="chart">
      {#each [0, 1, 2, 3] as i}
        <text
          x={LEFT + (i / 3) * (W - LEFT)}
          y={TOP - 8}
          text-anchor="middle"
          fill="var(--text-muted)"
          font-size="11"
        >
          {new Date(vStartMs + (i * spanMs) / 4).toLocaleString()}
        </text>
      {/each}
      {#each rows as row, rowIdx}
        <line
          x1={LEFT}
          y1={TOP + rowIdx * ROW_H + ROW_H / 2}
          x2={W}
          y2={TOP + rowIdx * ROW_H + ROW_H / 2}
          stroke="var(--border)"
        />
        <text x="4" y={TOP + rowIdx * ROW_H + ROW_H - 12} fill="var(--text)" font-size="12">
          {row.job_name.length > 24 ? row.job_name.slice(0, 23) + '…' : row.job_name}
        </text>
        {#each row.runs as run}
          {@const g = barGeometry(run)}
          <rect
            x={g.x}
            y={TOP + rowIdx * ROW_H + ROW_H * 0.15}
            width={g.w}
            height={ROW_H * 0.7}
            rx="3"
            fill={memoryColor(run.peak_memory_mb, limitMb)}
            stroke={runningBar(run) ? 'var(--primary)' : failed(run) ? 'var(--error)' : 'none'}
            stroke-width={failed(run) ? 2 : 1}
            stroke-dasharray={runningBar(run) ? '4 3' : undefined}
          >
            <title>{tooltip(run)}</title>
          </rect>
        {/each}
      {/each}
    </svg>

    {#if limitMb != null}
      <div class="legend small">
        <span><i style="background:#81c784"></i>&lt;50%</span>
        <span><i style="background:#fdd835"></i>50–70%</span>
        <span><i style="background:#ffb74d"></i>70–90%</span>
        <span><i style="background:#e57373"></i>≥90%</span>
        <span class="muted">of {limitMb} MB limit</span>
      </div>
    {:else}
      <div class="legend small muted">(no memory limit known)</div>
    {/if}
  {/if}
</div>

<style>
  .gantt {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .toolbar {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }
  .zooms {
    display: flex;
    gap: 6px;
  }
  .zooms .active {
    background: var(--surface-2);
    border-color: var(--primary);
    color: var(--primary);
  }
  .readout {
    font-variant-numeric: tabular-nums;
  }
  .panner {
    accent-color: var(--primary);
  }
  .chart {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    max-width: 100%;
    height: auto;
  }
  .legend {
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
  }
  .legend span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .legend i {
    width: 10px;
    height: 10px;
    border-radius: 2px;
    display: inline-block;
  }
</style>