"""Unit tests for onboarding helper functions."""

import pytest
from unittest.mock import Mock

from serena.tools.onboarding_helpers import (
    detect_tech_stack,
    find_command_files,
    detect_code_style,
    generate_commands_memory,
    generate_completion_checklist,
    read_json_safe,
    read_toml_safe,
    parse_makefile_targets,
)


class MockProject:
    """Mock Project class for testing."""

    def __init__(self, project_name="test_project", files=None, file_contents=None):
        self.project_name = project_name
        self.project_root = f"/path/to/{project_name}"
        self.language = "python"
        self._files = files or []
        self._file_contents = file_contents or {}

    def relative_path_exists(self, path: str) -> bool:
        return path in self._files

    def read_file(self, path: str) -> str:
        return self._file_contents.get(path, "")


class TestDetectTechStack:
    """Test tech stack detection."""

    def test_detect_nodejs_npm(self):
        """Test detecting Node.js with npm."""
        project = MockProject(files=["package.json"], file_contents={
            "package.json": '{"name": "test", "version": "1.0.0"}'
        })
        result = detect_tech_stack(project)
        assert "Node.js/npm" in result

    def test_detect_nodejs_with_react(self):
        """Test detecting Node.js with React framework."""
        project = MockProject(files=["package.json"], file_contents={
            "package.json": '{"dependencies": {"react": "^18.0.0"}}'
        })
        result = detect_tech_stack(project)
        assert "Node.js/npm" in result
        assert "React" in result

    def test_detect_nodejs_with_nextjs(self):
        """Test detecting Node.js with Next.js framework."""
        project = MockProject(files=["package.json"], file_contents={
            "package.json": '{"dependencies": {"next": "^13.0.0"}}'
        })
        result = detect_tech_stack(project)
        assert "Next.js" in result

    def test_detect_typescript(self):
        """Test detecting TypeScript."""
        project = MockProject(files=["package.json"], file_contents={
            "package.json": '{"devDependencies": {"typescript": "^5.0.0"}}'
        })
        result = detect_tech_stack(project)
        assert "TypeScript" in result

    def test_detect_python_poetry(self):
        """Test detecting Python with Poetry."""
        project = MockProject(files=["pyproject.toml"], file_contents={
            "pyproject.toml": '[tool.poetry]\nname = "test"\nversion = "0.1.0"'
        })
        result = detect_tech_stack(project)
        assert "Python" in result

    def test_detect_python_pip(self):
        """Test detecting Python with pip."""
        project = MockProject(files=["requirements.txt"])
        result = detect_tech_stack(project)
        assert "Python/pip" in result

    def test_detect_rust_cargo(self):
        """Test detecting Rust with Cargo."""
        project = MockProject(files=["Cargo.toml"])
        result = detect_tech_stack(project)
        assert "Rust/Cargo" in result

    def test_detect_go(self):
        """Test detecting Go."""
        project = MockProject(files=["go.mod"])
        result = detect_tech_stack(project)
        assert "Go" in result

    def test_detect_docker(self):
        """Test detecting Docker."""
        project = MockProject(files=["Dockerfile", "docker-compose.yml"])
        result = detect_tech_stack(project)
        assert "Docker" in result
        assert "Docker Compose" in result

    def test_detect_makefile(self):
        """Test detecting Make."""
        project = MockProject(files=["Makefile"])
        result = detect_tech_stack(project)
        assert "Make" in result

    def test_detect_unknown(self):
        """Test when no tech stack is detected."""
        project = MockProject(files=[])
        result = detect_tech_stack(project)
        assert result == "Unknown"


class TestFindCommandFiles:
    """Test command file detection."""

    def test_find_npm_scripts(self):
        """Test parsing npm scripts from package.json."""
        project = MockProject(files=["package.json"], file_contents={
            "package.json": '{"scripts": {"test": "jest", "build": "webpack"}}'
        })
        commands = find_command_files(project)
        assert "npm" in commands
        assert "test" in commands["npm"]
        assert commands["npm"]["test"] == "jest"

    def test_find_makefile_targets(self):
        """Test parsing Makefile targets."""
        makefile_content = """# Build the project
build:
\t@echo "Building..."

# Run tests
test:
\t@pytest
"""
        project = MockProject(files=["Makefile"], file_contents={
            "Makefile": makefile_content
        })
        commands = find_command_files(project)
        assert "make" in commands
        assert "build" in commands["make"]
        assert "test" in commands["make"]

    def test_find_cargo_commands(self):
        """Test finding Cargo commands."""
        project = MockProject(files=["Cargo.toml"])
        commands = find_command_files(project)
        assert "cargo" in commands
        assert "build" in commands["cargo"]
        assert "test" in commands["cargo"]

    def test_find_go_commands(self):
        """Test finding Go commands."""
        project = MockProject(files=["go.mod"])
        commands = find_command_files(project)
        assert "go" in commands
        assert "build" in commands["go"]
        assert "test" in commands["go"]

    def test_no_commands(self):
        """Test when no command files are found."""
        project = MockProject(files=[])
        commands = find_command_files(project)
        assert commands == {}


class TestDetectCodeStyle:
    """Test code style detection."""

    def test_detect_eslint(self):
        """Test detecting ESLint."""
        project = MockProject(files=[".eslintrc.json"])
        result = detect_code_style(project)
        assert "ESLint" in result

    def test_detect_prettier(self):
        """Test detecting Prettier."""
        project = MockProject(files=[".prettierrc"])
        result = detect_code_style(project)
        assert "Prettier" in result

    def test_detect_black_in_pyproject(self):
        """Test detecting Black in pyproject.toml."""
        project = MockProject(files=["pyproject.toml"], file_contents={
            "pyproject.toml": '[tool.black]\nline-length = 88'
        })
        result = detect_code_style(project)
        assert "Black" in result

    def test_detect_editorconfig(self):
        """Test detecting EditorConfig."""
        project = MockProject(files=[".editorconfig"])
        result = detect_code_style(project)
        assert "EditorConfig" in result

    def test_no_code_style(self):
        """Test when no code style is detected."""
        project = MockProject(files=[])
        result = detect_code_style(project)
        assert result == ""


class TestGenerateCommandsMemory:
    """Test commands memory generation."""

    def test_generate_with_npm_commands(self):
        """Test generating memory with npm commands."""
        commands = {"npm": {"test": "jest", "build": "webpack"}}
        project = MockProject()
        result = generate_commands_memory(commands, project)
        assert "npm Scripts" in result
        assert "npm run test" in result
        assert "npm run build" in result

    def test_generate_with_make_commands(self):
        """Test generating memory with make commands."""
        commands = {"make": {"build": "Build the project", "test": ""}}
        project = MockProject()
        result = generate_commands_memory(commands, project)
        assert "Make Targets" in result
        assert "make build" in result
        assert "Build the project" in result

    def test_generate_with_cargo_commands(self):
        """Test generating memory with Cargo commands."""
        commands = {"cargo": {"build": "Build the project"}}
        project = MockProject()
        result = generate_commands_memory(commands, project)
        assert "Cargo Commands" in result
        assert "cargo build" in result

    def test_generate_empty_commands(self):
        """Test generating memory with no commands."""
        commands = {}
        project = MockProject()
        result = generate_commands_memory(commands, project)
        assert "Common Development Commands" in result
        assert "git status" in result


class TestGenerateCompletionChecklist:
    """Test completion checklist generation."""

    def test_generate_with_npm_test(self):
        """Test generating checklist with npm test."""
        commands = {"npm": {"test": "jest"}}
        result = generate_completion_checklist(commands)
        assert "Tests pass" in result
        assert "`npm test`" in result

    def test_generate_with_cargo(self):
        """Test generating checklist with Cargo."""
        commands = {"cargo": {"build": "Build"}}
        result = generate_completion_checklist(commands)
        assert "Tests pass" in result
        assert "`cargo test`" in result
        assert "`cargo clippy`" in result

    def test_generate_with_npm_lint(self):
        """Test generating checklist with npm lint."""
        commands = {"npm": {"lint": "eslint"}}
        result = generate_completion_checklist(commands)
        assert "`npm run lint`" in result

    def test_generate_empty_commands(self):
        """Test generating checklist with no commands."""
        commands = {}
        result = generate_completion_checklist(commands)
        assert "Tests pass (if applicable)" in result
        assert "Code is properly formatted" in result
        assert "Git commit" in result


class TestHelperUtilities:
    """Test helper utility functions."""

    def test_read_json_safe_valid(self):
        """Test reading valid JSON."""
        project = MockProject(files=["test.json"], file_contents={
            "test.json": '{"key": "value"}'
        })
        result = read_json_safe(project, "test.json")
        assert result == {"key": "value"}

    def test_read_json_safe_invalid(self):
        """Test reading invalid JSON."""
        project = MockProject(files=["test.json"], file_contents={
            "test.json": '{invalid json'
        })
        result = read_json_safe(project, "test.json")
        assert result is None

    def test_read_json_safe_missing(self):
        """Test reading missing file."""
        project = MockProject(files=[])
        result = read_json_safe(project, "test.json")
        assert result is None

    def test_parse_makefile_targets(self):
        """Test parsing Makefile targets."""
        makefile = """# Build the project
build:
\t@echo "Building"

test:
\t@pytest

.PHONY: build test
"""
        project = MockProject(files=["Makefile"], file_contents={
            "Makefile": makefile
        })
        targets = parse_makefile_targets(project, "Makefile")
        assert "build" in targets
        assert targets["build"] == "Build the project"
        assert "test" in targets
        assert ".PHONY" not in targets  # Should skip special targets

    def test_parse_makefile_missing(self):
        """Test parsing missing Makefile."""
        project = MockProject(files=[])
        targets = parse_makefile_targets(project, "Makefile")
        assert targets == {}
