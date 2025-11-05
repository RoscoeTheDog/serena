# Implementation Sprint: MCP Interface Simplification

**Created**: 2025-11-04 21:37
**Status**: active
**Sprint Goal**: Simplify MCP tool interfaces to eliminate ambiguity and confusion for agents without explicit CLAUDE.md instructions

---

## Context

Following the completion of the Token Efficiency Enhancements sprint (Stories 1-14), a comprehensive risk assessment identified **3 HIGH RISK** and **5 MEDIUM RISK** interface issues that could cause agent confusion. This sprint addresses those issues using "simple first" principles.

**Risk Assessment Document**: `docs/mcp-interface-risk-assessment.md`

**Key Principles**:
1. Default to agent-friendly values (most common use case = default)
2. Prefer enums over booleans (clearer semantics)
3. Make dependent parameters obvious (no hidden dependencies)
4. Use positive logic (avoid double negatives)
5. Type everything strictly (use Literal types)
6. Self-documenting outputs (include expansion instructions)

---

## Stories

### Story 1: Fix `detail_level` Ambiguity in `find_symbol`
**Status**: unassigned
**Risk Level**: 🔴 HIGH
**Effort**: 2 days
**Files**: `src/serena/tools/symbol_tools.py`, tests

**Problem**:
- Three-way enum `Literal["full", "signature", "auto"]` with unclear semantics
- Ambiguous interaction with `include_body` parameter
- "auto" option documented as "not yet implemented" but still exposed
- Two ways to control the same thing (detail_level vs include_body)

**Solution**: Replace with clear, single-purpose enum

**Acceptance Criteria**:
- [ ] Remove `detail_level` parameter entirely
- [ ] Add new `output_format` parameter: `Literal["metadata", "signature", "body"] = "metadata"`
  - `"metadata"`: Symbol info without body (fastest, default)
  - `"signature"`: Signature + docstring + complexity analysis
  - `"body"`: Full source code
- [ ] Remove `include_body` parameter (redundant with output_format="body")
- [ ] Update all callers in codebase to use new parameter
- [ ] Add deprecation warning for `include_body` (backward compatibility phase)
- [ ] Update docstrings with clear examples
- [ ] Add `_migration_guide` to output when deprecated params used
- [ ] All existing tests pass with new interface
- [ ] Add new tests for output_format modes
- [ ] Token estimates include all three format options

**Migration Strategy**:
```python
# OLD (deprecated but still works)
find_symbol("User", include_body=True, detail_level="full")
# → Shows deprecation warning, maps to output_format="body"

# NEW (recommended)
find_symbol("User", output_format="body")
```

**Implementation Notes**:
- Phase 1: Add `output_format` alongside existing params
- Phase 2: Internal mapping: `include_body=True` → `output_format="body"`
- Phase 3: Add deprecation warnings to deprecated params
- Phase 4: Update all internal callers
- Phase 5: Remove deprecated params in next major version

---

### Story 2: Fix `output_mode` in `search_for_pattern`
**Status**: unassigned
**Risk Level**: 🔴 HIGH
**Effort**: 1 day
**Files**: `src/serena/tools/file_tools.py`, tests

**Problem**:
- Weak typing: uses `str` instead of `Literal["summary", "detailed"]`
- Wrong default: defaults to expensive "detailed" mode
- No clear guidance on when to use which mode
- Name collision risk with verbosity system

**Solution**: Strengthen typing, flip default, rename for clarity

**Acceptance Criteria**:
- [ ] Rename `output_mode` → `result_format` (avoid confusion with verbosity)
- [ ] Change type to `Literal["summary", "detailed"]`
- [ ] Change default from "detailed" to "summary" (BREAKING but correct)
- [ ] Add clear docstring explaining trade-offs
- [ ] Summary mode includes token estimate for detailed mode
- [ ] Add `_expansion_hint` in summary: "Use result_format='detailed' for full matches"
- [ ] Update all callers in codebase
- [ ] Add deprecation warning for `output_mode` parameter
- [ ] All tests pass
- [ ] Add new tests verifying default behavior

**Migration Strategy**:
```python
# OLD (still works, deprecated)
search_for_pattern("TODO", output_mode="detailed")

# NEW (recommended)
search_for_pattern("TODO")  # ← Now returns summary by default
search_for_pattern("TODO", result_format="detailed")  # ← Explicit opt-in
```

---

### Story 3: Replace `max_answer_chars` with Token-Aware System
**Status**: unassigned
**Risk Level**: 🔴 HIGH
**Effort**: 3 days
**Files**: `src/serena/tools/tools_base.py`, all tool files, tests

**Problem**:
- Magic number `-1` means "use config default" (not documented)
- Silent truncation causes agents to think "no results found"
- Inconsistent: some tools have it, others don't
- Wrong name: uses "chars" but tokens are what matter
- No metadata about truncation

**Solution**: Deprecate and replace with explicit, token-aware truncation

**Acceptance Criteria**:
- [ ] Add new parameter to Tool base class: `max_tokens: int | None = None`
- [ ] Add new parameter: `truncation: Literal["error", "summary", "paginate"] = "error"`
- [ ] Implement truncation modes:
  - `"error"`: Raise descriptive error with narrowing suggestions
  - `"summary"`: Return summary + instructions to get full results
  - `"paginate"`: Return first page + cursor for next page
- [ ] Add `_tokens` metadata to all responses showing actual vs available
- [ ] Deprecate `max_answer_chars` parameter (backward compat phase)
- [ ] Update all tools to use new system
- [ ] Add `_truncation` metadata when limits exceeded:
  ```json
  {
    "_tokens": {
      "returned": 4500,
      "total_available": 12000,
      "truncated": true
    },
    "_next": "Use max_tokens=15000 or narrow query with relative_path"
  }
  ```
- [ ] All tests pass
- [ ] Add integration tests for each truncation mode

**Migration Strategy**:
```python
# OLD (deprecated, still works)
find_symbol("User", max_answer_chars=5000)

# NEW (recommended)
find_symbol("User", max_tokens=2000, truncation="summary")
```

**Implementation Notes**:
- Use `FastTokenEstimator` from Story 10 for accurate estimation
- Truncation should be smart (at symbol boundaries, not mid-line)
- Error mode should suggest specific narrowing strategies

---

### Story 4: Flip `include_metadata` Default in `list_memories`
**Status**: unassigned
**Risk Level**: 🟡 MEDIUM
**Effort**: 0.5 days
**Files**: `src/serena/tools/memory_tools.py`, tests

**Problem**:
- Default `include_metadata=False` is backward for agents
- Agents typically want metadata to make informed decisions
- Leads to inefficient "list then read all" pattern

**Solution**: Make metadata the default, add clear opt-out

**Acceptance Criteria**:
- [ ] Change default: `include_metadata: bool = True` (BREAKING)
- [ ] Update docstring with clear examples
- [ ] Add note: "Use include_metadata=False for just names (rare)"
- [ ] Add `_token_savings` metadata showing what was saved vs reading all
- [ ] Update all internal callers
- [ ] All tests pass with new default
- [ ] Add migration note in output for old behavior

**Migration Strategy**:
```python
# OLD behavior (now requires explicit opt-out)
list_memories(include_metadata=False)  # ← Just names

# NEW default (what agents actually want)
list_memories()  # ← Returns metadata + previews
```

---

### Story 5: Rename `exclude_generated` to `search_scope`
**Status**: unassigned
**Risk Level**: 🟡 MEDIUM
**Effort**: 1.5 days
**Files**: `src/serena/tools/symbol_tools.py`, `src/serena/tools/file_tools.py`, tests

**Problem**:
- Negative logic: "exclude" + "generated" = double negative
- Default `False` may be wrong for most use cases
- "Generated" is ambiguous (build output? deps? migrations?)

**Solution**: Replace with positive, clear scope enum

**Acceptance Criteria**:
- [ ] Add new parameter `search_scope: Literal["all", "source", "custom"] = "source"`
  - `"all"`: Include everything (vendor, generated, etc.)
  - `"source"`: Exclude common generated/vendor patterns (new default)
  - `"custom"`: Use custom patterns from config
- [ ] Deprecate `exclude_generated` parameter
- [ ] Mapping: `exclude_generated=True` → `search_scope="source"`
- [ ] Mapping: `exclude_generated=False` → `search_scope="all"`
- [ ] Update `_excluded` metadata to reference `search_scope` parameter
- [ ] Document exactly what "source" excludes in docstring
- [ ] Update all affected tools: `find_symbol`, `search_for_pattern`, `list_dir`
- [ ] All tests pass
- [ ] Add tests for each scope mode

**Migration Strategy**:
```python
# OLD (deprecated)
find_symbol("User", exclude_generated=True)

# NEW (recommended)
find_symbol("User")  # ← Now excludes generated by default
find_symbol("User", search_scope="all")  # ← Explicit opt-in for everything
```

---

### Story 6: Unify `substring_matching` into `match_mode`
**Status**: unassigned
**Risk Level**: 🟡 MEDIUM
**Effort**: 2 days
**Files**: `src/serena/tools/symbol_tools.py`, tests

**Problem**:
- Boolean flag doesn't scale (what about glob? regex?)
- Not clear when to use vs patterns
- No performance hints for different modes
- Boolean naming is less clear than enum

**Solution**: Replace with comprehensive match mode enum

**Acceptance Criteria**:
- [ ] Add new parameter: `match_mode: Literal["exact", "substring", "glob", "regex"] = "exact"`
  - `"exact"`: Fast exact match (default)
  - `"substring"`: Current `substring_matching=True` behavior
  - `"glob"`: Support wildcards like `User*Service`
  - `"regex"`: Full regex power
- [ ] Deprecate `substring_matching` parameter
- [ ] Mapping: `substring_matching=True` → `match_mode="substring"`
- [ ] Add performance metadata: `_performance_hint` for slow modes
- [ ] Add examples for each mode in docstring
- [ ] Implement glob matching (new feature)
- [ ] Implement regex matching (new feature)
- [ ] Add validation: regex mode validates pattern is valid
- [ ] All tests pass
- [ ] Add comprehensive tests for each match mode

**Implementation Notes**:
- Glob: `fnmatch` for simple wildcards
- Regex: `re.compile()` with error handling
- Add performance warnings for broad patterns

**Migration Strategy**:
```python
# OLD (deprecated)
find_symbol("User", substring_matching=True)

# NEW (recommended)
find_symbol("User", match_mode="substring")
find_symbol("User*", match_mode="glob")  # ← New capability
find_symbol("User.*Service", match_mode="regex")  # ← New capability
```

---

### Story 7: Clarify `depth` Semantics in `find_symbol`
**Status**: unassigned
**Risk Level**: 🟡 MEDIUM
**Effort**: 1 day
**Files**: `src/serena/tools/symbol_tools.py`, tests

**Problem**:
- Unclear what `depth=0` means
- No max depth limit (agents could request depth=999)
- No token estimates by depth
- Integer parameter less clear than enum for common cases

**Solution**: Add clear documentation, limits, and estimates

**Acceptance Criteria**:
- [ ] Add alias enum: `depth: Literal["symbol_only", "with_children", "recursive"] | int = "symbol_only"`
  - `"symbol_only"` = `0`
  - `"with_children"` = `1`
  - `"recursive"` = `999`
- [ ] Add max depth validation: raise error if `depth > 5`
- [ ] Add clear docstring explaining each depth level with examples
- [ ] Add token estimates by depth in metadata:
  ```json
  {
    "_tokens": {
      "depth_0": 100,
      "depth_1": 500,
      "depth_2": 2000
    }
  }
  ```
- [ ] Add `_depth_hint`: "Use depth=1 to see methods, depth=2 for nested classes"
- [ ] All tests pass
- [ ] Add tests for depth limits and enum aliases

**Implementation Notes**:
- Backward compatible: integer depth still works
- Enum just provides clearer names for common cases
- Max depth prevents accidental huge outputs

---

### Story 8: Replace `preview_lines` with Enum in `list_memories`
**Status**: unassigned
**Risk Level**: 🟡 MEDIUM
**Effort**: 0.5 days
**Files**: `src/serena/tools/memory_tools.py`, tests

**Problem**:
- Magic number: why 3? Not explained
- No max limit (agent could request 1000 lines)
- No truncation indicator in preview
- Dependent parameter only works with `include_metadata=True`

**Solution**: Replace with clear enum and add truncation indicators

**Acceptance Criteria**:
- [ ] Replace `preview_lines: int` with `preview: Literal["none", "small", "medium", "full"] = "small"`
  - `"none"`: 0 lines (metadata only)
  - `"small"`: 3 lines (current default)
  - `"medium"`: 10 lines
  - `"full"`: All lines (capped at 50)
- [ ] Add truncation indicator: `... (N more lines)` when truncated
- [ ] Add `_preview_mode` metadata to output
- [ ] Make `preview` work even if `include_metadata=False` (show warning)
- [ ] All tests pass
- [ ] Add tests for each preview mode and truncation

**Implementation Notes**:
- "full" is capped at 50 lines to prevent accidents
- Truncation indicator is always added when preview < full file
- Token estimates include full file size

---

## Progress Log

### 2025-11-04 21:37 - Sprint Started
- Created sprint structure
- Archived previous sprint (Token Efficiency Enhancements)
- Defined 8 stories (3 HIGH RISK, 5 MEDIUM RISK)
- All stories address interface simplification and agent UX

### Next Steps
- Begin Story 1: Fix `detail_level` ambiguity
- Follow linear execution (one story at a time)
- Each story includes backward compatibility phase
- Test thoroughly before marking complete

---

## Sprint Summary
{To be filled upon completion}

---

## Backward Compatibility Strategy

All changes follow a **3-phase deprecation**:

**Phase 1**: Add new parameter alongside old (both work)
**Phase 2**: Add deprecation warnings to old parameter
**Phase 3**: Remove old parameter in next major version (with ample warning)

**Deprecation Warning Format**:
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

## Testing Strategy

For each story:
1. **Unit tests**: New parameter behavior
2. **Integration tests**: Tool workflows with new params
3. **Backward compat tests**: Old params still work with warnings
4. **Migration tests**: Mapping from old → new
5. **Documentation tests**: Examples in docstrings are valid

---

## Success Metrics

**Primary Goal**: Zero ambiguity in default usage
- ✅ Agent can use tools without reading CLAUDE.md
- ✅ Defaults are what agents want 95% of the time
- ✅ Expensive operations require explicit opt-in
- ✅ Self-documenting outputs guide next steps

**Secondary Goal**: Maintain backward compatibility
- ✅ All old code continues to work (with warnings)
- ✅ Clear migration path documented
- ✅ 2-version deprecation cycle (warning → removal)

**Quality Goal**: Comprehensive testing
- ✅ 100% test coverage on new parameters
- ✅ No regressions in existing functionality
- ✅ Performance not degraded

---

## Dependencies

**Depends on**:
- Story 10 (Token Estimation Framework) - already complete ✅
- `FastTokenEstimator` class - already implemented ✅

**No blocking dependencies** - can start immediately

---

## Risk Assessment

**Implementation Risks**: 🟡 MEDIUM
- Breaking changes in defaults (mitigated by deprecation cycle)
- Migration complexity for existing callers (mitigated by backward compat)
- Testing burden (8 tools × 3 phases = 24 test scenarios)

**Schedule Risks**: 🟢 LOW
- Stories are independent (can be done in any order)
- Small scope per story (0.5-3 days each)
- Total: ~12 days of work

**Quality Risks**: 🟢 LOW
- Clear acceptance criteria per story
- Comprehensive testing strategy
- Backward compatibility mitigates breakage

---

## Future Enhancements

**Not in this sprint** (defer to future):
- Tool versioning system (e.g., `find_symbol_v2`)
- Global config for parameter defaults
- Context-aware parameter suggestions
- Performance profiling system
- Automatic parameter optimization hints

These are valuable but not critical for "simple first" goal.
