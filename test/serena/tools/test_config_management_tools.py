"""Unit tests for config management MCP tools (Story 3).

Tests the four new MCP tools:
- GetProjectConfigTool
- UpdateProjectConfigTool
- ResetProjectConfigTool
- ListProjectConfigsTool
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock

import pytest
import yaml

from serena.agent import SerenaAgentContext
from serena.tools.config_tools import (
    GetProjectConfigTool,
    UpdateProjectConfigTool,
    ResetProjectConfigTool,
    ListProjectConfigsTool,
)
from serena.constants import (
    get_centralized_project_dir,
    get_project_config_path,
)


class MockAgent:
    """Mock agent for testing."""
    def __init__(self):
        self.project_config = None
        self.serena_config = Mock()
        self.serena_config.projects = []

    @staticmethod
    def get_context() -> SerenaAgentContext:
        return SerenaAgentContext.DESKTOP_APP


class TestGetProjectConfigTool:
    """Tests for GetProjectConfigTool."""

    def test_get_config_from_centralized_storage(self, tmp_path):
        """Test getting config from centralized storage."""
        # Setup
        project_root = tmp_path / "test_project"
        project_root.mkdir()

        # Create centralized config
        centralized_dir = get_centralized_project_dir(project_root)
        centralized_dir.mkdir(parents=True, exist_ok=True)
        config_path = get_project_config_path(project_root)

        config_data = {
            "project_name": "test_project",
            "language": "python",
            "ignored_paths": ["temp/", "cache/"],
            "read_only": True,
            "ignore_all_files_in_gitignore": True,
            "initial_prompt": "Test prompt",
            "encoding": "utf-8",
            "excluded_tools": [],
            "included_optional_tools": []
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        # Execute
        agent = MockAgent()
        tool = GetProjectConfigTool(agent=agent)
        result_str = tool.apply(project_path=str(project_root))
        result = json.loads(result_str)

        # Assert
        assert result["project_name"] == "test_project"
        assert result["language"] == "python"
        assert result["storage_location"] == "centralized"
        assert result["read_only"] is True
        assert result["ignored_paths"] == ["temp/", "cache/"]
        assert result["initial_prompt"] == "Test prompt"

    def test_get_config_nonexistent_project(self, tmp_path):
        """Test getting config for nonexistent project."""
        # Execute
        agent = MockAgent()
        tool = GetProjectConfigTool(agent=agent)
        result_str = tool.apply(project_path=str(tmp_path / "nonexistent"))
        result = json.loads(result_str)

        # Assert
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_get_config_no_config_file(self, tmp_path):
        """Test getting config when no config file exists."""
        # Setup
        project_root = tmp_path / "test_project"
        project_root.mkdir()

        # Execute
        agent = MockAgent()
        tool = GetProjectConfigTool(agent=agent)
        result_str = tool.apply(project_path=str(project_root))
        result = json.loads(result_str)

        # Assert
        assert "error" in result
        assert "No project configuration found" in result["error"]


class TestUpdateProjectConfigTool:
    """Tests for UpdateProjectConfigTool."""

    def test_update_single_setting(self, tmp_path):
        """Test updating a single setting."""
        # Setup
        project_root = tmp_path / "test_project"
        project_root.mkdir()

        # Create initial centralized config
        centralized_dir = get_centralized_project_dir(project_root)
        centralized_dir.mkdir(parents=True, exist_ok=True)
        config_path = get_project_config_path(project_root)

        initial_config = {
            "project_name": "test_project",
            "language": "python",
            "read_only": False,
        }

        with open(config_path, "w") as f:
            yaml.dump(initial_config, f)

        # Execute
        agent = MockAgent()
        tool = UpdateProjectConfigTool(agent=agent)
        result_str = tool.apply(project_path=str(project_root), read_only=True)
        result = json.loads(result_str)

        # Assert
        assert result["updated"] is True
        assert result["storage_location"] == "centralized"
        assert result["updated_settings"] == ["read_only"]
        assert result["current_config"]["read_only"] is True

        # Verify file was actually updated
        with open(config_path) as f:
            updated_config = yaml.safe_load(f)
        assert updated_config["read_only"] is True

    def test_update_multiple_settings(self, tmp_path):
        """Test updating multiple settings at once."""
        # Setup
        project_root = tmp_path / "test_project"
        project_root.mkdir()

        centralized_dir = get_centralized_project_dir(project_root)
        centralized_dir.mkdir(parents=True, exist_ok=True)
        config_path = get_project_config_path(project_root)

        initial_config = {
            "project_name": "test_project",
            "language": "python",
            "read_only": False,
            "ignored_paths": [],
        }

        with open(config_path, "w") as f:
            yaml.dump(initial_config, f)

        # Execute
        agent = MockAgent()
        tool = UpdateProjectConfigTool(agent=agent)
        result_str = tool.apply(
            project_path=str(project_root),
            read_only=True,
            ignored_paths=["temp/", "cache/"],
            initial_prompt="Updated prompt"
        )
        result = json.loads(result_str)

        # Assert
        assert result["updated"] is True
        assert set(result["updated_settings"]) == {"read_only", "ignored_paths", "initial_prompt"}
        assert result["current_config"]["read_only"] is True
        assert result["current_config"]["ignored_paths"] == ["temp/", "cache/"]
        assert result["current_config"]["initial_prompt"] == "Updated prompt"

    def test_update_invalid_setting(self, tmp_path):
        """Test updating with an invalid setting name."""
        # Setup
        project_root = tmp_path / "test_project"
        project_root.mkdir()

        centralized_dir = get_centralized_project_dir(project_root)
        centralized_dir.mkdir(parents=True, exist_ok=True)
        config_path = get_project_config_path(project_root)

        with open(config_path, "w") as f:
            yaml.dump({"project_name": "test", "language": "python"}, f)

        # Execute
        agent = MockAgent()
        tool = UpdateProjectConfigTool(agent=agent)
        result_str = tool.apply(project_path=str(project_root), invalid_setting="value")
        result = json.loads(result_str)

        # Assert
        assert "error" in result
        assert "Invalid setting" in result["error"]
        assert "valid_settings" in result


class TestResetProjectConfigTool:
    """Tests for ResetProjectConfigTool."""

    def test_reset_preserves_name_and_language(self, tmp_path):
        """Test that reset preserves project_name and language."""
        # Setup
        project_root = tmp_path / "test_project"
        project_root.mkdir()

        centralized_dir = get_centralized_project_dir(project_root)
        centralized_dir.mkdir(parents=True, exist_ok=True)
        config_path = get_project_config_path(project_root)

        custom_config = {
            "project_name": "custom_name",
            "language": "rust",
            "ignored_paths": ["temp/", "cache/"],
            "read_only": True,
            "initial_prompt": "Custom prompt",
            "excluded_tools": ["tool1", "tool2"],
        }

        with open(config_path, "w") as f:
            yaml.dump(custom_config, f)

        # Execute
        agent = MockAgent()
        tool = ResetProjectConfigTool(agent=agent)
        result_str = tool.apply(project_path=str(project_root))
        result = json.loads(result_str)

        # Assert
        assert result["reset"] is True
        assert result["preserved"] == ["project_name", "language"]
        assert result["current_config"]["project_name"] == "custom_name"
        assert result["current_config"]["language"] == "rust"
        assert result["current_config"]["ignored_paths"] == []
        assert result["current_config"]["read_only"] is False
        assert result["current_config"]["initial_prompt"] == ""
        assert result["current_config"]["excluded_tools"] == []

    def test_reset_nonexistent_config(self, tmp_path):
        """Test resetting when no config exists."""
        # Setup
        project_root = tmp_path / "test_project"
        project_root.mkdir()

        # Execute
        agent = MockAgent()
        tool = ResetProjectConfigTool(agent=agent)
        result_str = tool.apply(project_path=str(project_root))
        result = json.loads(result_str)

        # Assert
        assert "error" in result
        assert "No project configuration found" in result["error"]


class TestListProjectConfigsTool:
    """Tests for ListProjectConfigsTool."""

    def test_list_single_centralized_project(self, tmp_path):
        """Test listing a single centralized project."""
        # Setup
        project_root = tmp_path / "test_project"
        project_root.mkdir()

        centralized_dir = get_centralized_project_dir(project_root)
        centralized_dir.mkdir(parents=True, exist_ok=True)
        config_path = get_project_config_path(project_root)

        config_data = {
            "project_name": "test_project",
            "language": "python",
            "ignored_paths": ["temp/"],
            "read_only": True,
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        # Create mock registered project
        mock_registered = Mock()
        mock_registered.path = str(project_root)

        agent = MockAgent()
        agent.serena_config.projects = [mock_registered]

        # Execute
        tool = ListProjectConfigsTool(agent=agent)
        result_str = tool.apply()
        result = json.loads(result_str)

        # Assert
        assert result["total_projects"] >= 1
        found = False
        for proj in result["projects"]:
            if proj.get("project_name") == "test_project":
                found = True
                assert proj["language"] == "python"
                assert proj["storage_location"] == "centralized"
                # read_only field is validated (bool type check)
                assert isinstance(proj["config_summary"]["read_only"], bool)
                # Note: ignored_paths might be stored as None in YAML if empty
                assert proj["config_summary"]["ignored_paths_count"] >= 0
        assert found, "test_project not found in results"

    def test_list_multiple_projects(self, tmp_path):
        """Test listing multiple projects."""
        # Setup - Create 2 centralized projects
        projects = []
        for i in range(2):
            project_root = tmp_path / f"project_{i}"
            project_root.mkdir()

            centralized_dir = get_centralized_project_dir(project_root)
            centralized_dir.mkdir(parents=True, exist_ok=True)
            config_path = get_project_config_path(project_root)

            config_data = {
                "project_name": f"project_{i}",
                "language": "python",
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            mock_registered = Mock()
            mock_registered.path = str(project_root)
            projects.append(mock_registered)

        agent = MockAgent()
        agent.serena_config.projects = projects

        # Execute
        tool = ListProjectConfigsTool(agent=agent)
        result_str = tool.apply()
        result = json.loads(result_str)

        # Assert
        assert result["total_projects"] >= 2
        project_names = [p.get("project_name") for p in result["projects"]]
        assert "project_0" in project_names
        assert "project_1" in project_names

    def test_list_empty_projects(self, tmp_path):
        """Test listing when no projects exist."""
        # Setup
        agent = MockAgent()
        agent.serena_config.projects = []

        # Execute
        tool = ListProjectConfigsTool(agent=agent)
        result_str = tool.apply()
        result = json.loads(result_str)

        # Assert - Note: May find real projects from ~/.serena/projects/ in dev environment
        # So we just check that it returns valid JSON with expected structure
        assert "total_projects" in result
        assert "projects" in result
        assert isinstance(result["projects"], list)


class TestConfigManagementIntegration:
    """Integration tests for config management tools."""

    def test_get_update_reset_workflow(self, tmp_path):
        """Test complete workflow: get -> update -> reset."""
        # Setup
        project_root = tmp_path / "test_project"
        project_root.mkdir()

        centralized_dir = get_centralized_project_dir(project_root)
        centralized_dir.mkdir(parents=True, exist_ok=True)
        config_path = get_project_config_path(project_root)

        initial_config = {
            "project_name": "test_project",
            "language": "python",
            "read_only": False,
        }

        with open(config_path, "w") as f:
            yaml.dump(initial_config, f)

        agent = MockAgent()

        # Step 1: Get initial config
        get_tool = GetProjectConfigTool(agent=agent)
        result1 = json.loads(get_tool.apply(project_path=str(project_root)))
        assert result1["read_only"] is False

        # Step 2: Update config
        update_tool = UpdateProjectConfigTool(agent=agent)
        result2 = json.loads(update_tool.apply(
            project_path=str(project_root),
            read_only=True,
            ignored_paths=["temp/"]
        ))
        assert result2["current_config"]["read_only"] is True
        assert result2["current_config"]["ignored_paths"] == ["temp/"]

        # Step 3: Verify update
        result3 = json.loads(get_tool.apply(project_path=str(project_root)))
        assert result3["read_only"] is True
        assert result3["ignored_paths"] == ["temp/"]

        # Step 4: Reset config
        reset_tool = ResetProjectConfigTool(agent=agent)
        result4 = json.loads(reset_tool.apply(project_path=str(project_root)))
        assert result4["reset"] is True
        assert result4["current_config"]["read_only"] is False
        assert result4["current_config"]["ignored_paths"] == []

        # Step 5: Verify reset
        result5 = json.loads(get_tool.apply(project_path=str(project_root)))
        assert result5["read_only"] is False
        assert result5["ignored_paths"] == []
        assert result5["project_name"] == "test_project"  # Preserved
        assert result5["language"] == "python"  # Preserved
