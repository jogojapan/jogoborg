export interface Toast {
  id: number;
  kind: 'success' | 'error';
  message: string;
}

let nextId = 0;

export const toasts = $state<Toast[]>([]);

function push(kind: Toast['kind'], message: string): void {
  const id = ++nextId;
  toasts.push({ id, kind, message });
  setTimeout(() => {
    const idx = toasts.findIndex((t) => t.id === id);
    if (idx >= 0) toasts.splice(idx, 1);
  }, 4000);
}

export function toastSuccess(message: string): void {
  push('success', message);
}

export function toastError(message: string): void {
  push('error', message);
}

export function errMsg(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}