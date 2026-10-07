<script lang="ts">
  import * as api from '../lib/api';
  import { auth } from '../lib/auth.svelte';
  import { toastSuccess, toastError, errMsg } from '../lib/toast.svelte';
  import Modal from './Modal.svelte';

  let { onClose, onCreated }: {
    onClose: () => void;
    onCreated: () => void;
  } = $props();

  let name = $state('');
  let passphrase = $state('');
  let confirm = $state('');
  let submitting = $state(false);

  async function create() {
    if (!name.trim()) {
      toastError('Repository name is required');
      return;
    }
    if (!passphrase) {
      toastError('Passphrase is required');
      return;
    }
    if (confirm !== passphrase) {
      toastError('Passphrases do not match');
      return;
    }
    submitting = true;
    try {
      await api.post('/repositories', { name: name.trim(), passphrase }, auth.token);
      toastSuccess('Repository created');
      onCreated();
    } catch (e) {
      toastError('Failed to create repository: ' + errMsg(e));
    } finally {
      submitting = false;
    }
  }
</script>

<Modal title="New Repository" onClose={onClose}>
  <div class="field">
    <label for="repo-name">Repository Name</label>
    <input id="repo-name" bind:value={name} placeholder="e.g. my-backups" />
  </div>
  <div class="field">
    <label for="repo-pass">Passphrase</label>
    <input id="repo-pass" type="password" bind:value={passphrase} autocomplete="new-password" />
  </div>
  <div class="field">
    <label for="repo-pass2">Confirm passphrase</label>
    <input id="repo-pass2" type="password" bind:value={confirm} autocomplete="new-password" />
  </div>
  <div class="muted small">Encryption: repokey (Borg). Repositories you create here unlock automatically.</div>
  <div class="modal-actions">
    <button class="btn ghost" onclick={onClose}>Cancel</button>
    <button class="btn" onclick={create} disabled={submitting}>
      {submitting ? 'Creating…' : 'Create Repository'}
    </button>
  </div>
</Modal>