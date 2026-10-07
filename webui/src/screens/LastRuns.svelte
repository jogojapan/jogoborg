<script lang="ts">
  import * as api from '../lib/api';
  import { auth } from '../lib/auth.svelte';
  import { formatDate, formatDuration } from '../lib/format';
  import type { JobLog } from '../lib/types';

  let { jobId }: { jobId: number } = $props();

  let logs = $state<JobLog[]>([]);
  let loading = $state(true);

  async function load() {
    loading = true;
    try {
      const res = await api.get<{ logs: JobLog[] }>(
        `/jobs/${jobId}/logs?limit=3`,
        auth.token
      );
      logs = res.logs ?? [];
    } catch {
      /* quiet — last runs are best effort */
    } finally {
      loading = false;
    }
  }

  import { onMount } from 'svelte';
  onMount(() => { load(); });
</script>

{#if loading}
  <div class="muted small">Loading last runs…</div>
{:else if logs.length === 0}
  <div class="muted small">Last runs: No runs yet</div>
{:else}
  <div class="small" style="margin-top:8px">
    <b>Last {logs.length > 1 ? logs.length + ' runs' : 'run'}:</b>
    <table class="runs">
      <tbody>
        {#each logs as l}
          <tr>
            <td class="status">
              {#if l.status === 'success'}
                <span class="dot ok"></span>
              {:else}
                <span class="dot bad"></span>
              {/if}
            </td>
            <td>{formatDate(l.started_at)}</td>
            <td>{l.status}</td>
            <td class="muted">
              {#if l.create_duration != null}create {formatDuration(l.create_duration)}{/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}

<style>
  .runs {
    border-collapse: collapse;
    margin-top: 4px;
  }
  .runs td {
    padding: 2px 10px 2px 0;
  }
  .dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }
  .dot.ok { background: var(--success); }
  .dot.bad { background: var(--error); }
</style>