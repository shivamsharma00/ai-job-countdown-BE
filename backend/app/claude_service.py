"""Service layer for calling the Anthropic Claude API."""

import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

from app.ai_utils import _parse_json
from app.prompts.prompts import (
    ESTIMATE_SYSTEM_PROMPT,
    ESTIMATE_NARRATIVE_SYSTEM_PROMPT,
    FEED_SYSTEM_PROMPT,
    ROLE_SUGGESTIONS_SYSTEM_PROMPT,
    CITY_SUGGESTIONS_SYSTEM_PROMPT,
    TASK_SUGGESTIONS_SYSTEM_PROMPT,
    build_estimate_user_prompt,
    build_narrative_user_prompt,
    build_feed_user_prompt,
    build_role_suggestions_prompt,
    build_city_suggestions_prompt,
    build_task_suggestions_prompt,
)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"
# Haiku for narrative-only calls: much cheaper, sufficient for prose + tips
HAIKU_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 2048
NARRATIVE_MAX_TOKENS = 900   # description + 3 tips only
SUGGESTION_MAX_TOKENS = 768


def _get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")
    return key


def _headers(beta: str | None = None) -> dict:
    h = {
        "Content-Type": "application/json",
        "x-api-key": _get_api_key(),
        "anthropic-version": "2023-06-01",
    }
    if beta:
        h["anthropic-beta"] = beta
    return h


def _extract_text(response_json: dict) -> str:
    """Pull all text blocks out of a Claude API response."""
    blocks = response_json.get("content", [])
    return "\n".join(b["text"] for b in blocks if b.get("type") == "text")



async def get_estimate(
    role: str,
    location: str,
    company_size: str,
    company_name: str,
    tasks: list[str],
    ai_usage: int,
    computed_scores: Optional[dict] = None,
) -> dict:
    """
    Generate a job disruption estimate.

    If computed_scores is provided (DB scoring succeeded) we make ONE cheap
    Haiku call that only writes description + tips — scores are already computed.

    If computed_scores is None (DB unavailable) we fall back to one Sonnet call
    where the LLM computes everything from scratch.
    """
    if computed_scores is not None:
        # ── Fast / cheap path: DB did the math, LLM writes the prose ──
        user_msg = build_narrative_user_prompt(
            role=role,
            location=location,
            company_size=company_size,
            company_name=company_name,
            tasks=tasks,
            ai_usage=ai_usage,
            computed=computed_scores,
        )
        payload = {
            "model": HAIKU_MODEL,
            "max_tokens": NARRATIVE_MAX_TOKENS,
            "temperature": 0.3,
            "system": ESTIMATE_NARRATIVE_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_msg}],
        }
        timeout = 30
    else:
        # ── Fallback path: LLM computes everything ──
        user_msg = build_estimate_user_prompt(
            role=role,
            location=location,
            company_size=company_size,
            company_name=company_name,
            tasks=tasks,
            ai_usage=ai_usage,
        )
        payload = {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "temperature": 0.3,
            "system": ESTIMATE_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_msg}],
        }
        timeout = 60

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(ANTHROPIC_API_URL, json=payload, headers=_headers())
        if not resp.is_success:
            body = resp.text
            logger.error("Anthropic API error %s: %s", resp.status_code, body)
            try:
                detail = resp.json().get("error", {}).get("message", body)
            except Exception:
                detail = body
            raise RuntimeError(f"Anthropic API {resp.status_code}: {detail}")
        text = _extract_text(resp.json())
        narrative = _parse_json(text)

    if computed_scores is not None:
        # Merge: DB scores + LLM narrative
        return {
            **computed_scores,
            "description": narrative["description"],
            "tips": narrative["tips"],
        }
    # Fallback: LLM returned everything
    return narrative


async def get_feed(
    role: str,
    location: str,
    company_size: str,
    tasks: list[str],
) -> list[dict]:
    """Call Claude with web search to find related news/posts."""
    user_msg = build_feed_user_prompt(
        role=role,
        location=location,
        company_size=company_size,
        tasks=tasks,
    )

    payload = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": FEED_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_msg}],
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
    }

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(ANTHROPIC_API_URL, json=payload, headers=_headers(beta="web-search-2025-03-05"))
        if not resp.is_success:
            body = resp.text
            logger.error("Anthropic API error %s: %s", resp.status_code, body)
            try:
                detail = resp.json().get("error", {}).get("message", body)
            except Exception:
                detail = body
            raise RuntimeError(f"Anthropic API {resp.status_code}: {detail}")
        text = _extract_text(resp.json())
        result = _parse_json(text)
        if not isinstance(result, list):
            raise ValueError("Expected a JSON array from feed endpoint")
        return result


async def get_role_suggestions(city: str, region: str) -> list[str]:
    """Return 6 job roles common in the given city/region."""
    user_msg = build_role_suggestions_prompt(city, region)
    payload = {
        "model": MODEL,
        "max_tokens": SUGGESTION_MAX_TOKENS,
        "system": ROLE_SUGGESTIONS_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_msg}],
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(ANTHROPIC_API_URL, json=payload, headers=_headers())
        if not resp.is_success:
            body = resp.text
            logger.error("Anthropic API error %s: %s", resp.status_code, body)
            try:
                detail = resp.json().get("error", {}).get("message", body)
            except Exception:
                detail = body
            raise RuntimeError(f"Anthropic API {resp.status_code}: {detail}")
        text = _extract_text(resp.json())
        result = _parse_json(text)
        if not isinstance(result, list):
            raise ValueError("Expected a JSON array for role suggestions")
        return [str(r) for r in result[:6]]


async def get_city_suggestions(city: str, region: str) -> list[str]:
    """Return 6 cities near the given city/region."""
    user_msg = build_city_suggestions_prompt(city, region)
    payload = {
        "model": MODEL,
        "max_tokens": SUGGESTION_MAX_TOKENS,
        "system": CITY_SUGGESTIONS_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_msg}],
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(ANTHROPIC_API_URL, json=payload, headers=_headers())
        if not resp.is_success:
            body = resp.text
            logger.error("Anthropic API error %s: %s", resp.status_code, body)
            try:
                detail = resp.json().get("error", {}).get("message", body)
            except Exception:
                detail = body
            raise RuntimeError(f"Anthropic API {resp.status_code}: {detail}")
        text = _extract_text(resp.json())
        result = _parse_json(text)
        if not isinstance(result, list):
            raise ValueError("Expected a JSON array for city suggestions")
        return [str(r) for r in result[:6]]


async def get_task_suggestions(role: str, company_size: str) -> list[str]:
    """Return 10 daily task suggestions for the given role and company size."""
    user_msg = build_task_suggestions_prompt(role, company_size)
    payload = {
        "model": MODEL,
        "max_tokens": SUGGESTION_MAX_TOKENS,
        "system": TASK_SUGGESTIONS_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_msg}],
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(ANTHROPIC_API_URL, json=payload, headers=_headers())
        if not resp.is_success:
            body = resp.text
            logger.error("Anthropic API error %s: %s", resp.status_code, body)
            try:
                detail = resp.json().get("error", {}).get("message", body)
            except Exception:
                detail = body
            raise RuntimeError(f"Anthropic API {resp.status_code}: {detail}")
        text = _extract_text(resp.json())
        result = _parse_json(text)
        if not isinstance(result, list):
            raise ValueError("Expected a JSON array for task suggestions")
        return [str(r) for r in result[:10]]
