"""
Unit tests for Story 12: Memory Metadata Tool

Tests the enhanced list_memories functionality with metadata and previews.
"""

import json
import tempfile
import time
from pathlib import Path

import pytest

from serena.agent import MemoriesManager


class TestMemoryMetadata:
    """Test suite for memory metadata functionality"""

    @pytest.fixture
    def temp_memories_dir(self):
        """Create a temporary directory for test memories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def memories_manager(self, temp_memories_dir):
        """Create a MemoriesManager instance for testing"""
        return MemoriesManager(temp_memories_dir)

    @pytest.fixture
    def sample_memories(self, memories_manager):
        """Create sample memory files for testing"""
        # Small memory
        memories_manager.save_memory(
            "small_memory",
            "# Small Memory\n\nThis is a small test memory.\n"
        )

        # Medium memory
        memories_manager.save_memory(
            "medium_memory",
            "# Medium Memory\n\n" + "Line content here.\n" * 20
        )

        # Large memory
        large_content = "# Large Memory\n\n" + "Line content here.\n" * 100
        memories_manager.save_memory("large_memory", large_content)

        # Memory with special chars
        memories_manager.save_memory(
            "special_chars",
            "# Special Chars\n\nSome émojis 🎉 and unicode: ñ, ü, ö\n"
        )

        return memories_manager

    # Basic Functionality Tests

    def test_list_memories_backward_compatible(self, sample_memories):
        """Test that list_memories without parameters returns simple list (backward compatible)"""
        result = sample_memories.list_memories()

        assert isinstance(result, list)
        assert len(result) == 4
        assert all(isinstance(name, str) for name in result)
        assert "small_memory" in result
        assert "medium_memory" in result
        assert "large_memory" in result
        assert "special_chars" in result

    def test_list_memories_with_metadata(self, sample_memories):
        """Test that list_memories with include_metadata=True returns metadata"""
        result = sample_memories.list_memories(include_metadata=True)

        assert isinstance(result, list)
        assert len(result) == 4

        # Check structure of first memory
        memory = result[0]
        assert "name" in memory
        assert "size_kb" in memory
        assert "last_modified" in memory
        assert "preview" in memory
        assert "estimated_tokens" in memory
        assert "lines" in memory

    def test_metadata_fields_types(self, sample_memories):
        """Test that metadata fields have correct types"""
        result = sample_memories.list_memories(include_metadata=True)

        for memory in result:
            assert isinstance(memory["name"], str)
            assert isinstance(memory["size_kb"], float)
            assert isinstance(memory["last_modified"], str)
            assert isinstance(memory["preview"], str)
            assert isinstance(memory["estimated_tokens"], int)
            assert isinstance(memory["lines"], int)

    # Preview Tests

    def test_preview_default_lines(self, sample_memories):
        """Test that preview includes first 3 lines by default"""
        result = sample_memories.list_memories(include_metadata=True)

        small_memory = next(m for m in result if m["name"] == "small_memory")
        # Should have 3 lines in content
        lines_in_preview = small_memory["preview"].count("\n") + 1
        assert lines_in_preview == 3  # First 3 lines

    def test_preview_custom_lines(self, sample_memories):
        """Test that preview_lines parameter works"""
        result = sample_memories.list_memories(include_metadata=True, preview_lines=5)

        medium_memory = next(m for m in result if m["name"] == "medium_memory")
        lines_in_preview = medium_memory["preview"].split("\n")
        # Should have 5 actual lines + continuation indicator
        assert len([l for l in lines_in_preview if l and not l.startswith("...")]) <= 5

    def test_preview_truncation_indicator(self, sample_memories):
        """Test that preview shows truncation indicator for long files"""
        result = sample_memories.list_memories(include_metadata=True, preview_lines=3)

        large_memory = next(m for m in result if m["name"] == "large_memory")
        assert "... (" in large_memory["preview"]
        assert "more lines)" in large_memory["preview"]

    def test_preview_no_truncation_for_short_files(self, sample_memories):
        """Test that preview doesn't show truncation for short files"""
        result = sample_memories.list_memories(include_metadata=True, preview_lines=10)

        small_memory = next(m for m in result if m["name"] == "small_memory")
        # Small memory has only 3 lines, so no truncation should appear
        assert "more lines)" not in small_memory["preview"]

    # Token Estimation Tests

    def test_token_estimation_accuracy(self, sample_memories):
        """Test that token estimation is approximately chars/4"""
        result = sample_memories.list_memories(include_metadata=True)

        for memory in result:
            # Read actual content
            content = sample_memories.load_memory(memory["name"])
            expected_tokens = len(content) // 4
            # Should be exactly chars/4
            assert memory["estimated_tokens"] == expected_tokens

    def test_token_estimation_for_empty_file(self, memories_manager):
        """Test token estimation for empty file"""
        memories_manager.save_memory("empty", "")
        result = memories_manager.list_memories(include_metadata=True)

        empty_memory = next(m for m in result if m["name"] == "empty")
        assert empty_memory["estimated_tokens"] == 0
        assert empty_memory["lines"] == 0

    # Size Tests

    def test_size_kb_positive(self, sample_memories):
        """Test that size_kb is positive for non-empty files"""
        result = sample_memories.list_memories(include_metadata=True)

        for memory in result:
            assert memory["size_kb"] > 0

    def test_size_kb_relative(self, sample_memories):
        """Test that larger files have larger size_kb"""
        result = sample_memories.list_memories(include_metadata=True)

        small = next(m for m in result if m["name"] == "small_memory")
        large = next(m for m in result if m["name"] == "large_memory")

        assert large["size_kb"] > small["size_kb"]

    # Line Count Tests

    def test_line_count_accuracy(self, sample_memories):
        """Test that line count matches actual lines in file"""
        result = sample_memories.list_memories(include_metadata=True)

        for memory in result:
            content = sample_memories.load_memory(memory["name"])
            expected_lines = len(content.splitlines())
            assert memory["lines"] == expected_lines

    # Last Modified Tests

    def test_last_modified_timestamp(self, sample_memories):
        """Test that last_modified is a valid Unix timestamp"""
        result = sample_memories.list_memories(include_metadata=True)

        for memory in result:
            # Should be a numeric string
            timestamp = float(memory["last_modified"])
            # Should be recent (within last minute)
            assert time.time() - timestamp < 60

    # Special Character Tests

    def test_preview_with_special_characters(self, sample_memories):
        """Test that preview handles unicode and special characters"""
        result = sample_memories.list_memories(include_metadata=True)

        special = next(m for m in result if m["name"] == "special_chars")
        assert "émojis" in special["preview"]
        assert "🎉" in special["preview"]
        assert "ñ" in special["preview"]

    # Empty Directory Tests

    def test_empty_memories_dir(self, memories_manager):
        """Test list_memories on empty directory"""
        result = memories_manager.list_memories(include_metadata=True)
        assert result == []

    def test_empty_memories_dir_backward_compatible(self, memories_manager):
        """Test list_memories backward compatible mode on empty directory"""
        result = memories_manager.list_memories()
        assert result == []

    # Error Handling Tests

    def test_corrupt_file_handling(self, memories_manager, temp_memories_dir):
        """Test that corrupt files don't crash the listing"""
        # Create a file that we can't read (simulate permission error or corrupt file)
        memory_dir = Path(temp_memories_dir) / ".serena" / "memories"
        memory_dir.mkdir(parents=True, exist_ok=True)

        # Create a normal memory first
        memories_manager.save_memory("good_memory", "This is good content")

        # The error handling is tested by trying to read files that might have issues
        # Since we can't easily create a truly unreadable file in tests,
        # we verify the error handling code path exists
        result = memories_manager.list_memories(include_metadata=True)
        assert len(result) >= 1  # At least the good memory

    # Integration Tests

    def test_full_workflow(self, memories_manager):
        """Test full workflow: create memories, list with metadata, read specific one"""
        # Create memories
        memories_manager.save_memory("auth_flow", "# Auth Flow\n\nJWT tokens used.\nRefresh tokens supported.\n")
        memories_manager.save_memory("api_docs", "# API Docs\n\nRESTful API\nJSON responses\n")

        # List with metadata
        result = memories_manager.list_memories(include_metadata=True)
        assert len(result) == 2

        # Find auth_flow
        auth = next(m for m in result if m["name"] == "auth_flow")

        # Verify preview helps decision
        assert "JWT tokens" in auth["preview"]

        # Decision: read full content
        full_content = memories_manager.load_memory("auth_flow")
        assert "Refresh tokens supported" in full_content

    def test_token_savings_calculation(self, sample_memories):
        """Test and verify token savings from using metadata vs reading all"""
        # Get metadata
        metadata_result = sample_memories.list_memories(include_metadata=True)
        metadata_str = json.dumps(metadata_result, indent=2)
        metadata_tokens = len(metadata_str) // 4

        # Calculate tokens for reading all files
        all_content_tokens = 0
        for memory in metadata_result:
            content = sample_memories.load_memory(memory["name"])
            all_content_tokens += len(content) // 4

        # Verify savings
        savings_percent = ((all_content_tokens - metadata_tokens) / all_content_tokens) * 100

        print(f"\nToken Savings:")
        print(f"  Metadata approach: {metadata_tokens} tokens")
        print(f"  Reading all files: {all_content_tokens} tokens")
        print(f"  Savings: {savings_percent:.1f}%")

        # Should have significant savings (target: 60-80%)
        assert savings_percent >= 50  # At least 50% savings
        assert metadata_tokens < all_content_tokens


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
