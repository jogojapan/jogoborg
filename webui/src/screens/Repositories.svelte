<script lang="ts">
  import * as api from '../lib/api';
  import { auth } from '../lib/auth.svelte';
  import { toastError, toastSuccess, errMsg } from '../lib/toast.svelte';
  import { formatBytes, formatDate } from '../lib/format';
  import type { Repository, Archive } from '../lib/types';
  import Icon from '../components/Icon.svelte';
  import Modal from '../components/Modal.svelte';
  import NewRepositoryDialog from '../components/NewRepositoryDialog.svelte';
  import ArchiveBrowser from '../components/ArchiveBrowser.svelte';

  let repositories = $state<Repository[]>([]);
  let loading = $state(true);

  // active repository dialog state
  let dialog = $state<Repository | null>(null);
  let archives = $state<Archive[]>([]);
  let unlockKey = $state('');
  let unlocking = $state(false);
  let unlocked = $state(false);
  let showNew = $state(false);
  let showKeyField = $state(false);
  let remember = $state(true);
  let browse = $state<{
    repoId: number;
    repoName: string;
    archive: string;
    encryptionKey?: string;
  } | null>(null);

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
    showKeyField = !repo.has_stored_key;
    if (repo.has_stored_key) {
      unlock(); // auto-unlock using the stored passphrase
    }
  }

  async function unlock(key?: string) {
    if (!dialog) return;
    unlocking = true;
    try {
      const res = await api.post<{ archives: Archive[] }>(
        `/repositories/${dialog.id}/unlock`,
        key ? { encryption_key: key } : {},
        auth.token
      );
      archives = res.archives ?? [];
      unlocked = true;
      if (key && remember) {
        try {
          await api.put(
            `/repositories/${dialog.id}/passphrase`,
            { encryption_key: key },
            auth.token
          );
          toastSuccess('Passphrase saved for this repository');
          load(); // refresh has_stored_key on the card
        } catch (e) {
          toastError('Unlocked, but saving the passphrase failed: ' + errMsg(e));
        }
      }
    } catch (e) {
      if (!showKeyField) showKeyField = true; // fall back to manual entry
      toastError('Failed to unlock repository: ' + errMsg(e));
    } finally {
      unlocking = false;
    }
  }

  function closeDialog() {
    dialog = null;
  }

  function openArchive(a: Archive) {
    if (!dialog) return;
    browse = {
      repoId: dialog.id,
      repoName: dialog.name,
      archive: a.name,
      encryptionKey: unlockKey || undefined,
    };
    // Keep `dialog` set: the explorer replaces the modal view, and going back
    // to the archive list restores it without re-unlocking.
  }

  import { onMount } from 'svelte';
  onMount(() => { load(); });
</script>

<div class="toolbar">
  <button class="btn" onclick={() => (showNew = true)}>
    <Icon icon="add" /> New Repository
  </button>
  <button class="btn ghost" onclick={load}>
    <Icon icon="refresh" /> Refresh
  </button>
</div>

{#if browse}
  <ArchiveBrowser
    repoId={browse.repoId}
    repoName={browse.repoName}
    archive={browse.archive}
    encryptionKey={browse.encryptionKey}
    onBackToArchives={() => (browse = null)}
    onBack={() => {
      browse = null;
      dialog = null;
    }}
  />
{:else}
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
          <div class="small muted">Archives: {repo.archives_count ?? 'unknown'}</div>
        </button>
      {/each}
    </div>
  {/if}
{/if}

{#if showNew}
  <NewRepositoryDialog
    onClose={() => (showNew = false)}
    onCreated={() => {
      showNew = false;
      load();
    }}
  />
{/if}

{#if dialog && !browse}
  <Modal title={'Repository: ' + dialog.name} onClose={closeDialog}>
    <p class="muted">Path: {dialog.path}</p>

    {#if !unlocked}
      {#if unlocking}
        <div class="spinner"></div>
      {:else if !showKeyField}
        <button class="btn" onclick={() => unlock()}>
          <Icon icon="lock" /> Unlock (saved passphrase)
        </button>
        <button class="btn ghost" onclick={() => (showKeyField = true)}>
          Enter key manually
        </button>
      {:else}
        <div class="field">
          <label for="repo-key">Encryption Key</label>
          <input
            id="repo-key"
            type="password"
            bind:value={unlockKey}
            onkeydown={(e) => { if (e.key === 'Enter') unlock(unlockKey); }}
          />
        </div>
        <label class="remember">
          <input type="checkbox" bind:checked={remember} />
          Remember this passphrase (auto-unlock next time)
        </label>
        <button class="btn" onclick={() => unlock(unlockKey)} disabled={unlocking}>
          <Icon icon="lock" /> {unlocking ? 'Unlocking…' : 'Unlock'}
        </button>
      {/if}
    {:else}
      <h4>Archives (newest first):</h4>
      {#if archives.length === 0}
        <div class="empty-state">No archives found</div>
      {:else}
        <div class="small muted" style="margin-bottom:6px">
          Click an archive to browse its contents.
        </div>
        <ul class="archives">
          {#each archives as a}
            <li
              class="card archive"
              role="button"
              onclick={() => openArchive(a)}
            >
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
  .archives .archive {
    cursor: pointer;
  }
  .archives .archive:hover {
    background: var(--surface-2);
  }
  .remember {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--text-muted);
    margin: 8px 0;
    cursor: pointer;
  }
</style>