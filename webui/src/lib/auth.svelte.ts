import type { LoginResponse } from './types';
import * as api from './api';
import { router } from './router.svelte';

const TOKEN_KEY = 'jogoborg_auth_token';

function loadToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

// Reactive auth store (Svelte 5 runes).
export const auth = $state({
  token: loadToken() as string | null,
  initialized: false,

  get isAuthenticated(): boolean {
    return !!this.token;
  },
});

export function initialize(): void {
  if (!auth.initialized) {
    auth.initialized = true;
    enforceRoute();
  }
}

// Mirrors the old go_router redirect: unauthenticated users go to login;
// authenticated users are bounced off login.
export function enforceRoute(): void {
  const path = router.path;
  if (!auth.isAuthenticated && path !== '/login') {
    router.path = '/login';
    window.location.hash = '#/login';
  } else if (auth.isAuthenticated && path === '/login') {
    router.path = '/dashboard';
    window.location.hash = '#/dashboard';
  }
}

export async function login(
  username: string,
  password: string
): Promise<boolean> {
  try {
    const res = await api.post<LoginResponse>('/login', { username, password });
    if (res?.token) {
      auth.token = res.token;
      try {
        localStorage.setItem(TOKEN_KEY, res.token);
      } catch {
        /* storage unavailable */
      }
      router.path = '/dashboard';
      window.location.hash = '#/dashboard';
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

export function logout(): void {
  auth.token = null;
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
  router.path = '/login';
  window.location.hash = '#/login';
}