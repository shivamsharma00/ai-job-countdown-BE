"""In-memory cache with TTL and per-key async locking to prevent stampedes."""

import asyncio
import hashlib
import time
from typing import Any, Callable, Coroutine

# Sentinel for cache misses — distinguishable from a cached None/falsy value.
_MISSING = object()

# { key: (value, expires_at_monotonic) }
_store: dict[str, tuple[Any, float]] = {}
# Per-key locks to guard get→compute→set sequences
# NOTE: _locks grows with unique keys but never shrinks. Acceptable for this app's
# bounded key space. A future invalidate() helper could clean both _store and _locks.
_locks: dict[str, asyncio.Lock] = {}
_meta_lock = asyncio.Lock()


async def _get_lock(key: str) -> asyncio.Lock:
    async with _meta_lock:
        if key not in _locks:
            _locks[key] = asyncio.Lock()
        return _locks[key]


def get(key: str) -> Any:
    """Return cached value or _MISSING if cache miss or expired."""
    entry = _store.get(key)
    if entry is None:
        return _MISSING
    value, expires_at = entry
    if time.monotonic() > expires_at:
        _store.pop(key, None)
        return _MISSING
    return value


def cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    """Store value with a TTL in seconds."""
    _store[key] = (value, time.monotonic() + ttl_seconds)


def make_key(*parts: str) -> str:
    """Build a collision-safe cache key from parts using SHA-256."""
    combined = "\x00".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()


async def get_or_compute(
    key: str,
    compute_fn: Callable[[], Coroutine[Any, Any, Any]],
    ttl_seconds: int,
) -> Any:
    """Return cached value; if absent, call compute_fn once (even under concurrency)."""
    cached = get(key)
    if cached is not _MISSING:
        return cached

    lock = await _get_lock(key)
    async with lock:
        # Double-check after acquiring lock (another coroutine may have populated it)
        cached = get(key)
        if cached is not _MISSING:
            return cached
        value = await compute_fn()
        cache_set(key, value, ttl_seconds)
        return value
