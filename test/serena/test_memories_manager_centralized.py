"""
Unit tests for Story 5: Refactor MemoriesManager to Use Centralized Paths

Tests the refactored MemoriesManager with centralized storage and backward compatibility.
"""

import tempfile
from pathlib import Path

import pytest

from serena.agent import MemoriesManager
from serena.constants import (
    get_centralized_project_dir,
    get_legacy_project_dir,
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

    # Initialization Tests

    def test_init_creates_centralized_directory(self, temp_project_root):
        """Test that MemoriesManager creates centralized memories directory"""
        manager = MemoriesManager(str(temp_project_root))

        # Verify centralized directory was created
        centralized_dir = get_project_memories_path(temp_project_root)
        assert centralized_dir.exists()
        assert centralized_dir.is_dir()

    def test_init_does_not_create_legacy_directory(self, temp_project_root):
        """Test that MemoriesManager does NOT create legacy .serena directory"""
        manager = MemoriesManager(str(temp_project_root))

        # Verify legacy directory was NOT created
        legacy_dir = get_legacy_project_dir(temp_project_root) / "memories"
        assert not legacy_dir.exists()

    def test_init_stores_correct_paths(self, temp_project_root):
        """Test that MemoriesManager stores correct centralized path"""
        manager = MemoriesManager(str(temp_project_root))

        expected_centralized = get_project_memories_path(temp_project_root)

        assert manager._memory_dir == expected_centralized

    # Save Memory Tests (Centralized Only)

    def test_save_memory_to_centralized_location(self, memories_manager, temp_project_root):
        """Test that save_memory writes to centralized location"""
        memories_manager.save_memory("test_memory", "# Test Content\n\nThis is a test.")

        # Verify file exists in centralized location
        centralized_path = get_project_memories_path(temp_project_root) / "test_memory.md"
        assert centralized_path.exists()

        # Verify file does NOT exist in legacy location
        legacy_path = get_legacy_project_dir(temp_project_root) / "memories" / "test_memory.md"
        assert not legacy_path.exists()

    def test_save_memory_content_correct(self, memories_manager, temp_project_root):
        """Test that saved memory has correct content"""
        content = "# Test Memory\n\nSome important info here."
        memories_manager.save_memory("test", content)

        centralized_path = get_project_memories_path(temp_project_root) / "test.md"
        with open(centralized_path, encoding="utf-8") as f:
            saved_content = f.read()

        assert saved_content == content

    # Load Memory Tests (Backward Compatibility)

    def test_load_memory_from_centralized_location(self, memories_manager, temp_project_root):
        """Test that load_memory reads from centralized location"""
        content = "# Centralized Memory\n\nThis is stored centrally."
        memories_manager.save_memory("centralized", content)

        loaded = memories_manager.load_memory("centralized")
        assert loaded == content

    def test_load_memory_from_legacy_location(self, memories_manager, temp_project_root):
        """Test backward compatibility: load_memory reads from legacy location if exists"""
        # Manually create a memory in legacy location
        legacy_dir = get_legacy_project_dir(temp_project_root) / "memories"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_file = legacy_dir / "legacy_memory.md"
        legacy_content = "# Legacy Memory\n\nThis is from old .serena directory."
        legacy_file.write_text(legacy_content, encoding="utf-8")

        # Load should find the legacy memory
        loaded = memories_manager.load_memory("legacy_memory")
        assert loaded == legacy_content

    def test_load_memory_precedence_centralized_over_legacy(self, memories_manager, temp_project_root):
        """Test that centralized location takes precedence when both exist"""
        # Create memory in both locations with different content
        centralized_content = "# Centralized Version\n\nThis is the newer version."
        legacy_content = "# Legacy Version\n\nThis is the old version."

        # Save to centralized (via manager)
        memories_manager.save_memory("dual_memory", centralized_content)

        # Manually create in legacy location
        legacy_dir = get_legacy_project_dir(temp_project_root) / "memories"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_file = legacy_dir / "dual_memory.md"
        legacy_file.write_text(legacy_content, encoding="utf-8")

        # Load should return centralized version (takes precedence)
        loaded = memories_manager.load_memory("dual_memory")
        assert loaded == centralized_content

    def test_load_memory_not_found(self, memories_manager):
        """Test that load_memory returns helpful message for non-existent memory"""
        result = memories_manager.load_memory("nonexistent")
        assert "not found" in result.lower()
        assert "write_memory" in result

    # List Memories Tests (Merged from Both Locations)

    def test_list_memories_from_centralized_only(self, memories_manager):
        """Test list_memories when only centralized memories exist"""
        memories_manager.save_memory("memory1", "Content 1")
        memories_manager.save_memory("memory2", "Content 2")

        result = memories_manager.list_memories(include_metadata=False)
        assert len(result) == 2
        assert "memory1" in result
        assert "memory2" in result

    def test_list_memories_from_legacy_only(self, memories_manager, temp_project_root):
        """Test list_memories when only legacy memories exist"""
        # Create memories in legacy location
        legacy_dir = get_legacy_project_dir(temp_project_root) / "memories"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / "legacy1.md").write_text("Legacy 1", encoding="utf-8")
        (legacy_dir / "legacy2.md").write_text("Legacy 2", encoding="utf-8")

        result = memories_manager.list_memories(include_metadata=False)
        assert len(result) == 2
        assert "legacy1" in result
        assert "legacy2" in result

    def test_list_memories_merged_from_both_locations(self, memories_manager, temp_project_root):
        """Test that list_memories merges memories from both locations"""
        # Create centralized memories
        memories_manager.save_memory("centralized1", "Centralized 1")
        memories_manager.save_memory("centralized2", "Centralized 2")

        # Create legacy memories
        legacy_dir = get_legacy_project_dir(temp_project_root) / "memories"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / "legacy1.md").write_text("Legacy 1", encoding="utf-8")
        (legacy_dir / "legacy2.md").write_text("Legacy 2", encoding="utf-8")

        result = memories_manager.list_memories(include_metadata=False)
        assert len(result) == 4
        assert "centralized1" in result
        assert "centralized2" in result
        assert "legacy1" in result
        assert "legacy2" in result

    def test_list_memories_deduplication(self, memories_manager, temp_project_root):
        """Test that list_memories deduplicates when same memory exists in both locations"""
        # Create memory in centralized location
        memories_manager.save_memory("duplicate", "Centralized version")

        # Create same memory in legacy location
        legacy_dir = get_legacy_project_dir(temp_project_root) / "memories"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / "duplicate.md").write_text("Legacy version", encoding="utf-8")

        # Should only list once (centralized takes precedence)
        result = memories_manager.list_memories(include_metadata=False)
        assert result.count("duplicate") == 1

    def test_list_memories_with_metadata_from_both_locations(self, memories_manager, temp_project_root):
        """Test that list_memories with metadata works for both locations"""
        # Create memories in both locations
        memories_manager.save_memory("centralized", "# Centralized\n\nCentralized content")

        legacy_dir = get_legacy_project_dir(temp_project_root) / "memories"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / "legacy.md").write_text("# Legacy\n\nLegacy content", encoding="utf-8")

        result = memories_manager.list_memories(include_metadata=True)
        assert len(result) == 2

        # Verify metadata structure
        for memory in result:
            assert "name" in memory
            assert "size_kb" in memory
            assert "estimated_tokens" in memory
            assert memory["name"] in ["centralized", "legacy"]

    # Delete Memory Tests (Both Locations)

    def test_delete_memory_from_centralized_location(self, memories_manager, temp_project_root):
        """Test delete_memory removes from centralized location"""
        memories_manager.save_memory("to_delete", "Content to delete")

        centralized_path = get_project_memories_path(temp_project_root) / "to_delete.md"
        assert centralized_path.exists()

        result = memories_manager.delete_memory("to_delete")
        assert "deleted" in result.lower()
        assert not centralized_path.exists()

    def test_delete_memory_from_legacy_location(self, memories_manager, temp_project_root):
        """Test delete_memory removes from legacy location"""
        # Create memory in legacy location
        legacy_dir = get_legacy_project_dir(temp_project_root) / "memories"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_file = legacy_dir / "legacy_to_delete.md"
        legacy_file.write_text("Legacy content to delete", encoding="utf-8")

        assert legacy_file.exists()

        result = memories_manager.delete_memory("legacy_to_delete")
        assert "deleted" in result.lower()
        assert not legacy_file.exists()

    def test_delete_memory_precedence_centralized_first(self, memories_manager, temp_project_root):
        """Test that delete_memory tries centralized location first"""
        # Create memory in both locations
        memories_manager.save_memory("dual_delete", "Centralized")

        legacy_dir = get_legacy_project_dir(temp_project_root) / "memories"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_file = legacy_dir / "dual_delete.md"
        legacy_file.write_text("Legacy", encoding="utf-8")

        centralized_path = get_project_memories_path(temp_project_root) / "dual_delete.md"

        # Delete should remove centralized first
        memories_manager.delete_memory("dual_delete")

        assert not centralized_path.exists()
        assert legacy_file.exists()  # Legacy still exists

    def test_delete_memory_not_found(self, memories_manager):
        """Test delete_memory returns helpful message for non-existent memory"""
        result = memories_manager.delete_memory("nonexistent")
        assert "not found" in result.lower()

    # Edge Cases

    def test_memory_name_with_md_extension(self, memories_manager):
        """Test that memory names with .md extension are handled correctly"""
        # Save with .md extension (should be stripped)
        memories_manager.save_memory("test.md", "Content")

        # Load without extension should work
        loaded = memories_manager.load_memory("test")
        assert loaded == "Content"

        # Load with extension should also work
        loaded = memories_manager.load_memory("test.md")
        assert loaded == "Content"

    def test_empty_memories_directory(self, memories_manager):
        """Test operations on empty memories directory"""
        result = memories_manager.list_memories(include_metadata=False)
        assert result == []

        result = memories_manager.list_memories(include_metadata=True)
        assert result == []

    def test_unicode_memory_names_and_content(self, memories_manager):
        """Test that unicode characters work in memory names and content"""
        content = "# Unicode Test\n\némojis 🎉, ñ, ü, ö"
        memories_manager.save_memory("unicode_test", content)

        loaded = memories_manager.load_memory("unicode_test")
        assert loaded == content

    # Integration Test

    def test_full_migration_workflow(self, memories_manager, temp_project_root):
        """Test full workflow: legacy memories exist, new ones are created centralized"""
        # Step 1: Simulate existing legacy memories (from old version)
        legacy_dir = get_legacy_project_dir(temp_project_root) / "memories"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        (legacy_dir / "old_memory1.md").write_text("Old content 1", encoding="utf-8")
        (legacy_dir / "old_memory2.md").write_text("Old content 2", encoding="utf-8")

        # Step 2: User can still read old memories
        assert memories_manager.load_memory("old_memory1") == "Old content 1"
        assert memories_manager.load_memory("old_memory2") == "Old content 2"

        # Step 3: User creates new memories (go to centralized)
        memories_manager.save_memory("new_memory1", "New content 1")
        memories_manager.save_memory("new_memory2", "New content 2")

        # Step 4: List shows all memories (merged)
        all_memories = memories_manager.list_memories(include_metadata=False)
        assert len(all_memories) == 4
        assert set(all_memories) == {"old_memory1", "old_memory2", "new_memory1", "new_memory2"}

        # Step 5: New memories are in centralized location
        centralized_dir = get_project_memories_path(temp_project_root)
        assert (centralized_dir / "new_memory1.md").exists()
        assert (centralized_dir / "new_memory2.md").exists()

        # Step 6: Old memories remain in legacy location (not automatically migrated)
        assert (legacy_dir / "old_memory1.md").exists()
        assert (legacy_dir / "old_memory2.md").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
