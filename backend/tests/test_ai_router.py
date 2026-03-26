"""Tests for ai_router.py — patches env vars and service modules."""
import importlib
from unittest.mock import AsyncMock, patch

import pytest


def _reload_router(env: dict):
    """Reload ai_router with a specific environment."""
    with patch.dict("os.environ", env, clear=False):
        import app.ai_router as router
        importlib.reload(router)
        return router


@pytest.mark.asyncio
async def test_primary_succeeds_no_fallback_called():
    """When primary succeeds, fallback is never called."""
    router = _reload_router({"AI_PRIMARY_PROVIDER": "openai", "AI_FALLBACK_PROVIDER": "anthropic"})
    openai_mock = AsyncMock(return_value={"result": "from openai"})
    claude_mock = AsyncMock(return_value={"result": "from claude"})

    with patch.object(router._PROVIDERS["openai"], "get_estimate", openai_mock), \
         patch.object(router._PROVIDERS["anthropic"], "get_estimate", claude_mock):
        result = await router.get_estimate("eng", "nyc", "small", "", ["code"], 50)

    assert result == {"result": "from openai"}
    claude_mock.assert_not_called()


@pytest.mark.asyncio
async def test_primary_fails_fallback_called():
    """When primary raises, fallback is tried and its result returned."""
    router = _reload_router({"AI_PRIMARY_PROVIDER": "openai", "AI_FALLBACK_PROVIDER": "anthropic"})
    openai_mock = AsyncMock(side_effect=RuntimeError("OpenAI down"))
    claude_mock = AsyncMock(return_value={"result": "from claude"})

    with patch.object(router._PROVIDERS["openai"], "get_estimate", openai_mock), \
         patch.object(router._PROVIDERS["anthropic"], "get_estimate", claude_mock):
        result = await router.get_estimate("eng", "nyc", "small", "", ["code"], 50)

    assert result == {"result": "from claude"}


@pytest.mark.asyncio
async def test_primary_fails_no_fallback_raises():
    """When primary fails and no fallback configured, exception propagates."""
    router = _reload_router({"AI_PRIMARY_PROVIDER": "openai", "AI_FALLBACK_PROVIDER": ""})
    openai_mock = AsyncMock(side_effect=RuntimeError("OpenAI down"))

    with patch.object(router._PROVIDERS["openai"], "get_estimate", openai_mock):
        with pytest.raises(RuntimeError, match="OpenAI down"):
            await router.get_estimate("eng", "nyc", "small", "", ["code"], 50)


@pytest.mark.asyncio
async def test_both_providers_fail_raises_fallback_error():
    """When both fail, the fallback's exception propagates."""
    router = _reload_router({"AI_PRIMARY_PROVIDER": "openai", "AI_FALLBACK_PROVIDER": "anthropic"})
    openai_mock = AsyncMock(side_effect=RuntimeError("OpenAI down"))
    claude_mock = AsyncMock(side_effect=RuntimeError("Claude down"))

    with patch.object(router._PROVIDERS["openai"], "get_estimate", openai_mock), \
         patch.object(router._PROVIDERS["anthropic"], "get_estimate", claude_mock):
        with pytest.raises(RuntimeError, match="Claude down"):
            await router.get_estimate("eng", "nyc", "small", "", ["code"], 50)


@pytest.mark.asyncio
async def test_fallback_disabled_when_same_as_primary():
    """Exactly one call when fallback == primary."""
    router = _reload_router({"AI_PRIMARY_PROVIDER": "anthropic", "AI_FALLBACK_PROVIDER": "anthropic"})
    call_count = 0

    async def failing_fn(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise RuntimeError("always fails")

    with patch.object(router._PROVIDERS["anthropic"], "get_estimate", failing_fn):
        with pytest.raises(RuntimeError):
            await router.get_estimate("eng", "nyc", "small", "", ["code"], 50)

    assert call_count == 1


def test_default_primary_is_anthropic():
    """Unset AI_PRIMARY_PROVIDER defaults to anthropic."""
    router = _reload_router({"AI_PRIMARY_PROVIDER": "", "AI_FALLBACK_PROVIDER": ""})
    assert router.PRIMARY == "anthropic"


def test_fallback_none_when_unset():
    """Unset AI_FALLBACK_PROVIDER means FALLBACK is None."""
    router = _reload_router({"AI_PRIMARY_PROVIDER": "openai", "AI_FALLBACK_PROVIDER": ""})
    assert router.FALLBACK is None
