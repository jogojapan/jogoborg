<script lang="ts">
  import * as api from '../lib/api';
  import { auth } from '../lib/auth.svelte';
  import { toastError, toastSuccess, errMsg } from '../lib/toast.svelte';
  import type { DbConfig } from '../lib/types';
  import Modal from './Modal.svelte';

  let { initial, onClose, onSave }: {
    initial: DbConfig | null;
    onClose: () => void;
    onSave: (config: DbConfig) => void;
  } = $props();

  let type = $state(initial?.type ?? 'postgresql');
  let host = $state(initial?.host ?? '');
  let port = $state(String(initial?.port ?? 5432));
  let username = $state(initial?.username ?? '');
  let password = $state(initial?.password ?? '');
  let database = $state(initial?.database ?? '');
  let tables = $state((initial?.tables ?? []).join('\n'));

  let testing = $state(false);

  function config(): DbConfig {
    return {
      type,
      host,
      port: Number(port) || 5432,
      username,
      password,
      database,
      tables: tables.split('\n').map((t) => t.trim()).filter((t) => t.length > 0),
    };
  }

  async function testConnection() {
    testing = true;
    try {
      await api.post('/database/test', config(), auth.token);
      toastSuccess('Database connection successful!');
    } catch (e) {
      toastError('Connection failed: ' + errMsg(e));
    } finally {
      testing = false;
    }
  }

  function save() {
    onSave(config());
  }
</script>

<Modal title="Database Dump" onClose={onClose}>
  <div class="grid cols-2">
    <div class="field">
      <label for="db-type">Database Type</label>
      <select id="db-type" bind:value={type}>
        <option value="postgresql">PostgreSQL</option>
        <option value="mariadb">MariaDB/MySQL</option>
      </select>
    </div>
    <div class="field">
      <label for="db-port">Port</label>
      <input id="db-port" type="number" bind:value={port} />
    </div>
    <div class="field">
      <label for="db-host">Host</label>
      <input id="db-host" bind:value={host} />
    </div>
    <div class="field">
      <label for="db-user">Username</label>
      <input id="db-user" bind:value={username} />
    </div>
    <div class="field">
      <label for="db-pass">Password</label>
      <input id="db-pass" type="password" bind:value={password} />
    </div>
    <div class="field">
      <label for="db-name">Database Name</label>
      <input id="db-name" bind:value={database} />
    </div>
    <div class="field full">
      <label for="db-tables">Tables (one per line)</label>
      <textarea id="db-tables" bind:value={tables} rows="4" placeholder="users&#10;orders&#10;products"></textarea>
    </div>
  </div>
  <div class="modal-actions">
    <button class="btn ghost" onclick={onClose}>Cancel</button>
    <button class="btn ghost" onclick={testConnection} disabled={testing}>
      {testing ? 'Testing…' : 'Test Connection'}
    </button>
    <button class="btn" onclick={save}>Save</button>
  </div>
</Modal>

<style>
  .full {
    grid-column: 1 / -1;
  }
</style>