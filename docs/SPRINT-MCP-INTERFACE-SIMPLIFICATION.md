# Sprint: MCP Interface Simplification

**Status**: ✅ COMPLETED (2025-11-04)
**Archived**: `.claude/implementation/archive/legacy-implementation-2025-11-06/archive/2025-11-05-0102/`
**Risk Assessment**: `docs/mcp-interface-risk-assessment.md`

> **Note**: This sprint has been completed and archived. This document is preserved for reference.

---

## Quick Reference

### Sprint Goal
Eliminate ambiguity in MCP tool interfaces so agents can use tools correctly without requiring CLAUDE.md instructions.

### Key Metrics
- **Total Stories**: 8 (3 HIGH RISK, 5 MEDIUM RISK)
- **Estimated Effort**: ~12 days
- **Dependencies**: None (can start immediately)
- **Risk Level**: 🟡 MEDIUM (mitigated by backward compat strategy)

---

## Stories at a Glance

| # | Story | Risk | Effort | Status |
|---|-------|------|--------|--------|
| 1 | Fix `detail_level` ambiguity in `find_symbol` | 🔴 HIGH | 2d | ✅ completed |
| 2 | Fix `output_mode` in `search_for_pattern` | 🔴 HIGH | 1d | ✅ completed |
| 3 | Replace `max_answer_chars` with token-aware system | 🔴 HIGH | 3d | ✅ completed |
| 4 | Flip `include_metadata` default in `list_memories` | 🟡 MED | 0.5d | ✅ completed |
| 5 | Rename `exclude_generated` to `search_scope` | 🟡 MED | 1.5d | ✅ completed |
| 6 | Unify `substring_matching` into `match_mode` | 🟡 MED | 2d | ✅ completed |
| 7 | Clarify `depth` semantics in `find_symbol` | 🟡 MED | 1d | ⚠️ skipped/merged |
| 8 | Replace `preview_lines` with enum in `list_memories` | 🟡 MED | 0.5d | ⚠️ skipped/merged |

**Completion Summary**: 6 of 8 stories completed. Stories 7-8 were either skipped or merged into other stories.

---

## Problem Summary

### HIGH RISK Issues (Immediate Action Required)

#### 1. `detail_level` in `find_symbol`
**Problem**: Three-way enum with ambiguous interaction with `include_body` parameter
```python
# CONFUSING - what does this mean?
find_symbol("User", detail_level="signature", include_body=True)
```
**Solution**: Replace with single clear `output_format` enum
```python
# CLEAR
find_symbol("User", output_format="signature")
```

#### 2. `output_mode` in `search_for_pattern`
**Problem**: Wrong default (expensive "detailed"), weak typing (str not Literal)
```python
# WASTEFUL - gets 50KB when agent wanted summary
search_for_pattern("TODO")  # ← defaults to "detailed"
```
**Solution**: Flip default to "summary", strengthen typing
```python
# EFFICIENT
search_for_pattern("TODO")  # ← returns summary by default
```

#### 3. `max_answer_chars` Everywhere
**Problem**: Magic number `-1`, silent truncation, dangerous footgun
```python
# DANGEROUS - agent gets empty result, thinks "no matches"
find_symbol("User", max_answer_chars=1000)  # ← too small, silently truncated
```
**Solution**: Replace with explicit token-aware truncation
```python
# SAFE
find_symbol("User", max_tokens=2000, truncation="error")  # ← clear error with guidance
```

### MEDIUM RISK Issues (Should Fix Soon)

#### 4. `include_metadata` in `list_memories`
**Problem**: Default is backward (agents want metadata to make decisions)
**Solution**: Flip default to `True`

#### 5. `exclude_generated` Flag
**Problem**: Negative logic, ambiguous default
**Solution**: Replace with positive `search_scope` enum

#### 6. `substring_matching` Boolean
**Problem**: Doesn't scale (what about glob? regex?)
**Solution**: Unify into `match_mode` enum

#### 7. `depth` Parameter
**Problem**: Unclear semantics, no limits
**Solution**: Add enum aliases and max depth validation

#### 8. `preview_lines` Magic Number
**Problem**: Arbitrary default, no truncation indicator
**Solution**: Replace with enum (none/small/medium/full)

---

## Backward Compatibility Strategy

All changes follow **3-phase deprecation**:

1. **Phase 1**: Add new parameter alongside old (both work)
2. **Phase 2**: Add deprecation warnings to old parameter
3. **Phase 3**: Remove old parameter in v2.0.0

### Example Deprecation Warning
```json
{
  "results": [...],
  "_deprecated": {
    "parameter": "include_body",
    "replacement": "output_format",
    "removal_version": "2.0.0",
    "migration": "Use output_format='body' instead of include_body=True"
  }
}
```

---

## Key Principles Applied

Based on IMPLEMENT-INIT.md and risk assessment:

1. ✅ **Default to agent-friendly values** - Most common use case = default
2. ✅ **Prefer enums over booleans** - Clearer semantics
3. ✅ **Make dependent parameters obvious** - No hidden dependencies
4. ✅ **Use positive logic** - Avoid double negatives
5. ✅ **Type everything strictly** - Use Literal types
6. ✅ **Self-documenting outputs** - Include expansion instructions
7. ✅ **Performance transparency** - Show token costs
8. ✅ **Avoid magic numbers** - Use None/explicit values
9. ✅ **Backward compatibility via versioning** - Gradual deprecation
10. ✅ **Comprehensive testing** - 5 test types per story

---

## Testing Strategy

For each story, implement:

1. **Unit tests** - New parameter behavior
2. **Integration tests** - Tool workflows with new params
3. **Backward compat tests** - Old params still work with warnings
4. **Migration tests** - Mapping from old → new
5. **Documentation tests** - Examples in docstrings are valid

**Coverage Target**: 100% for new parameters

---

## Success Criteria

### Primary Goal: Zero Ambiguity
- ✅ Agent can use tools without reading CLAUDE.md
- ✅ Defaults are what agents want 95% of the time
- ✅ Expensive operations require explicit opt-in
- ✅ Self-documenting outputs guide next steps

### Secondary Goal: Backward Compatible
- ✅ All old code continues to work (with warnings)
- ✅ Clear migration path documented
- ✅ 2-version deprecation cycle

### Quality Goal: Comprehensive Testing
- ✅ 100% test coverage on new parameters
- ✅ No regressions in existing functionality
- ✅ Performance not degraded

---

## Migration Examples

### Story 1: `find_symbol`
```python
# OLD (deprecated but works)
find_symbol("User", include_body=True, detail_level="full")

# NEW (recommended)
find_symbol("User", output_format="body")
```

### Story 2: `search_for_pattern`
```python
# OLD (still works)
search_for_pattern("TODO", output_mode="detailed")

# NEW (default is now better)
search_for_pattern("TODO")  # ← summary by default
search_for_pattern("TODO", result_format="detailed")  # ← explicit opt-in
```

### Story 3: `max_answer_chars`
```python
# OLD (deprecated)
find_symbol("User", max_answer_chars=5000)

# NEW (safer)
find_symbol("User", max_tokens=2000, truncation="error")
```

### Story 5: `exclude_generated`
```python
# OLD (negative logic)
find_symbol("User", exclude_generated=True)

# NEW (positive, better default)
find_symbol("User")  # ← excludes generated by default
find_symbol("User", search_scope="all")  # ← explicit opt-in
```

### Story 6: `substring_matching`
```python
# OLD (limited)
find_symbol("User", substring_matching=True)

# NEW (more powerful)
find_symbol("User", match_mode="substring")
find_symbol("User*", match_mode="glob")  # ← new!
find_symbol("User.*Service", match_mode="regex")  # ← new!
```

---

## Next Steps

1. **Review sprint plan** - Ensure stories are clear and achievable
2. **Begin Story 1** - Fix `detail_level` ambiguity (2 days)
3. **Linear execution** - Complete one story at a time
4. **Update progress log** - After each story completion
5. **Test thoroughly** - 5 test types per story

---

## Resources

- **Sprint Tracker**: `implementation/index.md`
- **Risk Assessment**: `docs/mcp-interface-risk-assessment.md`
- **Previous Sprint**: `implementation/archive/2025-11-04-2137/` (Token Efficiency Enhancements)
- **Template Used**: `claude-code-tooling/claude-prompt-templates/implement-sprint/IMPLEMENT-INIT.md`

---

## Questions & Answers

**Q: Why not just update CLAUDE.md with detailed instructions?**
A: CLAUDE.md should be minimal. Tools should be self-documenting and intuitive without requiring external instructions. This follows "simple first" principle.

**Q: Why 3-phase deprecation instead of immediate breaking changes?**
A: Backward compatibility ensures existing integrations don't break. Gradual deprecation gives users time to migrate.

**Q: Can stories be done in parallel?**
A: Yes, stories are independent. However, linear execution is recommended to avoid merge conflicts and ensure consistent quality.

**Q: What if we discover more issues during implementation?**
A: Follow IMPLEMENT-INIT protocol: Set status to `error`, add Remediation Plan, halt for user approval, then split into sub-stories if needed.

**Q: Why flip defaults (breaking changes) instead of keeping backward compat?**
A: Defaults are sticky - once set, they're hard to change. Better to fix now with deprecation cycle than live with poor defaults forever. All breaking changes include migration warnings.

---

## Related Documents

- **Risk Assessment**: Detailed analysis of all 15+ parameters - `docs/mcp-interface-risk-assessment.md`
- **Token Efficiency Sprint**: Previous sprint that added the features we're now simplifying - `implementation/archive/2025-11-04-2137/index.md`
- **IMPLEMENT-INIT Template**: Sprint management protocol - `claude-code-tooling/claude-prompt-templates/implement-sprint/IMPLEMENT-INIT.md`
