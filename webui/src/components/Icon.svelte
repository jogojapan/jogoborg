<script lang="ts">
  // Minimal inline SVG icon set (stroke-based, currentColor). Mirrors the
  // Material icons the Flutter UI used, without pulling in a dependency.
  const paths: Record<string, string> = {
    dashboard: 'M3 3h8v10H3zM13 3h8v6h-8zM13 13h8v8h-8zM3 17h8v4H3z',
    repos:
      'M12 3a9 9 0 0 1 3 17v-2M12 8v5M12 12v9M12 3a9 9 0 0 0-9 9v3a3 3 0 0 0 3 3h6',
    folder: 'M3 5h6l2 3h10v11H3z',
    file: 'M6 3h8l4 4v14H6zM14 3v4h4',
    jobs: 'M12 5v7l4 2M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z',
    notifications:
      'M12 3a6 6 0 0 1 6 6v4l2 3H4l2-3V9a6 6 0 0 1 6-6zM10 19a2 2 0 0 0 4 0',
    logout: 'M9 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4M16 8l4 4-4 4M9 12h11',
    refresh: 'M20 12a8 8 0 1 1-2.3-5.6M20 4v4h-4',
    add: 'M12 5v14M5 12h14',
    edit: 'M16 3l5 5L8 21H3v-5z',
    trash: 'M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 11v6M14 11v6',
    play: 'M8 5v14l11-7z',
    lock: 'M6 11h12a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1zm1-3a5 5 0 0 1 10 0v3H7V8z',
    up: 'M12 20V6M6 12l6-6 6 6',
    down: 'M12 4v14M6 12l6 6 6-6',
    back: 'M15 5l-7 7 7 7',
    close: 'M6 6l12 12M18 6L6 18',
    archive: 'M4 4h16v5H4zM4 9h16l-1 11H5zM9 13h6',
    email: 'M4 6h16v12H4zM4 7l8 6 8-6',
    webhook: 'M4 12a3 3 0 1 1 3-3m10 3a3 3 0 1 0-3-3m0 10a3 3 0 1 0 3-3M8 18a3 3 0 1 1 3 3',
    database: 'M12 4c4 0 7 1.8 7 4s-3 4-7 4-7-1.8-7-4 3-4 7-4zm0 8c4 0 7-1.8 7-4M12 12c4 0 7 1.8 7 4M12 12c-4 0-7 1.8-7 4m7 0c-4 0-7 1.8-7 4s3 4 7 4 7-1.8 7-4-3-4-7-4z',
    key: 'M7 7a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM10 11l9-5v5M19 6v4',
    check: 'M5 13l4 4L19 7',
    info: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zm0 8v6m0-10v.01',
  };

  const fillIcons = new Set(['folder', 'file']);

  let { icon, size = 20 }: { icon: string; size?: number } = $props();
</script>

{#if paths[icon] !== undefined}
  {#if fillIcons.has(icon)}
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d={paths[icon]} />
    </svg>
  {:else}
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.8"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path d={paths[icon]} />
    </svg>
  {/if}
{/if}