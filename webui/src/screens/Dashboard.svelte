<script lang="ts">
  import Icon from '../components/Icon.svelte';

  const cards = [
    {
      path: '/repos',
      title: 'Borg Repositories',
      subtitle: 'View and manage backup repositories',
      icon: 'repos',
      color: 'var(--accent-blue)',
    },
    {
      path: '/sources',
      title: 'Source Directories',
      subtitle: 'Browse source file tree',
      icon: 'folder',
      color: 'var(--accent-green)',
    },
    {
      path: '/jobs',
      title: 'Backup Jobs',
      subtitle: 'Configure and monitor backup jobs',
      icon: 'jobs',
      color: 'var(--accent-orange)',
    },
    {
      path: '/notifications',
      title: 'Notifications',
      subtitle: 'Setup SMTP and webhook notifications',
      icon: 'notifications',
      color: 'var(--accent-red)',
    },
  ];
</script>

<div class="grid cols-3">
  {#each cards as c}
    <a class="card tile" href={'#' + c.path}>
      <Icon icon={c.icon} size={48} />
      <div style="color:{c.color}"></div>
      <h3>{c.title}</h3>
      <div class="muted small">{c.subtitle}</div>
    </a>
  {/each}
</div>

<style>
  .tile {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    text-align: center;
    text-decoration: none;
    color: var(--text);
    min-height: 160px;
    cursor: pointer;
  }
  .tile:hover {
    background: var(--surface-2);
  }
  .tile :global(svg) {
    color: var(--accent-blue);
  }
</style>