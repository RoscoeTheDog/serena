# Story 3: Merge Upstream Config Module Changes

**Status**: unassigned
**Created**: 2025-12-23 14:16

## Description

Integrate upstream changes to `serena_config.py` and `context_mode.py` while preserving our centralized path helpers.

## Discovery Phase

- [ ] (P0) **GATE**: Generate side-by-side diff of `context_mode.py` (ours vs upstream) → Present to HUMAN before any merge
- [ ] (P0) **GATE**: Generate side-by-side diff of `serena_config.py` (ours vs upstream) → Present to HUMAN before any merge
- [ ] (P0) **GATE**: Check if upstream introduces new path resolution patterns → If conflicts with SerenaPaths, HALT and present options

## Implementation Phase

- [ ] Merge `context_mode.py` changes (legacy_name_mapping, single_project field)
- [ ] Merge `serena_config.py` changes per HUMAN-approved strategy
- [ ] Preserve our `get_project_root()` and centralized storage implementation

## Testing Phase

- [ ] All existing tests pass after merge
- [ ] Import statements resolve correctly
- [ ] No circular dependencies introduced

## Dependencies

Story 2

## Implementation Notes

*To be added during implementation*

## Related Stories

- Story 1: Analyze Upstream Conflicts with Fork Enhancements
- Story 2: Rename ide-assistant to claude-code Context
