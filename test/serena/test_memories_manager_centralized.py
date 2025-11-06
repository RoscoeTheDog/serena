"""
Unit tests for MemoriesManager with Centralized Storage Only

Tests the MemoriesManager with centralized storage (legacy support removed).
"""

import tempfile
from pathlib import Path

import pytest

from serena.agent import MemoriesManager
from serena.constants import (
    get_centralized_project_dir,
    get_project_memories_path,
)


class TestMemoriesManagerCentralizedStorage:
    """Test suite for centralized memory storage functionality"""

    @pytest.fixture
    def temp_project_root(self):
        """Create a temporary project root directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def memories_manager(self, temp_project_root):
        """Create a MemoriesManager instance for testing"""
        return MemoriesManager(str(temp_project_root))

    # === Initialization Tests ===

    def test_init_creates_centralized_directory(self, temp_project_root):
        """Test that MemoriesManager creates centralized directory structure"""
        manager = MemoriesManager(str(temp_project_root))

        # Verify centralized directory was created
        centralized_dir = get_centralized_project_dir(temp_project_root)
        memories_dir = get_project_memories_path(temp_project_root)
        assert centralized_dir.exists()
        assert memories_dir.exists()

    def test_init_stores_correct_paths(self, temp_project_root):
        """Test that MemoriesManager stores correct centralized path"""
        manager = MemoriesManager(str(temp_project_root))

        expected_centralized = get_project_memories_path(temp_project_root)
        assert manager._project_memory_dir == expected_centralized

    # === Save Memory Tests ===

    def test_save_memory_to_centralized_location(self, memories_manager, temp_project_root):
        """Test that save_memory writes to centralized location"""
        content = "# Test Memory\n\nThis is a test memory."
        memories_manager.save_memory("test_memory", content)

        # Verify file exists in centralized location
        centralized_path = get_project_memories_path(temp_project_root) / "test_memory.md"
        assert centralized_path.exists()

    def test_save_memory_content_correct(self, memories_manager, temp_project_root):
        """Test that saved memory has correct content"""
        content = "# Important Note\n\nRemember to test thoroughly."
        memories_manager.save_memory("important", content)

        # Read and verify content
        saved_path = get_project_memories_path(temp_project_root) / "important.md"
        saved_content = saved_path.read_text(encoding="utf-8")
        assert saved_content == content

    # === Load Memory Tests ===

    def test_load_memory_from_centralized_location(self, memories_manager, temp_project_root):
        """Test load_memory reads from centralized location"""
        content = "# Centralized Memory\n\nStored in centralized location."
        memories_manager.save_memory("centralized_memory", content)
        loaded = memories_manager.load_memory("centralized_memory")
        assert loaded == content

    def test_load_memory_not_found(self, memories_manager):
        """Test load_memory raises FileNotFoundError for non-existent memory"""
        with pytest.raises(FileNotFoundError):
            memories_manager.load_memory("nonexistent_memory")

    # === List Memories Tests ===

    def test_list_memories_from_centralized_only(self, memories_manager):
        """Test list_memories when only centralized memories exist"""
        # Create memories in centralized location
        memories_manager.save_memory("memory1", "Content 1")
        memories_manager.save_memory("memory2", "Content 2")

        result = memories_manager.list_memories()
        assert "memory1" in result
        assert "memory2" in result

    def test_empty_memories_directory(self, memories_manager):
        """Test list_memories returns empty list when no memories exist"""
        result = memories_manager.list_memories()
        assert result == []

    def test_list_memories_with_metadata(self, memories_manager):
        """Test list_memories with include_metadata=True"""
        memories_manager.save_memory("test", "Content")

        result = memories_manager.list_memories(include_metadata=True)
        assert len(result) == 1
        assert result[0]["name"] == "test"
        assert "size" in result[0]
        assert "last_modified" in result[0]

    # === Delete Memory Tests ===

    def test_delete_memory_from_centralized_location(self, memories_manager, temp_project_root):
        """Test delete_memory removes from centralized location"""
        # Create memory
        memories_manager.save_memory("to_delete", "Content to delete")
        centralized_file = get_project_memories_path(temp_project_root) / "to_delete.md"
        assert centralized_file.exists()

        result = memories_manager.delete_memory("to_delete")
        assert not centralized_file.exists()

    def test_delete_memory_not_found(self, memories_manager):
        """Test delete_memory returns False for non-existent memory"""
        result = memories_manager.delete_memory("nonexistent")
        assert result is False

    # === Edge Cases ===

    def test_memory_name_with_md_extension(self, memories_manager):
        """Test that .md extension is handled correctly in memory names"""
        content = "# Test\n\nContent"

        # Save with .md extension
        memories_manager.save_memory("test.md", content)

        # Load both with and without extension should work
        loaded1 = memories_manager.load_memory("test")
        loaded2 = memories_manager.load_memory("test.md")

        assert loaded1 == content
        assert loaded2 == content

    def test_unicode_memory_names_and_content(self, memories_manager):
        """Test handling of unicode in memory names and content"""
        content = "# Émojis 🎉\n\n测试内容 тест"
        memories_manager.save_memory("unicode_test", content)
        loaded = memories_manager.load_memory("unicode_test")
        assert loaded == content
