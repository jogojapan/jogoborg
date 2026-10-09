<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import * as api from '../lib/api';
  import { auth } from '../lib/auth.svelte';
  import { toastError, errMsg } from '../lib/toast.svelte';
  import { formatBytes, formatDate } from '../lib/format';
  import type { ArchiveItem } from '../lib/types';
  import Icon from './Icon.svelte';

  let {
    repoId,
    repoName,
    archive,
    encryptionKey,
    onBackToArchives,
    onBack,
  }: {
    repoId: number;
    repoName: string;
    archive: string;
    encryptionKey?: string;
    onBackToArchives: () => void;
    onBack: () => void;
  } = $props();

  let path = $state('/');
  let items = $state<ArchiveItem[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let progress = $state<{
    running?: boolean;
    done?: number;
    total?: number | null;
    percent?: number | null;
  } | null>(null);
  let progressTimer: number | undefined;

  async function load() {
    loading = true;
    error = null;
    progress = null;
    clearInterval(progressTimer);
    progressTimer = setInterval(async () => {
      try {
        progress = await api.get<{
          running?: boolean;
          done?: number;
          total?: number | null;
          percent?: number | null;
        }>(
          `/repositories/${repoId}/archives/${encodeURIComponent(archive)}/progress`,
          auth.token
        );
      } catch {
        /* transient — the scan may have just ended */
      }
    }, 400);

    try {
      const res = await api.post<{ items: ArchiveItem[] }>(
        `/repositories/${repoId}/archives/${encodeURIComponent(archive)}/browse`,
        { path, ...(encryptionKey ? { encryption_key: encryptionKey } : {}) },
        auth.token
      );
      items = res.items ?? [];
    } catch (e) {
      const msg = errMsg(e);
      error = msg;
      toastError('Failed to browse archive: ' + msg);
    } finally {
      clearInterval(progressTimer);
      progressTimer = undefined;
      loading = false;
    }
  }

  onDestroy(() => {
    clearInterval(progressTimer);
    progressTimer = undefined;
  });

  onMount(() => {
    load();
  });

  function openDir(name: string) {
    path = path === '/' ? `/${name}` : `${path}/${name}`;
    load();
  }

  function up() {
    if (path === '/') return;
    path = path.substring(0, path.lastIndexOf('/')) || '/';
    load();
  }
</script>

<div class="toolbar">
  <button class="btn ghost" onclick={onBackToArchives}>
    <Icon icon="back" /> Archives
  </button>
  <button class="btn ghost" onclick={onBack}>
    <Icon icon="back" /> Repositories
  </button>
  <button class="btn ghost" onclick={up} disabled={path === '/'}>
    <Icon icon="up" /> Up
  </button>
  <span class="crumb small muted">
    <span class="crumb-main">{repoName} :: {archive}</span>
    <span class="crumb-path">{path}</span>
  </span>
</div>

{#if loading}
  {#if progress && progress.percent != null}
    <div class="scan">
      <div
        class="scan-bar"
        role="progressbar"
        aria-valuenow={Math.min(100, progress.percent)}
        aria-valuemin="0"
        aria-valuemax="100"
      >
        <div class="scan-fill" style="width:{Math.min(100, progress.percent)}%"></div>
      </div>
      <div class="small muted">
        Scanning archive… {Math.min(100, progress.percent)}%
        {#if progress && progress.done != null}({progress.done} items scanned){/if}
      </div>
    </div>
  {:else}
    <div class="spinner" aria-label="Loading" role="status"></div>
  {/if}
{:else if error}
  <div class="empty-state">
    <b>Couldn’t load archive</b>
    <div class="muted small">{error}</div>
  </div>
{:else if items.length === 0}
  <div class="empty-state">Empty directory</div>
{:else}
  <ul class="files">
    {#each items as item (item.name)}
      <li
        class="file"
        class:card={true}
        class:dir={item.is_directory}
        class:clickable={item.is_directory}
        onclick={() => item.is_directory && openDir(item.name)}
      >
        {#if item.is_directory}
          <span class="folder-icon"><Icon icon="folder" size={26} /></span>
        {:else}
          <span class="file-icon"><Icon icon="file" size={26} /></span>
        {/if}
        <span class="name" class:dir-name={item.is_directory}>{item.name}</span>
        <span class="size muted small">
          {item.is_directory ? '—' : formatBytes(item.size)}
        </span>
        <span class="date muted small">{formatDate(item.mtime)}</span>
      </li>
    {/each}
  </ul>
{/if}

<style>
  .toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 12px;
  }

  .crumb {
    display: flex;
    flex-direction: column;
    min-width: 0;
    margin-left: 8px;
    gap: 2px;
  }

  .crumb-main {
    font-weight: 600;
  }

  .crumb-path {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: monospace;
  }

  .files {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .file {
    display: grid;
    grid-template-columns: 32px minmax(0, 1fr) 90px 170px;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
  }

  .file.clickable {
    cursor: pointer;
  }

  .file.clickable:hover {
    border-color: var(--border);
    background: var(--surface-2);
  }

  .folder-icon {
    color: var(--accent-blue);
  }

  .file-icon {
    color: var(--text-muted);
  }

  .name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dir-name {
    font-weight: 600;
    color: var(--text);
  }

  .size {
    text-align: right;
    white-space: nowrap;
  }

  .date {
    text-align: right;
    white-space: nowrap;
  }

  .scan {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    max-width: 640px;
  }
  .scan-bar {
    width: 100%;
    height: 8px;
    border-radius: 4px;
    background: var(--surface-2);
    border: 1px solid var(--border);
    overflow: hidden;
  }
  .scan-fill {
    height: 100%;
    background: var(--primary);
    transition: width 0.2s;
  }
</style>