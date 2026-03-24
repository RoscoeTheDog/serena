"""Tests for result pagination and _apply_result_limit helper."""

from unittest.mock import MagicMock

import pytest

from serena.config.serena_config import SerenaConfig
from serena.tools.tools_base import Tool


class DummyTool(Tool):
    """Minimal concrete Tool subclass for testing _apply_result_limit."""

    def apply(self) -> str:
        """Dummy apply method."""
        return "ok"


def _make_tool(default_max_tool_results: int = 50) -> DummyTool:
    """Create a DummyTool with a mocked agent carrying the given config."""
    config = SerenaConfig(default_max_tool_results=default_max_tool_results)
    agent = MagicMock()
    agent.serena_config = config
    return DummyTool(agent)


class TestApplyResultLimit:
    """Tests for Tool._apply_result_limit()."""

    def test_returns_all_when_under_limit(self):
        tool = _make_tool(default_max_tool_results=50)
        items = list(range(10))
        result, meta = tool._apply_result_limit(items, max_results=-1)
        assert result == items
        assert meta is None

    def test_caps_at_config_default(self):
        tool = _make_tool(default_max_tool_results=5)
        items = list(range(20))
        result, meta = tool._apply_result_limit(items, max_results=-1)
        assert len(result) == 5
        assert result == [0, 1, 2, 3, 4]
        assert meta is not None
        assert meta["returned"] == 5
        assert meta["total_available"] == 20
        assert meta["offset"] == 0
        assert "next_cursor" in meta

    def test_explicit_max_results_overrides_config(self):
        tool = _make_tool(default_max_tool_results=50)
        items = list(range(100))
        result, meta = tool._apply_result_limit(items, max_results=10)
        assert len(result) == 10
        assert meta is not None
        assert meta["returned"] == 10
        assert meta["total_available"] == 100

    def test_unlimited_with_zero(self):
        tool = _make_tool(default_max_tool_results=5)
        items = list(range(200))
        result, meta = tool._apply_result_limit(items, max_results=0)
        assert result == items
        assert meta is None

    def test_cursor_pagination_first_page(self):
        tool = _make_tool(default_max_tool_results=50)
        items = list(range(25))
        result, meta = tool._apply_result_limit(items, max_results=10)
        assert result == list(range(10))
        assert meta is not None
        assert meta["next_cursor"] == "offset:10"
        assert meta["total_available"] == 25

    def test_cursor_pagination_second_page(self):
        tool = _make_tool(default_max_tool_results=50)
        items = list(range(25))
        result, meta = tool._apply_result_limit(items, max_results=10, page_cursor="offset:10")
        assert result == list(range(10, 20))
        assert meta is not None
        assert meta["offset"] == 10
        assert meta["next_cursor"] == "offset:20"

    def test_cursor_pagination_last_page(self):
        tool = _make_tool(default_max_tool_results=50)
        items = list(range(25))
        result, meta = tool._apply_result_limit(items, max_results=10, page_cursor="offset:20")
        assert result == [20, 21, 22, 23, 24]
        assert meta is not None
        assert meta["offset"] == 20
        assert "next_cursor" not in meta
        assert "hint" not in meta

    def test_cursor_beyond_end(self):
        tool = _make_tool(default_max_tool_results=50)
        items = list(range(10))
        result, meta = tool._apply_result_limit(items, max_results=5, page_cursor="offset:999")
        assert result == []
        assert meta is not None
        assert meta["returned"] == 0
        assert "hint" not in meta

    def test_invalid_cursor_treated_as_zero(self):
        tool = _make_tool(default_max_tool_results=50)
        items = list(range(20))
        result, meta = tool._apply_result_limit(items, max_results=10, page_cursor="garbage")
        assert result == list(range(10))
        assert meta is not None
        assert meta["offset"] == 0

    def test_exact_limit_no_pagination(self):
        """When items exactly equal the limit and no cursor, no pagination needed."""
        tool = _make_tool(default_max_tool_results=50)
        items = list(range(10))
        result, meta = tool._apply_result_limit(items, max_results=10)
        assert result == items
        assert meta is None

    def test_pagination_has_no_hint(self):
        """Verify pagination metadata does not contain a hint key."""
        tool = _make_tool(default_max_tool_results=50)
        items = list(range(100))
        result, meta = tool._apply_result_limit(items, max_results=30)
        assert meta is not None
        assert "hint" not in meta
        assert "next_cursor" in meta

    def test_pagination_metadata_structure(self):
        """Verify all expected keys are present in pagination metadata."""
        tool = _make_tool(default_max_tool_results=50)
        items = list(range(60))
        result, meta = tool._apply_result_limit(items, max_results=20)
        assert meta is not None
        assert set(meta.keys()) == {"returned", "total_available", "offset", "next_cursor"}


class TestConfigDefault:
    """Tests that default_max_tool_results is properly read from config."""

    def test_config_field_exists(self):
        config = SerenaConfig()
        assert config.default_max_tool_results == 20

    def test_config_custom_value(self):
        config = SerenaConfig(default_max_tool_results=100)
        assert config.default_max_tool_results == 100

    def test_config_zero_means_unlimited(self):
        config = SerenaConfig(default_max_tool_results=0)
        assert config.default_max_tool_results == 0
