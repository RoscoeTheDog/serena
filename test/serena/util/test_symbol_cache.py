"""
Tests for symbol cache with hash validation and delta updates.
"""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from serena.util.symbol_cache import SymbolCache, get_global_cache, reset_global_cache


class TestSymbolCache:
    """Test suite for SymbolCache"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def cache(self, temp_dir):
        """Create a fresh cache instance"""
        return SymbolCache(max_entries=10, project_root=temp_dir)

    @pytest.fixture
    def test_file(self, temp_dir):
        """Create a test file"""
        file_path = os.path.join(temp_dir, "test.py")
        with open(file_path, "w") as f:
            f.write("def hello():\n    return 'world'\n")
        return "test.py"

    def test_cache_miss_no_entry(self, cache):
        """Test cache miss when no entry exists"""
        cache_hit, data, metadata = cache.get("nonexistent.py")
        assert not cache_hit
        assert data is None
        assert metadata["cache_status"] == "miss"
        assert metadata["reason"] == "no_entry"

    def test_cache_hit(self, cache, test_file):
        """Test successful cache hit"""
        test_data = {"symbols": [{"name": "hello", "kind": "Function"}]}

        # Store data
        put_metadata = cache.put(test_file, test_data)
        assert put_metadata["cache_status"] == "cached"
        assert "cache_key" in put_metadata

        # Retrieve data
        cache_hit, data, metadata = cache.get(test_file)
        assert cache_hit
        assert data == test_data
        assert metadata["cache_status"] == "hit"
        assert metadata["hit_count"] == 1

    def test_cache_invalidation_file_changed(self, cache, test_file, temp_dir):
        """Test cache invalidation when file changes"""
        test_data = {"symbols": [{"name": "hello"}]}

        # Cache initial data
        cache.put(test_file, test_data)

        # Modify file
        time.sleep(0.01)  # Ensure different timestamp
        file_path = os.path.join(temp_dir, test_file)
        with open(file_path, "w") as f:
            f.write("def hello():\n    return 'universe'\n")

        # Try to retrieve - should be invalidated
        cache_hit, data, metadata = cache.get(test_file)
        assert not cache_hit
        assert metadata["cache_status"] == "miss"
        assert metadata["reason"] == "file_changed"
        assert "previous_hash" in metadata
        assert "current_hash" in metadata

    def test_cache_invalidation_file_deleted(self, cache, test_file, temp_dir):
        """Test cache invalidation when file is deleted"""
        test_data = {"symbols": [{"name": "hello"}]}

        # Cache data
        cache.put(test_file, test_data)

        # Delete file
        file_path = os.path.join(temp_dir, test_file)
        os.remove(file_path)

        # Try to retrieve - should be invalidated
        cache_hit, data, metadata = cache.get(test_file)
        assert not cache_hit
        assert metadata["cache_status"] == "miss"
        assert metadata["reason"] == "file_not_found"

    def test_query_params_different_results(self, cache, test_file):
        """Test that different query params create separate cache entries"""
        data1 = {"symbols": [{"name": "hello"}]}
        data2 = {"symbols": [{"name": "hello", "body": "def hello():\n    return 'world'\n"}]}

        # Cache with different params
        cache.put(test_file, data1, query_params={"include_body": False})
        cache.put(test_file, data2, query_params={"include_body": True})

        # Retrieve with matching params
        hit1, retrieved1, _ = cache.get(test_file, query_params={"include_body": False})
        hit2, retrieved2, _ = cache.get(test_file, query_params={"include_body": True})

        assert hit1 and hit2
        assert retrieved1 == data1
        assert retrieved2 == data2

    def test_lru_eviction(self, temp_dir):
        """Test LRU eviction when cache is full"""
        cache = SymbolCache(max_entries=3, project_root=temp_dir)

        # Create test files
        files = []
        for i in range(4):
            file_path = os.path.join(temp_dir, f"test{i}.py")
            with open(file_path, "w") as f:
                f.write(f"def func{i}(): pass\n")
            files.append(f"test{i}.py")

        # Fill cache
        for i in range(3):
            cache.put(files[i], {"data": i})

        # Add 4th entry - should evict first
        cache.put(files[3], {"data": 3})

        # Check that first entry was evicted
        hit0, _, _ = cache.get(files[0])
        assert not hit0

        # Check that others are still cached
        for i in range(1, 4):
            hit, data, _ = cache.get(files[i])
            assert hit
            assert data == {"data": i}

    def test_invalidate_file_explicit(self, cache, test_file):
        """Test explicit file invalidation"""
        test_data = {"symbols": [{"name": "hello"}]}

        # Cache with multiple query params
        cache.put(test_file, test_data, query_params={"param1": "a"})
        cache.put(test_file, test_data, query_params={"param2": "b"})

        # Invalidate all entries for file
        count = cache.invalidate_file(test_file)
        assert count == 2

        # Verify all entries are gone
        hit1, _, _ = cache.get(test_file, query_params={"param1": "a"})
        hit2, _, _ = cache.get(test_file, query_params={"param2": "b"})
        assert not hit1 and not hit2

    def test_invalidate_all(self, cache, temp_dir):
        """Test clearing entire cache"""
        # Create and cache multiple files
        for i in range(3):
            file_path = os.path.join(temp_dir, f"test{i}.py")
            with open(file_path, "w") as f:
                f.write(f"def func{i}(): pass\n")
            cache.put(f"test{i}.py", {"data": i})

        # Clear cache
        count = cache.invalidate_all()
        assert count == 3

        # Verify all gone
        for i in range(3):
            hit, _, _ = cache.get(f"test{i}.py")
            assert not hit

    def test_cache_stats(self, cache, test_file):
        """Test cache statistics"""
        # Initial stats
        stats = cache.get_stats()
        assert stats["entries"] == 0
        assert stats["hits"] == 0
        assert stats["misses"] == 0

        # Cache miss
        cache.get(test_file)
        stats = cache.get_stats()
        assert stats["misses"] == 1

        # Cache put and hit
        cache.put(test_file, {"data": "test"})
        cache.get(test_file)
        cache.get(test_file)
        stats = cache.get_stats()
        assert stats["entries"] == 1
        assert stats["hits"] == 2
        assert stats["hit_rate_percent"] > 0

    def test_compute_delta(self, cache):
        """Test delta computation between file sets"""
        old_files = {"file1.py", "file2.py", "file3.py"}
        new_files = {"file2.py", "file3.py", "file4.py"}

        delta = cache.compute_delta(old_files, new_files)

        assert "file4.py" in delta["added_files"]
        assert "file1.py" in delta["removed_files"]
        assert delta["total_changes"] >= 2

    def test_global_cache_singleton(self):
        """Test global cache singleton pattern"""
        reset_global_cache()

        cache1 = get_global_cache()
        cache2 = get_global_cache()

        assert cache1 is cache2

        # Cleanup
        reset_global_cache()

    def test_hit_count_increments(self, cache, test_file):
        """Test that hit count increments on repeated access"""
        cache.put(test_file, {"data": "test"})

        # Multiple hits
        for i in range(5):
            hit, _, metadata = cache.get(test_file)
            assert hit
            assert metadata["hit_count"] == i + 1

    def test_cache_with_json_data(self, cache, test_file):
        """Test caching JSON-serialized data (realistic use case)"""
        test_data = {
            "_schema": "structured_v1",
            "file": "test.py",
            "symbols": [
                {"name": "hello", "kind": "Function", "line": 1},
                {"name": "world", "kind": "Function", "line": 5}
            ]
        }

        # Store JSON string (as tools do)
        cache.put(test_file, json.dumps(test_data))

        # Retrieve and parse
        hit, cached_json, _ = cache.get(test_file)
        assert hit
        parsed_data = json.loads(cached_json)
        assert parsed_data == test_data
