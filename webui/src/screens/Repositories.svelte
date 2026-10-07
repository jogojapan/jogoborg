<script lang="ts">
  import * as api from '../lib/api';
  import { auth } from '../lib/auth.svelte';
  import { toastError, errMsg } from '../lib/toast.svelte';
  import { formatBytes, formatDate } from '../lib/format';
  import type { Repository, Archive } from '../lib/types';
  import Icon from '../components/Icon.svelte';
  import Modal from '../components/Modal.svelte';

  let repositories = $state<Repository[]>([]);
  let loading = $state(true);

  // active repository dialog state
  let dialog = $state<Repository | null>(null);
  let archives = $state<Archive[]>([]);
  let unlockKey = $state('');
  let unlocking = $state(false);
  let unlocked = $state(false);

  async function load() {
    loading = true;
    try {
      const res = await api.get<{ repositories: Repository[] }>(
        '/repositories',
        auth.token
      );
      repositories = res.repositories ?? [];
    } catch (e) {
      toastError('Failed to load repositories: ' + errMsg(e));
    } finally {
      loading = false;
    }
  }

  function openRepo(repo: Repository) {
    dialog = repo;
    archives = [];
    unlockKey = '';
    unlocked = false;
  }

  async function unlock() {
    if (!dialog || !unlockKey) {
      toastError('Please enter the encryption key');
      return;
    }
    unlocking = true;
    try {
      const res = await api.post<{ archives: Archive[] }>(
        `/repositories/${dialog.id}/unlock`,
        { encryption_key: unlockKey },
        auth.token
      );
      archives = res.archives ?? [];
      unlocked = true;
    } catch (e) {
      toastError('Failed to unlock repository: ' + errMsg(e));
    } finally {
      unlocking = false;
    }
  }

  function closeDialog() {
    dialog = null;
  }

  import { onMount } from 'svelte';
  onMount(() => { load(); });
</script>

<div class="toolbar">
  <button class="btn ghost" onclick={load}>
    <Icon icon="refresh" /> Refresh
  </button>
</div>

{#if loading}
  <div class="spinner"></div>
{:else if repositories.length === 0}
  <div class="empty-state">No repositories found in /borgspace</div>
{:else}
  <div class="grid cols-3">
    {#each repositories as repo}
      <button class="card repo" onclick={() => openRepo(repo)}>
        <div class="repo-head">
          <span class="icon"><Icon icon="repos" size={32} /></span>
          <span class="name">{repo.name}</span>
        </div>
        <div class="small muted">Path: {repo.path}</div>
        <div class="small muted">Archives: {repo.archives_count}</div>
      </button>
    {/each}
  </div>
{/if}

{#if dialog}
  <Modal title={'Repository: ' + dialog.name} onClose={closeDialog}>
    <p class="muted">Path: {dialog.path}</p>

    {#if !unlocked}
      <div class="field">
        <label for="repo-key">Encryption Key</label>
        <input
          id="repo-key"
          type="password"
          bind:value={unlockKey}
          onkeydown={(e) => { if (e.key === 'Enter') unlock(); }}
        />
      </div>
      <button class="btn" onclick={unlock} disabled={unlocking}>
        <Icon icon="lock" /> {unlocking ? 'Unlocking…' : 'Unlock'}
      </button>
    {:else}
      <h4>Archives (newest first):</h4>
      {#if archives.length === 0}
        <div class="empty-state">No archives found</div>
      {:else}
        <ul class="archives">
          {#each archives as a}
            <li class="card">
              <div class="a-name"><Icon icon="archive" /> {a.name}</div>
              <div class="small muted">Created: {formatDate(a.created_at)}</div>
              {#if a.size != null}
                <div class="small muted">Size: {formatBytes(a.size)}</div>
              {/if}
              {#if a.files_count != null}
                <div class="small muted">Files: {a.files_count}</div>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}
    {/if}
  </Modal>
{/if}

<style>
  .toolbar {
    margin-bottom: 14px;
    display: flex;
    justify-content: flex-end;
  }
  .repo {
    text-align: left;
    font-size: 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    cursor: pointer;
    color: var(--text);
  }
  .repo:hover {
    background: var(--surface-2);
  }
  .repo-head {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 6px;
  }
  .repo-head .name {
    font-size: 18px;
    font-weight: 700;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .repo-head .icon {
    color: var(--accent-blue);
  }
  .archives {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .archives .a-name {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
  }
</style>