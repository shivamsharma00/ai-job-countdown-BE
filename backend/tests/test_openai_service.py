"""Tests for openai_service.py — mocks httpx to avoid live API calls."""
import json
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_openai_response(text: str) -> dict:
    """Build a minimal mock OpenAI Responses API response.

    KEEP IN SYNC with _extract_text in openai_service.py.
    """
    return {
        "output_text": text,
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
    }


def _make_openai_response_with_search(text: str) -> dict:
    """Response shape when web search tool was used (output[0] is the search call)."""
    return {
        "output_text": text,
        "output": [
            {"type": "web_search_call", "id": "search_1", "queries": ["AI jobs"]},
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            },
        ],
    }


def _mock_client(response_json: dict, status_code: int = 200):
    mock_resp = MagicMock()
    mock_resp.is_success = status_code < 400
    mock_resp.status_code = status_code
    mock_resp.json.return_value = response_json
    mock_resp.text = json.dumps(response_json)

    mc = AsyncMock()
    mc.__aenter__ = AsyncMock(return_value=mc)
    mc.__aexit__ = AsyncMock(return_value=False)
    mc.post = AsyncMock(return_value=mock_resp)
    return mc


def _patches(mock):
    """Context manager that patches both httpx and the OPENAI_API_KEY."""
    stack = ExitStack()
    stack.enter_context(patch("app.openai_service.httpx.AsyncClient", return_value=mock))
    stack.enter_context(patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}))
    return stack


@pytest.mark.asyncio
async def test_get_estimate_returns_parsed_dict():
    payload = {"years": 3, "confidence": "high", "summary": "test"}
    mock = _mock_client(_make_openai_response(json.dumps(payload)))
    with _patches(mock):
        from app.openai_service import get_estimate
        result = await get_estimate("Engineer", "NYC", "startup", "", ["code"], 50)
    assert result == payload


@pytest.mark.asyncio
async def test_get_estimate_raises_on_api_error():
    mock = _mock_client({"error": {"message": "bad request"}}, status_code=400)
    with _patches(mock):
        from app.openai_service import get_estimate
        with pytest.raises(RuntimeError, match="400"):
            await get_estimate("Engineer", "NYC", "startup", "", ["code"], 50)


@pytest.mark.asyncio
async def test_get_role_suggestions_returns_list():
    payload = ["Software Engineer", "Data Scientist", "Product Manager",
               "DevOps Engineer", "UX Designer", "ML Engineer"]
    mock = _mock_client(_make_openai_response(json.dumps(payload)))
    with _patches(mock):
        from app.openai_service import get_role_suggestions
        result = await get_role_suggestions("San Francisco", "California")
    assert result == payload[:6]
    assert all(isinstance(r, str) for r in result)


@pytest.mark.asyncio
async def test_get_city_suggestions_returns_list():
    payload = ["Oakland", "San Jose", "Berkeley", "Palo Alto", "Fremont", "Hayward"]
    mock = _mock_client(_make_openai_response(json.dumps(payload)))
    with _patches(mock):
        from app.openai_service import get_city_suggestions
        result = await get_city_suggestions("San Francisco", "California")
    assert result == payload[:6]


@pytest.mark.asyncio
async def test_get_task_suggestions_caps_at_10():
    tasks = [f"task {i}" for i in range(12)]
    mock = _mock_client(_make_openai_response(json.dumps(tasks)))
    with _patches(mock):
        from app.openai_service import get_task_suggestions
        result = await get_task_suggestions("Engineer", "startup")
    assert len(result) == 10


@pytest.mark.asyncio
async def test_get_feed_returns_list_of_dicts():
    items = [{"title": "AI News", "url": "https://example.com", "summary": "test"}]
    mock = _mock_client(_make_openai_response(json.dumps(items)))
    with _patches(mock):
        from app.openai_service import get_feed
        result = await get_feed("Engineer", "NYC", "startup", ["code"])
    assert isinstance(result, list)
    assert result[0]["title"] == "AI News"


@pytest.mark.asyncio
async def test_get_feed_works_with_web_search_response():
    """Response with web_search_call in output[0] and message in output[1]."""
    items = [{"title": "Search Result", "url": "https://example.com", "summary": "found"}]
    mock = _mock_client(_make_openai_response_with_search(json.dumps(items)))
    with _patches(mock):
        from app.openai_service import get_feed
        result = await get_feed("Engineer", "NYC", "startup", ["code"])
    assert result[0]["title"] == "Search Result"


@pytest.mark.asyncio
async def test_get_feed_raises_if_not_list():
    mock = _mock_client(_make_openai_response('{"not": "a list"}'))
    with _patches(mock):
        from app.openai_service import get_feed
        with pytest.raises(ValueError, match="JSON array"):
            await get_feed("Engineer", "NYC", "startup", ["code"])
