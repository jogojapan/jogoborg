"""Container memory limit/usage discovery (cgroup v1 and v2).

Used by the scheduler to gate job dispatch under memory pressure, and by the
web API to color the scheduling Gantt by usage relative to the container
limit. Outside a container (e.g. local dev) the limit may be unavailable, in
which case functions return None and the gate is disabled.

In Docker the container's cgroup is at /sys/fs/cgroup. If no explicit limit is
set the value may be "max"; that is treated as "unknown/unlimited".
"""

import os

CGROUP_V2 = {
    'limit': '/sys/fs/cgroup/memory.max',
    'usage': '/sys/fs/cgroup/memory.current',
}
CGROUP_V1 = {
    'limit': '/sys/fs/cgroup/memory/memory.limit_in_bytes',
    'usage': '/sys/fs/cgroup/memory/memory.usage_in_bytes',
}

_MB = 1024 * 1024


def _read_bytes(path):
    """Read a cgroup byte value; None if missing, non-numeric, or 'max'."""
    try:
        with open(path) as f:
            raw = f.read().strip()
    except OSError:
        return None
    if not raw or raw == 'max':
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def host_total_bytes():
    """Total physical RAM on the host (bytes) from /proc/meminfo, or None."""
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    # Field is in kB.
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError):
        pass
    return None


def memory_limit_bytes():
    """Container memory limit in bytes, or None if not in a container.

    An unlimited container (cgroup 'max', 0, or a value at/above the host's
    RAM) shares the host's memory, so the host's physical RAM is the effective
    cap and is reported as the limit. Outside a container there is no cgroup
    limit and this returns None.
    """
    limit_file = None
    for paths in (CGROUP_V2, CGROUP_V1):
        if os.path.exists(paths['limit']):
            limit_file = paths['limit']
            break
    if limit_file is None:
        return None  # not running under a container cgroup

    value = _read_bytes(limit_file)  # None for 'max' / missing / 0
    host = host_total_bytes()

    # A genuine per-container limit is below the host's RAM; use it directly.
    if value:
        reference = host if host else (1 << 44)
        if value < reference:
            return value

    # Unlimited (or at least as large as the host): the shared host RAM is the
    # effective cap (e.g. a --memory-less Docker container reports the host
    # total in cgroup memory.max; /proc/meminfo MemTotal is that same host RAM
    # inside the container).
    return host


def memory_current_bytes():
    """Current container memory usage in bytes, or None if unavailable."""
    for paths in (CGROUP_V2, CGROUP_V1):
        if os.path.exists(paths['usage']):
            value = _read_bytes(paths['usage'])
            if value is not None:
                return value
    return None


def memory_stats():
    """Return {'limit_mb','current_mb'} or None when limits are unavailable.

    limit_mb is always present when a limit exists; current_mb may be None if
    current usage cannot be read.
    """
    limit = memory_limit_bytes()
    if limit is None:
        return None
    return {
        'limit_mb': round(limit / _MB, 1),
        'current_mb': (
            round(memory_current_bytes() / _MB, 1)
            if memory_current_bytes() is not None
            else None
        ),
    }