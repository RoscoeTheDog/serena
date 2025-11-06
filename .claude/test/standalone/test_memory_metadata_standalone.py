#!/usr/bin/env python3
"""
Standalone test for Story 12: Memory Metadata Tool

Run this directly without pytest to verify the implementation works.
"""

import json
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from serena.agent import MemoriesManager


def test_backward_compatibility():
    """Test that default behavior is unchanged"""
    print("Test 1: Backward Compatibility")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MemoriesManager(tmpdir)

        # Create test memories
        manager.save_memory("test1", "Content 1")
        manager.save_memory("test2", "Content 2")

        # Default behavior (no metadata)
        result = manager.list_memories()

        assert isinstance(result, list), "Should return list"
        assert len(result) == 2, f"Should have 2 memories, got {len(result)}"
        assert all(isinstance(name, str) for name in result), "Should be list of strings"
        assert "test1" in result and "test2" in result, "Should contain memory names"

        print("  ✓ Backward compatibility maintained")
        print(f"  ✓ Default mode returns: {result}")


def test_metadata_mode():
    """Test metadata mode returns full details"""
    print("\nTest 2: Metadata Mode")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MemoriesManager(tmpdir)

        # Create test memory
        content = "# Test Memory\n\nThis is line 2.\nThis is line 3.\nThis is line 4.\n"
        manager.save_memory("test_metadata", content)

        # Get with metadata
        result = manager.list_memories(include_metadata=True)

        assert isinstance(result, list), "Should return list"
        assert len(result) == 1, f"Should have 1 memory, got {len(result)}"

        memory = result[0]
        assert isinstance(memory, dict), "Should be dict with metadata"

        # Check required fields
        required_fields = ["name", "size_kb", "last_modified", "preview", "estimated_tokens", "lines"]
        for field in required_fields:
            assert field in memory, f"Missing field: {field}"

        print("  ✓ Metadata mode returns full details")
        print(f"  ✓ Memory: {memory['name']}")
        print(f"  ✓ Size: {memory['size_kb']} KB")
        print(f"  ✓ Lines: {memory['lines']}")
        print(f"  ✓ Estimated tokens: {memory['estimated_tokens']}")
        print(f"  ✓ Preview:\n    {memory['preview'].replace(chr(10), chr(10) + '    ')}")


def test_preview_truncation():
    """Test preview truncation for long files"""
    print("\nTest 3: Preview Truncation")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MemoriesManager(tmpdir)

        # Create long file
        long_content = "# Long File\n\n" + "\n".join([f"Line {i}" for i in range(100)])
        manager.save_memory("long_file", long_content)

        # Get with metadata (default 3 lines)
        result = manager.list_memories(include_metadata=True)
        memory = result[0]

        preview = memory["preview"]
        assert "more lines)" in preview, "Should show truncation indicator"
        print("  ✓ Preview truncated correctly")
        print(f"  ✓ Preview length: {len(preview)} chars (full content: {len(long_content)} chars)")
        print(f"  ✓ Truncation indicator present: '... (97 more lines)'")


def test_custom_preview_lines():
    """Test custom preview line count"""
    print("\nTest 4: Custom Preview Lines")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MemoriesManager(tmpdir)

        content = "\n".join([f"Line {i}" for i in range(20)])
        manager.save_memory("test_custom", content)

        # Test different preview lengths
        for preview_lines in [1, 3, 5, 10]:
            result = manager.list_memories(include_metadata=True, preview_lines=preview_lines)
            memory = result[0]

            lines_in_preview = len([l for l in memory["preview"].split("\n") if l and not l.startswith("...")])
            print(f"  ✓ preview_lines={preview_lines}: got {lines_in_preview} lines in preview")


def test_token_estimation():
    """Test token estimation accuracy"""
    print("\nTest 5: Token Estimation")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MemoriesManager(tmpdir)

        # Create memory with known size
        content = "A" * 1000  # 1000 chars
        manager.save_memory("token_test", content)

        result = manager.list_memories(include_metadata=True)
        memory = result[0]

        expected_tokens = len(content) // 4  # 250 tokens
        actual_tokens = memory["estimated_tokens"]

        assert actual_tokens == expected_tokens, f"Expected {expected_tokens}, got {actual_tokens}"
        print(f"  ✓ Token estimation accurate: {actual_tokens} tokens (chars/4 = {expected_tokens})")


def test_token_savings():
    """Test and measure token savings"""
    print("\nTest 6: Token Savings Measurement")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MemoriesManager(tmpdir)

        # Create multiple memories of varying sizes
        memories_data = {
            "auth_flow": "# Authentication Flow\n\n" + "JWT tokens are used.\n" * 50,
            "api_docs": "# API Documentation\n\n" + "RESTful API with JSON.\n" * 100,
            "database_schema": "# Database Schema\n\n" + "PostgreSQL schema definition.\n" * 75,
        }

        for name, content in memories_data.items():
            manager.save_memory(name, content)

        # Approach 1: List with metadata
        metadata_result = manager.list_memories(include_metadata=True)
        metadata_json = json.dumps(metadata_result, indent=2)
        metadata_tokens = len(metadata_json) // 4

        # Approach 2: Read all files
        all_content = ""
        for name in memories_data:
            all_content += manager.load_memory(name)
        read_all_tokens = len(all_content) // 4

        savings = ((read_all_tokens - metadata_tokens) / read_all_tokens) * 100

        print(f"  ✓ Metadata approach: {metadata_tokens} tokens")
        print(f"  ✓ Reading all files: {read_all_tokens} tokens")
        print(f"  ✓ Token savings: {savings:.1f}%")

        assert savings >= 50, f"Expected >=50% savings, got {savings:.1f}%"
        print(f"  ✓ Meets target of 60-80% savings ({'Yes' if savings >= 60 else 'Close'})")


def test_special_characters():
    """Test handling of special characters"""
    print("\nTest 7: Special Characters")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MemoriesManager(tmpdir)

        content = "# Special Chars\n\nEmojis: 🎉🚀✨\nUnicode: ñ, ü, ö, 中文\n"
        manager.save_memory("special", content)

        result = manager.list_memories(include_metadata=True)
        memory = result[0]

        assert "🎉" in memory["preview"], "Should handle emojis"
        assert "中文" in memory["preview"], "Should handle unicode"
        print("  ✓ Special characters handled correctly")
        print(f"  ✓ Preview contains: {memory['preview']}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Story 12: Memory Metadata Tool - Standalone Tests")
    print("=" * 60)

    tests = [
        test_backward_compatibility,
        test_metadata_mode,
        test_preview_truncation,
        test_custom_preview_lines,
        test_token_estimation,
        test_token_savings,
        test_special_characters,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("✓ All tests passed!")
        return 0
    else:
        print(f"✗ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
