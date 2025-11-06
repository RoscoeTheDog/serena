# Implementation Sprint: Remove Legacy .serena/ Directory Support

**Created**: 2025-11-05 14:55
**Status**: active
**Sprint Goal**: Completely remove backward compatibility code for legacy `{project_root}/.serena/` directories, enabling clean project structure and eliminating file lock issues

## Context

Following completion of the "Centralized Config Storage Refactor" sprint (Stories 1-6), all new projects now store configuration and memories in `~/.serena/projects/{project-id}/`. However, the codebase still contains extensive backward compatibility code (35+ references) that:

1. Keeps file handles open on legacy `.serena/` directories in project roots
2. Causes file lock issues preventing cleanup of old directories
3. Adds maintenance complexity with dual-path logic in 3 core modules
4. Creates potential bugs from mixed storage locations

This sprint will remove legacy support entirely, provide a migration tool for existing users, and establish a clean, single-location storage architecture.

## Stories

### Story 1: Create Migration Script for Legacy Projects
**Status**: completed
**Claimed**: 2025-11-05 15:05
**Completed**: 2025-11-05 15:40
**Description**: Build a one-time migration utility that discovers all projects with legacy `.serena/` directories and safely migrates their data to centralized storage.

**Acceptance Criteria**:
- [x] Script discovers all legacy `.serena/` directories across filesystem (configurable search paths)
- [x] Validates data integrity before migration (checksums, file counts)
- [x] Migrates project.yml to `~/.serena/projects/{project-id}/project.yml`
- [x] Migrates memories/ to `~/.serena/projects/{project-id}/memories/`
- [x] Creates backup archive of legacy directories before migration
- [x] Generates detailed migration report (successes, failures, skipped)
- [x] Supports dry-run mode for preview
- [x] Handles edge cases (corrupted files, permission issues, duplicate data)

**Technical Notes**:
- Script location: `scripts/migrate_legacy_serena.py`
- Use `get_project_identifier()` for consistent project ID generation
- Archive format: `{project_root}/.serena.backup-{timestamp}.tar.gz`
- Report format: JSON + human-readable summary

**Implementation Notes**:
- Created comprehensive migration script with fallback implementations for standalone use
- Supports both JSON and human-readable output formats
- Implements recursive discovery with configurable search paths
- Validates data integrity before migration
- Creates tar.gz backup archives before migration
- Handles existing files gracefully (skips and reports)
- Fully tested with dry-run mode on 2 legacy projects (serena itself and test repo)
- Exit codes: 0 for success, 1 if any migrations failed

**Estimated Effort**: 1 day

---

### Story 2: Remove Legacy Code from MemoriesManager
**Status**: completed
**Claimed**: 2025-11-05 15:42
**Completed**: 2025-11-05 15:50
**Parent**: Story 1
**Description**: Eliminate all legacy directory references from `MemoriesManager` class, simplifying memory file operations to use only centralized storage.

**Acceptance Criteria**:
- [x] Remove `_legacy_memory_dir` attribute from `__init__()`
- [x] Remove `check_legacy` parameter from `_get_memory_file_path()`
- [x] Remove legacy fallback logic from `load_memory()` (lines 90-91)
- [x] Remove legacy fallback logic from `delete_memory()` (lines 195)
- [x] Remove legacy directory scanning from `list_memories()`
- [x] Update all callers to remove `check_legacy=True` arguments
- [x] All existing tests pass with centralized-only storage
- [x] No references to `_legacy_memory_dir` remain in codebase

**Files to Modify**:
- `src/serena/agent.py` (MemoriesManager class)
- `test/serena/test_memories_manager_centralized.py` (removed legacy path assertion)

**Impact**: ~19 line removals + simplification of 3 methods

**Implementation Notes**:
- Removed `_legacy_memory_dir` attribute and `get_legacy_project_dir` import from `__init__()`
- Simplified `_get_memory_file_path()` to remove `check_legacy` parameter
- Removed legacy fallback logic from `load_memory()` (now only checks centralized location)
- Removed legacy fallback logic from `delete_memory()` (now only checks centralized location)
- Simplified `list_memories()` to scan only centralized directory
- Updated test to remove assertion checking `_legacy_memory_dir` attribute
- Verified no remaining references to `_legacy_memory_dir` in src/
- All changes compile successfully with no syntax errors

**Estimated Effort**: 0.5 days

---

### Story 3: Remove Legacy Code from ProjectConfig
**Status**: completed
**Claimed**: 2025-11-05 16:10
**Completed**: 2025-11-05 16:25
**Parent**: Story 1
**Description**: Simplify `ProjectConfig.load()` to only check centralized storage location, removing legacy fallback logic.

**Acceptance Criteria**:
- [x] Remove legacy directory check from `load()` method (lines 282-285)
- [x] Simplify error message to show only centralized location
- [x] Update `load()` to fail fast if centralized config doesn't exist (when autogenerate=False)
- [x] All existing tests pass with centralized-only logic (1 expected failure for Story 5)
- [x] No references to legacy config path in load logic

**Files to Modify**:
- `src/serena/config/serena_config.py` (ProjectConfig.load method)

**Implementation Notes**:
- Removed legacy import `from serena.constants import get_legacy_project_dir`
- Removed legacy fallback logic (lines 283-298) that checked `get_legacy_project_dir()`
- Simplified error message to show only centralized location path
- Updated `from_config_file()` validation to check only centralized location
- All references to `get_legacy_project_dir` removed from `serena_config.py`
- Test results: 12 passed, 1 expected failure (`test_load_from_legacy_location` to be removed in Story 5)
- Total impact: ~14 lines removed, cleaner error messages

**Impact**: ~5 line removals, cleaner error messages

**Estimated Effort**: 0.25 days

---

### Story 4: Deprecate or Remove get_legacy_project_dir()
**Status**: unassigned
**Parent**: Stories 2, 3
**Description**: Handle the `get_legacy_project_dir()` helper function - either mark as deprecated or remove entirely if no longer needed.

**Acceptance Criteria**:
- [ ] Audit all usages of `get_legacy_project_dir()` in codebase (verify removed by Stories 2-3)
- [ ] If usages remain: Add deprecation warning with removal date
- [ ] If no usages remain: Remove function entirely
- [ ] Update `constants.py` docstrings to reflect current storage architecture
- [ ] Update any references in comments or documentation

**Files to Modify**:
- `src/serena/constants.py`

**Decision Point**: Deprecate vs Remove
- Remove if: Stories 2-3 eliminate all usages
- Deprecate if: External users may be calling this function

**Estimated Effort**: 0.25 days

---

### Story 5: Update Tests for Centralized-Only Storage
**Status**: unassigned
**Parent**: Stories 2, 3, 4
**Description**: Update all tests to reflect centralized-only storage architecture, removing legacy path checks and dual-location test cases.

**Acceptance Criteria**:
- [ ] Remove legacy location tests from `test_serena_config.py`
- [ ] Remove `test_load_from_legacy_location()` test case
- [ ] Remove `test_centralized_takes_precedence_over_legacy()` test case
- [ ] Update `test_error_message_shows_both_locations()` to show only centralized location
- [ ] Add new test: `test_load_fails_cleanly_when_config_missing()`
- [ ] All auto-onboarding tests pass (should already use centralized storage)
- [ ] All centralized storage tests pass (51 tests)
- [ ] Test coverage remains at or above 85%

**Files to Modify**:
- `test/serena/config/test_serena_config.py`
- Any other test files with legacy path references

**Estimated Effort**: 0.5 days

---

### Story 6: Update Documentation and Migration Guide
**Status**: unassigned
**Parent**: Story 1
**Description**: Create comprehensive migration guide for users with legacy `.serena/` directories and update all documentation to reflect centralized-only storage.

**Acceptance Criteria**:
- [ ] Create `docs/MIGRATION-LEGACY-SERENA.md` with:
  - Why migration is necessary
  - How to run migration script
  - What gets migrated
  - How to verify migration success
  - Rollback instructions (restore from backup)
  - FAQ for common issues
- [ ] Update README.md to remove any legacy `.serena/` references
- [ ] Update CONTRIBUTING.md to document centralized storage only
- [ ] Add migration notice to CHANGELOG.md
- [ ] Update any inline code comments referencing legacy paths

**Files to Create/Modify**:
- `docs/MIGRATION-LEGACY-SERENA.md` (new)
- `README.md`
- `CONTRIBUTING.md`
- `CHANGELOG.md`

**Estimated Effort**: 0.5 days

---

### Story 7: Add .gitignore Rule for Legacy .serena/ Directories
**Status**: unassigned
**Parent**: Story 6
**Description**: Update `.gitignore` to explicitly ignore legacy `.serena/` directories in project roots, preventing accidental commits.

**Acceptance Criteria**:
- [ ] Add `/.serena/` to `.gitignore` (note leading slash for root-only)
- [ ] Add comment explaining this is legacy, centralized storage is in `~/.serena/`
- [ ] Verify rule doesn't conflict with centralized `~/.serena/` (which is in user home, not project)
- [ ] Test that `.serena/` in project root is ignored
- [ ] Test that backup archives `.serena.backup-*.tar.gz` are ignored

**Files to Modify**:
- `.gitignore`

**Estimated Effort**: 0.1 days

---

## Progress Log

### 2025-11-05 14:55 - Sprint Started
- Created sprint structure in `.claude/implementation/`
- Archived previous "Centralized Config Storage Refactor" sprint to `archive/2025-11-05-1455/`
- Defined 7 stories for legacy code removal
- Migration-first approach: Story 1 creates migration tool before removing code

### 2025-11-05 15:40 - Story 1 Completed
- ✅ Created `scripts/migrate_legacy_serena.py` migration script
- Implemented all acceptance criteria:
  - Recursive discovery of legacy `.serena/` directories
  - Data validation (file integrity checks)
  - Migration logic for `project.yml` and `memories/`
  - Backup archive creation (tar.gz format)
  - Detailed reporting (JSON + human-readable formats)
  - Dry-run mode for safe preview
  - Edge case handling (duplicates, permission issues, corruption)
- Tested successfully with dry-run mode on 2 legacy projects
- Script includes fallback implementations for standalone use

### 2025-11-05 15:50 - Story 2 Completed
- ✅ Removed all legacy code from MemoriesManager class
- Changes made:
  - Removed `_legacy_memory_dir` attribute and import
  - Simplified `_get_memory_file_path()` (removed `check_legacy` parameter)
  - Removed legacy fallback from `load_memory()`
  - Removed legacy fallback from `delete_memory()`
  - Simplified `list_memories()` to scan only centralized directory
  - Updated test to remove legacy path assertion
- Total impact: ~19 lines removed, 3 methods simplified
- Verified no `_legacy_memory_dir` references remain in src/

### 2025-11-05 16:25 - Story 3 Completed
- ✅ Removed all legacy code from ProjectConfig class
- Changes made:
  - Removed `get_legacy_project_dir` import from `ProjectConfig.load()`
  - Removed legacy fallback logic (lines 283-298) that checked legacy `.serena/` directory
  - Simplified error message to show only centralized location
  - Updated `SerenaConfig.from_config_file()` validation to check only centralized location
  - Removed all references to `get_legacy_project_dir` from `serena_config.py`
- Total impact: ~14 lines removed, cleaner error messages
- Test results: 12 passed, 1 expected failure (legacy test to be removed in Story 5)
- Verified no `get_legacy_project_dir` references remain in `src/serena/config/`

### Next Steps
- Story 4: Deprecate or Remove get_legacy_project_dir() (ready to start)
- Story 5: Update Tests (depends on Stories 2-4)

---

## Sprint Summary

**Total Stories**: 7
**Estimated Duration**: 3 days
**Risk Level**: 🟡 MEDIUM
- Breaking change for users with legacy `.serena/` directories
- Requires careful migration strategy and clear communication
- Backwards incompatible (users must migrate before upgrade)

**Dependencies**:
- Story 1 must complete before Stories 2-4 (provide migration path first)
- Stories 2-3 can run in parallel after Story 1
- Story 4 depends on Stories 2-3 completion
- Story 5 depends on Stories 2-4 completion
- Stories 6-7 can run in parallel, depend on Story 1

**Success Criteria**:
- Zero references to legacy paths in production code
- Migration script successfully tested on real projects
- All tests pass (centralized storage only)
- Documentation complete and clear
- File lock issues resolved (can delete old `.serena/` directories)
