// Thin typed client for the Jogoborg REST API (same-origin /api).

const BASE = '/api';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Invoked when an authenticated request returns 401 (stale/invalid token), so
// the app can log out and return to the login screen. Not used for /login.
let onUnauthorized: (() => void) | null = null;

export function setOnUnauthorized(hook: (() => void) | null): void {
  onUnauthorized = hook;
}

async function request(
  method: 'GET' | 'POST' | 'PUT' | 'DELETE',
  endpoint: string,
  body?: unknown,
  token?: string | null
): Promise<unknown> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${endpoint}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    if (res.status === 401 && !endpoint.startsWith('/login')) {
      onUnauthorized?.();
    }
    const detail = `${errorMessage(data, res.status)} (HTTP ${res.status}: ${method} ${endpoint})`;
    throw new ApiError(res.status, detail);
  }
  return data ?? {};
}

function isErrorPayload(v: unknown): v is { error: string } {
  return (
    typeof v === 'object' &&
    v !== null &&
    'error' in v &&
    typeof (v as Record<string, unknown>).error === 'string'
  );
}

function isMessagePayload(v: unknown): v is { message: string } {
  return (
    typeof v === 'object' &&
    v !== null &&
    'message' in v &&
    typeof (v as Record<string, unknown>).message === 'string'
  );
}

function errorMessage(data: unknown, status: number): string {
  if (typeof data === 'string' && data) return data;
  if (isErrorPayload(data)) return data.error;
  if (isMessagePayload(data)) return data.message;
  // Fallback: pull a readable string out of common keys before giving up.
  if (data != null && typeof data === 'object') {
    const rec = data as Record<string, unknown>;
    for (const k of ['detail', 'error', 'error_message', 'message', 'reason']) {
      if (typeof rec[k] === 'string' && rec[k]) return rec[k];
    }
    return JSON.stringify(rec) || `Request failed (${status})`;
  }
  if (data != null) return String(data);
  return `Request failed (${status})`;
}

export function get<T>(endpoint: string, token?: string | null): Promise<T> {
  return request('GET', endpoint, undefined, token) as Promise<T>;
}

export function post<T>(
  endpoint: string,
  body: unknown,
  token?: string | null
): Promise<T> {
  return request('POST', endpoint, body, token) as Promise<T>;
}

export function put<T>(
  endpoint: string,
  body: unknown,
  token?: string | null
): Promise<T> {
  return request('PUT', endpoint, body, token) as Promise<T>;
}

export function del<T>(endpoint: string, token?: string | null): Promise<T> {
  return request('DELETE', endpoint, undefined, token) as Promise<T>;
}