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


def memory_limit_bytes():
    """Container memory limit in bytes, or None if unavailable/unlimited."""
    for paths in (CGROUP_V2, CGROUP_V1):
        if os.path.exists(paths['limit']):
            value = _read_bytes(paths['limit'])
            # A limit of 0 in v1 means "no limit".
            if value:
                return value
    return None


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