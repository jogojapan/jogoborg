import * as api from './api';
import { auth } from './auth.svelte';
import type { JobRun, MemorySystemResponse, TimelineResponse } from './types';

export const ZOOM_HOURS = [3, 6, 12, 24, 48, 72, 92] as const;
export const DEFAULT_ZOOM_HOURS = 24;

const HOUR_MS = 3_600_000;

export async function fetchTimeline(hours: number): Promise<TimelineResponse> {
  const until = new Date();
  const since = new Date(until.getTime() - hours * HOUR_MS);
  const qs = `since=${encodeURIComponent(since.toISOString())}&until=${encodeURIComponent(
    until.toISOString()
  )}`;
  return api.get<TimelineResponse>(`/job-logs?${qs}`, auth.token);
}

export async function fetchMemory(): Promise<MemorySystemResponse> {
  return api.get<MemorySystemResponse>('/system/memory', auth.token);
}

// Effective end of a run: use its finish time, or "now" if still running.
export function runEndMs(run: JobRun, nowMs: number): number {
  return run.finished_at ? new Date(run.finished_at).getTime() : nowMs;
}

// Peak memory as a fraction of the container limit (0..1), or null if unknown.
export function memoryRatio(peakMb: number | null, limitMb: number | null): number | null {
  if (peakMb == null || !limitMb || limitMb <= 0) return null;
  return Math.min(1, peakMb / limitMb);
}

// Bar colour by memory usage relative to the container limit.
export function memoryColor(peakMb: number | null, limitMb: number | null): string {
  const ratio = memoryRatio(peakMb, limitMb);
  if (ratio == null) return 'var(--primary)';
  if (ratio >= 0.9) return '#e57373'; // red
  if (ratio >= 0.7) return '#ffb74d'; // amber
  if (ratio >= 0.5) return '#fdd835'; // yellow
  return '#81c784'; // green
}