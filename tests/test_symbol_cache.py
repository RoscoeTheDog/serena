"""
Unit tests for symbol_cache module.
"""

import hashlib
import os
import tempfile
import time
from pathlib import Path

import pytest

from serena.util.symbol_cache import SymbolCache, get_global_cache, reset_global_cache


@pytest.fixture
def temp_project():
    """Create a temporary project directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        test_file1 = Path(tmpdir) / "test1.py"
        test_file1.write_text("def hello():\n    return 'world'\n")

        test_file2 = Path(tmpdir) / "test2.py"
        test_file2.write_text("class Foo:\n    pass\n")

        yield tmpdir


@pytest.fixture
def cache(temp_project):
    """Create a fresh cache instance for each test."""
    return SymbolCache(max_entries=10, project_root=temp_project)


def test_cache_initialization():
    """Test cache initialization with default parameters."""
    cache = SymbolCache()
    assert cache.max_entries == 500
    assert cache.project_root == "."
    assert len(cache._cache) == 0


def test_file_hash_computation(cache, temp_project):
    """Test file hash computation."""
    file_path = "test1.py"
    file_hash = cache._compute_file_hash(file_path)

    assert file_hash is not None
    assert len(file_hash) == 64  # SHA256 hex digest length

    # Verify hash is consistent
    file_hash2 = cache._compute_file_hash(file_path)
    assert file_hash == file_hash2


def test_file_hash_nonexistent_file(cache):
    """Test hash computation for non-existent file."""
    file_hash = cache._compute_file_hash("nonexistent.py")
    assert file_hash is None


def test_cache_key_generation(cache):
    """Test cache key generation."""
    key1 = cache._make_cache_key("test.py")
    assert key1 == "test.py"

    key2 = cache._make_cache_key("test.py", {"include_body": True, "depth": 1})
    assert "test.py" in key2
    assert "include_body" in key2


def test_cache_put_and_get(cache, temp_project):
    """Test basic cache put and get operations."""
    file_path = "test1.py"
    test_data = {"symbols": ["hello"]}

    # Put data in cache
    metadata = cache.put(file_path, test_data)
    assert metadata["cache_status"] == "cached"
    assert "cache_key" in metadata

    # Get data from cache
    hit, data, get_metadata = cache.get(file_path)
    assert hit is True
    assert data == test_data
    assert get_metadata["cache_status"] == "hit"


def test_cache_miss_no_entry(cache):
    """Test cache miss when entry doesn't exist."""
    hit, data, metadata = cache.get("nonexistent.py")
    assert hit is False
    assert data is None
    assert metadata["cache_status"] == "miss"
    assert metadata["reason"] == "no_entry"


def test_cache_invalidation_on_file_change(cache, temp_project):
    """Test cache invalidation when file content changes."""
    file_path = "test1.py"
    test_data = {"symbols": ["hello"]}

    # Cache the data
    cache.put(file_path, test_data)

    # Verify cache hit
    hit, data, _ = cache.get(file_path)
    assert hit is True

    # Modify the file
    full_path = Path(temp_project) / file_path
    full_path.write_text("def hello():\n    return 'changed'\n")

    # Verify cache miss due to file change
    hit, data, metadata = cache.get(file_path)
    assert hit is False
    assert metadata["cache_status"] == "miss"
    assert metadata["reason"] == "file_changed"


def test_cache_with_query_params(cache, temp_project):
    """Test caching with different query parameters."""
    file_path = "test1.py"
    data1 = {"symbols": ["hello"], "include_body": False}
    data2 = {"symbols": ["hello"], "include_body": True, "body": "..."}

    # Cache with different parameters
    cache.put(file_path, data1, {"include_body": False})
    cache.put(file_path, data2, {"include_body": True})

    # Get with matching parameters
    hit1, retrieved1, _ = cache.get(file_path, {"include_body": False})
    hit2, retrieved2, _ = cache.get(file_path, {"include_body": True})

    assert hit1 is True
    assert retrieved1 == data1
    assert hit2 is True
    assert retrieved2 == data2


def test_lru_eviction(cache, temp_project):
    """Test LRU eviction when cache reaches max capacity."""
    # Cache is set to max_entries=10
    # Add 11 entries to trigger eviction
    for i in range(11):
        file_path = f"test{i}.py"
        # Create the file
        full_path = Path(temp_project) / file_path
        full_path.write_text(f"# File {i}\n")

        cache.put(file_path, {"file": i})

    # Verify cache size is at max
    assert len(cache._cache) == 10

    # First entry should have been evicted
    hit, _, _ = cache.get("test0.py")
    assert hit is False

    # Last entry should still be there
    hit, _, _ = cache.get("test10.py")
    assert hit is True


def test_invalidate_file(cache, temp_project):
    """Test explicit file invalidation."""
    file_path = "test1.py"

    # Cache with different query params
    cache.put(file_path, {"data": 1}, {"param": "a"})
    cache.put(file_path, {"data": 2}, {"param": "b"})

    # Verify both are cached
    assert len(cache._cache) == 2

    # Invalidate the file
    count = cache.invalidate_file(file_path)
    assert count == 2
    assert len(cache._cache) == 0


def test_invalidate_all(cache, temp_project):
    """Test invalidating all cache entries."""
    # Cache multiple files
    cache.put("test1.py", {"data": 1})
    cache.put("test2.py", {"data": 2})

    assert len(cache._cache) == 2

    # Invalidate all
    count = cache.invalidate_all()
    assert count == 2
    assert len(cache._cache) == 0


def test_get_stats(cache, temp_project):
    """Test cache statistics."""
    file_path = "test1.py"

    # Initial stats
    stats = cache.get_stats()
    assert stats["entries"] == 0
    assert stats["hits"] == 0
    assert stats["misses"] == 0

    # Cache miss
    cache.get(file_path)
    stats = cache.get_stats()
    assert stats["misses"] == 1

    # Cache put and hit
    cache.put(file_path, {"data": 1})
    cache.get(file_path)
    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["entries"] == 1
    assert stats["hit_rate_percent"] == 50.0  # 1 hit, 1 miss


def test_compute_delta():
    """Test delta computation between file sets."""
    cache = SymbolCache()

    old_files = {"file1.py", "file2.py", "file3.py"}
    new_files = {"file2.py", "file3.py", "file4.py"}

    delta = cache.compute_delta(old_files, new_files)

    assert "file1.py" in delta["removed_files"]
    assert "file4.py" in delta["added_files"]
    assert delta["total_changes"] >= 2


def test_global_cache_singleton(temp_project):
    """Test global cache singleton behavior."""
    reset_global_cache()

    cache1 = get_global_cache(temp_project)
    cache2 = get_global_cache(temp_project)

    assert cache1 is cache2

    reset_global_cache()


def test_cache_hit_count(cache, temp_project):
    """Test hit count tracking."""
    file_path = "test1.py"
    cache.put(file_path, {"data": 1})

    # Multiple hits
    for i in range(3):
        hit, data, metadata = cache.get(file_path)
        assert hit is True
        assert metadata["hit_count"] == i + 1


def test_cache_with_path_normalization(cache, temp_project):
    """Test that paths with different separators are normalized."""
    # Put with forward slash
    cache.put("subdir/test.py", {"data": 1})

    # Get with backslash (should be normalized)
    key1 = cache._make_cache_key("subdir/test.py")
    key2 = cache._make_cache_key("subdir\\test.py")

    # Keys should match after normalization
    assert "/" in key1
    assert "/" in key2
    assert "\\" not in key1
    assert "\\" not in key2


def test_cache_timestamp(cache, temp_project):
    """Test that cache entries include timestamps."""
    file_path = "test1.py"

    before = time.time()
    cache.put(file_path, {"data": 1})
    after = time.time()

    hit, data, metadata = cache.get(file_path)
    assert hit is True
    assert "cached_at" in metadata

    # Parse timestamp and verify it's within reasonable range
    cached_time = time.strptime(metadata["cached_at"], "%Y-%m-%dT%H:%M:%SZ")
    cached_timestamp = time.mktime(cached_time)
    assert before <= cached_timestamp <= after + 2  # Allow small tolerance


def test_cache_file_not_found_after_caching(cache, temp_project):
    """Test cache miss when file is deleted after caching."""
    file_path = "temp_test.py"

    # Create and cache file
    full_path = Path(temp_project) / file_path
    full_path.write_text("# Temp file\n")
    cache.put(file_path, {"data": 1})

    # Verify cache hit
    hit, _, _ = cache.get(file_path)
    assert hit is True

    # Delete the file
    full_path.unlink()

    # Verify cache miss
    hit, data, metadata = cache.get(file_path)
    assert hit is False
    assert metadata["reason"] == "file_not_found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
