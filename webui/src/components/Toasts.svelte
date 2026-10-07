<script lang="ts">
  import { toasts } from '../lib/toast.svelte';
</script>

<div class="toast-wrap">
  {#each toasts as t (t.id)}
    <div class="toast {t.kind}">{t.message}</div>
  {/each}
</div>