"""Integration tests for auto-onboarding workflow.

Tests the complete flow of ActivateProjectTool with auto-onboarding.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from serena.project import Project
from serena.tools.config_tools import ActivateProjectTool
from serena.tools.memory_tools import ListMemoriesTool
from serena.agent import SerenaAgent, SerenaAgentContext


class MockAgent:
    """Mock agent for testing."""
    def __init__(self, project_root=None):
        self.project_config = None
        self.serena_config = None
        self._tools = {}
        self.project = None
        self.active_project = None
        self.memories_manager = None
        self._project_root = project_root

    @staticmethod
    def get_context() -> SerenaAgentContext:
        return SerenaAgentContext.DESKTOP_APP

    def get_tool(self, tool_class):
        """Get a tool instance by class."""
        return self._tools.get(tool_class)

    def register_tool(self, tool_class, tool_instance):
        """Register a mock tool for testing."""
        self._tools[tool_class] = tool_instance

    def activate_project_from_path_or_name(self, project_path: str) -> Project:
        """Activate a project from path."""
        from serena.agent import MemoriesManager

        # Load the project using Project.load()
        self.active_project = Project.load(project_path, autogenerate=True)
        self.project = self.active_project
        self._project_root = project_path

        # Initialize memories manager for this project
        self.memories_manager = MemoriesManager(project_root=project_path)

        return self.active_project

    def get_active_tool_names(self) -> list:
        """Get list of active tool names."""
        return [tool_class.__name__ for tool_class in self._tools.keys()]


class TestAutoOnboardingIntegration:
    """Integration tests for auto-onboarding during project activation."""

    def test_auto_onboard_new_nodejs_project(self, tmp_path):
        """Test that activating a new Node.js project creates onboarding memories automatically."""
        # Create a temp Node.js project
        project_dir = tmp_path / "test_nodejs_project"
        project_dir.mkdir()

        # Create package.json with scripts
        package_json = project_dir / "package.json"
        package_json.write_text('''{
  "name": "test-project",
  "version": "1.0.0",
  "scripts": {
    "start": "node index.js",
    "test": "jest",
    "build": "webpack"
  },
  "dependencies": {
    "react": "^18.2.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "jest": "^29.0.0"
  }
}''')

        # Create .eslintrc.json for code style detection
        eslintrc = project_dir / ".eslintrc.json"
        eslintrc.write_text('{"extends": "eslint:recommended"}')

        # Create a source file so autogenerate can detect the language
        index_js = project_dir / "index.js"
        index_js.write_text('console.log("Hello World");')

        # Create a git repo (auto-onboarding requires git repo)
        import subprocess
        subprocess.run(["git", "init"], cwd=str(project_dir), capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(project_dir), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(project_dir), capture_output=True)

        # Mock the WriteMemoryTool to capture what memories are created
        created_memories = []

        class MockWriteMemoryTool:
            def apply(self, memory_name, content, max_answer_chars=-1):
                created_memories.append({
                    "name": memory_name,
                    "content": content
                })
                return f"Memory '{memory_name}' created successfully."

        class MockListMemoriesTool:
            def apply(self, include_metadata=True):
                # Return empty list to trigger auto-onboarding
                return json.dumps([])

        # Set up agent with mock tools
        from serena.tools.memory_tools import WriteMemoryTool, ListMemoriesTool
        agent = MockAgent()
        agent.register_tool(WriteMemoryTool, MockWriteMemoryTool())
        agent.register_tool(ListMemoriesTool, MockListMemoriesTool())

        # Activate the project
        activate_tool = ActivateProjectTool(agent)
        result = activate_tool.apply(project=str(project_dir))

        # Assertions
        assert "activated" in result.lower()

        # Should have created 3-4 memories
        assert len(created_memories) >= 3, f"Expected at least 3 memories, got {len(created_memories)}"

        # Check memory names
        memory_names = [m["name"] for m in created_memories]
        assert any("tech_stack" in name.lower() for name in memory_names), "Missing tech stack memory"
        assert any("command" in name.lower() for name in memory_names), "Missing commands memory"
        assert any("checklist" in name.lower() or "completion" in name.lower() for name in memory_names), "Missing checklist memory"

        # Verify tech stack memory content
        tech_stack_memory = next(m for m in created_memories if "tech_stack" in m["name"].lower())
        content = tech_stack_memory["content"]
        assert "Node.js" in content or "npm" in content, "Tech stack should mention Node.js/npm"
        assert "React" in content, "Tech stack should detect React"
        assert "TypeScript" in content, "Tech stack should detect TypeScript"

        # Verify commands memory content
        commands_memory = next(m for m in created_memories if "command" in m["name"].lower())
        content = commands_memory["content"]
        assert "npm run start" in content or "npm start" in content, "Commands should include start script"
        assert "npm test" in content or "npm run test" in content, "Commands should include test script"
        assert "npm run build" in content, "Commands should include build script"

        # Verify code style memory if created
        if any("code_style" in name.lower() for name in memory_names):
            code_style_memory = next(m for m in created_memories if "code_style" in m["name"].lower())
            content = code_style_memory["content"]
            assert "ESLint" in content, "Code style should mention ESLint"

    def test_skip_onboarding_for_existing_project(self, tmp_path):
        """Test that activating an already-onboarded project skips auto-onboarding."""
        # Create a temp project
        project_dir = tmp_path / "existing_project"
        project_dir.mkdir()

        # Create package.json
        package_json = project_dir / "package.json"
        package_json.write_text('{"name": "existing", "version": "1.0.0"}')

        # Create a source file
        index_js = project_dir / "index.js"
        index_js.write_text('console.log("Hello");')

        # Create git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=str(project_dir), capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(project_dir), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(project_dir), capture_output=True)

        # Create .serena directory with existing onboarding memories
        serena_dir = project_dir / ".serena" / "memories"
        serena_dir.mkdir(parents=True)

        # Create a tech stack memory to simulate existing onboarding
        tech_stack_memory = serena_dir / "tech_stack_and_structure.md"
        tech_stack_memory.write_text("# Tech Stack\n\nNode.js/npm")

        # Mock WriteMemoryTool to verify no new memories are created
        created_memories = []

        def mock_write_memory(memory_name, content, max_answer_chars=-1):
            created_memories.append({
                "name": memory_name,
                "content": content
            })
            return f"Memory '{memory_name}' created successfully."

        # Activate the project
        activate_tool = ActivateProjectTool(MockAgent())

        with patch.object(activate_tool.write_memory_tool, 'apply', side_effect=mock_write_memory):
            result = activate_tool.apply(project=str(project_dir))

        # Assertions
        assert "activated" in result.lower()

        # Should NOT have created onboarding memories (already exists)
        # Note: There might be 0 memories created, or the result might mention "already onboarded"
        assert len(created_memories) == 0 or "already" in result.lower(), \
            f"Should not auto-onboard existing project, but created {len(created_memories)} memories"

    def test_auto_onboard_python_poetry_project(self, tmp_path):
        """Test auto-onboarding a Python Poetry project."""
        # Create a temp Python project
        project_dir = tmp_path / "test_python_project"
        project_dir.mkdir()

        # Create pyproject.toml with Poetry config
        pyproject_toml = project_dir / "pyproject.toml"
        pyproject_toml.write_text('''[tool.poetry]
name = "test-project"
version = "0.1.0"
description = "Test project"

[tool.poetry.dependencies]
python = "^3.11"
requests = "^2.31.0"

[tool.poetry.scripts]
start = "test_project.main:main"
test = "pytest tests/"

[tool.black]
line-length = 100

[tool.ruff]
line-length = 100
''')

        # Create a Python source file
        main_py = project_dir / "main.py"
        main_py.write_text('print("Hello World")')

        # Create git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=str(project_dir), capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(project_dir), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(project_dir), capture_output=True)

        # Mock WriteMemoryTool
        created_memories = []

        def mock_write_memory(memory_name, content, max_answer_chars=-1):
            created_memories.append({
                "name": memory_name,
                "content": content
            })
            return f"Memory '{memory_name}' created successfully."

        # Activate the project
        activate_tool = ActivateProjectTool(MockAgent())

        with patch.object(activate_tool.write_memory_tool, 'apply', side_effect=mock_write_memory):
            result = activate_tool.apply(project=str(project_dir))

        # Assertions
        assert "activated" in result.lower()
        assert len(created_memories) >= 3

        # Verify tech stack detects Python/Poetry
        tech_stack_memory = next(m for m in created_memories if "tech_stack" in m["name"].lower())
        content = tech_stack_memory["content"]
        assert "Python" in content, "Should detect Python"
        assert "Poetry" in content or "pyproject.toml" in content, "Should detect Poetry"

        # Verify commands memory
        commands_memory = next(m for m in created_memories if "command" in m["name"].lower())
        content = commands_memory["content"]
        assert "poetry" in content.lower(), "Commands should mention poetry"

        # Verify code style memory mentions Black and Ruff
        if any("code_style" in name.lower() for name in [m["name"] for m in created_memories]):
            code_style_memory = next(m for m in created_memories if "code_style" in m["name"].lower())
            content = code_style_memory["content"]
            assert "Black" in content or "black" in content, "Should detect Black"
            assert "Ruff" in content or "ruff" in content, "Should detect Ruff"

    def test_graceful_handling_of_malformed_json(self, tmp_path):
        """Test that malformed package.json doesn't crash auto-onboarding."""
        # Create a temp project with malformed JSON
        project_dir = tmp_path / "malformed_json_project"
        project_dir.mkdir()

        # Create malformed package.json
        package_json = project_dir / "package.json"
        package_json.write_text('{"name": "test", "version": 1.0.0}')  # Missing quotes around version

        # Create a source file
        index_js = project_dir / "index.js"
        index_js.write_text('console.log("test");')

        # Create git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=str(project_dir), capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(project_dir), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(project_dir), capture_output=True)

        # Mock WriteMemoryTool
        created_memories = []

        def mock_write_memory(memory_name, content, max_answer_chars=-1):
            created_memories.append({
                "name": memory_name,
                "content": content
            })
            return f"Memory '{memory_name}' created successfully."

        # Activate the project - should not crash
        activate_tool = ActivateProjectTool(MockAgent())

        with patch.object(activate_tool.write_memory_tool, 'apply', side_effect=mock_write_memory):
            result = activate_tool.apply(project=str(project_dir))

        # Assertions
        assert "activated" in result.lower(), "Activation should succeed despite malformed JSON"
        # May or may not create memories depending on fallback behavior
        # But importantly, it should not crash

    def test_minimal_project_with_no_config_files(self, tmp_path):
        """Test auto-onboarding a project with no recognizable config files."""
        # Create a minimal project
        project_dir = tmp_path / "minimal_project"
        project_dir.mkdir()

        # Create just a README
        readme = project_dir / "README.md"
        readme.write_text("# Minimal Project")

        # Create a minimal source file so autogenerate can detect a language
        script_sh = project_dir / "script.sh"
        script_sh.write_text('#!/bin/bash\necho "Hello"')

        # Create git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=str(project_dir), capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(project_dir), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(project_dir), capture_output=True)

        # Mock WriteMemoryTool
        created_memories = []

        def mock_write_memory(memory_name, content, max_answer_chars=-1):
            created_memories.append({
                "name": memory_name,
                "content": content
            })
            return f"Memory '{memory_name}' created successfully."

        # Activate the project
        activate_tool = ActivateProjectTool(MockAgent())

        with patch.object(activate_tool.write_memory_tool, 'apply', side_effect=mock_write_memory):
            result = activate_tool.apply(project=str(project_dir))

        # Assertions
        assert "activated" in result.lower()
        # Should still create basic memories (even if tech stack is "Unknown")
        # The system should gracefully handle the lack of config files
        # Either creates minimal memories or skips onboarding gracefully
        # Main point: no crash, successful activation
