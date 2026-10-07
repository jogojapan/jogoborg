// Human-readable formatting helpers (mirrors the original Flutter UI).

const BYTE_SUFFIXES = ['B', 'KB', 'MB', 'GB', 'TB'];

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null || isNaN(bytes)) return '—';
  let size = bytes;
  let i = 0;
  while (size >= 1024 && i < BYTE_SUFFIXES.length - 1) {
    size /= 1024;
    i++;
  }
  return `${size.toFixed(1)} ${BYTE_SUFFIXES[i]}`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || isNaN(seconds)) return '—';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

export function formatMemory(mb: number | null | undefined): string {
  if (mb == null || isNaN(mb)) return '—';
  return `${mb.toFixed(1)} MB`;
}