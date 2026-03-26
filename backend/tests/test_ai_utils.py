import pytest
from app.ai_utils import _parse_json


def test_plain_json_object():
    assert _parse_json('{"a": 1}') == {"a": 1}


def test_plain_json_array():
    assert _parse_json('[1, 2, 3]') == [1, 2, 3]


def test_strips_markdown_fences_with_language_tag():
    raw = '```json\n{"a": 1}\n```'
    assert _parse_json(raw) == {"a": 1}


def test_strips_markdown_fences_without_language_tag():
    raw = '```\n{"a": 1}\n```'
    assert _parse_json(raw) == {"a": 1}


def test_strips_surrounding_whitespace():
    assert _parse_json('  {"a": 1}  ') == {"a": 1}


def test_invalid_json_raises():
    with pytest.raises(Exception):
        _parse_json("not json")
