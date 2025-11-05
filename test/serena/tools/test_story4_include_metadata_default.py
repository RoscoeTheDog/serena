"""
Test suite for Story 4: Flip include_metadata Default in list_memories

Tests the default behavior change from include_metadata=False to include_metadata=True,
ensuring agents get useful metadata by default while maintaining backward compatibility.
"""

import pytest
import json
import tempfile
from pathlib import Path
from serena.agent import MemoriesManager


@pytest.fixture
def temp_memory_dir():
    """Create a temporary directory for memory files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_memories(temp_memory_dir):
    """Create sample memory files for testing"""
    memories = {
        "authentication_flow": "# Authentication Flow\n\nThe system uses JWT tokens for authentication.\nTokens expire after 24 hours.\nRefresh tokens are stored in httpOnly cookies.",
        "error_handling": "# Error Handling\n\nAll errors are caught at the route level.\nErrors are logged to CloudWatch.\nUser-facing errors use standardized format.",
        "database_schema": "# Database Schema\n\nUsers table: id, email, password_hash, created_at\nSessions table: id, user_id, token, expires_at",
    }

    for name, content in memories.items():
        file_path = temp_memory_dir / f"{name}.md"
        file_path.write_text(content, encoding="utf-8")

    return MemoriesManager(temp_memory_dir)


# =============================================================================
# Unit Tests: Default Behavior
# =============================================================================

def test_default_returns_metadata(sample_memories):
    """Test that calling list_memories() without args returns metadata by default"""
    result = sample_memories.list_memories()

    assert isinstance(result, list)
    assert len(result) == 3
    assert all(isinstance(mem, dict) for mem in result)

    # Check that metadata fields are present
    for mem in result:
        assert "name" in mem
        assert "size_kb" in mem
        assert "last_modified" in mem
        assert "preview" in mem
        assert "estimated_tokens" in mem
        assert "lines" in mem


def test_explicit_true_returns_metadata(sample_memories):
    """Test that include_metadata=True explicitly works"""
    result = sample_memories.list_memories(include_metadata=True)

    assert isinstance(result, list)
    assert len(result) == 3
    assert all(isinstance(mem, dict) for mem in result)


def test_explicit_false_returns_names_only(sample_memories):
    """Test that include_metadata=False returns just names (backward compat)"""
    result = sample_memories.list_memories(include_metadata=False)

    assert isinstance(result, list)
    assert len(result) == 3
    assert all(isinstance(mem, str) for mem in result)

    # Check that we get simple strings, not dicts
    assert "authentication_flow" in result
    assert "error_handling" in result
    assert "database_schema" in result


# =============================================================================
# Integration Tests: Tool Output
# =============================================================================

def test_tool_output_with_default(sample_memories):
    """Test that the tool returns JSON with _token_savings when using default"""
    from serena.tools.memory_tools import ListMemoriesTool
    from serena.agent import SerenaAgent

    # Create a minimal agent with just memory manager
    class MinimalAgent:
        def __init__(self, memories_manager):
            self.memories_manager = memories_manager

    agent = MinimalAgent(sample_memories)
    tool = ListMemoriesTool(agent)

    # Call with default (should return metadata)
    result_json = tool.apply()
    result = json.loads(result_json)

    assert "memories" in result
    assert "_token_savings" in result

    # Check memories structure
    assert isinstance(result["memories"], list)
    assert len(result["memories"]) == 3

    # Check _token_savings structure
    savings = result["_token_savings"]
    assert "current_output" in savings
    assert "if_read_all_files" in savings
    assert "savings_pct" in savings
    assert "note" in savings

    # Verify savings are positive
    assert savings["current_output"] > 0
    assert savings["if_read_all_files"] > savings["current_output"]
    assert 0 <= savings["savings_pct"] <= 100


def test_tool_output_without_metadata(sample_memories):
    """Test that the tool returns simple list when include_metadata=False"""
    from serena.tools.memory_tools import ListMemoriesTool

    class MinimalAgent:
        def __init__(self, memories_manager):
            self.memories_manager = memories_manager

    agent = MinimalAgent(sample_memories)
    tool = ListMemoriesTool(agent)

    # Call with include_metadata=False
    result_json = tool.apply(include_metadata=False)
    result = json.loads(result_json)

    assert isinstance(result, list)
    assert all(isinstance(mem, str) for mem in result)
    assert "_token_savings" not in result_json


# =============================================================================
# Metadata Content Tests
# =============================================================================

def test_metadata_includes_all_fields(sample_memories):
    """Test that metadata mode includes all required fields"""
    result = sample_memories.list_memories(include_metadata=True)

    for mem in result:
        # Required fields
        assert "name" in mem
        assert "size_kb" in mem
        assert "last_modified" in mem
        assert "preview" in mem
        assert "estimated_tokens" in mem
        assert "lines" in mem

        # Type checks
        assert isinstance(mem["name"], str)
        assert isinstance(mem["size_kb"], (int, float))
        assert isinstance(mem["last_modified"], str)
        assert isinstance(mem["preview"], str)
        assert isinstance(mem["estimated_tokens"], int)
        assert isinstance(mem["lines"], int)


def test_preview_contains_first_lines(sample_memories):
    """Test that preview contains the first N lines of the file"""
    result = sample_memories.list_memories(include_metadata=True, preview_lines=2)

    # Find authentication_flow memory
    auth_mem = next(m for m in result if m["name"] == "authentication_flow")

    # Check that preview contains first 2 lines
    assert "# Authentication Flow" in auth_mem["preview"]
    assert "The system uses JWT tokens" in auth_mem["preview"]

    # Check that it indicates more lines
    assert "more lines" in auth_mem["preview"]


def test_estimated_tokens_reasonable(sample_memories):
    """Test that estimated tokens are in a reasonable range"""
    result = sample_memories.list_memories(include_metadata=True)

    for mem in result:
        # Tokens should be positive
        assert mem["estimated_tokens"] > 0

        # Tokens should be roughly chars / 4 (typical token estimation)
        # We can't be exact, but it should be in the ballpark
        assert mem["estimated_tokens"] > 10  # At least some tokens
        assert mem["estimated_tokens"] < 10000  # Not absurdly large for test files


# =============================================================================
# Token Savings Calculation Tests
# =============================================================================

def test_token_savings_calculations(sample_memories):
    """Test that token savings are calculated correctly"""
    from serena.tools.memory_tools import ListMemoriesTool

    class MinimalAgent:
        def __init__(self, memories_manager):
            self.memories_manager = memories_manager

    agent = MinimalAgent(sample_memories)
    tool = ListMemoriesTool(agent)

    result_json = tool.apply()
    result = json.loads(result_json)

    savings = result["_token_savings"]
    memories = result["memories"]

    # Total if read all should equal sum of estimated_tokens
    total_if_read_all = sum(m["estimated_tokens"] for m in memories)
    assert savings["if_read_all_files"] == total_if_read_all

    # Current output should be less than total
    assert savings["current_output"] < savings["if_read_all_files"]

    # Savings percentage should be correct
    expected_savings_pct = round((1 - savings["current_output"] / savings["if_read_all_files"]) * 100)
    assert savings["savings_pct"] == expected_savings_pct


# =============================================================================
# Backward Compatibility Tests
# =============================================================================

def test_backward_compat_explicit_false(sample_memories):
    """Test that old code using include_metadata=False still works"""
    # Old code pattern: list_memories(include_metadata=False)
    result = sample_memories.list_memories(include_metadata=False)

    # Should return list of strings (names only)
    assert isinstance(result, list)
    assert all(isinstance(mem, str) for mem in result)


def test_backward_compat_explicit_true(sample_memories):
    """Test that code using include_metadata=True explicitly still works"""
    # Code pattern: list_memories(include_metadata=True)
    result = sample_memories.list_memories(include_metadata=True)

    # Should return list of dicts (metadata)
    assert isinstance(result, list)
    assert all(isinstance(mem, dict) for mem in result)


# =============================================================================
# Edge Cases
# =============================================================================

def test_empty_memory_directory(temp_memory_dir):
    """Test behavior with no memories"""
    memories_manager = MemoriesManager(temp_memory_dir)

    # With metadata (default)
    result = memories_manager.list_memories()
    assert isinstance(result, list)
    assert len(result) == 0

    # Without metadata
    result = memories_manager.list_memories(include_metadata=False)
    assert isinstance(result, list)
    assert len(result) == 0


def test_single_memory(temp_memory_dir):
    """Test with just one memory file"""
    file_path = temp_memory_dir / "single.md"
    file_path.write_text("# Single Memory\n\nJust one file here.", encoding="utf-8")

    memories_manager = MemoriesManager(temp_memory_dir)
    result = memories_manager.list_memories()

    assert len(result) == 1
    assert result[0]["name"] == "single"


def test_very_short_file(temp_memory_dir):
    """Test with a very short memory file (fewer lines than preview_lines)"""
    file_path = temp_memory_dir / "short.md"
    file_path.write_text("Short", encoding="utf-8")

    memories_manager = MemoriesManager(temp_memory_dir)
    result = memories_manager.list_memories(preview_lines=5)

    assert len(result) == 1
    mem = result[0]
    assert mem["preview"] == "Short"
    assert "more lines" not in mem["preview"]


def test_tool_with_empty_memories(temp_memory_dir):
    """Test that tool output handles empty memories correctly"""
    from serena.tools.memory_tools import ListMemoriesTool

    class MinimalAgent:
        def __init__(self, memories_manager):
            self.memories_manager = memories_manager

    memories_manager = MemoriesManager(temp_memory_dir)
    agent = MinimalAgent(memories_manager)
    tool = ListMemoriesTool(agent)

    # With metadata (default) - should not add _token_savings for empty list
    result_json = tool.apply()
    result = json.loads(result_json)

    assert isinstance(result, list)
    assert len(result) == 0


# =============================================================================
# Documentation Tests
# =============================================================================

def test_docstring_examples_are_accurate():
    """Test that the docstring examples match actual behavior"""
    # This is a meta-test to ensure documentation stays in sync
    from serena.tools.memory_tools import ListMemoriesTool

    # Check that docstring mentions the new default
    assert "default: True" in ListMemoriesTool.apply.__doc__
    assert "rare" in ListMemoriesTool.apply.__doc__.lower()

    # Check that it mentions token savings
    assert "token" in ListMemoriesTool.apply.__doc__.lower()
    assert "savings" in ListMemoriesTool.apply.__doc__.lower()


# =============================================================================
# Performance Tests
# =============================================================================

def test_metadata_mode_is_efficient(sample_memories):
    """Test that metadata mode is indeed more efficient than reading all files"""
    # Get metadata output
    result = sample_memories.list_memories(include_metadata=True)

    # Calculate preview size vs full file size
    total_preview_chars = sum(len(mem["preview"]) for mem in result)
    total_file_tokens = sum(mem["estimated_tokens"] for mem in result)
    preview_tokens = total_preview_chars // 4

    # Preview should be significantly smaller than full files
    assert preview_tokens < total_file_tokens

    # Should achieve at least 50% savings
    savings_pct = (1 - preview_tokens / total_file_tokens) * 100
    assert savings_pct > 50


# =============================================================================
# Migration Tests
# =============================================================================

def test_migration_pattern_old_to_new():
    """Document the migration pattern from old to new behavior"""
    # OLD: list_memories(include_metadata=False)  # Default was False
    # NEW: list_memories()  # Default is now True

    # This test serves as documentation
    # Old code that relied on default False needs to be explicit:
    #   list_memories(include_metadata=False)
    # New code can use default:
    #   list_memories()  # Gets metadata
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
