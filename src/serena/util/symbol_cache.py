"""
Symbol cache with hash-based validation and delta updates.

This module provides a caching layer for symbol results to reduce token consumption.
Cache keys are based on file paths + content hashes to ensure validity.
"""

import hashlib
import json
import logging
import os
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """
    A single cache entry with metadata.
    """
    key: str
    data: Any
    file_hash: str
    timestamp: float
    hit_count: int = 0


class SymbolCache:
    """
    LRU cache for symbol results with hash-based validation.

    Features:
    - File hash-based cache keys (file_path:sha256)
    - Automatic invalidation on file changes
    - LRU eviction when memory limit reached
    - Delta updates showing what changed
    - Cache metadata in all responses
    """

    def __init__(self, max_entries: int = 500, project_root: str = "."):
        """
        Initialize the symbol cache.

        :param max_entries: Maximum number of cache entries (LRU eviction)
        :param project_root: Root directory of the project for resolving file paths
        """
        self.max_entries = max_entries
        self.project_root = project_root
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
            "evictions": 0
        }

    def _compute_file_hash(self, file_path: str) -> str | None:
        """
        Compute SHA256 hash of a file's contents.

        :param file_path: Path to file (relative to project root)
        :return: Hex digest of file hash, or None if file doesn't exist
        """
        try:
            full_path = os.path.join(self.project_root, file_path)
            if not os.path.exists(full_path):
                return None

            hasher = hashlib.sha256()
            with open(full_path, 'rb') as f:
                # Read in chunks for memory efficiency
                for chunk in iter(lambda: f.read(4096), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            log.warning(f"Failed to compute hash for {file_path}: {e}")
            return None

    def _make_cache_key(self, file_path: str, query_params: dict[str, Any] = None) -> str:
        """
        Generate a cache key from file path and optional query parameters.

        :param file_path: File path relative to project root
        :param query_params: Optional parameters that affect the query (e.g., include_body, depth)
        :return: Cache key string
        """
        # Normalize path separators
        normalized_path = file_path.replace("\\", "/")

        if query_params:
            # Sort params for consistent keys
            param_str = json.dumps(query_params, sort_keys=True)
            return f"{normalized_path}:{param_str}"

        return normalized_path

    def get(self, file_path: str, query_params: dict[str, Any] = None) -> tuple[bool, Any, dict[str, Any]]:
        """
        Get cached result if valid (file hasn't changed).

        :param file_path: File path relative to project root
        :param query_params: Optional query parameters that affect the result
        :return: Tuple of (cache_hit: bool, data: Any, metadata: dict)
        """
        cache_key = self._make_cache_key(file_path, query_params)

        # Check if entry exists
        if cache_key not in self._cache:
            self._stats["misses"] += 1
            return False, None, {
                "cache_status": "miss",
                "reason": "no_entry"
            }

        entry = self._cache[cache_key]

        # Validate file hash
        current_hash = self._compute_file_hash(file_path)
        if current_hash is None:
            # File no longer exists - invalidate
            del self._cache[cache_key]
            self._stats["invalidations"] += 1
            return False, None, {
                "cache_status": "miss",
                "reason": "file_not_found"
            }

        if current_hash != entry.file_hash:
            # File changed - invalidate
            del self._cache[cache_key]
            self._stats["invalidations"] += 1
            return False, None, {
                "cache_status": "miss",
                "reason": "file_changed",
                "previous_hash": entry.file_hash[:8],
                "current_hash": current_hash[:8]
            }

        # Cache hit - move to end (LRU)
        self._cache.move_to_end(cache_key)
        entry.hit_count += 1
        self._stats["hits"] += 1

        metadata = {
            "cache_status": "hit",
            "cache_key": f"{file_path}:sha256:{current_hash[:8]}...",
            "cached_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(entry.timestamp)),
            "hit_count": entry.hit_count
        }

        return True, entry.data, metadata

    def put(self, file_path: str, data: Any, query_params: dict[str, Any] = None) -> dict[str, Any]:
        """
        Store result in cache with current file hash.

        :param file_path: File path relative to project root
        :param data: Data to cache
        :param query_params: Optional query parameters
        :return: Cache metadata
        """
        cache_key = self._make_cache_key(file_path, query_params)
        file_hash = self._compute_file_hash(file_path)

        if file_hash is None:
            log.warning(f"Cannot cache result for {file_path} - file not found")
            return {"cache_status": "not_cached", "reason": "file_not_found"}

        # LRU eviction if at capacity
        if len(self._cache) >= self.max_entries and cache_key not in self._cache:
            self._cache.popitem(last=False)  # Remove oldest
            self._stats["evictions"] += 1

        entry = CacheEntry(
            key=cache_key,
            data=data,
            file_hash=file_hash,
            timestamp=time.time()
        )

        self._cache[cache_key] = entry
        self._cache.move_to_end(cache_key)  # Mark as most recent

        return {
            "cache_status": "cached",
            "cache_key": f"{file_path}:sha256:{file_hash[:8]}...",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(entry.timestamp))
        }

    def invalidate_file(self, file_path: str) -> int:
        """
        Invalidate all cache entries for a specific file.

        :param file_path: File path relative to project root
        :return: Number of entries invalidated
        """
        normalized_path = file_path.replace("\\", "/")
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(normalized_path + ":") or k == normalized_path]

        for key in keys_to_remove:
            del self._cache[key]
            self._stats["invalidations"] += 1

        if keys_to_remove:
            log.debug(f"Invalidated {len(keys_to_remove)} cache entries for {file_path}")

        return len(keys_to_remove)

    def invalidate_all(self) -> int:
        """
        Clear entire cache.

        :return: Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        self._stats["invalidations"] += count
        log.debug(f"Cleared all {count} cache entries")
        return count

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        :return: Dictionary with cache stats
        """
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate_percent": round(hit_rate, 2),
            "invalidations": self._stats["invalidations"],
            "evictions": self._stats["evictions"]
        }

    def compute_delta(self, old_file_paths: set[str], new_file_paths: set[str]) -> dict[str, Any]:
        """
        Compute delta between two sets of file paths.

        This is useful for showing what changed when caches are invalidated.

        :param old_file_paths: Previous set of file paths
        :param new_file_paths: Current set of file paths
        :return: Delta information
        """
        added = new_file_paths - old_file_paths
        removed = old_file_paths - new_file_paths
        common = old_file_paths & new_file_paths

        # Check which common files actually changed
        modified = set()
        for file_path in common:
            # Check if any cache entry for this file was invalidated
            normalized_path = file_path.replace("\\", "/")
            cache_exists = any(k.startswith(normalized_path + ":") or k == normalized_path for k in self._cache.keys())
            if not cache_exists:
                # Cache was invalidated, so file likely changed
                modified.add(file_path)

        return {
            "added_files": sorted(list(added)),
            "removed_files": sorted(list(removed)),
            "modified_files": sorted(list(modified)),
            "total_changes": len(added) + len(removed) + len(modified)
        }


# Global cache instance (singleton pattern)
_global_cache: SymbolCache | None = None


def get_global_cache(project_root: str = ".") -> SymbolCache:
    """
    Get or create the global symbol cache instance.

    :param project_root: Project root directory
    :return: Global SymbolCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = SymbolCache(project_root=project_root)
    return _global_cache


def reset_global_cache():
    """
    Reset the global cache instance (useful for testing).
    """
    global _global_cache
    _global_cache = None
