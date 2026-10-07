<script lang="ts">
  import * as api from '../lib/api';
  import { auth } from '../lib/auth.svelte';
  import { toastError, errMsg } from '../lib/toast.svelte';
  import { fetchTimeline } from '../lib/timeline';
  import type { Job, JobPayload, S3Config, DbConfig, JobRun } from '../lib/types';
  import Modal from './Modal.svelte';
  import Icon from './Icon.svelte';
  import DirectoryPicker from './DirectoryPicker.svelte';
  import S3Dialog from './S3Dialog.svelte';
  import DbDialog from './DbDialog.svelte';
  import CommandsDialog from './CommandsDialog.svelte';
  import MiniGantt from './MiniGantt.svelte';

  let { job, onClose, onSaved }: {
    job: Job | null;
    onClose: () => void;
    onSaved: () => void;
  } = $props();

  const isEditing = job !== null;

  let name = $state(job?.name ?? '');
  let schedule = $state(job?.schedule ?? '');
  let compression = $state(job?.compression ?? 'lz4');
  let excludePatterns = $state(job?.exclude_patterns ?? '');
  let keepDaily = $state(String(job?.keep_daily ?? 7));
  let keepMonthly = $state(String(job?.keep_monthly ?? 6));
  let keepYearly = $state(String(job?.keep_yearly ?? 1));
  let passphrase = $state('');
  let sourceDirs = $state<string[]>([...(job?.source_directories ?? [])]);
  let s3Config = $state<S3Config | null>(job?.s3_config ?? null);
  let dbConfig = $state<DbConfig | null>(job?.db_config ?? null);
  let preCommand = $state(job?.pre_command ?? '');
  let postCommand = $state(job?.post_command ?? '');

  let saving = $state(false);
  let activeDialog = $state<'dir' | 's3' | 'db' | 'commands' | null>(null);

  // "View activity" mini Gantt (recent runs, to pick a quiet window)
  let showActivity = $state(false);
  let actRuns = $state<JobRun[]>([]);
  let actLimit = $state<number | null>(null);
  let actLoading = $state(false);

  async function toggleActivity() {
    showActivity = !showActivity;
    if (showActivity && actRuns.length === 0) {
      actLoading = true;
      try {
        const res = await fetchTimeline(72);
        actRuns = res.logs;
        actLimit = res.memory_limit_mb;
      } catch (e) {
        toastError('Failed to load scheduling activity: ' + errMsg(e));
      } finally {
        actLoading = false;
      }
    }
  }

  function addSource(dir: string) {
    if (!sourceDirs.includes(dir)) sourceDirs.push(dir);
    activeDialog = null;
  }

  async function saveJob() {
    if (!name.trim() || !schedule.trim()) {
      toastError('Name and schedule are required');
      return;
    }
    if (sourceDirs.length === 0) {
      toastError('Please add at least one source directory');
      return;
    }
    if (!isEditing && !passphrase) {
      toastError('Repository passphrase is required');
      return;
    }

    saving = true;
    const payload: JobPayload = {
      name: name.trim(),
      schedule: schedule.trim(),
      compression: compression.trim() || 'lz4',
      exclude_patterns: excludePatterns,
      keep_daily: Number(keepDaily) || 7,
      keep_monthly: Number(keepMonthly) || 6,
      keep_yearly: Number(keepYearly) || 1,
      source_directories: sourceDirs,
      pre_command: preCommand,
      post_command: postCommand,
      s3_config: s3Config,
      db_config: dbConfig,
    };
    // Send the passphrase only when creating a job, or when the user enters a
    // new one on edit (backend keeps the stored value otherwise).
    if (!isEditing || passphrase) {
      payload.repository_passphrase = passphrase;
    }
    try {
      if (isEditing && job) {
        await api.put(`/jobs/${job.id}`, payload, auth.token);
      } else {
        await api.post('/jobs', payload, auth.token);
      }
      onSaved();
      onClose();
    } catch (e) {
      toastError('Failed to save job: ' + errMsg(e));
    } finally {
      saving = false;
    }
  }
</script>

<Modal title={isEditing ? 'Edit Job' : 'New Job'} onClose={onClose}>
  <div class="field">
    <label for="job-name">Job Name</label>
    <input id="job-name" bind:value={name} />
  </div>
  <div class="field">
    <label for="job-schedule">Schedule (cron)</label>
    <input id="job-schedule" bind:value={schedule} placeholder="0 2 * * *" />
  </div>
  <button class="btn ghost" onclick={toggleActivity} style="margin:-2px 0 10px">
    <Icon icon="activity" />
    {showActivity ? 'Hide' : 'View'} scheduling activity
  </button>
  {#if showActivity}
    <div class="mini-wrap">
      {#if actLoading}
        <div class="spinner"></div>
      {:else}
        <MiniGantt runs={actRuns} limitMb={actLimit} hours={72} />
      {/if}
    </div>
  {/if}
  <div class="field">
    {#if !isEditing}
      <label for="job-pass">Repository Passphrase</label>
      <input
        id="job-pass"
        type="password"
        bind:value={passphrase}
        autocomplete="new-password"
        required
        placeholder="Enter a strong passphrase for Borg encryption"
      />
    {:else}
      <label for="job-pass">Repository Passphrase (leave empty to keep current)</label>
      <input
        id="job-pass"
        type="password"
        bind:value={passphrase}
        autocomplete="new-password"
        placeholder="Only if you need to change it"
      />
    {/if}
  </div>
  <div class="grid cols-2">
    <div class="field">
      <label for="job-comp">Compression</label>
      <input id="job-comp" bind:value={compression} placeholder="lz4" />
    </div>
    <div class="field">
      <label for="job-excl">Exclude Patterns (one per line)</label>
      <input id="job-excl" bind:value={excludePatterns} placeholder="*.log&#10;*.tmp" />
    </div>
    <div class="field">
      <label for="job-kd">Keep Daily</label>
      <input id="job-kd" type="number" bind:value={keepDaily} />
    </div>
    <div class="field">
      <label for="job-km">Keep Monthly</label>
      <input id="job-km" type="number" bind:value={keepMonthly} />
    </div>
    <div class="field">
      <label for="job-ky">Keep Yearly</label>
      <input id="job-ky" type="number" bind:value={keepYearly} />
    </div>
  </div>

  <h4>Source Directories</h4>
  <div class="src-list">
    {#each sourceDirs as dir}
      <div class="src-row">
        <Icon icon="folder" size={16} />
        <span>{dir}</span>
        <button
          class="icon-btn"
          aria-label="Remove"
          onclick={() => { sourceDirs = sourceDirs.filter((d) => d !== dir); }}
        >
          <Icon icon="close" size={16} />
        </button>
      </div>
    {/each}
    <button class="btn ghost" onclick={() => (activeDialog = 'dir')}>
      <Icon icon="add" /> Add Source Directory
    </button>
  </div>

  <h4>Advanced</h4>
  <div class="adv-row">
    <button class="btn ghost" onclick={() => (activeDialog = 's3')}>
      <Icon icon="webhook" /> {s3Config ? 'Edit S3 Configuration' : 'Configure S3'}
    </button>
    <button class="btn ghost" onclick={() => (activeDialog = 'db')}>
      <Icon icon="database" /> {dbConfig ? 'Edit Database Dump' : 'Configure Database Dump'}
    </button>
    <button class="btn ghost" onclick={() => (activeDialog = 'commands')}>
      <Icon icon="info" /> Commands
    </button>
  </div>

  <div class="summary small muted">
    {#if s3Config}
      <div>S3: {s3Config.provider === 'minio' ? 'MinIO' : 'Amazon S3'} →
        bucket {s3Config.bucket || '—'}</div>
    {/if}
    {#if dbConfig}
      <div>
        DB: {dbConfig.type === 'mariadb' ? 'MariaDB/MySQL' : 'PostgreSQL'} →
        {dbConfig.database || '—'}
      </div>
    {/if}
    {#if preCommand}<div>Pre: {preCommand}</div>{/if}
    {#if postCommand}<div>Post: {postCommand}</div>{/if}
  </div>

  <div class="modal-actions">
    <button class="btn ghost" onclick={onClose}>Cancel</button>
    <button class="btn" onclick={saveJob} disabled={saving}>
      {saving ? 'Saving…' : 'Save'}
    </button>
  </div>
</Modal>

{#if activeDialog === 'dir'}
  <DirectoryPicker onClose={() => (activeDialog = null)} onSelect={addSource} />
{/if}
{#if activeDialog === 's3'}
  <S3Dialog initial={s3Config} onClose={() => (activeDialog = null)} onSave={(c) => { s3Config = c; activeDialog = null; }} />
{/if}
{#if activeDialog === 'db'}
  <DbDialog initial={dbConfig} onClose={() => (activeDialog = null)} onSave={(c) => { dbConfig = c; activeDialog = null; }} />
{/if}
{#if activeDialog === 'commands'}
  <CommandsDialog initial={{ pre: preCommand, post: postCommand }} onClose={() => (activeDialog = null)} onSave={(v) => { preCommand = v.pre; postCommand = v.post; activeDialog = null; }} />
{/if}

<style>
  h4 {
    margin: 16px 0 8px;
  }
  .mini-wrap {
    margin-bottom: 12px;
    padding: 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow-x: auto;
    background: var(--surface-2);
  }
  .src-list,
  .summary {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .src-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .src-row span {
    flex: 1;
  }
  .adv-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }
  .summary {
    margin-top: 12px;
  }
</style>