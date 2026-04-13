"""Service layer for calling the OpenAI Responses API."""

import logging
import os

import httpx

from app.ai_utils import _parse_json
from app.prompts.prompts import (
    CITY_SUGGESTIONS_SYSTEM_PROMPT,
    ESTIMATE_SYSTEM_PROMPT,
    FEED_SYSTEM_PROMPT,
    ROLE_SUGGESTIONS_SYSTEM_PROMPT,
    TASK_SUGGESTIONS_SYSTEM_PROMPT,
    build_city_suggestions_prompt,
    build_estimate_user_prompt,
    build_feed_user_prompt,
    build_role_suggestions_prompt,
    build_task_suggestions_prompt,
)

logger = logging.getLogger(__name__)

OPENAI_API_URL = "https://api.openai.com/v1/responses"
MODEL = "gpt-5-mini"
MAX_TOKENS = 2048
SUGGESTION_MAX_TOKENS = 768


def _get_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")
    return key


def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_get_api_key()}",
    }


def _extract_text(response_json: dict) -> str:
    """Extract assistant text from an OpenAI Responses API response.

    Uses the top-level `output_text` convenience field when present.
    Falls back to iterating `output` items for the first message block,
    which correctly handles both plain responses and web-search responses
    (where output[0] is a web_search_call and output[1] is the message).
    """
    if "output_text" in response_json:
        return response_json["output_text"]
    for item in response_json.get("output", []):
        if item.get("type") == "message":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    return block.get("text", "")
    return ""


def _build_payload(
    system: str, user: str, max_tokens: int, tools: list | None = None
) -> dict:
    """Build a Responses API request payload."""
    payload: dict = {
        "model": MODEL,
        "instructions": system,
        "input": user,
        "max_output_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = tools
    return payload


async def _post(payload: dict, timeout: int) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(OPENAI_API_URL, json=payload, headers=_headers())
        if not resp.is_success:
            body = resp.text
            logger.error("OpenAI API error %s: %s", resp.status_code, body)
            try:
                detail = resp.json().get("error", {}).get("message", body)
            except Exception:
                detail = body
            raise RuntimeError(f"OpenAI API {resp.status_code}: {detail}")
        return resp.json()


async def get_estimate(
    role: str,
    location: str,
    company_size: str,
    company_name: str,
    tasks: list[str],
    ai_usage: int,
    computed_scores=None,  # accepted but ignored; OpenAI path always does full scoring
) -> dict:
    """Call OpenAI to generate a job disruption estimate."""
    user_msg = build_estimate_user_prompt(
        role=role,
        location=location,
        company_size=company_size,
        company_name=company_name,
        tasks=tasks,
        ai_usage=ai_usage,
    )
    payload = _build_payload(ESTIMATE_SYSTEM_PROMPT, user_msg, MAX_TOKENS)
    return _parse_json(_extract_text(await _post(payload, timeout=60)))


async def get_feed(
    role: str,
    location: str,
    company_size: str,
    tasks: list[str],
) -> list[dict]:
    """Call OpenAI with web search to find related news/posts."""
    user_msg = build_feed_user_prompt(
        role=role,
        location=location,
        company_size=company_size,
        tasks=tasks,
    )
    tools = [{"type": "web_search"}]
    payload = _build_payload(FEED_SYSTEM_PROMPT, user_msg, MAX_TOKENS, tools=tools)
    result = _parse_json(_extract_text(await _post(payload, timeout=90)))
    if not isinstance(result, list):
        raise ValueError("Expected a JSON array from feed endpoint")
    return result


async def get_role_suggestions(city: str, region: str) -> list[str]:
    """Return 6 job roles common in the given city/region."""
    user_msg = build_role_suggestions_prompt(city, region)
    payload = _build_payload(ROLE_SUGGESTIONS_SYSTEM_PROMPT, user_msg, SUGGESTION_MAX_TOKENS)
    result = _parse_json(_extract_text(await _post(payload, timeout=30)))
    if not isinstance(result, list):
        raise ValueError("Expected a JSON array for role suggestions")
    return [str(r) for r in result[:6]]


async def get_city_suggestions(city: str, region: str) -> list[str]:
    """Return 6 cities near the given city/region."""
    user_msg = build_city_suggestions_prompt(city, region)
    payload = _build_payload(CITY_SUGGESTIONS_SYSTEM_PROMPT, user_msg, SUGGESTION_MAX_TOKENS)
    result = _parse_json(_extract_text(await _post(payload, timeout=30)))
    if not isinstance(result, list):
        raise ValueError("Expected a JSON array for city suggestions")
    return [str(r) for r in result[:6]]


async def get_task_suggestions(role: str, company_size: str) -> list[str]:
    """Return 10 daily task suggestions for the given role and company size."""
    user_msg = build_task_suggestions_prompt(role, company_size)
    payload = _build_payload(TASK_SUGGESTIONS_SYSTEM_PROMPT, user_msg, SUGGESTION_MAX_TOKENS)
    result = _parse_json(_extract_text(await _post(payload, timeout=30)))
    if not isinstance(result, list):
        raise ValueError("Expected a JSON array for task suggestions")
    return [str(r) for r in result[:10]]
