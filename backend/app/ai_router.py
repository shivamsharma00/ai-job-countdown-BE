"""Routes AI service calls to the configured primary provider with automatic fallback."""

import logging
import os

import app.claude_service as _claude
import app.openai_service as _openai

logger = logging.getLogger(__name__)

PRIMARY = os.getenv("AI_PRIMARY_PROVIDER", "anthropic").strip().lower() or "anthropic"
FALLBACK = os.getenv("AI_FALLBACK_PROVIDER", "").strip().lower()

# Disable fallback if unset, empty, or identical to primary
if not FALLBACK or FALLBACK == PRIMARY:
    FALLBACK = None

_PROVIDERS = {
    "anthropic": _claude,
    "openai": _openai,
}


async def _call(fn_name: str, *args, **kwargs):
    primary_fn = getattr(_PROVIDERS[PRIMARY], fn_name)
    try:
        return await primary_fn(*args, **kwargs)
    except Exception as exc:
        if FALLBACK is None:
            raise
        logger.warning(
            "AI provider %r failed for %s (%s: %s); falling back to %r",
            PRIMARY, fn_name, type(exc).__name__, exc, FALLBACK,
        )
    return await getattr(_PROVIDERS[FALLBACK], fn_name)(*args, **kwargs)


async def get_estimate(role, location, company_size, company_name, tasks, ai_usage):
    return await _call("get_estimate", role, location, company_size, company_name, tasks, ai_usage)


async def get_feed(role, location, company_size, tasks):
    return await _call("get_feed", role, location, company_size, tasks)


async def get_role_suggestions(city, region):
    return await _call("get_role_suggestions", city, region)


async def get_city_suggestions(city, region):
    return await _call("get_city_suggestions", city, region)


async def get_task_suggestions(role, company_size):
    return await _call("get_task_suggestions", role, company_size)
