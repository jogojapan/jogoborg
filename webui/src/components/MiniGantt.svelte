<script lang="ts">
  import { runEndMs, memoryColor } from '../lib/timeline';
  import type { JobRun } from '../lib/types';

  let { runs, limitMb, hours = 72 }: { runs: JobRun[]; limitMb: number | null; hours?: number } =
    $props();

  const W = 600;
  const ROW_H = 20;
  const LEFT = 150;
  const TOP = 14;
  const HOUR_MS = 3_600_000;

  const nowMs = Date.now();
  const vStartMs = nowMs - hours * HOUR_MS;
  const vEndMs = nowMs;
  const spanMs = vEndMs - vStartMs;

  const rows = (() => {
    const list: { job_id: number; job_name: string; runs: JobRun[] }[] = [];
    const byId = new Map<number, number>();
    for (const run of runs) {
      let idx = byId.get(run.job_id);
      if (idx == null) {
        idx = list.length;
        byId.set(run.job_id, idx);
        list.push({ job_id: run.job_id, job_name: run.job_name, runs: [] });
      }
      list[idx].runs.push(run);
    }
    return list;
  })();

  const svgH = TOP + rows.length * ROW_H + 8;

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

{#if runs.length === 0}
  <div class="small muted">No recent runs</div>
{:else}
  <div class="mini-gantt">
    <svg width={W} height={svgH}>
      {#each rows as row, rowIdx}
        <line
          x1={LEFT}
          y1={TOP + rowIdx * ROW_H + ROW_H / 2}
          x2={W}
          y2={TOP + rowIdx * ROW_H + ROW_H / 2}
          stroke="var(--border)"
        />
        <text x="4" y={TOP + rowIdx * ROW_H + ROW_H - 6} fill="var(--text)" font-size="11">
          {row.job_name}
        </text>
        {#each row.runs as run}
          {@const g = barGeometry(run)}
          <rect
            x={g.x}
            y={TOP + rowIdx * ROW_H + ROW_H * 0.1}
            width={g.w}
            height={ROW_H * 0.8}
            rx="2"
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
    <div class="small muted">Last {hours} hours</div>
  </div>
{/if}

<style>
  .mini-gantt {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-top: 10px;
  }
  .mini-gantt svg {
    max-width: 100%;
    height: auto;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 6px;
  }
</style>