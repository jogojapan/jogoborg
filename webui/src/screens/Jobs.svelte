<script lang="ts">
  import * as api from '../lib/api';
  import { auth } from '../lib/auth.svelte';
  import { toastError, toastSuccess, errMsg } from '../lib/toast.svelte';
  import type { Job } from '../lib/types';
  import Icon from '../components/Icon.svelte';
  import Modal from '../components/Modal.svelte';
  import JobForm from '../components/JobForm.svelte';
  import LastRuns from './LastRuns.svelte';

  let jobs = $state<Job[]>([]);
  let loading = $state(true);
  let showForm = $state(false);
  let editing = $state<Job | null>(null);

  // confirm dialog state
  let confirm = $state<{ title: string; message: string; action: () => Promise<void> } | null>(null);

  async function load() {
    loading = true;
    try {
      const res = await api.get<{ jobs: Job[] }>('/jobs', auth.token);
      jobs = res.jobs ?? [];
    } catch (e) {
      toastError('Failed to load jobs: ' + errMsg(e));
    } finally {
      loading = false;
    }
  }

  function openNew() {
    editing = null;
    showForm = true;
  }

  function openEdit(job: Job) {
    editing = job;
    showForm = true;
  }

  async function runNow(job: Job) {
    try {
      await api.post(`/jobs/${job.id}/trigger`, {}, auth.token);
      toastSuccess(`Job "${job.name}" has been triggered and is running in the background`);
      load();
    } catch (e) {
      toastError('Failed to trigger job: ' + errMsg(e));
    }
  }

  async function deleteJob(job: Job) {
    try {
      await api.del(`/jobs/${job.id}`, auth.token);
      toastSuccess('Job deleted successfully');
      load();
    } catch (e) {
      toastError('Failed to delete job: ' + errMsg(e));
    }
  }

  import { onMount } from 'svelte';
  onMount(() => { load(); });
</script>

<div class="toolbar">
  <button class="btn" onclick={openNew}>
    <Icon icon="add" /> New Job
  </button>
  <button class="btn ghost" onclick={load}>
    <Icon icon="refresh" /> Refresh
  </button>
</div>

{#if loading}
  <div class="spinner"></div>
{:else if jobs.length === 0}
  <div class="empty-state">No backup jobs yet</div>
{:else}
  {#each jobs as job}
    <article class="card job">
      <div class="job-head">
        <div>
          <h3>{job.name}</h3>
          <div class="small muted">Schedule: {job.schedule || 'Not set'}</div>
        </div>
        <span class="menu">
          <button class="btn ghost sm" onclick={() => runNow(job)}>
            <Icon icon="play" size={16} /> Run Now
          </button>
          <button class="btn ghost sm" onclick={() => openEdit(job)}>Details</button>
          <button
            class="icon-btn"
            title="Delete"
            aria-label="Delete"
            onclick={() => {
              confirm = {
                title: 'Delete Job',
                message: `Are you sure you want to delete job "${job.name}"?`,
                action: () => deleteJob(job),
              };
            }}
          >
            <Icon icon="trash" size={18} />
          </button>
        </span>
      </div>

      <div class="small">
        <b>Compression:</b> {job.compression ?? 'lz4'} ·{' '}
        <b>Retention:</b> Daily: {job.keep_daily}, Monthly: {job.keep_monthly},
        Yearly: {job.keep_yearly}
      </div>

      {#if job.source_directories.length > 0}
        <div class="srcs small">
          <b>Source Directories:</b>
          <ul>
            {#each job.source_directories as d}
              <li><Icon icon="folder" size={14} /> {d}</li>
            {/each}
          </ul>
        </div>
      {/if}

      <LastRuns jobId={job.id} />
    </article>
  {/each}
{/if}

{#if showForm}
  <JobForm
    job={editing}
    onClose={() => (showForm = false)}
    onSaved={load}
  />
{/if}

{#if confirm}
  <Modal title={confirm.title} onClose={() => (confirm = null)}>
    <p>{confirm.message}</p>
    <div class="modal-actions">
      <button class="btn ghost" onclick={() => (confirm = null)}>Cancel</button>
      <button
        class="btn danger"
        onclick={async () => {
          await confirm?.action();
          confirm = null;
        }}
      >
        Confirm
      </button>
    </div>
  </Modal>
{/if}

<style>
  .toolbar {
    display: flex;
    gap: 10px;
    margin-bottom: 16px;
  }
  .sm {
    padding: 5px 10px;
    font-size: 12px;
  }
  .job {
    margin-bottom: 14px;
  }
  .job-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 8px;
  }
  .job-head h3 {
    margin: 0;
    font-size: 20px;
  }
  .menu {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .srcs ul {
    margin: 4px 0 0;
    padding-left: 20px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .srcs li {
    display: flex;
    align-items: center;
    gap: 6px;
  }
</style>