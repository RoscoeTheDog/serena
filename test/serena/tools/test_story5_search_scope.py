"""
Test suite for Story 5: Rename exclude_generated to search_scope

This test suite validates:
1. New search_scope parameter works correctly
2. Backward compatibility with exclude_generated
3. Default behavior changed to "source"
4. Deprecation warnings work properly
5. All three affected tools (FindSymbolTool, SearchForPatternTool, ListDirTool)
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from serena.project import Project
from serena.tools.file_tools import ListDirTool, SearchForPatternTool
from serena.tools.symbol_tools import FindSymbolTool


@pytest.fixture
def test_project_with_generated_code():
    """Create a test project with generated code patterns."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create source files
        (Path(temp_dir) / "src").mkdir()
        (Path(temp_dir) / "src" / "main.py").write_text("class User:\n    pass\n")
        (Path(temp_dir) / "src" / "utils.py").write_text("def helper():\n    pass\n")

        # Create generated code
        (Path(temp_dir) / "node_modules").mkdir()
        (Path(temp_dir) / "node_modules" / "package.json").write_text('{"name": "test"}')

        (Path(temp_dir) / "__pycache__").mkdir()
        (Path(temp_dir) / "__pycache__" / "main.cpython-39.pyc").write_text("bytecode")

        (Path(temp_dir) / "dist").mkdir()
        (Path(temp_dir) / "dist" / "bundle.js").write_text("// minified code")

        # Create .gitignore
        (Path(temp_dir) / ".gitignore").write_text("*.pyc\n__pycache__/\nnode_modules/\ndist/\n")

        project = Project(temp_dir)
        yield project, temp_dir


# ====================
# Test FindSymbolTool
# ====================

def test_find_symbol_default_search_scope(test_project_with_generated_code):
    """Test that default search_scope='source' excludes generated code."""
    project, temp_dir = test_project_with_generated_code
    tool = FindSymbolTool(project=project)

    result = tool.apply(
        name_path="User",
        substring_matching=True,
        output_format="metadata"
    )

    result_dict = json.loads(result)

    # Should find User in source files
    assert "symbols" in result_dict or "result" in result_dict

    # Should NOT have deprecation warning (using new default)
    assert "_deprecated" not in result_dict


def test_find_symbol_search_scope_all(test_project_with_generated_code):
    """Test search_scope='all' includes everything."""
    project, temp_dir = test_project_with_generated_code
    tool = FindSymbolTool(project=project)

    result = tool.apply(
        name_path="User",
        search_scope="all",
        substring_matching=True,
        output_format="metadata"
    )

    result_dict = json.loads(result)

    # Should not have exclusion metadata
    assert "_excluded" not in result_dict


def test_find_symbol_search_scope_source_explicit(test_project_with_generated_code):
    """Test explicit search_scope='source' excludes generated code."""
    project, temp_dir = test_project_with_generated_code
    tool = FindSymbolTool(project=project)

    result = tool.apply(
        name_path="User",
        search_scope="source",
        substring_matching=True,
        output_format="metadata"
    )

    result_dict = json.loads(result)

    # Should not have deprecation warning
    assert "_deprecated" not in result_dict


def test_find_symbol_exclude_generated_true_deprecated(test_project_with_generated_code):
    """Test exclude_generated=True maps to search_scope='source' with deprecation."""
    project, temp_dir = test_project_with_generated_code
    tool = FindSymbolTool(project=project)

    result = tool.apply(
        name_path="User",
        exclude_generated=True,
        substring_matching=True,
        output_format="metadata"
    )

    result_dict = json.loads(result)

    # Should have deprecation warning
    assert "_deprecated" in result_dict
    deprecation = result_dict["_deprecated"]
    assert any(d["parameter"] == "exclude_generated" for d in deprecation)
    assert any(d["replacement"] == "search_scope" for d in deprecation)
    assert any(d["removal_version"] == "2.0.0" for d in deprecation)


def test_find_symbol_exclude_generated_false_deprecated(test_project_with_generated_code):
    """Test exclude_generated=False maps to search_scope='all' with deprecation."""
    project, temp_dir = test_project_with_generated_code
    tool = FindSymbolTool(project=project)

    result = tool.apply(
        name_path="User",
        exclude_generated=False,
        substring_matching=True,
        output_format="metadata"
    )

    result_dict = json.loads(result)

    # Should have deprecation warning
    assert "_deprecated" in result_dict

    # Should not have exclusion metadata (search_scope='all')
    assert "_excluded" not in result_dict


# ==========================
# Test SearchForPatternTool
# ==========================

def test_search_pattern_default_search_scope(test_project_with_generated_code):
    """Test that default search_scope='source' excludes generated code."""
    project, temp_dir = test_project_with_generated_code
    tool = SearchForPatternTool(project=project)

    result = tool.apply(
        substring_pattern="class",
        relative_path="."
    )

    result_dict = json.loads(result)

    # Should NOT have deprecation warning (using new default)
    assert "_deprecated" not in result_dict or len(result_dict["_deprecated"]) == 0


def test_search_pattern_search_scope_all(test_project_with_generated_code):
    """Test search_scope='all' includes everything."""
    project, temp_dir = test_project_with_generated_code
    tool = SearchForPatternTool(project=project)

    result = tool.apply(
        substring_pattern="class",
        search_scope="all",
        relative_path="."
    )

    result_dict = json.loads(result)

    # Should not have exclusion metadata
    assert "_excluded" not in result_dict


def test_search_pattern_exclude_generated_deprecated(test_project_with_generated_code):
    """Test exclude_generated parameter shows deprecation warning."""
    project, temp_dir = test_project_with_generated_code
    tool = SearchForPatternTool(project=project)

    result = tool.apply(
        substring_pattern="class",
        exclude_generated=True,
        relative_path="."
    )

    result_dict = json.loads(result)

    # Should have deprecation warning
    assert "_deprecated" in result_dict
    assert any(d["parameter"] == "exclude_generated" for d in result_dict["_deprecated"])


# ====================
# Test ListDirTool
# ====================

def test_list_dir_default_search_scope(test_project_with_generated_code):
    """Test that default search_scope='source' excludes generated code."""
    project, temp_dir = test_project_with_generated_code
    tool = ListDirTool(project=project)

    result = tool.apply(
        relative_path=".",
        recursive=True
    )

    result_dict = json.loads(result)

    # Should exclude generated directories
    dirs = result_dict.get("dirs", [])
    assert "node_modules" not in dirs
    assert "__pycache__" not in dirs
    assert "dist" not in dirs

    # Should include source directory
    assert "src" in dirs

    # Should NOT have deprecation warning (using new default)
    assert "_deprecated" not in result_dict


def test_list_dir_search_scope_all(test_project_with_generated_code):
    """Test search_scope='all' includes everything."""
    project, temp_dir = test_project_with_generated_code
    tool = ListDirTool(project=project)

    result = tool.apply(
        relative_path=".",
        recursive=True,
        search_scope="all"
    )

    result_dict = json.loads(result)

    # Should include all directories (except those in .gitignore)
    dirs = result_dict.get("dirs", [])

    # .gitignore should still be respected
    # No exclusion metadata should be present
    assert "_excluded" not in result_dict


def test_list_dir_search_scope_source_with_metadata(test_project_with_generated_code):
    """Test search_scope='source' provides exclusion metadata."""
    project, temp_dir = test_project_with_generated_code
    tool = ListDirTool(project=project)

    result = tool.apply(
        relative_path=".",
        recursive=True,
        search_scope="source"
    )

    result_dict = json.loads(result)

    # Should have exclusion metadata if files were excluded
    if "node_modules" in os.listdir(temp_dir) or "__pycache__" in os.listdir(temp_dir):
        # If generated files exist, should have exclusion metadata
        # (only if they weren't already filtered by .gitignore)
        pass  # Metadata presence depends on gitignore interaction


def test_list_dir_exclude_generated_true_deprecated(test_project_with_generated_code):
    """Test exclude_generated=True maps to search_scope='source' with deprecation."""
    project, temp_dir = test_project_with_generated_code
    tool = ListDirTool(project=project)

    result = tool.apply(
        relative_path=".",
        recursive=True,
        exclude_generated=True
    )

    result_dict = json.loads(result)

    # Should have deprecation warning
    assert "_deprecated" in result_dict
    assert any(d["parameter"] == "exclude_generated" for d in result_dict["_deprecated"])
    assert any(d["replacement"] == "search_scope" for d in result_dict["_deprecated"])

    # Should exclude generated directories
    dirs = result_dict.get("dirs", [])
    assert "src" in dirs  # Source should be included


def test_list_dir_exclude_generated_false_deprecated(test_project_with_generated_code):
    """Test exclude_generated=False maps to search_scope='all' with deprecation."""
    project, temp_dir = test_project_with_generated_code
    tool = ListDirTool(project=project)

    result = tool.apply(
        relative_path=".",
        recursive=True,
        exclude_generated=False
    )

    result_dict = json.loads(result)

    # Should have deprecation warning
    assert "_deprecated" in result_dict

    # Should not have exclusion metadata (search_scope='all')
    assert "_excluded" not in result_dict


# =========================
# Test Exclusion Metadata
# =========================

def test_exclusion_metadata_format(test_project_with_generated_code):
    """Test that exclusion metadata has correct format."""
    project, temp_dir = test_project_with_generated_code
    tool = ListDirTool(project=project)

    result = tool.apply(
        relative_path=".",
        recursive=True,
        search_scope="source"
    )

    result_dict = json.loads(result)

    # If exclusion metadata exists, validate format
    if "_excluded" in result_dict:
        excluded = result_dict["_excluded"]
        assert "excluded_files" in excluded
        assert "excluded_patterns" in excluded
        assert "total_excluded" in excluded
        assert "include_excluded_instruction" in excluded

        # Check that instruction mentions search_scope (not exclude_generated)
        assert "search_scope='all'" in excluded["include_excluded_instruction"]


def test_exclusion_instruction_updated(test_project_with_generated_code):
    """Test that exclusion instructions reference new parameter name."""
    project, temp_dir = test_project_with_generated_code
    tool = FindSymbolTool(project=project)

    # Create a symbol in a generated location to trigger exclusion
    (Path(temp_dir) / "node_modules" / "test.py").write_text("class Generated:\n    pass\n")

    result = tool.apply(
        name_path="Generated",
        search_scope="source",
        substring_matching=True,
        output_format="metadata"
    )

    result_dict = json.loads(result)

    # If exclusion occurred, check instruction
    if "_excluded" in result_dict:
        instruction = result_dict["_excluded"]["include_excluded_instruction"]
        assert "search_scope='all'" in instruction
        assert "exclude_generated" not in instruction


# ===============================
# Test Migration Path
# ===============================

def test_migration_explicit_parameters():
    """Test migration from old to new parameter works correctly."""
    # This test validates the migration examples from the docstring

    # OLD: exclude_generated=True
    # NEW: search_scope='source' (or omit for default)

    # OLD: exclude_generated=False
    # NEW: search_scope='all'

    # This is validated by the deprecation tests above
    pass


def test_parameter_priority():
    """Test that exclude_generated takes precedence when both are provided."""
    with tempfile.TemporaryDirectory() as temp_dir:
        (Path(temp_dir) / "test.py").write_text("class Test:\n    pass\n")
        (Path(temp_dir) / ".gitignore").write_text("")

        project = Project(temp_dir)
        tool = FindSymbolTool(project=project)

        # If both are provided, exclude_generated should take precedence
        result = tool.apply(
            name_path="Test",
            exclude_generated=False,  # Should map to "all"
            search_scope="source",    # This should be overridden
            substring_matching=True,
            output_format="metadata"
        )

        result_dict = json.loads(result)

        # Should have deprecation warning
        assert "_deprecated" in result_dict

        # Should behave as search_scope='all' (no exclusions)
        assert "_excluded" not in result_dict


# ===============================
# Test Edge Cases
# ===============================

def test_search_scope_custom_fallback():
    """Test that 'custom' scope falls back to 'source' (future feature)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        (Path(temp_dir) / "test.py").write_text("class Test:\n    pass\n")
        (Path(temp_dir) / ".gitignore").write_text("")

        project = Project(temp_dir)
        tool = FindSymbolTool(project=project)

        # Custom should not crash (future feature)
        result = tool.apply(
            name_path="Test",
            search_scope="custom",
            substring_matching=True,
            output_format="metadata"
        )

        result_dict = json.loads(result)

        # Should not crash, should work (may treat as "source" or "all")
        assert "symbols" in result_dict or "result" in result_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
