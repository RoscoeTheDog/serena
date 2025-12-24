# Story 6: Run Integration Tests

**Status**: unassigned
**Created**: 2025-12-23 14:16

## Description

Execute comprehensive integration tests to verify merge didn't break existing functionality.

## Discovery Phase

- [ ] (P0) **GATE**: Review test suite for coverage of our enhancements → If gaps found, HALT and ask HUMAN if we should add tests first
- [ ] (P0) Identify which upstream tests are new vs modified

## Implementation Phase

- [ ] Run full unit test suite
- [ ] Run MCP server smoke tests
- [ ] Test parent project inheritance workflow
- [ ] Test centralized storage path resolution

## Testing Phase

- [ ] (P0) **GATE**: If any test fails → HALT, present failure details to HUMAN with options (fix/skip/investigate)
- [ ] All existing unit tests pass
- [ ] MCP server starts with both context names
- [ ] LSP backend initializes properly

## Dependencies

Story 5

## Implementation Notes

*To be added during implementation*

## Related Stories

- Story 5: Merge Tool and Resource Updates
