"""
Story 1 Tests: Fix detail_level Ambiguity in find_symbol

Tests for the new output_format parameter that replaces include_body and detail_level.

Test Categories:
1. Unit tests - New parameter behavior
2. Integration tests - Tool workflows with new params
3. Backward compatibility tests - Old params still work with warnings
4. Migration tests - Mapping from old → new
5. Documentation tests - Examples in docstrings are valid
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from serena.agent import SerenaAgent
from serena.project import Project
from serena.tools.symbol_tools import FindSymbolTool


@pytest.fixture
def temp_project():
    """Create a temporary project with test Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a Python file with various symbols
        test_file = Path(tmpdir) / "example.py"
        test_file.write_text('''
"""Example module for testing."""

class UserService:
    """Service for user management."""

    def __init__(self, db_connection):
        """Initialize the service.

        Args:
            db_connection: Database connection object
        """
        self.db = db_connection

    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate a user with username and password.

        This method validates credentials against the database.
        It uses secure hashing for password comparison.

        Args:
            username: The username to authenticate
            password: The password to verify

        Returns:
            True if authentication succeeds, False otherwise

        Raises:
            DatabaseError: If database connection fails
        """
        # Hash the password
        hashed = self._hash_password(password)

        # Query database
        user = self.db.query("SELECT * FROM users WHERE username = ?", username)

        # Compare hashes
        if user and user.password_hash == hashed:
            return True
        return False

    def _hash_password(self, password: str) -> str:
        """Internal method to hash passwords."""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()


def standalone_function():
    """A standalone function for testing."""
    return "Hello, World!"
''')

        yield tmpdir


@pytest.fixture
def agent(temp_project):
    """Create a Serena agent with the temp project."""
    project = Project(temp_project)
    agent = SerenaAgent(project)
    return agent


@pytest.fixture
def find_tool(agent):
    """Get the FindSymbolTool from the agent."""
    return agent.get_tool(FindSymbolTool)


# ==============================================================================
# 1. UNIT TESTS - New Parameter Behavior
# ==============================================================================

def test_output_format_metadata_default(find_tool):
    """Test that output_format='metadata' is the default and returns minimal info."""
    result_str = find_tool.apply(name_path="UserService", relative_path="example.py")
    result = json.loads(result_str)

    assert "symbols" in result
    symbols = result["symbols"]
    assert len(symbols) > 0

    # Metadata mode should NOT include body
    symbol = symbols[0]
    assert "name" in symbol or "name_path" in symbol
    assert "kind" in symbol
    assert "location" in symbol

    # Should NOT have body in metadata mode
    assert "body" not in symbol or symbol.get("body") is None


def test_output_format_signature(find_tool):
    """Test that output_format='signature' returns signature + docstring + complexity."""
    result_str = find_tool.apply(
        name_path="UserService/authenticate",
        relative_path="example.py",
        output_format="signature"
    )
    result = json.loads(result_str)

    assert "symbols" in result
    symbols = result["symbols"]
    assert len(symbols) > 0

    symbol = symbols[0]

    # Signature mode should include signature and docstring
    assert "signature" in symbol
    assert "authenticate" in symbol["signature"]

    # Should include docstring
    assert "docstring" in symbol
    assert "Authenticate a user" in symbol["docstring"]

    # Should include complexity analysis
    assert "complexity" in symbol

    # Should include token estimates
    assert "tokens_estimate" in symbol
    assert "signature_plus_docstring" in symbol["tokens_estimate"]
    assert "full_body" in symbol["tokens_estimate"]
    assert "savings" in symbol["tokens_estimate"]

    # Should NOT include full body
    assert "body" not in symbol or symbol.get("body") is None


def test_output_format_body(find_tool):
    """Test that output_format='body' returns full source code."""
    result_str = find_tool.apply(
        name_path="UserService",
        relative_path="example.py",
        output_format="body"
    )
    result = json.loads(result_str)

    assert "symbols" in result
    symbols = result["symbols"]
    assert len(symbols) > 0

    symbol = symbols[0]

    # Body mode should include full body
    assert "body" in symbol
    assert "class UserService" in symbol["body"]
    assert "def authenticate" in symbol["body"]
    assert "def _hash_password" in symbol["body"]


def test_output_format_metadata_no_body(find_tool):
    """Test that metadata mode explicitly does not fetch body (performance)."""
    result_str = find_tool.apply(
        name_path="UserService",
        relative_path="example.py",
        output_format="metadata"
    )
    result = json.loads(result_str)

    symbols = result["symbols"]
    symbol = symbols[0]

    # Metadata should be fast - no body fetching
    assert "body" not in symbol or symbol.get("body") is None

    # But should have location for later retrieval
    assert "location" in symbol


# ==============================================================================
# 2. INTEGRATION TESTS - Tool Workflows
# ==============================================================================

def test_workflow_explore_then_read(find_tool):
    """Test typical workflow: explore with metadata, then read specific symbols."""
    # Step 1: Explore the file structure with metadata (fast)
    result1_str = find_tool.apply(
        name_path="UserService",
        relative_path="example.py",
        output_format="metadata",
        depth=1  # Get methods too
    )
    result1 = json.loads(result1_str)

    # Should find class with methods
    assert len(result1["symbols"]) > 0
    symbol = result1["symbols"][0]
    assert "children" in symbol
    methods = symbol["children"]

    # Find authenticate method
    auth_method = next(m for m in methods if "authenticate" in m.get("name", ""))

    # Step 2: Read specific method signature (moderate)
    result2_str = find_tool.apply(
        name_path="UserService/authenticate",
        relative_path="example.py",
        output_format="signature"
    )
    result2 = json.loads(result2_str)

    # Should have signature and complexity
    symbol2 = result2["symbols"][0]
    assert "signature" in symbol2
    assert "complexity" in symbol2

    # Step 3: Read full implementation only if needed (expensive)
    result3_str = find_tool.apply(
        name_path="UserService/authenticate",
        relative_path="example.py",
        output_format="body"
    )
    result3 = json.loads(result3_str)

    # Should have full body
    symbol3 = result3["symbols"][0]
    assert "body" in symbol3
    assert "hashed = self._hash_password" in symbol3["body"]


# ==============================================================================
# 3. BACKWARD COMPATIBILITY TESTS - Old Params with Warnings
# ==============================================================================

def test_include_body_true_deprecated(find_tool):
    """Test that include_body=True still works but shows deprecation warning."""
    result_str = find_tool.apply(
        name_path="UserService",
        relative_path="example.py",
        include_body=True
    )
    result = json.loads(result_str)

    # Should still work - return body
    symbols = result["symbols"]
    assert len(symbols) > 0
    symbol = symbols[0]
    assert "body" in symbol

    # Should have deprecation warning
    assert "_deprecated" in result
    deprecations = result["_deprecated"]
    assert any(d["parameter"] == "include_body" for d in deprecations)

    # Check migration guidance
    include_body_dep = next(d for d in deprecations if d["parameter"] == "include_body")
    assert "output_format" in include_body_dep["replacement"]
    assert "2.0.0" in include_body_dep["removal_version"]


def test_include_body_false_deprecated(find_tool):
    """Test that include_body=False still works but shows deprecation warning."""
    result_str = find_tool.apply(
        name_path="UserService",
        relative_path="example.py",
        include_body=False
    )
    result = json.loads(result_str)

    # Should work - return metadata
    symbols = result["symbols"]
    assert len(symbols) > 0
    symbol = symbols[0]
    assert "body" not in symbol or symbol.get("body") is None

    # Should have deprecation warning
    assert "_deprecated" in result


def test_detail_level_signature_deprecated(find_tool):
    """Test that detail_level='signature' still works but shows deprecation warning."""
    result_str = find_tool.apply(
        name_path="UserService/authenticate",
        relative_path="example.py",
        detail_level="signature"
    )
    result = json.loads(result_str)

    # Should work - return signature
    symbols = result["symbols"]
    assert len(symbols) > 0
    symbol = symbols[0]
    assert "signature" in symbol
    assert "complexity" in symbol

    # Should have deprecation warning
    assert "_deprecated" in result
    deprecations = result["_deprecated"]
    assert any(d["parameter"] == "detail_level" for d in deprecations)


def test_detail_level_full_deprecated(find_tool):
    """Test that detail_level='full' still works but shows deprecation warning."""
    result_str = find_tool.apply(
        name_path="UserService",
        relative_path="example.py",
        detail_level="full"
    )
    result = json.loads(result_str)

    # Should work - behavior depends on include_body
    assert "_deprecated" in result


def test_combined_deprecated_params(find_tool):
    """Test that using both deprecated params shows both warnings."""
    result_str = find_tool.apply(
        name_path="UserService",
        relative_path="example.py",
        include_body=True,
        detail_level="full"
    )
    result = json.loads(result_str)

    # Should work
    symbols = result["symbols"]
    assert len(symbols) > 0

    # Should have both deprecation warnings
    assert "_deprecated" in result
    deprecations = result["_deprecated"]
    assert len(deprecations) >= 2
    param_names = [d["parameter"] for d in deprecations]
    assert "include_body" in param_names
    assert "detail_level" in param_names


# ==============================================================================
# 4. MIGRATION TESTS - Mapping from Old → New
# ==============================================================================

def test_migration_include_body_true_to_output_format_body(find_tool):
    """Test that include_body=True maps to output_format='body'."""
    # Old way
    result_old_str = find_tool.apply(
        name_path="UserService",
        relative_path="example.py",
        include_body=True
    )
    result_old = json.loads(result_old_str)

    # New way
    result_new_str = find_tool.apply(
        name_path="UserService",
        relative_path="example.py",
        output_format="body"
    )
    result_new = json.loads(result_new_str)

    # Results should be equivalent (minus deprecation warnings)
    assert len(result_old["symbols"]) == len(result_new["symbols"])

    # Both should have body
    assert "body" in result_old["symbols"][0]
    assert "body" in result_new["symbols"][0]

    # New way should NOT have deprecation warnings
    assert "_deprecated" not in result_new


def test_migration_include_body_false_to_output_format_metadata(find_tool):
    """Test that include_body=False maps to output_format='metadata'."""
    # Old way
    result_old_str = find_tool.apply(
        name_path="UserService",
        relative_path="example.py",
        include_body=False
    )
    result_old = json.loads(result_old_str)

    # New way (default)
    result_new_str = find_tool.apply(
        name_path="UserService",
        relative_path="example.py",
        output_format="metadata"
    )
    result_new = json.loads(result_new_str)

    # Results should be equivalent
    assert len(result_old["symbols"]) == len(result_new["symbols"])

    # Neither should have body
    assert "body" not in result_old["symbols"][0] or result_old["symbols"][0].get("body") is None
    assert "body" not in result_new["symbols"][0] or result_new["symbols"][0].get("body") is None


def test_migration_detail_level_signature(find_tool):
    """Test that detail_level='signature' maps to output_format='signature'."""
    # Old way
    result_old_str = find_tool.apply(
        name_path="UserService/authenticate",
        relative_path="example.py",
        detail_level="signature"
    )
    result_old = json.loads(result_old_str)

    # New way
    result_new_str = find_tool.apply(
        name_path="UserService/authenticate",
        relative_path="example.py",
        output_format="signature"
    )
    result_new = json.loads(result_new_str)

    # Results should be equivalent
    assert "signature" in result_old["symbols"][0]
    assert "signature" in result_new["symbols"][0]
    assert "complexity" in result_old["symbols"][0]
    assert "complexity" in result_new["symbols"][0]


# ==============================================================================
# 5. DOCUMENTATION TESTS - Examples Are Valid
# ==============================================================================

def test_docstring_example_default(find_tool):
    """Test the default example from docstring works."""
    # Example: find_symbol("UserService")
    result_str = find_tool.apply(name_path="UserService", relative_path="example.py")
    result = json.loads(result_str)

    assert len(result["symbols"]) > 0
    symbol = result["symbols"][0]
    assert "name" in symbol or "name_path" in symbol


def test_docstring_example_signature(find_tool):
    """Test the signature example from docstring works."""
    # Example: find_symbol("UserService/authenticate", output_format="signature")
    result_str = find_tool.apply(
        name_path="UserService/authenticate",
        relative_path="example.py",
        output_format="signature"
    )
    result = json.loads(result_str)

    assert len(result["symbols"]) > 0
    symbol = result["symbols"][0]
    assert "signature" in symbol
    assert "docstring" in symbol


def test_docstring_example_body(find_tool):
    """Test the body example from docstring works."""
    # Example: find_symbol("UserService/authenticate", output_format="body")
    result_str = find_tool.apply(
        name_path="UserService/authenticate",
        relative_path="example.py",
        output_format="body"
    )
    result = json.loads(result_str)

    assert len(result["symbols"]) > 0
    symbol = result["symbols"][0]
    assert "body" in symbol


# ==============================================================================
# ADDITIONAL TESTS
# ==============================================================================

def test_output_format_with_depth(find_tool):
    """Test that output_format works correctly with depth parameter."""
    result_str = find_tool.apply(
        name_path="UserService",
        relative_path="example.py",
        output_format="metadata",
        depth=1
    )
    result = json.loads(result_str)

    symbol = result["symbols"][0]
    assert "children" in symbol
    # Children should also not have body in metadata mode
    for child in symbol["children"]:
        assert "body" not in child or child.get("body") is None


def test_output_format_signature_without_body(find_tool):
    """Test that signature mode works even for symbols without docstrings."""
    result_str = find_tool.apply(
        name_path="standalone_function",
        relative_path="example.py",
        output_format="signature"
    )
    result = json.loads(result_str)

    assert len(result["symbols"]) > 0
    symbol = result["symbols"][0]

    # Should still have signature even if simple
    assert "signature" in symbol or "name" in symbol


def test_cache_with_output_format(find_tool):
    """Test that caching works with the new output_format parameter."""
    # First call - cache miss
    result1_str = find_tool.apply(
        name_path="UserService",
        relative_path="example.py",
        output_format="body"
    )
    result1 = json.loads(result1_str)

    # Second call - cache hit
    result2_str = find_tool.apply(
        name_path="UserService",
        relative_path="example.py",
        output_format="body"
    )
    result2 = json.loads(result2_str)

    # Results should be the same
    assert result1["symbols"] == result2["symbols"]

    # Second call should be cached
    if "_cache" in result2:
        assert result2["_cache"]["cache_status"] == "hit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
