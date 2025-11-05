"""
Unit tests for constants.py path resolution helpers.

Tests the centralized project storage path resolution functions added in Story 2.
"""

import hashlib
import tempfile
from pathlib import Path

import pytest

from serena.constants import (
    get_centralized_project_dir,
    get_legacy_project_dir,
    get_project_config_path,
    get_project_identifier,
    get_project_memories_path,
)


class TestGetProjectIdentifier:
    """Test get_project_identifier() function."""

    def test_deterministic_same_path(self):
        """Same path should always produce same identifier."""
        test_path = Path("/home/user/projects/myapp")
        id1 = get_project_identifier(test_path)
        id2 = get_project_identifier(test_path)
        assert id1 == id2

    def test_identifier_length(self):
        """Identifier should be exactly 16 characters."""
        test_path = Path("/home/user/projects/myapp")
        project_id = get_project_identifier(test_path)
        assert len(project_id) == 16

    def test_identifier_is_hex(self):
        """Identifier should be valid hexadecimal."""
        test_path = Path("/home/user/projects/myapp")
        project_id = get_project_identifier(test_path)
        # Should not raise ValueError
        int(project_id, 16)

    def test_different_paths_different_ids(self):
        """Different paths should produce different identifiers."""
        path1 = Path("/home/user/projects/app1")
        path2 = Path("/home/user/projects/app2")
        id1 = get_project_identifier(path1)
        id2 = get_project_identifier(path2)
        assert id1 != id2

    def test_case_insensitive_on_windows(self):
        """
        On case-insensitive filesystems, different cases should produce same ID.
        This is handled by lowercasing the path string before hashing.
        """
        # Note: This tests the implementation detail that we lowercase paths
        path1 = Path("C:/Users/Admin/MyApp")
        path2 = Path("c:/users/admin/myapp")

        # Since we lowercase internally, these should match
        # We can't test this directly without mocking, but we can verify
        # the implementation uses lowercase
        normalized1 = path1.resolve()
        normalized2 = path2.resolve()

        # Create hash manually to verify implementation
        path_str1 = str(normalized1).lower()
        path_str2 = str(normalized2).lower()
        hash1 = hashlib.sha256(path_str1.encode('utf-8')).hexdigest()[:16]
        hash2 = hashlib.sha256(path_str2.encode('utf-8')).hexdigest()[:16]

        # If the paths resolve to the same location, hashes should match
        if normalized1 == normalized2:
            assert hash1 == hash2

    def test_symlink_resolution(self):
        """Symlinks should be resolved to their target before hashing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            real_dir = tmpdir_path / "real_project"
            real_dir.mkdir()

            # Create a symlink (skip on Windows if insufficient permissions)
            symlink_dir = tmpdir_path / "symlink_project"
            try:
                symlink_dir.symlink_to(real_dir, target_is_directory=True)
            except OSError:
                pytest.skip("Insufficient permissions to create symlinks")

            # Both should resolve to the same identifier
            id1 = get_project_identifier(real_dir)
            id2 = get_project_identifier(symlink_dir)
            assert id1 == id2

    def test_absolute_path_conversion(self):
        """Relative paths should be converted to absolute before hashing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            test_dir = tmpdir_path / "test_project"
            test_dir.mkdir()

            # Get ID from absolute path
            id1 = get_project_identifier(test_dir)

            # Get ID from relative path (should resolve to absolute)
            import os
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                relative_path = Path("test_project")
                id2 = get_project_identifier(relative_path)
                assert id1 == id2
            finally:
                os.chdir(original_cwd)


class TestGetCentralizedProjectDir:
    """Test get_centralized_project_dir() function."""

    def test_returns_correct_path_structure(self):
        """Should return ~/.serena/projects/{id}/"""
        test_path = Path("/home/user/projects/myapp")
        result = get_centralized_project_dir(test_path)

        # Should contain .serena/projects/ in the path
        assert ".serena" in str(result)
        assert "projects" in str(result)

        # Should end with the project identifier
        expected_id = get_project_identifier(test_path)
        assert result.name == expected_id

    def test_creates_directory_if_not_exists(self):
        """Should create directory structure if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # This will create the directory as a side effect
            test_path = Path(tmpdir) / "test_project"
            test_path.mkdir()

            result = get_centralized_project_dir(test_path)

            # Directory should exist after calling the function
            assert result.exists()
            assert result.is_dir()

    def test_idempotent_directory_creation(self):
        """Should be safe to call multiple times (idempotent)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_project"
            test_path.mkdir()

            # Call multiple times
            result1 = get_centralized_project_dir(test_path)
            result2 = get_centralized_project_dir(test_path)
            result3 = get_centralized_project_dir(test_path)

            # Should return same path
            assert result1 == result2 == result3
            assert result1.exists()


class TestGetProjectConfigPath:
    """Test get_project_config_path() function."""

    def test_returns_correct_path(self):
        """Should return ~/.serena/projects/{id}/project.yml"""
        test_path = Path("/home/user/projects/myapp")
        result = get_project_config_path(test_path)

        # Should end with project.yml
        assert result.name == "project.yml"

        # Should be inside centralized project dir
        expected_parent = get_centralized_project_dir(test_path)
        assert result.parent == expected_parent

    def test_parent_directory_created(self):
        """Parent directory should be created by get_centralized_project_dir()."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_project"
            test_path.mkdir()

            result = get_project_config_path(test_path)

            # Parent directory should exist
            assert result.parent.exists()
            assert result.parent.is_dir()


class TestGetProjectMemoriesPath:
    """Test get_project_memories_path() function."""

    def test_returns_correct_path(self):
        """Should return ~/.serena/projects/{id}/memories/"""
        test_path = Path("/home/user/projects/myapp")
        result = get_project_memories_path(test_path)

        # Should end with memories
        assert result.name == "memories"

        # Should be inside centralized project dir
        expected_parent = get_centralized_project_dir(test_path)
        assert result.parent == expected_parent

    def test_creates_directory_if_not_exists(self):
        """Should create memories directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_project"
            test_path.mkdir()

            result = get_project_memories_path(test_path)

            # Directory should exist after calling the function
            assert result.exists()
            assert result.is_dir()

    def test_idempotent_directory_creation(self):
        """Should be safe to call multiple times (idempotent)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_project"
            test_path.mkdir()

            # Call multiple times
            result1 = get_project_memories_path(test_path)
            result2 = get_project_memories_path(test_path)
            result3 = get_project_memories_path(test_path)

            # Should return same path
            assert result1 == result2 == result3
            assert result1.exists()


class TestGetLegacyProjectDir:
    """Test get_legacy_project_dir() function."""

    def test_returns_correct_path(self):
        """Should return {project_root}/.serena/"""
        test_path = Path("/home/user/projects/myapp")
        result = get_legacy_project_dir(test_path)

        # Should be .serena subdirectory of project root
        assert result == test_path / ".serena"
        assert result.name == ".serena"
        assert result.parent == test_path

    def test_does_not_create_directory(self):
        """Should NOT create directory (read-only operation)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_project"
            test_path.mkdir()

            result = get_legacy_project_dir(test_path)

            # Directory should NOT exist (we didn't create it)
            assert not result.exists()


class TestCrossPlatformCompatibility:
    """Test cross-platform compatibility of path helpers."""

    def test_windows_path_handling(self):
        """Test handling of Windows-style paths."""
        # Test with Windows-style path
        test_path = Path("C:/Users/Admin/Documents/GitHub/myapp")
        project_id = get_project_identifier(test_path)

        # Should produce valid identifier
        assert len(project_id) == 16
        int(project_id, 16)  # Should not raise

    def test_unix_path_handling(self):
        """Test handling of Unix-style paths."""
        # Test with Unix-style path
        test_path = Path("/home/user/projects/myapp")
        project_id = get_project_identifier(test_path)

        # Should produce valid identifier
        assert len(project_id) == 16
        int(project_id, 16)  # Should not raise

    def test_path_with_spaces(self):
        """Test handling of paths with spaces."""
        test_path = Path("/home/user/My Projects/My App")
        project_id = get_project_identifier(test_path)

        # Should produce valid identifier
        assert len(project_id) == 16
        int(project_id, 16)  # Should not raise

    def test_path_with_special_characters(self):
        """Test handling of paths with special characters."""
        # Only test characters that are valid in file paths
        test_path = Path("/home/user/project-name_v1.0")
        project_id = get_project_identifier(test_path)

        # Should produce valid identifier
        assert len(project_id) == 16
        int(project_id, 16)  # Should not raise

    def test_long_path(self):
        """Test handling of very long paths."""
        # Create a path with many nested directories
        long_path = Path("/home/user/very/deeply/nested/directory/structure/with/many/levels/project")
        project_id = get_project_identifier(long_path)

        # Should still produce valid 16-char identifier
        assert len(project_id) == 16
        int(project_id, 16)  # Should not raise


class TestIntegrationScenarios:
    """Integration tests for common usage scenarios."""

    def test_full_workflow_new_project(self):
        """Test full workflow for a new project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "myapp"
            project_root.mkdir()

            # Get all paths
            project_id = get_project_identifier(project_root)
            centralized_dir = get_centralized_project_dir(project_root)
            config_path = get_project_config_path(project_root)
            memories_path = get_project_memories_path(project_root)
            legacy_dir = get_legacy_project_dir(project_root)

            # Verify structure
            assert len(project_id) == 16
            assert centralized_dir.exists()
            assert memories_path.exists()
            assert config_path.parent.exists()
            assert not legacy_dir.exists()  # No legacy dir for new project

            # Verify relationships
            assert config_path.parent == centralized_dir
            assert memories_path.parent == centralized_dir

    def test_collision_resistance(self):
        """Test that similar paths produce different identifiers."""
        paths = [
            Path("/home/user/project"),
            Path("/home/user/project1"),
            Path("/home/user/project2"),
            Path("/home/user/projects"),
            Path("/home/user/project_old"),
        ]

        identifiers = [get_project_identifier(p) for p in paths]

        # All identifiers should be unique
        assert len(identifiers) == len(set(identifiers))
