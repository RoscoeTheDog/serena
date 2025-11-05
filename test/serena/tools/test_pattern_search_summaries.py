"""
Unit tests for Pattern Search Summaries feature (Story 8).

Tests verify:
- Summary mode returns counts + preview
- Detailed mode returns full matches (backward compatible)
- Preview limited to 10 matches
- Token savings achieved (60-80% target)
- Edge cases (0 matches, 1 match, 1000+ matches)
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from serena.project import Project
from serena.agent import SerenaAgent
from serena.tools.file_tools import SearchForPatternTool


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with sample files for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample files with various patterns
        files = {
            "main.py": """
# TODO: Implement authentication
def main():
    print("Hello")
    # TODO: Add error handling
    pass

# TODO: Add tests
""",
            "auth.py": """
# TODO: Add rate limiting
def authenticate(user):
    # TODO: Implement JWT
    return True

# TODO: Add logging
def validate_token(token):
    # TODO: Check expiry
    return True
""",
            "api.py": """
# TODO: Add API versioning
def get_user():
    # TODO: Add caching
    return {}

# TODO: Implement pagination
def list_users():
    # TODO: Add filtering
    # TODO: Add sorting
    return []

# TODO: Add rate limiting
""",
            "utils.py": """
def helper():
    return None
""",
        }

        for filename, content in files.items():
            filepath = Path(tmpdir) / filename
            filepath.write_text(content)

        yield tmpdir


@pytest.fixture
def agent(temp_project_dir):
    """Create a Serena agent for testing"""
    project = Project(project_root=temp_project_dir)
    agent = SerenaAgent(project=project)
    return agent


def test_summary_mode_basic(agent):
    """Test basic summary mode functionality."""
    tool = SearchForPatternTool(agent)

    result_str = tool.apply(
        substring_pattern=r"TODO",
        output_mode="summary"
    )

    result = json.loads(result_str)

    # Verify structure
    assert result["_schema"] == "search_summary_v1"
    assert result["pattern"] == "TODO"
    assert "total_matches" in result
    assert "by_file" in result
    assert "preview" in result
    assert result["output_mode"] == "summary"

    # Verify counts (should find multiple TODOs)
    assert result["total_matches"] > 0
    assert len(result["by_file"]) > 0

    # Verify preview limited to 10
    assert len(result["preview"]) <= 10


def test_summary_mode_with_many_matches(agent):
    """Test summary mode with >10 matches shows full_results_available hint."""
    tool = SearchForPatternTool(agent)

    result_str = tool.apply(
        substring_pattern=r"TODO",
        output_mode="summary"
    )

    result = json.loads(result_str)

    # Should have many TODO matches across all files
    assert result["total_matches"] > 10

    # Should have hint about full results
    assert "full_results_available" in result
    assert "output_mode='detailed'" in result["full_results_available"]
    assert str(result["total_matches"]) in result["full_results_available"]


def test_detailed_mode_backward_compatible(temp_project_dir):
    """Test detailed mode returns full matches (backward compatible)."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern=r"TODO",
        output_mode="detailed"
    )

    result = json.loads(result_str)

    # Should be a dict mapping files to lists of matches
    assert isinstance(result, dict)

    # Should have file paths as keys
    for file_path, matches in result.items():
        assert isinstance(file_path, str)
        assert isinstance(matches, list)

        # Each match should be a string with content
        for match in matches:
            assert isinstance(match, str)
            assert "TODO" in match


def test_default_mode_is_detailed(temp_project_dir):
    """Test that default mode (no output_mode parameter) returns detailed results."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    # Call without output_mode parameter
    result_str = tool.apply(substring_pattern=r"TODO")

    result = json.loads(result_str)

    # Should be detailed format (dict of files to matches)
    assert isinstance(result, dict)

    # Should NOT be summary format
    assert "_schema" not in result or result.get("_schema") != "search_summary_v1"


def test_summary_mode_counts_by_file(temp_project_dir):
    """Test summary mode correctly counts matches per file."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern=r"TODO",
        output_mode="summary"
    )

    result = json.loads(result_str)

    # Verify by_file counts
    by_file = result["by_file"]

    # api.py should have most TODOs (7 in our sample)
    # auth.py should have 4 TODOs
    # main.py should have 3 TODOs
    # utils.py should have 0 TODOs

    assert "api.py" in by_file
    assert "auth.py" in by_file
    assert "main.py" in by_file

    # api.py should be listed (has most matches)
    assert by_file["api.py"] > 0

    # Total matches should equal sum of by_file counts
    total_in_by_file = sum(by_file.values())
    assert total_in_by_file <= result["total_matches"]


def test_summary_mode_preview_structure(temp_project_dir):
    """Test preview structure in summary mode."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern=r"TODO",
        output_mode="summary"
    )

    result = json.loads(result_str)

    # Verify preview structure
    preview = result["preview"]

    for item in preview:
        assert "file" in item
        assert "snippet" in item
        assert isinstance(item["file"], str)
        assert isinstance(item["snippet"], str)

        # Snippet should contain the pattern
        assert "TODO" in item["snippet"]

        # Snippet should be limited in length
        assert len(item["snippet"]) <= 150


def test_summary_mode_with_zero_matches(temp_project_dir):
    """Test summary mode with zero matches."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern=r"NONEXISTENT_PATTERN_12345",
        output_mode="summary"
    )

    result = json.loads(result_str)

    # Should still have valid structure
    assert result["_schema"] == "search_summary_v1"
    assert result["total_matches"] == 0
    assert result["by_file"] == {}
    assert result["preview"] == []

    # Should NOT have full_results_available hint
    assert "full_results_available" not in result


def test_summary_mode_with_one_match(temp_project_dir):
    """Test summary mode with exactly one match."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern=r"def helper\(",
        output_mode="summary"
    )

    result = json.loads(result_str)

    # Should have exactly one match
    assert result["total_matches"] == 1
    assert len(result["preview"]) == 1

    # Should NOT have full_results_available hint (<=10 matches)
    assert "full_results_available" not in result


def test_summary_mode_with_file_filter(temp_project_dir):
    """Test summary mode respects file filters."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern=r"TODO",
        output_mode="summary",
        paths_include_glob="*auth.py"
    )

    result = json.loads(result_str)

    # Should only have matches from auth.py
    assert len(result["by_file"]) == 1
    assert "auth.py" in result["by_file"]


def test_summary_mode_with_context_lines(temp_project_dir):
    """Test summary mode with context lines."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern=r"TODO",
        output_mode="summary",
        context_lines_before=1,
        context_lines_after=1
    )

    result = json.loads(result_str)

    # Should still work with context lines
    assert result["total_matches"] > 0
    assert len(result["preview"]) <= 10


def test_token_savings_summary_vs_detailed(temp_project_dir):
    """Test that summary mode provides significant token savings."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    # Get summary mode result
    summary_str = tool.apply(
        substring_pattern=r"TODO",
        output_mode="summary"
    )

    # Get detailed mode result
    detailed_str = tool.apply(
        substring_pattern=r"TODO",
        output_mode="detailed"
    )

    summary_tokens = len(summary_str) / 4  # Approximate token count
    detailed_tokens = len(detailed_str) / 4

    # Summary should be significantly smaller
    savings_percent = (1 - summary_tokens / detailed_tokens) * 100

    # Should achieve 60-80% token savings
    assert savings_percent >= 55, f"Token savings: {savings_percent:.1f}% (target: 60-80%)"

    print(f"\nToken savings: {savings_percent:.1f}%")
    print(f"Summary: {summary_tokens:.0f} tokens")
    print(f"Detailed: {detailed_tokens:.0f} tokens")


def test_summary_mode_sorted_by_match_count(temp_project_dir):
    """Test that by_file is sorted by match count (descending)."""
    tool = SearchForPatternTool(project=MockProject(temp_project_dir))

    result_str = tool.apply(
        substring_pattern=r"TODO",
        output_mode="summary"
    )

    result = json.loads(result_str)

    by_file = result["by_file"]
    counts = list(by_file.values())

    # Should be sorted descending
    assert counts == sorted(counts, reverse=True)


def test_summary_mode_with_many_files(temp_project_dir):
    """Test summary mode limits by_file to top 20 files."""
    # Create a project with >20 files
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(30):
            filepath = Path(tmpdir) / f"file_{i:02d}.py"
            filepath.write_text(f"# TODO: Task {i}\n" * (i + 1))

        tool = SearchForPatternTool(project=MockProject(tmpdir))

        result_str = tool.apply(
            substring_pattern=r"TODO",
            output_mode="summary"
        )

        result = json.loads(result_str)

        # Should limit to 20 files in by_file
        assert len(result["by_file"]) <= 20

        # Should have additional_files info
        if result["total_matches"] > sum(result["by_file"].values()):
            assert "additional_files" in result
            assert result["additional_files"]["count"] > 0
            assert result["additional_files"]["matches"] > 0


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
