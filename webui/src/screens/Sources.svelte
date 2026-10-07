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
    if (sizes.has(item.path)) return;
    try {
      const res = await api.post<{ size: number }>(
        '/sources/size',
        { path: item.path },
        auth.token
      );
      sizes.set(item.path, formatBytes(res.size));
      items = [...items];
    } catch {
      sizes.set(item.path, 'Error');
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
            {#if item.is_directory && sizes.has(item.path)}
              Size: {sizes.get(item.path)} ·
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
            onclick={(e) => { e.stopPropagation(); calcSize(item); }}
          >
            Size
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
  }
</style>