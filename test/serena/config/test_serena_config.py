import shutil
import tempfile
from pathlib import Path

import pytest

from serena.config.serena_config import ProjectConfig
from solidlsp.ls_config import Language


class TestProjectConfigAutogenerate:
    """Test class for ProjectConfig autogeneration functionality."""

    def setup_method(self):
        """Set up test environment before each test method."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.project_path = Path(self.test_dir)

    def teardown_method(self):
        """Clean up test environment after each test method."""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    def test_autogenerate_empty_directory(self):
        """Test that autogenerate raises ValueError with helpful message for empty directory."""
        with pytest.raises(ValueError) as exc_info:
            ProjectConfig.autogenerate(self.project_path, save_to_disk=False)

        error_message = str(exc_info.value)
        # Check that the error message contains all the key information
        assert "No source files found" in error_message
        assert str(self.project_path.resolve()) in error_message
        assert "To use Serena with this project" in error_message
        assert "Add source files in one of the supported languages" in error_message
        assert "Create a project configuration file manually" in error_message
        # Check that it mentions the centralized config path (contains .serena/projects/)
        assert ".serena" in error_message and "projects" in error_message
        assert "project.yml" in error_message
        assert "Example project.yml:" in error_message
        assert f"project_name: {self.project_path.name}" in error_message
        assert "language: python" in error_message

    def test_autogenerate_with_python_files(self):
        """Test successful autogeneration with Python source files."""
        # Create a Python file
        python_file = self.project_path / "main.py"
        python_file.write_text("def hello():\n    print('Hello, world!')\n")

        # Run autogenerate
        config = ProjectConfig.autogenerate(self.project_path, save_to_disk=False)

        # Verify the configuration
        assert config.project_name == self.project_path.name
        assert config.language == Language.PYTHON

    def test_autogenerate_with_multiple_languages(self):
        """Test autogeneration picks dominant language when multiple are present."""
        # Create files for multiple languages
        (self.project_path / "main.py").write_text("print('Python')")
        (self.project_path / "util.py").write_text("def util(): pass")
        (self.project_path / "small.js").write_text("console.log('JS');")

        # Run autogenerate - should pick Python as dominant
        config = ProjectConfig.autogenerate(self.project_path, save_to_disk=False)

        assert config.language == Language.PYTHON

    def test_autogenerate_saves_to_disk(self):
        """Test that autogenerate can save the configuration to disk."""
        from serena.constants import get_project_config_path

        # Create a Go file
        go_file = self.project_path / "main.go"
        go_file.write_text("package main\n\nfunc main() {}\n")

        # Run autogenerate with save_to_disk=True
        config = ProjectConfig.autogenerate(self.project_path, save_to_disk=True)

        # Verify the configuration file was created in centralized location
        config_path = get_project_config_path(self.project_path)
        assert config_path.exists(), f"Config file not found at {config_path}"

        # Verify the content
        assert config.language == Language.GO

    def test_autogenerate_nonexistent_path(self):
        """Test that autogenerate raises FileNotFoundError for non-existent path."""
        non_existent = self.project_path / "does_not_exist"

        with pytest.raises(FileNotFoundError) as exc_info:
            ProjectConfig.autogenerate(non_existent, save_to_disk=False)

        assert "Project root not found" in str(exc_info.value)

    def test_autogenerate_with_gitignored_files_only(self):
        """Test autogenerate behavior when only gitignored files exist."""
        # Create a .gitignore that ignores all Python files
        gitignore = self.project_path / ".gitignore"
        gitignore.write_text("*.py\n")

        # Create Python files that will be ignored
        (self.project_path / "ignored.py").write_text("print('ignored')")

        # Should still raise ValueError as no source files are detected
        with pytest.raises(ValueError) as exc_info:
            ProjectConfig.autogenerate(self.project_path, save_to_disk=False)

        assert "No source files found" in str(exc_info.value)

    def test_autogenerate_custom_project_name(self):
        """Test autogenerate with custom project name."""
        # Create a TypeScript file
        ts_file = self.project_path / "index.ts"
        ts_file.write_text("const greeting: string = 'Hello';\n")

        # Run autogenerate with custom name
        custom_name = "my-custom-project"
        config = ProjectConfig.autogenerate(self.project_path, project_name=custom_name, save_to_disk=False)

        assert config.project_name == custom_name
        assert config.language == Language.TYPESCRIPT

    def test_autogenerate_error_message_format(self):
        """Test the specific format of the error message for better user experience."""
        with pytest.raises(ValueError) as exc_info:
            ProjectConfig.autogenerate(self.project_path, save_to_disk=False)

        error_lines = str(exc_info.value).split("\n")

        # Verify the structure of the error message
        assert len(error_lines) >= 8  # Should have multiple lines of helpful information

        # Check for numbered instructions
        assert any("1." in line for line in error_lines)
        assert any("2." in line for line in error_lines)

        # Check for supported languages list
        assert any("Python" in line and "TypeScript" in line for line in error_lines)

        # Check example includes comment about language options
        assert any("# or typescript, java, csharp" in line for line in error_lines)


class TestProjectConfigCentralizedStorage:
    """Test class for centralized config storage functionality."""

    def setup_method(self):
        """Set up test environment before each test method."""
        self.test_dir = tempfile.mkdtemp()
        self.project_path = Path(self.test_dir) / "test_project"
        self.project_path.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Clean up test environment after each test method."""
        shutil.rmtree(self.test_dir)

    def test_load_from_centralized_location(self):
        """Test that ProjectConfig.load() reads from centralized location."""
        from serena.constants import get_project_config_path

        # Create a Python file so autogenerate works
        python_file = self.project_path / "main.py"
        python_file.write_text("print('hello')\n")

        # Autogenerate config (saves to centralized location)
        ProjectConfig.autogenerate(self.project_path, save_to_disk=True)

        # Verify config is in centralized location
        centralized_path = get_project_config_path(self.project_path)
        assert centralized_path.exists(), f"Config not found at {centralized_path}"

        # Verify it's NOT in the project root
        legacy_path = self.project_path / ".serena" / "project.yml"
        assert not legacy_path.exists(), "Config should not be in legacy location"

        # Load the config
        loaded_config = ProjectConfig.load(self.project_path)
        assert loaded_config.project_name == self.project_path.name
        assert loaded_config.language == Language.PYTHON

    def test_load_with_autogenerate_creates_centralized(self):
        """Test that autogenerate creates config in centralized location."""
        from serena.constants import get_project_config_path

        # Create a Python file
        python_file = self.project_path / "main.py"
        python_file.write_text("print('hello')\n")

        # Load with autogenerate=True
        loaded_config = ProjectConfig.load(self.project_path, autogenerate=True)

        # Verify config was created in centralized location
        centralized_path = get_project_config_path(self.project_path)
        assert centralized_path.exists(), f"Config not found at {centralized_path}"

        # Verify it's NOT in legacy location
        legacy_path = self.project_path / ".serena" / "project.yml"
        assert not legacy_path.exists(), "Config should not be in legacy location"

        assert loaded_config.language == Language.PYTHON

    def test_error_message_shows_centralized_location(self):
        """Test that error message when config not found shows centralized location."""
        from serena.constants import get_project_config_path

        # Don't create any config files
        with pytest.raises(FileNotFoundError) as exc_info:
            ProjectConfig.load(self.project_path, autogenerate=False)

        error_message = str(exc_info.value)
        # Should mention the centralized location
        centralized_path = get_project_config_path(self.project_path)
        assert str(centralized_path) in error_message or ".serena" in error_message
        assert "not found" in error_message.lower()
        # Should NOT mention legacy location
        assert "Legacy:" not in error_message

    def test_load_fails_cleanly_when_config_missing(self):
        """Test that load() fails cleanly with clear error when config doesn't exist."""
        from serena.constants import get_project_config_path

        # Don't create any config files
        centralized_path = get_project_config_path(self.project_path)

        with pytest.raises(FileNotFoundError) as exc_info:
            ProjectConfig.load(self.project_path, autogenerate=False)

        error_message = str(exc_info.value)
        # Should have a clear, helpful error message
        assert "not found" in error_message.lower()
        assert str(centralized_path) in error_message or "project.yml" in error_message
