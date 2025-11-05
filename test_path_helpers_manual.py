"""
Manual test script for path resolution helpers.
This can be run directly without pytest to verify basic functionality.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path so we can import serena
sys.path.insert(0, str(Path(__file__).parent / "src"))

from serena.constants import (
    get_centralized_project_dir,
    get_legacy_project_dir,
    get_project_config_path,
    get_project_identifier,
    get_project_memories_path,
)


def test_deterministic():
    """Test that same path produces same identifier."""
    test_path = Path("C:/Users/Admin/Documents/GitHub/serena")
    id1 = get_project_identifier(test_path)
    id2 = get_project_identifier(test_path)
    assert id1 == id2, f"IDs don't match: {id1} != {id2}"
    assert len(id1) == 16, f"ID length wrong: {len(id1)} != 16"
    print(f"[PASS] Deterministic test passed: {id1}")


def test_different_paths():
    """Test that different paths produce different IDs."""
    path1 = Path("C:/Users/Admin/project1")
    path2 = Path("C:/Users/Admin/project2")
    id1 = get_project_identifier(path1)
    id2 = get_project_identifier(path2)
    assert id1 != id2, f"IDs should differ: {id1} == {id2}"
    print(f"[PASS] Different paths test passed: {id1} vs {id2}")


def test_centralized_dir():
    """Test centralized directory creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "test_project"
        test_path.mkdir()

        result = get_centralized_project_dir(test_path)
        assert result.exists(), f"Directory not created: {result}"
        assert result.is_dir(), f"Not a directory: {result}"
        assert ".serena" in str(result), f"Missing .serena in path: {result}"
        assert "projects" in str(result), f"Missing projects in path: {result}"

        project_id = get_project_identifier(test_path)
        assert result.name == project_id, f"Dir name mismatch: {result.name} != {project_id}"

        print(f"[PASS] Centralized dir test passed: {result}")


def test_config_path():
    """Test config path generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "test_project"
        test_path.mkdir()

        result = get_project_config_path(test_path)
        assert result.name == "project.yml", f"Wrong filename: {result.name}"
        assert result.parent.exists(), f"Parent doesn't exist: {result.parent}"

        centralized = get_centralized_project_dir(test_path)
        assert result.parent == centralized, f"Parent mismatch: {result.parent} != {centralized}"

        print(f"[PASS] Config path test passed: {result}")


def test_memories_path():
    """Test memories path generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "test_project"
        test_path.mkdir()

        result = get_project_memories_path(test_path)
        assert result.exists(), f"Memories dir not created: {result}"
        assert result.is_dir(), f"Not a directory: {result}"
        assert result.name == "memories", f"Wrong name: {result.name}"

        centralized = get_centralized_project_dir(test_path)
        assert result.parent == centralized, f"Parent mismatch: {result.parent} != {centralized}"

        print(f"[PASS] Memories path test passed: {result}")


def test_legacy_path():
    """Test legacy path generation."""
    test_path = Path("C:/Users/Admin/Documents/GitHub/myapp")
    result = get_legacy_project_dir(test_path)

    assert result == test_path / ".serena", f"Wrong path: {result}"
    assert result.name == ".serena", f"Wrong name: {result.name}"
    assert result.parent == test_path, f"Wrong parent: {result.parent}"

    print(f"[PASS] Legacy path test passed: {result}")


def test_hex_validity():
    """Test that identifiers are valid hex."""
    test_path = Path("C:/Users/Admin/Documents/GitHub/serena")
    project_id = get_project_identifier(test_path)

    try:
        int(project_id, 16)
        print(f"[PASS] Hex validity test passed: {project_id}")
    except ValueError as e:
        raise AssertionError(f"ID is not valid hex: {project_id}") from e


def test_windows_paths():
    """Test Windows-specific path handling."""
    paths = [
        Path("C:/Users/Admin/Documents"),
        Path("C:\\Users\\Admin\\Documents"),
        Path("D:/Projects/MyApp"),
    ]

    for path in paths:
        project_id = get_project_identifier(path)
        assert len(project_id) == 16, f"Wrong length for {path}: {len(project_id)}"
        int(project_id, 16)  # Should not raise

    print(f"[PASS] Windows paths test passed")


def test_idempotent():
    """Test that repeated calls return same results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "test_project"
        test_path.mkdir()

        # Call multiple times
        dir1 = get_centralized_project_dir(test_path)
        dir2 = get_centralized_project_dir(test_path)
        dir3 = get_centralized_project_dir(test_path)

        mem1 = get_project_memories_path(test_path)
        mem2 = get_project_memories_path(test_path)
        mem3 = get_project_memories_path(test_path)

        assert dir1 == dir2 == dir3, f"Dirs don't match"
        assert mem1 == mem2 == mem3, f"Memory dirs don't match"

        print(f"[PASS] Idempotent test passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Path Resolution Helpers")
    print("=" * 60)

    tests = [
        test_deterministic,
        test_different_paths,
        test_centralized_dir,
        test_config_path,
        test_memories_path,
        test_legacy_path,
        test_hex_validity,
        test_windows_paths,
        test_idempotent,
    ]

    failed = []
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"[FAIL] {test.__name__} FAILED: {e}")
            failed.append((test.__name__, e))

    print("=" * 60)
    if failed:
        print(f"FAILED: {len(failed)} test(s) failed")
        for name, error in failed:
            print(f"  - {name}: {error}")
        sys.exit(1)
    else:
        print(f"SUCCESS: All {len(tests)} tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
