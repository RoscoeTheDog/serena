# Centralized Config Storage Architecture

**Status**: Design Phase
**Created**: 2025-11-05
**Author**: Sprint 2025-11-05 (Centralized Config Storage Refactor)

---

## Problem Statement

Serena currently creates a `.serena` directory in every project root containing:
- `project.yml` - project configuration
- `memories/` - project-specific memories

This pollutes user filesystems, especially problematic when:
1. Auto-initialization spawns in multiple directories
2. Users have many projects
3. `.serena` is in `.gitignore` but still clutters `git status`
4. Difficult to back up all Serena data (scattered across projects)

---

## Solution: Centralized Storage

Move all project-specific data to `~/.serena/projects/` using project identifiers.

### Storage Layout

```
~/.serena/
├── serena_config.yml           # Global config (already exists)
├── projects/                   # NEW: Centralized project data
│   ├── {project-id}/
│   │   ├── project.yml         # Project config
│   │   ├── memories/           # Project memories
│   │   │   ├── code_style_and_conventions.md
│   │   │   ├── project_overview.md
│   │   │   └── ...
│   │   └── metadata.json       # Optional: cached metadata
│   └── index.json              # Optional: quick lookup map
└── logs/                        # Global logs (already exists)
    └── {date}/
        └── mcp_*.txt
```

---

## Project Identifier Strategy

### Chosen Approach: SHA256 Hash (first 16 chars)

**Rationale**:
- ✅ Deterministic (same project always gets same ID)
- ✅ No path length issues
- ✅ No special character problems
- ✅ Collision-resistant (16 hex chars = 64 bits)
- ✅ Cross-platform compatible
- ✅ Anonymous (doesn't reveal project path)

**Implementation**:
```python
import hashlib
from pathlib import Path

def get_project_identifier(project_root: Path) -> str:
    """
    Generate a deterministic project identifier from absolute path.

    Args:
        project_root: Absolute path to project root

    Returns:
        16-character hex string (first 16 chars of SHA256 hash)

    Example:
        /home/user/projects/myapp -> "a1b2c3d4e5f6g7h8"
        C:\Users\Admin\Documents\GitHub\serena -> "f9e8d7c6b5a4321"
    """
    # Normalize path (resolve symlinks, convert to absolute)
    normalized = project_root.resolve()

    # Hash the string representation (lowercase for case-insensitive FS)
    path_str = str(normalized).lower()
    hash_obj = hashlib.sha256(path_str.encode('utf-8'))

    # Return first 16 hex characters
    return hash_obj.hexdigest()[:16]
```

### Alternative Approaches (Rejected)

1. **Sanitized Path** (`home_user_projects_myapp`)
   - ❌ Can be very long
   - ❌ Special character issues
   - ❌ Reveals project structure

2. **Project Name** (`myapp`)
   - ❌ Not unique (multiple projects with same name)
   - ❌ Conflicts on rename

3. **UUID** (random)
   - ❌ Not deterministic
   - ❌ Requires persistent mapping

---

## Path Resolution Helpers

### Core Functions

```python
# In src/serena/constants.py

def get_centralized_project_dir(project_root: Path) -> Path:
    """
    Get the centralized directory for a project's Serena data.

    Args:
        project_root: Absolute path to project root

    Returns:
        Path to ~/.serena/projects/{project-id}/
    """
    project_id = get_project_identifier(project_root)
    return Path.home() / ".serena" / "projects" / project_id

def get_project_config_path(project_root: Path) -> Path:
    """Get path to centralized project.yml"""
    return get_centralized_project_dir(project_root) / "project.yml"

def get_project_memories_path(project_root: Path) -> Path:
    """Get path to centralized memories directory"""
    return get_centralized_project_dir(project_root) / "memories"

def get_legacy_project_dir(project_root: Path) -> Path:
    """
    Get the legacy (old) .serena directory path in project root.
    Used for backward compatibility checks.
    """
    return project_root / ".serena"
```

### Directory Creation Strategy

**Lazy Creation**: Directories created only when first needed
- `get_centralized_project_dir()` creates `~/.serena/projects/{id}/`
- `get_project_memories_path()` creates `memories/` subdirectory
- Uses `mkdir(parents=True, exist_ok=True)` for safety

---

## Safe Default Configurations

### Philosophy

**"Junior Dev Friendly"**: Works great with no parameters, agents can request more when needed

**Optimization Goals**:
1. Search accuracy (find the right code)
2. Token efficiency (minimize context consumption)
3. Fail-safe defaults (hard to mess up)

### Default `project.yml` Template

```yaml
# Serena Project Configuration
# Auto-generated on {timestamp}

project_name: {project_name}
language: {detected_language}

# Search behavior
search_scope: "source"           # Exclude generated/vendor files (95% use case)
                                  # Options: "all", "source", "custom"

# Token management
max_answer_chars: -1             # Use global default (150,000 chars)
                                  # Set positive value to override per-project

# Tool output defaults
result_format: "summary"         # Token-efficient summaries by default
                                  # Options: "summary", "detailed"
                                  # Agents can override per-call

match_mode: "exact"              # Precise symbol matching
                                  # Options: "exact", "substring", "glob", "regex"
                                  # Agents escalate if nothing found

# Context behavior
include_metadata: true           # Provide rich context for decisions
                                  # Helps agents understand without reading full code

# Path filtering
ignored_paths: []                # Additional paths to ignore (beyond search_scope)
                                  # Example: ["internal/", "temp/"]

# File handling
ignore_all_files_in_gitignore: true  # Respect .gitignore (standard behavior)
read_only: false                 # Allow write operations

# Encoding
encoding: "utf-8"                # Default text encoding
```

### Rationale for Each Default

| Setting | Default | Rationale |
|---------|---------|-----------|
| `search_scope` | `"source"` | 95% of queries target source code, not generated files |
| `max_answer_chars` | `-1` | Use global limit (prevents per-project override complexity) |
| `result_format` | `"summary"` | 60-80% token savings, agents request `"detailed"` when needed |
| `match_mode` | `"exact"` | Precise first, agents can escalate to `"substring"` if nothing found |
| `include_metadata` | `true` | Rich context helps agents make decisions without full code reads |
| `ignore_all_files_in_gitignore` | `true` | Standard Git behavior, users expect this |
| `read_only` | `false` | Allow edits by default (Serena is for active development) |

---

## Backward Compatibility Strategy

### Migration Approach

**Automatic Migration on Project Activation**:

1. **Check centralized config**: Does `~/.serena/projects/{id}/project.yml` exist?
   - ✅ Yes: Use centralized config
   - ❌ No: Proceed to step 2

2. **Check legacy config**: Does `{project_root}/.serena/project.yml` exist?
   - ✅ Yes: Migrate automatically
   - ❌ No: Auto-generate new config

3. **Migration Steps**:
   ```python
   def migrate_project_data(project_root: Path, remove_old: bool = False):
       """
       Migrate project data from legacy to centralized location.

       Args:
           project_root: Absolute path to project root
           remove_old: If True, remove legacy .serena directory after migration
       """
       legacy_dir = get_legacy_project_dir(project_root)
       centralized_dir = get_centralized_project_dir(project_root)

       if not legacy_dir.exists():
           return  # Nothing to migrate

       # Create centralized directory
       centralized_dir.mkdir(parents=True, exist_ok=True)

       # Migrate project.yml
       legacy_config = legacy_dir / "project.yml"
       if legacy_config.exists():
           shutil.copy2(legacy_config, centralized_dir / "project.yml")

       # Migrate memories directory
       legacy_memories = legacy_dir / "memories"
       if legacy_memories.exists():
           shutil.copytree(
               legacy_memories,
               centralized_dir / "memories",
               dirs_exist_ok=True
           )

       # Log migration
       log.info(f"Migrated {project_root.name} from {legacy_dir} to {centralized_dir}")

       # Optionally remove old directory
       if remove_old:
           shutil.rmtree(legacy_dir)
           log.info(f"Removed legacy .serena directory from {project_root}")
   ```

4. **Migration Triggers**:
   - Automatic: On project activation via `activate_project_from_path_or_name()`
   - Manual: New MCP tool `migrate_project_config(project_path, remove_old=False)`

### Backward Read Fallback

**Config Loading Priority**:
1. Read centralized: `~/.serena/projects/{id}/project.yml`
2. If not found, read legacy: `{project_root}/.serena/project.yml`
3. If not found, auto-generate new centralized config

**Memory Loading Priority**:
1. Read centralized: `~/.serena/projects/{id}/memories/`
2. If not found, read legacy: `{project_root}/.serena/memories/`
3. If not found, create empty centralized memories dir

---

## MCP Tools for Config Management

### Tool Signatures

```python
def get_project_config(project_path: str) -> dict:
    """
    Retrieve current project configuration.

    Args:
        project_path: Absolute path to project root

    Returns:
        {
            "project_name": str,
            "language": str,
            "search_scope": str,
            "max_answer_chars": int,
            "result_format": str,
            "match_mode": str,
            "include_metadata": bool,
            "storage_location": str,  # centralized or legacy
            ...
        }
    """

def update_project_config(
    project_path: str,
    **settings: Any
) -> dict:
    """
    Update project configuration settings.

    Args:
        project_path: Absolute path to project root
        **settings: Configuration keys to update

    Returns:
        Updated config dict

    Example:
        update_project_config(
            "/path/to/project",
            search_scope="all",
            max_answer_chars=200000
        )
    """

def reset_project_config(project_path: str) -> dict:
    """
    Reset project configuration to safe defaults.

    Args:
        project_path: Absolute path to project root

    Returns:
        Reset config dict
    """

def list_project_configs() -> list[dict]:
    """
    List all configured projects.

    Returns:
        [
            {
                "project_name": str,
                "project_path": str,
                "storage_location": str,
                "last_accessed": str,
                "config_summary": {...}
            },
            ...
        ]
    """

def migrate_project_config(
    project_path: str,
    remove_old: bool = False
) -> dict:
    """
    Manually trigger migration from legacy to centralized storage.

    Args:
        project_path: Absolute path to project root
        remove_old: If True, remove legacy .serena directory

    Returns:
        {
            "migrated": bool,
            "source": str,
            "destination": str,
            "files_migrated": list[str]
        }
    """
```

---

## Implementation Phases

### Phase 1: Foundation (Stories 1-3)
- Design document (this file)
- Path resolution helpers
- MCP config management tools

### Phase 2: Core Refactor (Stories 4-6)
- ProjectConfig refactor
- MemoriesManager refactor
- Project initialization update

### Phase 3: Migration & Polish (Stories 7-10)
- Migration logic
- Documentation updates
- Test updates
- Safe defaults

---

## Testing Strategy

### Unit Tests
- Path resolution helpers (cross-platform)
- Project identifier generation (deterministic)
- Config loading/saving (centralized paths)
- Migration logic (idempotent)

### Integration Tests
- Fresh project activation (creates centralized config)
- Legacy project migration (automatic)
- Config management tools (CRUD operations)
- Memory operations (centralized storage)

### Manual Testing
- Activate fresh project (no `.serena` created in project root)
- Activate legacy project (migration occurs)
- Modify config via MCP tools
- Verify backup/restore of `~/.serena/`

---

## Benefits Summary

| Benefit | Before | After |
|---------|--------|-------|
| **Project Pollution** | ✗ `.serena/` in every project | ✓ Clean project roots |
| **Backup** | ✗ Scattered across projects | ✓ Single `~/.serena/` backup |
| **Config Management** | ✗ Manual file editing | ✓ MCP tools + agents |
| **Migration** | N/A | ✓ Automatic on activation |
| **DB Resilience** | ✗ Mixed DB + FS | ✓ Precious data in FS |
| **Agent Experience** | ✗ Complex setup | ✓ Safe defaults + tools |

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Migration data loss | 🔴 HIGH | Copy (not move) during migration, add verify step |
| Hash collisions | 🟡 MEDIUM | 16 hex chars = 2^64 space, negligible risk |
| Cross-platform paths | 🟡 MEDIUM | Use `pathlib.Path`, extensive cross-platform testing |
| Backward compat | 🟢 LOW | Fallback reads from legacy location |
| Performance | 🟢 LOW | Hash computation is fast, cache project IDs |

---

## Future Enhancements

1. **Index File**: Add `~/.serena/projects/index.json` for O(1) project lookup
2. **Metadata Cache**: Store project metadata for faster loading
3. **Multi-Root Projects**: Support monorepos with multiple project configs
4. **Cloud Sync**: Optional sync to cloud storage (Dropbox, etc.)
5. **Config Versioning**: Track config schema versions for future migrations

---

## References

- Similar approach: [claude-context MCP server](https://github.com/modelcontextprotocol/servers/tree/main/src/claude-context)
- Sprint: `implementation/index.md` (Story 1)
- Related: `.gitignore` patterns, XDG Base Directory spec
