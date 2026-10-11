<script lang="ts">
  import * as api from '../lib/api';
  import { auth } from '../lib/auth.svelte';
  import { toastError, errMsg } from '../lib/toast.svelte';
  import { formatBytes, formatDate } from '../lib/format';
  import type { SourceItem } from '../lib/types';
  import Icon from '../components/Icon.svelte';

  let currentPath = $state('/sourcespace');
  let items = $state<SourceItem[]>([]);
  let loading = $state(true);
  const pathHistory = $state<string[]>(['/sourcespace']);

  // per-path size request state
  const sizes = $state(new Map<string, string>());
  // paths with an in-flight size request
  const pendingSizes = $state(new Set<string>());

  async function load() {
    loading = true;
    try {
      const res = await api.post<{ items: SourceItem[] }>(
        '/sources/browse',
        { path: currentPath },
        auth.token
      );
      items = res.items ?? [];
    } catch (e) {
      toastError('Failed to load directory: ' + errMsg(e));
    } finally {
      loading = false;
    }
  }

  function navigateTo(path: string) {
    currentPath = path;
    if (pathHistory[pathHistory.length - 1] !== path) pathHistory.push(path);
    load();
  }

  function goBack() {
    if (pathHistory.length > 1) {
      pathHistory.pop();
      currentPath = pathHistory[pathHistory.length - 1];
      load();
    }
  }

  function goUp() {
    if (currentPath !== '/sourcespace' && currentPath !== '/') {
      const parent = currentPath.substring(0, currentPath.lastIndexOf('/'));
      navigateTo(parent.length === 0 ? '/' : parent);
    }
  }

  async function calcSize(item: SourceItem) {
    if (sizes.has(item.path) || pendingSizes.has(item.path)) return;
    pendingSizes.add(item.path);
    sizes.delete(item.path);
    try {
      const res = await api.post<{ size: number; approximate?: boolean }>(
        '/sources/size',
        { path: item.path },
        auth.token
      );
      sizes.set(
        item.path,
        (res.approximate ? '~' : '') + formatBytes(res.size)
      );
    } catch (e) {
      sizes.set(item.path, 'Error');
      toastError('Failed to calculate size: ' + errMsg(e));
    } finally {
      pendingSizes.delete(item.path);
      items = [...items];
    }
  }

  function open(item: SourceItem) {
    if (item.is_directory) {
      navigateTo(item.path);
    }
  }

  import { onMount } from 'svelte';
  onMount(() => { load(); });
</script>

<div class="toolbar">
  <button class="btn ghost" onclick={goBack} disabled={pathHistory.length <= 1}>
    <Icon icon="back" /> Back
  </button>
  <button
    class="btn ghost"
    onclick={goUp}
    disabled={currentPath === '/sourcespace' || currentPath === '/'}
  >
    <Icon icon="up" /> Up
  </button>
  <span class="path muted">{currentPath}</span>
</div>

{#if loading}
  <div class="spinner"></div>
{:else if items.length === 0}
  <div class="empty-state">Empty directory</div>
{:else}
  <ul class="files">
    {#each items as item}
      <li
        class="card file"
        class:dir={item.is_directory}
        onclick={() => open(item)}
      >
        <span class="file-icon">
          <Icon icon={item.is_directory ? 'folder' : 'file'} size={28} />
        </span>
        <div class="file-body">
          <span class="name">{item.name}</span>
          <div class="small muted">
            {#if item.permissions}Permissions: {item.permissions} · {/if}
            {#if item.is_directory && (pendingSizes.has(item.path) || sizes.has(item.path))}
              Size: {#if pendingSizes.has(item.path)}
                <span class="mini-spinner"></span> Computing…
              {:else}
                {sizes.get(item.path)}
              {/if} ·
            {/if}
            {#if !item.is_directory && item.size != null}
              Size: {formatBytes(item.size)} ·
            {/if}
            {#if item.last_modified}Modified: {formatDate(item.last_modified)}{/if}
          </div>
        </div>
        {#if item.is_directory && !sizes.has(item.path)}
          <button
            class="btn ghost size-btn"
            disabled={pendingSizes.has(item.path)}
            onclick={(e) => {
              e.stopPropagation();
              calcSize(item);
            }}
          >
            {#if pendingSizes.has(item.path)}
              <span class="mini-spinner"></span> Computing…
            {:else}
              Size
            {/if}
          </button>
        {/if}
      </li>
    {/each}
  </ul>
{/if}

<style>
  .toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
  }
  .path {
    margin-left: auto;
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
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    cursor: pointer;
  }
  .file:hover {
    background: var(--surface-2);
  }
  .file-icon {
    color: var(--accent-blue);
  }
  .file.dir .name {
    font-weight: 700;
  }
  .file-body {
    flex: 1;
    min-width: 0;
  }
  .file-body .name {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .size-btn {
    padding: 4px 10px;
    font-size: 12px;
    cursor: pointer;
  }
  .size-btn:hover:not(:disabled) {
    color: var(--accent-blue);
  }
  .size-btn:disabled {
    cursor: default;
    opacity: 0.8;
  }
  .size-btn .mini-spinner {
    vertical-align: middle;
    margin-right: 4px;
  }
  .mini-spinner {
    width: 11px;
    height: 11px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: size-spin 0.8s linear infinite;
    display: inline-block;
  }
  @keyframes size-spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>