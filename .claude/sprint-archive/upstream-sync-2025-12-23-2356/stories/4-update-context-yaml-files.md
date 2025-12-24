# Story 4: Update Context YAML Files

**Status**: unassigned
**Created**: 2025-12-23 14:16

## Description

Sync context YAML files with upstream (add new `ide.yml`, update existing contexts).

## Discovery Phase

- [ ] (P0) List all context YAML changes between fork and upstream
- [ ] (P0) **GATE**: If any context files have fork-specific customizations → Present diff to HUMAN for approval

## Implementation Phase

- [ ] Add new `ide.yml` context file from upstream
- [ ] Update `claude-code.yml` with upstream prompt improvements
- [ ] Update `desktop-app.yml`, `agent.yml`, `chatgpt.yml`, `codex.yml` from upstream
- [ ] Update `context.template.yml` with `single_project` field documentation
- [ ] Archive `ide-assistant.yml` (replaced by `claude-code.yml`)

## Testing Phase

- [ ] All context files parse correctly
- [ ] Context loading works for all registered contexts

## Dependencies

Story 2

## Implementation Notes

*To be added during implementation*

## Related Stories

- Story 2: Rename ide-assistant to claude-code Context
