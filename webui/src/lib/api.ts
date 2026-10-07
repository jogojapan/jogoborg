// Thin typed client for the Jogoborg REST API (same-origin /api).

const BASE = '/api';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
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
    throw new ApiError(res.status, errorMessage(data, res.status));
  }
  return data ?? {};
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
  if (isMessagePayload(data)) return data.message;
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