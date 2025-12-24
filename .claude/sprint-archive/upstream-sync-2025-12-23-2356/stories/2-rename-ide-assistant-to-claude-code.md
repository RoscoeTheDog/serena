# Story 2: Rename ide-assistant to claude-code Context

**Status**: unassigned
**Created**: 2025-12-23 14:16

## Description

Align context naming with upstream by renaming `ide-assistant` to `claude-code` while preserving our fork's customizations.

## Discovery Phase

- [ ] (P0) **GATE**: Compare our `ide-assistant.yml` with upstream's `claude-code.yml` → Present diff to HUMAN if significant divergence
- [ ] (P0) Identify all code references to `ide-assistant` context name
- [ ] (P0) **GATE**: Check if our customizations (excluded tools, prompts) are preserved upstream → If not, HALT and ask HUMAN which version to keep

## Implementation Phase

- [ ] Create `claude-code.yml` context file aligned with upstream
- [ ] Add deprecation mapping in `context_mode.py` for backwards compatibility
- [ ] Add `single_project: true` field to new context
- [ ] Update internal references from `ide-assistant` to `claude-code`

## Testing Phase

- [ ] MCP server starts with `--context claude-code`
- [ ] Backwards compatibility: `--context ide-assistant` still works (with deprecation warning)

## Dependencies

Story 1

## Implementation Notes

*To be added during implementation*

## Related Stories

- Story 1: Analyze Upstream Conflicts with Fork Enhancements
