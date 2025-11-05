"""
Test suite for Story 2: Fix `output_mode` in `search_for_pattern`

This test suite validates:
1. New result_format parameter with Literal typing
2. Deprecation of output_mode parameter
3. Default changed from "detailed" to "summary"
4. _expansion_hint in summary mode
5. Token estimates in summary output
6. Backward compatibility with output_mode
"""

import json
import tempfile
from pathlib import Path

import pytest

from serena.project import Project
from serena.tools.file_tools import SearchForPatternTool


class MockProject(Project):
    """Mock project for testing without full project setup."""

    def __init__(self, root_path: str):
        self.root_path = root_path

    def get_project_root(self):
        return self.root_path

    def is_ignored_path(self, path: str) -> bool:
        return False


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with sample files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files with various patterns
        test_files = {
            "file1.py": "# TODO: implement feature\nclass User:\n    pass\n# TODO: add tests",
            "file2.py": "def main():\n    # TODO: refactor\n    pass",
            "file3.py": "# Simple file\nprint('hello')",
        }

        for filename, content in test_files.items():
            Path(tmpdir, filename).write_text(content)

        yield tmpdir


# ============================================================================
# UNIT TESTS: New result_format parameter
# ============================================================================


def test_result_format_summary_mode(temp_project_dir):
    """Test summary mode with new result_format parameter."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern="TODO",
        result_format="summary"
    )
    result = json.loads(result_str)

    # Verify structure
    assert result["_schema"] == "search_summary_v1"
    assert result["result_format"] == "summary"
    assert "total_matches" in result
    assert "by_file" in result
    assert "preview" in result
    assert result["total_matches"] == 3  # 3 TODO comments


def test_result_format_detailed_mode(temp_project_dir):
    """Test detailed mode with new result_format parameter."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern="TODO",
        result_format="detailed"
    )
    result = json.loads(result_str)

    # Verify structure (should be dict of files to matches)
    assert isinstance(result, dict)
    # Should have file keys (not metadata fields)
    file_keys = [k for k in result.keys() if not k.startswith("_")]
    assert len(file_keys) > 0


def test_default_is_summary_mode(temp_project_dir):
    """Test that default mode is now 'summary' (not 'detailed')."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    # Call without result_format or output_mode
    result_str = tool.apply(substring_pattern="TODO")
    result = json.loads(result_str)

    # Should be summary format
    assert result["_schema"] == "search_summary_v1"
    assert result["result_format"] == "summary"


# ============================================================================
# INTEGRATION TESTS: Token estimates and expansion hints
# ============================================================================


def test_summary_includes_token_estimate(temp_project_dir):
    """Test summary mode includes token estimates."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern="TODO",
        result_format="summary"
    )
    result = json.loads(result_str)

    # Verify token estimate structure
    assert "_token_estimate" in result
    assert "current" in result["_token_estimate"]
    assert "detailed" in result["_token_estimate"]
    assert "savings_pct" in result["_token_estimate"]

    # Verify estimates are reasonable
    assert result["_token_estimate"]["current"] < result["_token_estimate"]["detailed"]
    assert 0 <= result["_token_estimate"]["savings_pct"] <= 100


def test_summary_includes_expansion_hint_when_truncated(temp_project_dir):
    """Test summary mode includes _expansion_hint when results are truncated."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    # Create many matches to trigger truncation
    # (The test files have 3 TODOs, which is < 10, so we need more)
    test_dir = temp_project_dir
    for i in range(15):
        Path(test_dir, f"extra{i}.py").write_text(f"# TODO: task {i}")

    result_str = tool.apply(
        substring_pattern="TODO",
        result_format="summary"
    )
    result = json.loads(result_str)

    # Should have expansion hint since total_matches > 10
    assert "_expansion_hint" in result
    assert "result_format='detailed'" in result["_expansion_hint"]
    assert str(result["total_matches"]) in result["_expansion_hint"]


def test_summary_no_expansion_hint_when_few_results(temp_project_dir):
    """Test summary mode doesn't include expansion hint when results fit in preview."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern="TODO",
        result_format="summary"
    )
    result = json.loads(result_str)

    # Should NOT have expansion hint since total_matches <= 10
    assert "_expansion_hint" not in result


# ============================================================================
# BACKWARD COMPATIBILITY TESTS: Deprecated output_mode parameter
# ============================================================================


def test_output_mode_deprecated_but_works_summary(temp_project_dir):
    """Test that output_mode='summary' still works but shows deprecation warning."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern="TODO",
        output_mode="summary"
    )
    result = json.loads(result_str)

    # Should work as summary
    assert result["_schema"] == "search_summary_v1"
    assert result["result_format"] == "summary"

    # Should include deprecation warning
    assert "_deprecated" in result
    assert result["_deprecated"]["parameter"] == "output_mode"
    assert result["_deprecated"]["replacement"] == "result_format"
    assert result["_deprecated"]["removal_version"] == "2.0.0"
    assert "result_format='summary'" in result["_deprecated"]["migration"]


def test_output_mode_deprecated_but_works_detailed(temp_project_dir):
    """Test that output_mode='detailed' still works but shows deprecation warning."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern="TODO",
        output_mode="detailed"
    )
    result = json.loads(result_str)

    # Should work as detailed
    assert isinstance(result, dict)
    file_keys = [k for k in result.keys() if not k.startswith("_")]
    assert len(file_keys) > 0

    # Should include deprecation warning
    assert "_deprecated" in result
    assert result["_deprecated"]["parameter"] == "output_mode"
    assert result["_deprecated"]["replacement"] == "result_format"


def test_result_format_takes_precedence_over_output_mode(temp_project_dir):
    """Test that result_format parameter takes precedence when both are provided."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern="TODO",
        result_format="detailed",
        output_mode="summary"  # Should be ignored
    )
    result = json.loads(result_str)

    # Should be detailed (result_format wins)
    assert isinstance(result, dict)
    file_keys = [k for k in result.keys() if not k.startswith("_")]
    assert len(file_keys) > 0

    # Should NOT have deprecation warning (new param used)
    assert "_deprecated" not in result


# ============================================================================
# MIGRATION TESTS: Verify parameter mapping
# ============================================================================


def test_migration_output_mode_summary_to_result_format(temp_project_dir):
    """Test migration from output_mode='summary' to result_format='summary'."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    # OLD way (deprecated)
    old_result_str = tool.apply(
        substring_pattern="TODO",
        output_mode="summary"
    )
    old_result = json.loads(old_result_str)

    # NEW way (recommended)
    new_result_str = tool.apply(
        substring_pattern="TODO",
        result_format="summary"
    )
    new_result = json.loads(new_result_str)

    # Results should be equivalent (ignoring deprecation warning)
    assert old_result["_schema"] == new_result["_schema"]
    assert old_result["total_matches"] == new_result["total_matches"]
    assert old_result["by_file"] == new_result["by_file"]


def test_migration_output_mode_detailed_to_result_format(temp_project_dir):
    """Test migration from output_mode='detailed' to result_format='detailed'."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    # OLD way (deprecated)
    old_result_str = tool.apply(
        substring_pattern="TODO",
        output_mode="detailed"
    )
    old_result = json.loads(old_result_str)

    # NEW way (recommended)
    new_result_str = tool.apply(
        substring_pattern="TODO",
        result_format="detailed"
    )
    new_result = json.loads(new_result_str)

    # Filter out metadata fields
    old_files = {k: v for k, v in old_result.items() if not k.startswith("_")}
    new_files = {k: v for k, v in new_result.items() if not k.startswith("_")}

    # Results should be equivalent
    assert old_files == new_files


def test_migration_default_behavior_changed(temp_project_dir):
    """Test that default behavior changed from detailed to summary."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    # Default call (no parameters)
    result_str = tool.apply(substring_pattern="TODO")
    result = json.loads(result_str)

    # Should now be summary by default (not detailed)
    assert "_schema" in result  # Summary has schema
    assert result["_schema"] == "search_summary_v1"
    assert result["result_format"] == "summary"


# ============================================================================
# DOCUMENTATION TESTS: Verify output structure
# ============================================================================


def test_summary_output_structure_documented(temp_project_dir):
    """Test that summary output has documented structure."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern="TODO",
        result_format="summary"
    )
    result = json.loads(result_str)

    # Verify all expected fields
    expected_fields = ["_schema", "pattern", "total_matches", "by_file", "preview", "result_format"]
    for field in expected_fields:
        assert field in result, f"Missing field: {field}"

    # Verify preview structure
    if len(result["preview"]) > 0:
        preview_item = result["preview"][0]
        assert "file" in preview_item
        assert "snippet" in preview_item


def test_detailed_output_structure_documented(temp_project_dir):
    """Test that detailed output has documented structure."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern="TODO",
        result_format="detailed"
    )
    result = json.loads(result_str)

    # Should be dict mapping files to match lists
    assert isinstance(result, dict)
    file_keys = [k for k in result.keys() if not k.startswith("_")]
    assert len(file_keys) > 0

    # Each file should map to a list of strings
    for key in file_keys:
        assert isinstance(result[key], list)
        if len(result[key]) > 0:
            assert isinstance(result[key][0], str)


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


def test_zero_matches_summary_mode(temp_project_dir):
    """Test summary mode with zero matches."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern="NONEXISTENT_PATTERN_XYZ",
        result_format="summary"
    )
    result = json.loads(result_str)

    assert result["total_matches"] == 0
    assert len(result["by_file"]) == 0
    assert len(result["preview"]) == 0
    assert "_expansion_hint" not in result  # No hint when no matches


def test_zero_matches_detailed_mode(temp_project_dir):
    """Test detailed mode with zero matches."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern="NONEXISTENT_PATTERN_XYZ",
        result_format="detailed"
    )
    result = json.loads(result_str)

    # Should be empty dict
    file_keys = [k for k in result.keys() if not k.startswith("_")]
    assert len(file_keys) == 0


def test_exactly_10_matches_no_expansion_hint(temp_project_dir):
    """Test that exactly 10 matches doesn't trigger expansion hint."""
    test_dir = temp_project_dir
    # Create exactly 10 TODO comments total (3 exist, add 7 more)
    for i in range(7):
        Path(test_dir, f"extra{i}.py").write_text(f"# TODO: task {i}")

    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern="TODO",
        result_format="summary"
    )
    result = json.loads(result_str)

    assert result["total_matches"] == 10
    # Should NOT have expansion hint (threshold is > 10, not >= 10)
    assert "_expansion_hint" not in result


def test_11_matches_triggers_expansion_hint(temp_project_dir):
    """Test that 11 matches triggers expansion hint."""
    test_dir = temp_project_dir
    # Create 11 TODO comments total (3 exist, add 8 more)
    for i in range(8):
        Path(test_dir, f"extra{i}.py").write_text(f"# TODO: task {i}")

    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern="TODO",
        result_format="summary"
    )
    result = json.loads(result_str)

    assert result["total_matches"] == 11
    # Should have expansion hint (> 10)
    assert "_expansion_hint" in result
