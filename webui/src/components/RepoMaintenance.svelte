<script lang="ts">
  import * as api from '../lib/api';
  import { auth } from '../lib/auth.svelte';
  import { toastError, errMsg } from '../lib/toast.svelte';
  import Icon from './Icon.svelte';

  let { repoId, encryptionKey }: { repoId: number; encryptionKey?: string } =
    $props();

  let kind = $state<'check' | 'repair' | null>(null);
  let running = $state(false);
  let exitCode = $state<number | null>(null);
  let output = $state<string[]>([]);
  let verifyData = $state(false);
  let confirmRepair = $state(false);
  let error = $state<string | null>(null);
  let pollId: ReturnType<typeof setInterval> | null = null;

  const body = (): Record<string, unknown> =>
    encryptionKey ? { encryption_key: encryptionKey } : {};

  function start(k: 'check' | 'repair') {
    error = null;
    exitCode = null;
    output = [];
    kind = k;
    running = true;
    const payload = body();
    if (k === 'check' && verifyData) payload.verify_data = true;
    if (k === 'repair') payload.confirm = true;
    api
      .post(`/repositories/${repoId}/${k}`, payload, auth.token)
      .then(() => {
        pollId = setInterval(poll, 1000);
      })
      .catch((e) => {
        running = false;
        kind = null;
        error = errMsg(e);
        toastError(`Failed to start ${k}: ${error}`);
      });
  }

  function poll() {
    api
      .get<{
        running: boolean;
        kind: string | null;
        exit_code: number | null;
        output: string[];
      }>(`/repositories/${repoId}/maintenance`, auth.token)
      .then((st) => {
        output = st.output ?? [];
        if (!st.running) {
          if (pollId) {
            clearInterval(pollId);
            pollId = null;
          }
          running = false;
          exitCode = st.exit_code ?? null;
        }
      })
      .catch((e) => {
        error = errMsg(e);
        toastError('Failed to poll maintenance: ' + error);
        if (pollId) {
          clearInterval(pollId);
          pollId = null;
        }
        running = false;
      });
  }

  // Stop polling when the dialog unmounts.
  $effect(() => {
    return () => {
      if (pollId) clearInterval(pollId);
    };
  });

  function doRepair() {
    confirmRepair = false;
    start('repair');
  }
</script>

<div class="maint">
  <h4>Repository Maintenance</h4>

  {#if running}
    <div class="running">
      <span class="spinner"></span>
      {kind === 'check' ? 'Checking repository…' : 'Repairing repository…'}
    </div>
  {:else}
    <div class="controls">
      <label class="verify">
        <input type="checkbox" bind:checked={verifyData} />
        Deep check (--verify-data, slower)
      </label>
      <button class="btn" onclick={() => start('check')}>
        <Icon icon="check" /> Check
      </button>
      <button class="btn danger" onclick={() => (confirmRepair = true)}>
        <Icon icon="wrench" /> Repair
      </button>
    </div>
  {/if}

  {#if confirmRepair}
    <div class="confirm">
      <p>
        <b>Repair</b> runs <code>borg check --repair</code>, which rebuilds the
        repository index and can be slow on large repositories. Make sure a
        recent successful backup exists before proceeding. Continue?
      </p>
      <div class="row">
        <button class="btn danger" onclick={doRepair}>Repair anyway</button>
        <button class="btn ghost" onclick={() => (confirmRepair = false)}>
          Cancel
        </button>
      </div>
    </div>
  {/if}

  {#if error}
    <p class="error">{error}</p>
  {/if}

  {#if kind && !running}
    <p class="done">
      {kind === 'check' ? 'Check' : 'Repair'} finished with exit code
      {exitCode === 0 ? '0 (ok)' : (exitCode ?? 'n/a')}.
    </p>
  {/if}

  {#if output.length > 0}
    <pre class="log">{output.join('\n')}</pre>
  {/if}
</div>

<style>
  .maint {
    margin-top: 6px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
  }
  .controls {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 8px;
  }
  .verify {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: var(--text-muted);
    cursor: pointer;
  }
  .running {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    color: var(--text-muted);
  }
  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  .confirm {
    margin-top: 10px;
    padding: 12px;
    border: 1px solid var(--warning-border, var(--border));
    background: var(--surface-1);
  }
  .row {
    display: flex;
    gap: 10px;
    margin-top: 8px;
  }
  .error {
    color: var(--error);
    margin: 8px 0;
  }
  .done {
    margin: 8px 0;
    color: var(--success);
  }
  .log {
    margin-top: 8px;
    max-height: 220px;
    overflow: auto;
    background: var(--code-bg, var(--surface-1));
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px;
    font-size: 12px;
    white-space: pre-wrap;
    word-break: break-word;
  }
</style>