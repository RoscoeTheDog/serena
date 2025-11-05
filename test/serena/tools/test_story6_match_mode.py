"""
Story 6 Tests: Unify substring_matching into match_mode

Tests for the new match_mode parameter that replaces substring_matching
and adds glob and regex matching capabilities.

Test Categories:
1. Unit tests - New match_mode parameter behavior
2. Integration tests - Tool workflows with all match modes
3. Backward compatibility tests - substring_matching still works with warnings
4. Migration tests - Mapping from old → new
5. Performance tests - Verify performance hints for slow modes
6. Edge cases - Invalid regex, complex patterns
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
        # Create Python files with various naming patterns
        test_file1 = Path(tmpdir) / "services.py"
        test_file1.write_text('''
"""Services module for testing match modes."""

class UserService:
    """Service for user management."""

    def authenticate(self, username: str) -> bool:
        """Authenticate user."""
        return True

class UserAuthService:
    """Extended authentication service."""

    def authenticate_with_2fa(self, username: str) -> bool:
        """Authenticate with 2FA."""
        return True

class UserApiService:
    """API service for users."""

    def get_user(self, user_id: int):
        """Get user by ID."""
        return None

class AdminService:
    """Admin management service."""

    def create_user(self):
        """Create new user."""
        pass

class ServiceManager:
    """Manager for all services."""

    def register_service(self, service):
        """Register a service."""
        pass

def setup_service():
    """Setup services."""
    pass

def service_factory():
    """Factory for creating services."""
    pass
''')

        test_file2 = Path(tmpdir) / "helpers.py"
        test_file2.write_text('''
"""Helper functions."""

def user_helper():
    """Helper for users."""
    pass

def admin_helper():
    """Helper for admins."""
    pass

class UserValidator:
    """Validator for user data."""
    pass

class User1Validator:
    """Validator for specific user type."""
    pass

class User2Validator:
    """Another user validator."""
    pass
''')

        # Create project and agent
        project = Project(project_root=tmpdir)
        agent = SerenaAgent(project, create_global_server=False)

        yield tmpdir, project, agent


# ===== Unit Tests: New match_mode Parameter =====

def test_match_mode_exact_default(temp_project):
    """Test that exact matching is the default mode."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # Search for "UserService" - should find only exact match
    result = json.loads(tool.apply(
        name_path="UserService",
        relative_path="services.py",
        output_format="metadata"
    ))

    symbols = result.get("symbols", [])
    assert len(symbols) == 1
    assert symbols[0]["name_path"] == "UserService"


def test_match_mode_exact_explicit(temp_project):
    """Test explicit exact match mode."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    result = json.loads(tool.apply(
        name_path="UserService",
        relative_path="services.py",
        match_mode="exact"
    ))

    symbols = result.get("symbols", [])
    assert len(symbols) == 1
    assert symbols[0]["name_path"] == "UserService"


def test_match_mode_substring(temp_project):
    """Test substring matching mode."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # Search for "Service" - should find all classes with "Service" in name
    result = json.loads(tool.apply(
        name_path="Service",
        relative_path="services.py",
        match_mode="substring"
    ))

    symbols = result.get("symbols", [])
    symbol_names = [s["name_path"] for s in symbols]

    # Should match UserService, UserAuthService, UserApiService, AdminService, ServiceManager
    assert "UserService" in symbol_names
    assert "UserAuthService" in symbol_names
    assert "UserApiService" in symbol_names
    assert "AdminService" in symbol_names
    assert "ServiceManager" in symbol_names
    assert len(symbols) >= 5


def test_match_mode_glob_asterisk(temp_project):
    """Test glob matching with asterisk wildcard."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # Search for "User*Service" - should match UserService, UserAuthService, UserApiService
    result = json.loads(tool.apply(
        name_path="User*Service",
        relative_path="services.py",
        match_mode="glob"
    ))

    symbols = result.get("symbols", [])
    symbol_names = [s["name_path"] for s in symbols]

    assert "UserService" in symbol_names
    assert "UserAuthService" in symbol_names
    assert "UserApiService" in symbol_names
    # Should NOT match AdminService or ServiceManager
    assert "AdminService" not in symbol_names
    assert "ServiceManager" not in symbol_names


def test_match_mode_glob_question_mark(temp_project):
    """Test glob matching with question mark wildcard."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # Search for "User?Validator" - should match User1Validator, User2Validator
    result = json.loads(tool.apply(
        name_path="User?Validator",
        relative_path="helpers.py",
        match_mode="glob"
    ))

    symbols = result.get("symbols", [])
    symbol_names = [s["name_path"] for s in symbols]

    assert "User1Validator" in symbol_names
    assert "User2Validator" in symbol_names
    # Should NOT match UserValidator (no character between User and Validator)
    assert "UserValidator" not in symbol_names


def test_match_mode_regex_simple(temp_project):
    """Test regex matching with simple pattern."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # Search for "User.*Service" - should match all User...Service classes
    result = json.loads(tool.apply(
        name_path="User.*Service",
        relative_path="services.py",
        match_mode="regex"
    ))

    symbols = result.get("symbols", [])
    symbol_names = [s["name_path"] for s in symbols]

    assert "UserService" in symbol_names
    assert "UserAuthService" in symbol_names
    assert "UserApiService" in symbol_names


def test_match_mode_regex_complex(temp_project):
    """Test regex matching with complex pattern."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # Search for "User[A-Z]+Service" - should match UserAuthService, UserApiService but not UserService
    result = json.loads(tool.apply(
        name_path="User[A-Z][a-z]+Service",
        relative_path="services.py",
        match_mode="regex"
    ))

    symbols = result.get("symbols", [])
    symbol_names = [s["name_path"] for s in symbols]

    assert "UserAuthService" in symbol_names
    assert "UserApiService" in symbol_names
    # UserService doesn't have capital letters between User and Service
    assert "UserService" not in symbol_names


# ===== Backward Compatibility Tests =====

def test_backward_compat_substring_matching_true(temp_project):
    """Test that substring_matching=True still works and shows deprecation."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    result = json.loads(tool.apply(
        name_path="Service",
        relative_path="services.py",
        substring_matching=True
    ))

    # Should find matches
    symbols = result.get("symbols", [])
    assert len(symbols) >= 5

    # Should have deprecation warning
    deprecated = result.get("_deprecated")
    assert deprecated is not None
    assert any(d["parameter"] == "substring_matching" for d in deprecated)

    # Check migration guidance
    substring_dep = next(d for d in deprecated if d["parameter"] == "substring_matching")
    assert "match_mode='substring'" in substring_dep["migration"]
    assert substring_dep["removal_version"] == "2.0.0"


def test_backward_compat_substring_matching_false(temp_project):
    """Test that substring_matching=False still works (exact mode)."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    result = json.loads(tool.apply(
        name_path="UserService",
        relative_path="services.py",
        substring_matching=False
    ))

    symbols = result.get("symbols", [])
    assert len(symbols) == 1
    assert symbols[0]["name_path"] == "UserService"

    # Should have deprecation warning
    deprecated = result.get("_deprecated")
    assert deprecated is not None
    assert any(d["parameter"] == "substring_matching" for d in deprecated)


def test_backward_compat_parameter_priority(temp_project):
    """Test that substring_matching takes precedence over match_mode for backward compat."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # substring_matching=True should override match_mode="exact"
    result = json.loads(tool.apply(
        name_path="Service",
        relative_path="services.py",
        substring_matching=True,
        match_mode="exact"
    ))

    symbols = result.get("symbols", [])
    # Should use substring matching (many results), not exact (0 results)
    assert len(symbols) >= 5


# ===== Performance Tests =====

def test_performance_hint_glob(temp_project):
    """Test that glob mode includes performance hint."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    result = json.loads(tool.apply(
        name_path="User*Service",
        relative_path="services.py",
        match_mode="glob"
    ))

    # Should have performance hint
    performance_hint = result.get("_performance_hint")
    assert performance_hint is not None
    assert "glob" in performance_hint.lower() or "moderately fast" in performance_hint.lower()


def test_performance_hint_regex(temp_project):
    """Test that regex mode includes performance hint."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    result = json.loads(tool.apply(
        name_path="User.*Service",
        relative_path="services.py",
        match_mode="regex"
    ))

    # Should have performance hint
    performance_hint = result.get("_performance_hint")
    assert performance_hint is not None
    assert "regex" in performance_hint.lower() or "slower" in performance_hint.lower()


def test_no_performance_hint_exact(temp_project):
    """Test that exact mode does NOT include performance hint."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    result = json.loads(tool.apply(
        name_path="UserService",
        relative_path="services.py",
        match_mode="exact"
    ))

    # Should NOT have performance hint (exact is already optimal)
    performance_hint = result.get("_performance_hint")
    assert performance_hint is None


# ===== Edge Cases =====

def test_invalid_regex_pattern(temp_project):
    """Test that invalid regex patterns return helpful error."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # Invalid regex: unmatched bracket
    result = json.loads(tool.apply(
        name_path="User[Service",
        relative_path="services.py",
        match_mode="regex"
    ))

    # Should return error
    assert "error" in result
    assert result["error"] == "Invalid regex pattern"
    assert "User[Service" in result["pattern"]
    assert "suggestion" in result


def test_match_mode_with_depth(temp_project):
    """Test that match_mode works correctly with depth parameter."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # Search for classes matching User* and get their methods
    result = json.loads(tool.apply(
        name_path="User*",
        relative_path="services.py",
        match_mode="glob",
        depth=1
    ))

    symbols = result.get("symbols", [])
    # Should find UserService, UserAuthService, UserApiService
    user_service_symbols = [s for s in symbols if "UserService" in s["name_path"] and "/" not in s["name_path"]]
    assert len(user_service_symbols) >= 3

    # At least one should have children (methods)
    has_children = any("children" in s and s["children"] for s in symbols)
    assert has_children


def test_glob_no_match(temp_project):
    """Test glob pattern that matches nothing."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    result = json.loads(tool.apply(
        name_path="Nonexistent*Pattern",
        relative_path="services.py",
        match_mode="glob"
    ))

    symbols = result.get("symbols", [])
    assert len(symbols) == 0


def test_regex_case_sensitive(temp_project):
    """Test that regex matching is case-sensitive."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # Lowercase pattern should not match capitalized symbols
    result = json.loads(tool.apply(
        name_path="user.*service",
        relative_path="services.py",
        match_mode="regex"
    ))

    symbols = result.get("symbols", [])
    # Should not find UserService (case mismatch)
    assert len(symbols) == 0


def test_glob_with_functions(temp_project):
    """Test glob matching with functions."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # Match functions starting with "service"
    result = json.loads(tool.apply(
        name_path="service*",
        relative_path="services.py",
        match_mode="glob"
    ))

    symbols = result.get("symbols", [])
    symbol_names = [s["name_path"] for s in symbols]

    # Should match service_factory
    assert "service_factory" in symbol_names


# ===== Integration Tests =====

def test_match_mode_with_output_format_body(temp_project):
    """Test match_mode with output_format='body'."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    result = json.loads(tool.apply(
        name_path="User*Service",
        relative_path="services.py",
        match_mode="glob",
        output_format="body"
    ))

    symbols = result.get("symbols", [])
    # Should have body for each symbol
    for symbol in symbols:
        assert "body" in symbol
        assert len(symbol["body"]) > 0


def test_match_mode_with_include_kinds(temp_project):
    """Test match_mode with kind filtering."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # Search for symbols with "service" using substring mode, but only functions (kind 12)
    result = json.loads(tool.apply(
        name_path="service",
        relative_path="services.py",
        match_mode="substring",
        include_kinds=[12]  # Function kind
    ))

    symbols = result.get("symbols", [])
    symbol_names = [s["name_path"] for s in symbols]

    # Should match functions with "service" in name
    assert "setup_service" in symbol_names
    assert "service_factory" in symbol_names

    # Should NOT match classes even if they have "service" in name
    assert "UserService" not in symbol_names
    assert "AdminService" not in symbol_names


def test_migration_example_from_docstring(temp_project):
    """Test the migration examples from docstring work correctly."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # OLD way (deprecated)
    old_result = json.loads(tool.apply(
        name_path="Service",
        relative_path="services.py",
        substring_matching=True
    ))

    # NEW way (recommended)
    new_result = json.loads(tool.apply(
        name_path="Service",
        relative_path="services.py",
        match_mode="substring"
    ))

    # Should have same symbols (excluding deprecation warning)
    old_symbols = old_result.get("symbols", [])
    new_symbols = new_result.get("symbols", [])

    old_names = sorted([s["name_path"] for s in old_symbols])
    new_names = sorted([s["name_path"] for s in new_symbols])

    assert old_names == new_names


# ===== Documentation Tests =====

def test_docstring_example_exact(temp_project):
    """Test the exact match example from docstring."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # Example: find_symbol("UserService")  # Only matches "UserService"
    result = json.loads(tool.apply(
        name_path="UserService",
        relative_path="services.py"
    ))

    symbols = result.get("symbols", [])
    assert len(symbols) == 1
    assert symbols[0]["name_path"] == "UserService"


def test_docstring_example_substring(temp_project):
    """Test the substring match example from docstring."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # Example: find_symbol("Service", match_mode="substring")
    # Should match UserService, AuthService, etc.
    result = json.loads(tool.apply(
        name_path="Service",
        relative_path="services.py",
        match_mode="substring"
    ))

    symbols = result.get("symbols", [])
    symbol_names = [s["name_path"] for s in symbols]

    assert "UserService" in symbol_names
    assert "AdminService" in symbol_names


def test_docstring_example_glob(temp_project):
    """Test the glob pattern example from docstring."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # Example: find_symbol("User*Service", match_mode="glob")
    # Should match UserAuthService, UserApiService, etc.
    result = json.loads(tool.apply(
        name_path="User*Service",
        relative_path="services.py",
        match_mode="glob"
    ))

    symbols = result.get("symbols", [])
    symbol_names = [s["name_path"] for s in symbols]

    assert "UserAuthService" in symbol_names
    assert "UserApiService" in symbol_names


def test_docstring_example_regex(temp_project):
    """Test the regex pattern example from docstring."""
    tmpdir, project, agent = temp_project
    tool = FindSymbolTool(agent)

    # Example: find_symbol("User.*Service", match_mode="regex")
    result = json.loads(tool.apply(
        name_path="User.*Service",
        relative_path="services.py",
        match_mode="regex"
    ))

    symbols = result.get("symbols", [])
    symbol_names = [s["name_path"] for s in symbols]

    assert "UserAuthService" in symbol_names
    assert "UserApiService" in symbol_names
