<script lang="ts">
  import Modal from './Modal.svelte';

  let {
    initial,
    onClose,
    onSave,
  }: {
    initial: { pre: string; post: string };
    onClose: () => void;
    onSave: (v: { pre: string; post: string }) => void;
  } = $props();

  let pre = $state(initial.pre);
  let post = $state(initial.post);
</script>

<Modal title="Command Hooks" onClose={onClose}>
  <div class="field">
    <label for="pre-cmd">Pre-Command (runs before backup)</label>
    <input id="pre-cmd" bind:value={pre} placeholder="docker stop myservice" />
  </div>
  <div class="field">
    <label for="post-cmd">Post-Command (runs after backup)</label>
    <input id="post-cmd" bind:value={post} placeholder="docker start myservice" />
  </div>
  <div class="modal-actions">
    <button class="btn ghost" onclick={onClose}>Cancel</button>
    <button class="btn" onclick={() => onSave({ pre, post })}>Save</button>
  </div>
</Modal>