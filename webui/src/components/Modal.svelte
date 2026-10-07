<script lang="ts">
  import Icon from './Icon.svelte';

  let { title = '', onClose }: { title?: string; onClose: () => void } = $props();
</script>

<div class="modal-backdrop" role="presentation" onclick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
  <div class="modal" role="dialog" aria-modal="true" aria-label={title || 'dialog'}>
    <h3>
      <span class="modal-title">{title}</span>
      <button class="icon-btn" aria-label="Close" onclick={onClose}>
        <Icon icon="close" />
      </button>
    </h3>
    <slot />
  </div>
</div>