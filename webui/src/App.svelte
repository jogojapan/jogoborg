<script lang="ts">
  import { router } from './lib/router.svelte';
  import { auth, logout } from './lib/auth.svelte';
  import { theme, toggleTheme } from './lib/theme.svelte';
  import { buildInfo } from './lib/build-info';
  import Toasts from './components/Toasts.svelte';
  import Icon from './components/Icon.svelte';
  import Login from './screens/Login.svelte';
  import Dashboard from './screens/Dashboard.svelte';
  import Repositories from './screens/Repositories.svelte';
  import Sources from './screens/Sources.svelte';
  import Jobs from './screens/Jobs.svelte';
  import Notifications from './screens/Notifications.svelte';
  import Gantt from './screens/Gantt.svelte';

  const nav = [
    { path: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
    { path: '/repos', label: 'Repositories', icon: 'repos' },
    { path: '/sources', label: 'Source Directories', icon: 'folder' },
    { path: '/jobs', label: 'Backup Jobs', icon: 'jobs' },
    { path: '/notifications', label: 'Notifications', icon: 'notifications' },
    { path: '/gantt', label: 'Scheduling', icon: 'activity' },
  ];

  const titles: Record<string, string> = {
    '/dashboard': 'Jogoborg Dashboard',
    '/repos': 'Borg Repositories',
    '/sources': 'Source Directories',
    '/jobs': 'Backup Jobs',
    '/notifications': 'Notification Settings',
    '/gantt': 'Scheduling Overview',
  };

  // Auth guard: bounce unauthenticated users to login and authenticated users
  // off login (mirrors the old go_router redirect).
  $effect(() => {
    const p = router.path;
    if (!auth.isAuthenticated && p !== '/login' && p !== '/') {
      window.location.hash = '#/login';
    } else if (auth.isAuthenticated && p === '/login') {
      window.location.hash = '#/dashboard';
    }
  });
</script>

{#if !auth.isAuthenticated}
  <Login />
{:else}
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">Jogoborg</div>
      <nav>
        {#each nav as item}
          <a
            class="nav-item"
            class:active={router.path === item.path}
            href={'#' + item.path}
          >
            <Icon icon={item.icon} />
            <span>{item.label}</span>
          </a>
        {/each}
      </nav>
      <button class="nav-item logout" onclick={logout}>
        <Icon icon="logout" />
        <span>Logout</span>
      </button>
      <div class="version">
        <div class="version-line">
          <span class="version-tag">v{buildInfo.tag}</span>
          <span class="version-commit" title={buildInfo.commit}>
            {buildInfo.commit}
          </span>
        </div>
        <div class="version-date">
          built {new Date(buildInfo.date).toLocaleDateString()}
        </div>
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <h1>{titles[router.path] ?? ''}</h1>
        <button
          class="icon-btn"
          onclick={toggleTheme}
          title="Toggle theme"
          aria-label="Toggle theme"
        >
          {theme.mode === 'dark' ? '☀️' : '🌙'}
        </button>
      </header>
      <main class="content">
        {#if router.path === '/dashboard'}
          <Dashboard />
        {:else if router.path === '/repos'}
          <Repositories />
        {:else if router.path === '/sources'}
          <Sources />
        {:else if router.path === '/jobs'}
          <Jobs />
        {:else if router.path === '/notifications'}
          <Notifications />
        {:else if router.path === '/gantt'}
          <Gantt />
        {:else}
          <Dashboard />
        {/if}
      </main>
    </div>
  </div>
{/if}

<Toasts />

<style>
  .shell {
    display: grid;
    grid-template-columns: 220px 1fr;
    min-height: 100vh;
  }
  .sidebar {
    background: var(--drawer-bg);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    padding: 16px 10px;
    gap: 6px;
  }
  .brand {
    font-size: 20px;
    font-weight: 700;
    color: var(--primary);
    padding: 4px 10px 16px;
  }
  nav {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: var(--text-muted);
    text-decoration: none;
    font-size: 14px;
    cursor: pointer;
  }
  .nav-item:hover {
    background: var(--surface-2);
    color: var(--text);
  }
  .nav-item.active {
    color: var(--selected-text);
    font-weight: 600;
  }
  .nav-item.logout {
    margin-top: auto;
    color: var(--error);
  }
  .version {
    margin-top: 12px;
    padding: 10px 12px;
    border-top: 1px solid var(--border);
    font-size: 10.5px;
    line-height: 1.5;
    color: var(--text-muted);
    word-break: break-all;
  }
  .version-line {
    display: flex;
    align-items: baseline;
    gap: 6px;
  }
  .version-tag {
    font-weight: 600;
    color: var(--text);
  }
  .version-commit {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .version-date {
    opacity: 0.8;
  }

  @media (max-width: 720px) {
    .version {
      display: none;
    }
  }
  .main {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 24px;
    background: var(--appbar-bg);
    color: var(--appbar-text);
  }
  .topbar h1 {
    font-size: 20px;
    margin: 0;
    font-weight: 600;
  }
  .content {
    padding: 24px;
    flex: 1;
  }

  @media (max-width: 720px) {
    .shell {
      grid-template-columns: 64px 1fr;
    }
    .nav-item span,
    .brand {
      display: none;
    }
    .nav-item {
      justify-content: center;
    }
  }
</style>