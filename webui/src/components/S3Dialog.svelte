<script lang="ts">
  import * as api from '../lib/api';
  import { auth } from '../lib/auth.svelte';
  import { toastError, toastSuccess, errMsg } from '../lib/toast.svelte';
  import type { S3Config } from '../lib/types';
  import Modal from './Modal.svelte';

  let { initial, onClose, onSave }: {
    initial: S3Config | null;
    onClose: () => void;
    onSave: (config: S3Config) => void;
  } = $props();

  let provider = $state(initial?.provider ?? 'aws');
  let endpoint = $state(initial?.endpoint ?? '');
  let bucket = $state(initial?.bucket ?? '');
  let region = $state(initial?.region ?? 'us-east-1');
  let accessKey = $state(initial?.access_key ?? '');
  let secretKey = $state(initial?.secret_key ?? '');
  let storageClass = $state(initial?.storage_class ?? 'STANDARD');
  let maxConcurrent = $state(String(initial?.max_concurrent_requests ?? 10));
  let maxQueue = $state(String(initial?.max_queue_size ?? 1000));
  let chunkSize = $state(initial?.multipart_chunk_size != null ? String(initial.multipart_chunk_size) : '8MB');

  let testing = $state(false);

  function config(): S3Config {
    return {
      provider,
      endpoint,
      bucket,
      region,
      access_key: accessKey,
      secret_key: secretKey,
      storage_class: storageClass,
      max_concurrent_requests: Number(maxConcurrent) || 10,
      max_queue_size: Number(maxQueue) || 1000,
      multipart_chunk_size: chunkSize,
    };
  }

  async function testConnection() {
    if (!bucket) return toastError('Please enter a bucket name');
    if (!accessKey || !secretKey) return toastError('Please enter access key and secret key');
    testing = true;
    try {
      await api.post('/s3/test', config(), auth.token);
      toastSuccess('S3 connection successful!');
    } catch (e) {
      toastError('S3 test failed: ' + errMsg(e));
    } finally {
      testing = false;
    }
  }

  function save() {
    onSave(config());
  }
</script>

<Modal title="S3 Synchronization" onClose={onClose}>
  <div class="grid cols-2">
    <div class="field">
      <label for="s3-provider">Provider</label>
      <select id="s3-provider" bind:value={provider}>
        <option value="aws">Amazon S3</option>
        <option value="minio">MinIO</option>
      </select>
    </div>
    <div class="field">
      <label for="s3-endpoint">Endpoint</label>
      <input id="s3-endpoint" bind:value={endpoint} placeholder="https://minio.example.com" />
    </div>
    <div class="field">
      <label for="s3-bucket">Bucket Name</label>
      <input id="s3-bucket" bind:value={bucket} />
    </div>
    <div class="field">
      <label for="s3-region">AWS Region</label>
      <input id="s3-region" bind:value={region} placeholder="us-east-1" />
    </div>
    <div class="field">
      <label for="s3-ak">Access Key</label>
      <input id="s3-ak" bind:value={accessKey} />
    </div>
    <div class="field">
      <label for="s3-sk">Secret Key</label>
      <input id="s3-sk" type="password" bind:value={secretKey} />
    </div>
    <div class="field">
      <label for="s3-class">Storage Class</label>
      <select id="s3-class" bind:value={storageClass}>
        <option value="STANDARD">Standard</option>
        <option value="STANDARD_IA">Standard-IA</option>
        <option value="GLACIER">Glacier</option>
        <option value="DEEP_ARCHIVE">Deep Archive</option>
      </select>
    </div>
    <div class="field">
      <label for="s3-mcr">Max Concurrent Requests</label>
      <input id="s3-mcr" type="number" bind:value={maxConcurrent} />
    </div>
    <div class="field">
      <label for="s3-mqs">Max Queue Size</label>
      <input id="s3-mqs" type="number" bind:value={maxQueue} />
    </div>
    <div class="field">
      <label for="s3-chunk">Multipart Chunk Size</label>
      <input id="s3-chunk" bind:value={chunkSize} />
    </div>
  </div>
  <div class="modal-actions">
    <button class="btn ghost" onclick={onClose}>Cancel</button>
    <button class="btn ghost" onclick={testConnection} disabled={testing}>
      {testing ? 'Testing…' : 'Test'}
    </button>
    <button class="btn" onclick={save}>Save</button>
  </div>
</Modal>