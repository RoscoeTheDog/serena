"""Test suite for context mode loading and deprecation handling.

This test suite verifies the changes made in Story 2:
- Load claude-code context successfully
- Load ide-assistant context with deprecation warning (backwards compatibility)
- Verify claude-code.yml contains all fork customizations
- Verify RegisteredContext enum includes CLAUDE_CODE
- Deprecation warning logged when using ide-assistant
"""

import logging
from pathlib import Path

import pytest

from serena.config.context_mode import RegisteredContext, SerenaAgentContext


class TestContextModeLoading:
    """Unit tests for context loading functionality."""

    def test_claude_code_context_loads(self):
        """Test that claude-code context loads successfully."""
        context = SerenaAgentContext.from_name("claude-code")

        assert context is not None
        assert context.name == "claude-code"
        assert context.description is not None
        assert len(context.excluded_tools) > 0

    def test_ide_assistant_context_loads_with_deprecation(self, caplog):
        """Test that ide-assistant context still loads (backwards compatibility)."""
        with caplog.at_level(logging.WARNING):
            context = SerenaAgentContext.from_name("ide-assistant")

        # Should successfully load claude-code context
        assert context is not None
        assert context.name == "claude-code"  # Redirected to claude-code

        # Should log deprecation warning
        assert any("deprecated" in record.message.lower() for record in caplog.records)
        assert any("ide-assistant" in record.message for record in caplog.records)
        assert any("claude-code" in record.message for record in caplog.records)

    def test_claude_code_enum_exists(self):
        """Test that RegisteredContext enum includes CLAUDE_CODE."""
        assert hasattr(RegisteredContext, "CLAUDE_CODE")
        assert RegisteredContext.CLAUDE_CODE.value == "claude-code"

    def test_ide_assistant_enum_exists_but_deprecated(self):
        """Test that RegisteredContext enum includes IDE_ASSISTANT (deprecated)."""
        assert hasattr(RegisteredContext, "IDE_ASSISTANT")
        assert RegisteredContext.IDE_ASSISTANT.value == "ide-assistant"

        # Verify deprecation notice - check if it's mentioned in the source
        # The docstring is attached to the enum value during class definition
        import inspect
        source = inspect.getsource(RegisteredContext)
        # Find the IDE_ASSISTANT line and the comment after it
        assert "IDE_ASSISTANT" in source
        assert "DEPRECATED" in source

    def test_claude_code_has_fork_customizations(self):
        """Test that claude-code.yml contains all fork customizations."""
        context = SerenaAgentContext.from_name("claude-code")

        # Verify excluded tools preserved from ide-assistant
        expected_excluded_tools = {
            "create_text_file",
            "read_file",
            "execute_shell_command",
            "prepare_for_new_conversation",
            "replace_regex",
        }
        assert expected_excluded_tools.issubset(set(context.excluded_tools))

        # Verify custom prompt exists and mentions symbolic tools
        assert context.prompt is not None
        assert len(context.prompt) > 0
        assert "symbolic" in context.prompt.lower() or "symbol" in context.prompt.lower()

    def test_claude_code_has_single_project_flag(self):
        """Test that claude-code.yml has single_project: true field in the YAML file."""
        import yaml
        from pathlib import Path
        from serena.config.context_mode import SERENAS_OWN_CONTEXT_YAMLS_DIR

        # Read the YAML file directly to check for single_project field
        claude_code_path = Path(SERENAS_OWN_CONTEXT_YAMLS_DIR) / "claude-code.yml"
        with open(claude_code_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Verify single_project field exists and is True
        assert "single_project" in data
        assert data["single_project"] is True


class TestContextModeIntegration:
    """Integration tests for context mode."""

    def test_enum_load_method_works(self):
        """Test that RegisteredContext enum's load() method works."""
        context = RegisteredContext.CLAUDE_CODE.load()

        assert context is not None
        assert context.name == "claude-code"

    def test_ide_assistant_enum_load_redirects(self, caplog):
        """Test that IDE_ASSISTANT enum load redirects to claude-code."""
        with caplog.at_level(logging.WARNING):
            context = RegisteredContext.IDE_ASSISTANT.load()

        # Should load claude-code context
        assert context.name == "claude-code"

        # Should log deprecation warning
        assert any("deprecated" in record.message.lower() for record in caplog.records)

    def test_context_list_includes_both_names(self):
        """Test that context listing includes both claude-code and ide-assistant."""
        context_names = SerenaAgentContext.list_registered_context_names(include_user_contexts=False)

        assert "claude-code" in context_names
        # ide-assistant.yml should still exist for backwards compatibility
        assert "ide-assistant" in context_names

    def test_context_files_exist(self):
        """Test that both context YAML files exist."""
        from serena.config.context_mode import SERENAS_OWN_CONTEXT_YAMLS_DIR

        claude_code_path = Path(SERENAS_OWN_CONTEXT_YAMLS_DIR) / "claude-code.yml"
        ide_assistant_path = Path(SERENAS_OWN_CONTEXT_YAMLS_DIR) / "ide-assistant.yml"

        assert claude_code_path.exists(), "claude-code.yml should exist"
        assert ide_assistant_path.exists(), "ide-assistant.yml should exist for backwards compatibility"


class TestContextModeSecurity:
    """Security tests for context mode."""

    def test_no_security_tools_accidentally_enabled(self):
        """Test that no security-critical tools were accidentally enabled."""
        context = SerenaAgentContext.from_name("claude-code")

        # These tools should remain excluded for security
        dangerous_tools = {
            "execute_shell_command",
            "create_text_file",  # Prevents arbitrary file creation
            "replace_regex",     # Prevents uncontrolled regex operations
        }

        for tool in dangerous_tools:
            assert tool in context.excluded_tools, f"{tool} should remain excluded"

    def test_excluded_tools_list_preserved_exactly(self):
        """Test that excluded_tools list is preserved exactly from ide-assistant to claude-code."""
        # Load both contexts
        claude_code = SerenaAgentContext.from_name("claude-code")
        ide_assistant_raw = SerenaAgentContext.from_yaml(
            SerenaAgentContext.get_path("ide-assistant")
        )

        # Excluded tools should be identical
        assert set(claude_code.excluded_tools) == set(ide_assistant_raw.excluded_tools)


class TestDeprecationWarningContent:
    """Test the specific content of deprecation warnings."""

    def test_deprecation_message_format(self, caplog):
        """Test that deprecation warning has helpful message."""
        with caplog.at_level(logging.WARNING):
            SerenaAgentContext.from_name("ide-assistant")

        warning_messages = [record.message for record in caplog.records if record.levelno == logging.WARNING]
        assert len(warning_messages) > 0

        warning = warning_messages[0]
        # Should mention both old and new names
        assert "ide-assistant" in warning
        assert "claude-code" in warning
        # Should suggest what to do
        assert "use" in warning.lower() or "please" in warning.lower()
        # Should mention backwards compatibility
        assert "backwards compatibility" in warning or "automatically redirecting" in warning.lower()


# Test metadata
__test_story__ = "2"
__test_phase__ = "testing"
__test_categories__ = ["unit", "integration", "security"]
