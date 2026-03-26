# backend/tests/test_cache.py
import asyncio
import time
import pytest
from app.cache import _MISSING, get, cache_set, make_key, get_or_compute


def test_make_key_is_deterministic():
    assert make_key("a", "b") == make_key("a", "b")


def test_make_key_differs_with_different_parts():
    assert make_key("a", "b") != make_key("a", "c")


def test_make_key_null_byte_separator_prevents_collision():
    # "ab" + "c" must differ from "a" + "bc"
    assert make_key("ab", "c") != make_key("a", "bc")


def test_set_and_get_returns_value():
    cache_set("testkey", {"foo": 1}, ttl_seconds=60)
    assert get("testkey") == {"foo": 1}


def test_get_returns_missing_for_missing_key():
    assert get("nonexistent_xyz") is _MISSING


def test_expired_entry_returns_missing():
    cache_set("expiring", "value", ttl_seconds=0)
    time.sleep(0.01)
    assert get("expiring") is _MISSING


async def test_get_or_compute_calls_fn_once_for_same_key():
    call_count = 0

    async def expensive():
        nonlocal call_count
        call_count += 1
        return "result"

    key = make_key("test", "stampede")
    result1 = await get_or_compute(key, expensive, ttl_seconds=60)
    result2 = await get_or_compute(key, expensive, ttl_seconds=60)

    assert result1 == "result"
    assert result2 == "result"
    assert call_count == 1


async def test_get_or_compute_handles_falsy_cached_value():
    call_count = 0

    async def returns_empty_list():
        nonlocal call_count
        call_count += 1
        return []

    key = make_key("test", "falsy")
    result1 = await get_or_compute(key, returns_empty_list, ttl_seconds=60)
    result2 = await get_or_compute(key, returns_empty_list, ttl_seconds=60)
    assert result1 == []
    assert result2 == []
    assert call_count == 1


async def test_get_or_compute_concurrent_calls_only_compute_once():
    call_count = 0

    async def slow_fn():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return "slow_result"

    key = make_key("test", "concurrent")
    results = await asyncio.gather(
        get_or_compute(key, slow_fn, ttl_seconds=60),
        get_or_compute(key, slow_fn, ttl_seconds=60),
        get_or_compute(key, slow_fn, ttl_seconds=60),
    )
    assert all(r == "slow_result" for r in results)
    assert call_count == 1
