"""
Tests for the shared base extraction utilities.
"""

import json
from unittest.mock import MagicMock

import pytest

from agent.extractors.base import extract_with_llm, merge_model, parse_llm_json
from app.models.schemas import UserProfile


class TestParseLlmJson:
    def test_raw_json(self):
        result = parse_llm_json('{"name": "John"}')
        assert result == {"name": "John"}

    def test_json_with_whitespace(self):
        result = parse_llm_json('  \n {"name": "John"} \n ')
        assert result == {"name": "John"}

    def test_json_in_markdown_code_block(self):
        text = '```json\n{"name": "John"}\n```'
        result = parse_llm_json(text)
        assert result == {"name": "John"}

    def test_json_in_plain_code_block(self):
        text = '```\n{"name": "John"}\n```'
        result = parse_llm_json(text)
        assert result == {"name": "John"}

    def test_json_with_surrounding_text(self):
        text = 'Here is the result:\n```json\n{"name": "John"}\n```\nDone!'
        result = parse_llm_json(text)
        assert result == {"name": "John"}

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_llm_json("not valid json at all")

    def test_empty_string_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_llm_json("")

    def test_nested_json(self):
        data = {"profile": {"name": "John"}, "count": 1}
        result = parse_llm_json(json.dumps(data))
        assert result == data


class TestMergeModel:
    def test_merge_new_values(self):
        current = UserProfile(name="John")
        result = merge_model(current, {"age": "35", "residence": "Beijing"})
        assert result.name == "John"
        assert result.age == "35"
        assert result.residence == "Beijing"

    def test_does_not_overwrite_with_empty(self):
        current = UserProfile(name="John", age="35")
        result = merge_model(current, {"name": "", "age": ""})
        assert result.name == "John"
        assert result.age == "35"

    def test_overwrites_with_new_value(self):
        current = UserProfile(name="John")
        result = merge_model(current, {"name": "Jane"})
        assert result.name == "Jane"

    def test_ignores_unknown_keys(self):
        current = UserProfile(name="John")
        result = merge_model(current, {"unknown_key": "value", "name": "Jane"})
        assert result.name == "Jane"

    def test_strips_whitespace(self):
        current = UserProfile()
        result = merge_model(current, {"name": "  John  "})
        assert result.name == "John"

    def test_empty_dict_returns_same(self):
        current = UserProfile(name="John")
        result = merge_model(current, {})
        assert result.name == "John"


class TestExtractWithLlm:
    def test_success(self):
        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = '{"name": "Alice", "age": "25"}'
        mock_llm.complete.return_value = mock_resp

        result = extract_with_llm(mock_llm, "some prompt", UserProfile())
        assert result.name == "Alice"
        assert result.age == "25"

    def test_markdown_response(self):
        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = '```json\n{"name": "Bob"}\n```'
        mock_llm.complete.return_value = mock_resp

        result = extract_with_llm(mock_llm, "some prompt", UserProfile())
        assert result.name == "Bob"

    def test_invalid_json_returns_current(self):
        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = "not json"
        mock_llm.complete.return_value = mock_resp

        current = UserProfile(name="Original")
        result = extract_with_llm(mock_llm, "some prompt", current)
        assert result.name == "Original"

    def test_llm_exception_returns_current(self):
        mock_llm = MagicMock()
        mock_llm.complete.side_effect = RuntimeError("LLM down")

        current = UserProfile(name="Safe")
        result = extract_with_llm(mock_llm, "some prompt", current)
        assert result.name == "Safe"
