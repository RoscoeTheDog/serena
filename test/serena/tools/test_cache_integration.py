"""
Integration tests for cache functionality with symbol tools.

Tests that cache is properly invalidated when files are edited.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from serena.project import Project
from serena.agent import SerenaAgent
from serena.tools.symbol_tools import (
    FindSymbolTool,
    GetSymbolsOverviewTool,
    ReplaceSymbolBodyTool,
    InsertAfterSymbolTool,
    InsertBeforeSymbolTool,
)
from serena.util.symbol_cache import get_global_cache, reset_global_cache


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple Python file
        test_file = os.path.join(tmpdir, "example.py")
        with open(test_file, "w") as f:
            f.write("""def hello():
    return "world"

def goodbye():
    return "farewell"
""")
        yield tmpdir


@pytest.fixture
def agent(temp_project_dir):
    """Create a Serena agent for testing"""
    project = Project(project_root=temp_project_dir)
    agent = SerenaAgent(project=project)
    return agent


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset global cache before each test"""
    reset_global_cache()
    yield
    reset_global_cache()


class TestCacheIntegration:
    """Integration tests for cache with symbol tools"""

    def test_find_symbol_caches_result(self, agent, temp_project_dir):
        """Test that FindSymbolTool caches results"""
        tool = FindSymbolTool(agent)
        cache = get_global_cache(temp_project_dir)

        # First query - should be cache miss
        result1_str = tool.apply(name_path="hello", relative_path="example.py")
        result1 = json.loads(result1_str)

        # Check cache metadata
        assert "_cache" in result1
        assert result1["_cache"]["cache_status"] == "cached"

        # Second query - should be cache hit
        result2_str = tool.apply(name_path="hello", relative_path="example.py")
        result2 = json.loads(result2_str)

        assert "_cache" in result2
        assert result2["_cache"]["cache_status"] == "hit"
        assert result2["_cache"]["hit_count"] == 1

        # Verify stats
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0

    def test_get_symbols_overview_caches_result(self, agent, temp_project_dir):
        """Test that GetSymbolsOverviewTool caches results"""
        tool = GetSymbolsOverviewTool(agent)

        # First query
        result1_str = tool.apply(relative_path="example.py")
        result1 = json.loads(result1_str)

        assert "_cache" in result1
        assert result1["_cache"]["cache_status"] == "cached"

        # Second query - should hit cache
        result2_str = tool.apply(relative_path="example.py")
        result2 = json.loads(result2_str)

        assert result2["_cache"]["cache_status"] == "hit"

    def test_replace_symbol_invalidates_cache(self, agent, temp_project_dir):
        """Test that ReplaceSymbolBodyTool invalidates cache"""
        find_tool = FindSymbolTool(agent)
        replace_tool = ReplaceSymbolBodyTool(agent)
        cache = get_global_cache(temp_project_dir)

        # Cache initial result
        result1_str = find_tool.apply(name_path="hello", relative_path="example.py")
        result1 = json.loads(result1_str)
        assert result1["_cache"]["cache_status"] == "cached"

        # Edit the file
        edit_result_str = replace_tool.apply(
            name_path="hello",
            relative_path="example.py",
            body='def hello():\n    return "universe"',
            response_format="summary"
        )
        edit_result = json.loads(edit_result_str)

        # Check that cache was invalidated
        assert "_cache_invalidated" in edit_result
        assert edit_result["_cache_invalidated"] >= 1

        # Query again - should be cache miss (file changed)
        result2_str = find_tool.apply(name_path="hello", relative_path="example.py")
        result2 = json.loads(result2_str)

        # Should be new cache entry, not a hit
        assert result2["_cache"]["cache_status"] == "cached"

        # Verify the content actually changed
        stats = cache.get_stats()
        assert stats["invalidations"] >= 1

    def test_insert_after_invalidates_cache(self, agent, temp_project_dir):
        """Test that InsertAfterSymbolTool invalidates cache"""
        find_tool = FindSymbolTool(agent)
        insert_tool = InsertAfterSymbolTool(agent)

        # Cache initial result
        result1_str = find_tool.apply(name_path="hello", relative_path="example.py")
        result1 = json.loads(result1_str)
        assert result1["_cache"]["cache_status"] == "cached"

        # Insert new function
        edit_result_str = insert_tool.apply(
            name_path="hello",
            relative_path="example.py",
            body='\ndef new_function():\n    return "new"',
            response_format="summary"
        )
        edit_result = json.loads(edit_result_str)
        assert "_cache_invalidated" in edit_result

        # Query again - cache should be invalidated
        result2_str = find_tool.apply(name_path="new_function", relative_path="example.py", include_body=True)
        result2 = json.loads(result2_str)

        # Should find the new function
        assert len(result2["symbols"]) > 0

    def test_insert_before_invalidates_cache(self, agent, temp_project_dir):
        """Test that InsertBeforeSymbolTool invalidates cache"""
        overview_tool = GetSymbolsOverviewTool(agent)
        insert_tool = InsertBeforeSymbolTool(agent)

        # Cache initial overview
        result1_str = overview_tool.apply(relative_path="example.py")
        result1 = json.loads(result1_str)
        initial_count = len(result1["symbols"])

        # Insert before first function
        edit_result_str = insert_tool.apply(
            name_path="hello",
            relative_path="example.py",
            body='def first_function():\n    return "first"\n\n',
            response_format="summary"
        )
        edit_result = json.loads(edit_result_str)
        assert "_cache_invalidated" in edit_result

        # Get overview again - should see new function
        result2_str = overview_tool.apply(relative_path="example.py")
        result2 = json.loads(result2_str)

        # Should have one more symbol
        assert len(result2["symbols"]) > initial_count

    def test_cache_with_different_query_params(self, agent):
        """Test that different query parameters create separate cache entries"""
        tool = FindSymbolTool(agent)

        # Query without body
        result1_str = tool.apply(
            name_path="hello",
            relative_path="example.py",
            include_body=False
        )
        result1 = json.loads(result1_str)

        # Query with body
        result2_str = tool.apply(
            name_path="hello",
            relative_path="example.py",
            include_body=True
        )
        result2 = json.loads(result2_str)

        # Both should be cached separately
        assert result1["_cache"]["cache_status"] == "cached"
        assert result2["_cache"]["cache_status"] == "cached"

        # Query again without body - should hit cache
        result3_str = tool.apply(
            name_path="hello",
            relative_path="example.py",
            include_body=False
        )
        result3 = json.loads(result3_str)
        assert result3["_cache"]["cache_status"] == "hit"

    def test_cache_performance_benefit(self, agent, temp_project_dir):
        """Test that cache provides performance benefit"""
        tool = FindSymbolTool(agent)
        cache = get_global_cache(temp_project_dir)

        # Run multiple queries
        for _ in range(10):
            tool.apply(name_path="hello", relative_path="example.py")

        # Check hit rate
        stats = cache.get_stats()
        # First query is a miss, rest are hits
        assert stats["hits"] == 9
        assert stats["misses"] == 0
        assert stats["hit_rate_percent"] == 100.0

    def test_multiple_file_edits_invalidate_correctly(self, agent, temp_project_dir):
        """Test that editing one file doesn't invalidate cache for other files"""
        # Create second file
        second_file = os.path.join(temp_project_dir, "other.py")
        with open(second_file, "w") as f:
            f.write("def other():\n    return 'other'\n")

        find_tool = FindSymbolTool(agent)
        replace_tool = ReplaceSymbolBodyTool(agent)
        cache = get_global_cache(temp_project_dir)

        # Cache both files
        find_tool.apply(name_path="hello", relative_path="example.py")
        find_tool.apply(name_path="other", relative_path="other.py")

        # Edit only first file
        replace_tool.apply(
            name_path="hello",
            relative_path="example.py",
            body='def hello():\n    return "changed"',
            response_format="summary"
        )

        # Query second file - should still be cached (hit)
        result_str = find_tool.apply(name_path="other", relative_path="other.py")
        result = json.loads(result_str)

        assert result["_cache"]["cache_status"] == "hit"
