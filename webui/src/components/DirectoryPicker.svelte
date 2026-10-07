<script lang="ts">
  import * as api from '../lib/api';
  import { auth } from '../lib/auth.svelte';
  import { toastError, errMsg } from '../lib/toast.svelte';
  import type { SourceItem } from '../lib/types';
  import Icon from './Icon.svelte';
  import Modal from './Modal.svelte';

  let { onClose, onSelect }: { onClose: () => void; onSelect: (dir: string) => void } = $props();

  let currentPath = $state('/sourcespace');
  let items = $state<SourceItem[]>([]);
  let loading = $state(true);

  async function load() {
    loading = true;
    try {
      const res = await api.post<{ items: SourceItem[] }>(
        '/sources/browse',
        { path: currentPath },
        auth.token
      );
      items = (res.items ?? []).filter((i) => i.is_directory);
    } catch (e) {
      toastError('Failed to browse: ' + errMsg(e));
    } finally {
      loading = false;
    }
  }

  function enter(dir: SourceItem) {
    currentPath = dir.path;
    load();
  }

  function up() {
    if (currentPath === '/sourcespace') return;
    const parent = currentPath.substring(0, currentPath.lastIndexOf('/'));
    currentPath = parent.length === 0 ? '/' : parent;
    load();
  }

  import { onMount } from 'svelte';
  onMount(() => { load(); });
</script>

<Modal title="Select Source Directory" onClose={onClose}>
  <div class="crumb">
    <button class="btn ghost" onclick={up} disabled={currentPath === '/sourcespace'}>
      <Icon icon="up" /> Up
    </button>
    <span class="muted">{currentPath}</span>
  </div>

  <div class="dirs">
    {#if loading}
      <div class="spinner"></div>
    {:else if items.length === 0}
      <div class="empty-state">No subdirectories</div>
    {:else}
      {#each items as d}
        <button class="dir" onclick={() => enter(d)}>
          <Icon icon="folder" />
          <span>{d.name}</span>
        </button>
      {/each}
    {/if}
  </div>

  <div class="modal-actions">
    <button class="btn ghost" onclick={onClose}>Cancel</button>
    <button class="btn" onclick={() => onSelect(currentPath)}>
      Select This Directory
    </button>
  </div>
</Modal>

<style>
  .crumb {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
  }
  .dirs {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-height: 320px;
    overflow: auto;
  }
  .dir {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    border: none;
    background: transparent;
    color: var(--text);
    border-radius: 6px;
    cursor: pointer;
    text-align: left;
    font-size: 14px;
  }
  .dir:hover {
    background: var(--surface-2);
  }
  .dir :global(svg) {
    color: var(--accent-blue);
  }
</style>