<script lang="ts">
  import { login } from '../lib/auth.svelte';
  import { toastError } from '../lib/toast.svelte';

  let username = $state('');
  let password = $state('');
  let loading = $state(false);

  async function submit() {
    if (loading) return;
    if (!username || !password) {
      toastError('Please enter username and password');
      return;
    }
    loading = true;
    try {
      const ok = await login(username, password);
      if (!ok) toastError('Invalid credentials');
    } finally {
      loading = false;
    }
  }
</script>

<div class="login-wrap">
  <div class="card login-card">
    <h1 class="title">Jogoborg</h1>
    <div class="subtitle muted">Borg Backup Manager</div>

    <form onsubmit={(e) => { e.preventDefault(); submit(); }}>
      <div class="field">
        <label for="username">Username</label>
        <input
          id="username"
          name="username"
          autocomplete="username"
          type="text"
          bind:value={username}
          required
        />
      </div>
      <div class="field">
        <label for="password">Password</label>
        <input
          id="password"
          name="current-password"
          autocomplete="current-password"
          type="password"
          bind:value={password}
          required
        />
      </div>
      <button class="btn" type="submit" style="width:100%" disabled={loading}>
        {loading ? 'Logging in…' : 'Login'}
      </button>
    </form>
  </div>
</div>

<style>
  .login-wrap {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg);
  }
  .login-card {
    width: 400px;
    max-width: 92vw;
    padding: 32px;
  }
  .title {
    text-align: center;
    font-size: 30px;
    color: var(--accent-blue);
    margin: 0;
  }
  .subtitle {
    text-align: center;
    margin: 6px 0 24px;
  }
  .btn {
    margin-top: 8px;
  }
</style>