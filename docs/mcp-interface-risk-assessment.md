# Serena MCP Interface Risk Assessment
**Date**: 2025-11-04
**Sprint**: Token Efficiency Enhancements (Stories 10-14)
**Purpose**: Identify ambiguous parameters and interfaces that could confuse agents without explicit instructions

---

## Executive Summary

After implementing Stories 10-14 (Token Estimation Framework, On-Demand Body Retrieval, Memory Metadata, Reference Count Mode, and Exclude Generated Code), this assessment evaluates the risk of parameter ambiguity and interface confusion for client agents operating without CLAUDE.md instructions.

**Key Findings**:
- **HIGH RISK**: 3 parameters/features identified
- **MEDIUM RISK**: 5 parameters/features identified
- **LOW RISK**: 7 parameters/features identified
- **Total New Parameters Added**: 15+ across recent stories

---

## "Simple First" Principles (from IMPLEMENT-INIT.md)

Based on the sprint initialization template, the key principle for agent-facing interfaces is:

> **"Simple First, Progressive Disclosure"**

1. **Default behavior should be intuitive** - The most common use case should require minimal parameters
2. **Opt-in for complexity** - Advanced features should be explicit opt-in, not hidden behind defaults
3. **Self-documenting outputs** - Results should include guidance on how to get more detail
4. **Backward compatibility always** - New features must not break existing workflows
5. **Clear naming** - Parameter names should be unambiguous about their effect
6. **Avoid negative logic** - Prefer `include_X` over `exclude_X` when both options exist
7. **Transparency for filtering** - Always show what was filtered/excluded with override instructions

---

## Risk Assessment Matrix

### HIGH RISK: Requires Immediate Attention

#### 1. `detail_level` in `find_symbol` (Story 5)
**Risk Level**: 🔴 HIGH
**Issue**: Three-way enum with unclear semantics

**Current Interface**:
```python
def find_symbol(
    name_path: str,
    detail_level: Literal["full", "signature", "auto"] = "full",
    include_body: bool = False,
    ...
)
```

**Problems**:
- **Interaction confusion**: How does `detail_level="signature"` interact with `include_body=True`?
- **"auto" is vaporware**: Documentation says "not yet implemented, defaults to 'full'" - why expose it?
- **Two ways to control same thing**: Both `detail_level` and `include_body` affect body inclusion
- **Signature mode still fetches body**: Under the hood, it fetches the body for analysis then strips it

**Agent Confusion Scenarios**:
```python
# What does this mean? Get signature only, or signature with body?
find_symbol("User", detail_level="signature", include_body=True)

# Does "auto" do anything? (No - it defaults to "full")
find_symbol("User", detail_level="auto")  # ← Confusing no-op

# Is this redundant? (Yes)
find_symbol("User", detail_level="full", include_body=True)
```

**Recommendation**:
- **OPTION A (Simple)**: Remove `detail_level` entirely, use only `include_body` + add `include_signature` boolean
- **OPTION B (Keep)**: Make the interaction explicit:
  - `detail_level="signature"` IGNORES `include_body` (document this clearly)
  - Remove "auto" option until implemented
  - Rename to `output_format` for clarity
- **OPTION C (Progressive)**: Single enum that's clear:
  ```python
  output_format: Literal["metadata_only", "with_signature", "with_body"] = "metadata_only"
  # Then include_body becomes redundant and is removed
  ```

---

#### 2. `output_mode` in `search_for_pattern` (Story 8)
**Risk Level**: 🔴 HIGH
**Issue**: Two modes with unclear default expectations

**Current Interface**:
```python
def search_for_pattern(
    substring_pattern: str,
    output_mode: str = "detailed",  # ← "summary" also available
    ...
)
```

**Problems**:
- **Type isn't constrained**: Uses `str` instead of `Literal["summary", "detailed"]`
- **Default is expensive**: Defaults to `"detailed"` for backward compatibility, but this is the 90% token-heavy option
- **No guidance on when to use what**: Docstring doesn't explain trade-offs
- **Name collision risk**: "summary" vs "detailed" could be confused with verbosity levels

**Agent Confusion Scenarios**:
```python
# Agent doesn't know "summary" exists, uses default
search_for_pattern("TODO")  # ← Gets 50KB of matches, wastes tokens

# Agent typos the mode
search_for_pattern("TODO", output_mode="summery")  # ← Silent failure? Error?

# Agent confuses with verbosity
search_for_pattern("TODO", output_mode="minimal")  # ← Does this work?
```

**Recommendation**:
- **Fix type**: Change to `Literal["summary", "detailed"]`
- **Change default**: Make `"summary"` the default (BREAKING but correct)
  - Add `output_mode="detailed"` to get full matches (explicit opt-in for expensive operation)
- **Rename parameter**: Consider `match_detail` or `result_format` to avoid verbosity confusion
- **Add token estimates**: Include `estimated_tokens_full` in summary mode

---

#### 3. `max_answer_chars` Everywhere
**Risk Level**: 🔴 HIGH
**Issue**: Universal parameter with unclear semantics and dangerous default

**Current Interface**:
```python
def find_symbol(..., max_answer_chars: int = -1)
def search_for_pattern(..., max_answer_chars: int = -1)
def get_symbols_overview(..., max_answer_chars: int = -1)
def list_memories(..., max_answer_chars: int = -1)  # ← Wait, this one doesn't have it
```

**Problems**:
- **Magic number**: `-1` means "use config default" - not documented in signature
- **Silent truncation**: When exceeded, returns empty content or truncated output with no clear indication
- **Not universal**: Some tools have it, some don't (inconsistent)
- **Wrong name**: "chars" implies characters, but token limits are what matter
- **No metadata**: Doesn't tell agent "I truncated this, here's how to see more"
- **Agents will misuse**: Agents may set it to avoid long outputs, then get empty results and not know why

**Agent Confusion Scenarios**:
```python
# Agent wants to avoid long output, sets conservative limit
symbols = find_symbol("User", max_answer_chars=1000)
# ← Returns nothing (too short), agent thinks "no matches found"

# Agent doesn't know what -1 means
symbols = find_symbol("User", max_answer_chars=-1)  # Default, but unclear

# Agent sets it globally and forgets
symbols = find_symbol("User", max_answer_chars=5000)  # Seems safe
# ← Works for first query, fails silently on larger results later
```

**Recommendation**:
- **DEPRECATE this parameter** - It's a footgun for agents
- **Replace with token-aware system**:
  ```python
  def find_symbol(
      name_path: str,
      max_tokens: int | None = None,  # None = no limit (safe default)
      truncation: Literal["error", "summary", "paginate"] = "error",
      ...
  )
  ```
  - `truncation="error"`: Raise error with metadata on how to narrow query
  - `truncation="summary"`: Return summary + instructions to retrieve details
  - `truncation="paginate"`: Return first page + cursor for next page
- **Add output metadata**:
  ```json
  {
    "results": [...],
    "_tokens": {
      "returned": 4500,
      "total_available": 12000,
      "next_page": "Use offset=10 to see more"
    }
  }
  ```

---

### MEDIUM RISK: Confusing But Manageable

#### 4. `include_metadata` in `list_memories` (Story 12)
**Risk Level**: 🟡 MEDIUM
**Issue**: Opt-in for metadata is backward but understandable

**Current Interface**:
```python
def list_memories(
    include_metadata: bool = False,  # ← Defaults to minimal
    preview_lines: int = 3,
)
```

**Problems**:
- **Backward for agents**: Agents likely want metadata by default (to make informed decisions)
- **Dependent parameter confusion**: `preview_lines` only matters if `include_metadata=True`, but this isn't enforced
- **No token estimate in output**: Doesn't tell agent how much they'd save by using metadata mode

**Agent Confusion Scenarios**:
```python
# Agent sets preview_lines but forgets include_metadata
list_memories(preview_lines=5)  # ← Does nothing, preview_lines ignored

# Agent doesn't know metadata exists, reads all files
memories = list_memories()  # ← Gets just names
for mem in memories:
    read_memory(mem)  # ← Reads everything, no filtering
```

**Recommendation**:
- **Flip the default**: `include_metadata=True` should be default
  - Breaking change but correct for agent UX
  - Add note: "Use include_metadata=False for just names (rare)"
- **Make preview_lines part of metadata**:
  ```python
  def list_memories(
      detail: Literal["names", "metadata", "preview"] = "metadata",
      preview_lines: int = 3,  # Only used if detail="preview"
  )
  ```
- **Add token metadata**:
  ```json
  {
    "memories": [...],
    "_tokens": {
      "this_response": 200,
      "if_read_all": 15000,
      "savings": "93%"
    }
  }
  ```

---

#### 5. `exclude_generated` Flag (Story 14)
**Risk Level**: 🟡 MEDIUM
**Issue**: Negative logic and unclear default expectations

**Current Interface**:
```python
def find_symbol(..., exclude_generated: bool = False)
def search_for_pattern(..., exclude_generated: bool = False)
def list_dir(..., exclude_generated: bool = False)  # ← Not implemented yet?
```

**Problems**:
- **Negative logic**: "exclude" + "generated" = double negative thinking
- **Default may be wrong**: `False` means "include generated code by default" - is this what agents want?
- **Inconsistent application**: Not clear if it applies to all tools uniformly
- **"Generated" is ambiguous**: Does it mean build output? Dependencies? Migrations? All of above?

**Agent Confusion Scenarios**:
```python
# Agent wants to search own code, not node_modules
search_for_pattern("TODO")  # ← Gets 5000 matches from node_modules

# Agent doesn't understand what "generated" means
find_symbol("Component", exclude_generated=True)
# ← Excludes migrations AND vendor AND maybe custom code-gen?

# Agent forgets to set it consistently
find_symbol("User", exclude_generated=True)  # Excludes generated
search_for_pattern("User", exclude_generated=False)  # Oops, included generated
```

**Recommendation**:
- **Rename to positive**: `search_scope: Literal["all", "source_only", "custom"] = "source_only"`
  - `"all"`: Everything (rare use case)
  - `"source_only"`: Exclude vendor/generated (common default)
  - `"custom"`: Use custom patterns from config
- **Make default smart**: Default to `"source_only"` (exclude generated)
  - This matches agent expectations 95% of the time
  - Add clear override: `search_scope="all"` to include everything
- **Document patterns clearly**: In output metadata, show what was excluded and why

---

#### 6. `substring_matching` in `find_symbol` (Story 11+)
**Risk Level**: 🟡 MEDIUM
**Issue**: Not clear when to use vs. regex patterns

**Current Interface**:
```python
def find_symbol(
    name_path: str,
    substring_matching: bool = False,
    ...
)
```

**Problems**:
- **Two search modes**: Exact vs substring, but no regex option
- **Interaction with name_path**: How does `substring_matching` interact with path patterns like `"class/method"`?
- **Performance implications**: Not documented that substring search is slower
- **No examples**: Docstring doesn't show when you'd use this

**Agent Confusion Scenarios**:
```python
# Agent wants regex, tries substring
find_symbol("User.*", substring_matching=True)  # ← Doesn't work as expected

# Agent doesn't know about substring option
find_symbol("User")  # ← Misses UserService, UserRepository, etc.

# Agent uses substring for everything
find_symbol("er", substring_matching=True)  # ← Gets 1000 matches (User, Server, etc.)
```

**Recommendation**:
- **Unify search modes**:
  ```python
  def find_symbol(
      name_path: str,
      match_mode: Literal["exact", "substring", "glob", "regex"] = "exact",
      ...
  )
  ```
  - `"exact"`: Fast, default
  - `"substring"`: Current substring_matching=True
  - `"glob"`: Support wildcards like `User*Service`
  - `"regex"`: Full regex power
- **Add performance hints**: In output, include `"_search_hint": "Narrow your pattern for faster results"`
- **Document examples clearly**: Show when to use each mode

---

#### 7. `depth` Parameter in `find_symbol`
**Risk Level**: 🟡 MEDIUM
**Issue**: Semantics unclear, especially with depth=0

**Current Interface**:
```python
def find_symbol(
    name_path: str,
    depth: int = 0,
    ...
)
```

**Problems**:
- **What does depth=0 mean?**: "Just the symbol" or "symbol + immediate children"?
- **Interaction with include_body**: Does depth affect body inclusion?
- **No max depth**: Agent could accidentally request depth=100 and get huge output
- **No token estimate by depth**: Agent can't know cost before requesting

**Agent Confusion Scenarios**:
```python
# Agent wants class + methods
find_symbol("User", depth=1)  # ← Gets methods, but also nested classes?

# Agent wants everything
find_symbol("User", depth=999)  # ← Potentially huge output

# Agent doesn't understand depth
find_symbol("User")  # depth=0, gets just the class, misses methods
```

**Recommendation**:
- **Clarify semantics**: Document exactly what each depth level means
  - `depth=0`: Just the matched symbol (no children)
  - `depth=1`: Matched symbol + direct children (methods, fields)
  - `depth=2`: ... + nested children
- **Add max depth limit**: Cap at `depth=3` or similar, raise error if exceeded
- **Add token estimates by depth**: Show `_tokens: {depth_0: 100, depth_1: 500, depth_2: 2000}`
- **Consider enum**:
  ```python
  depth: Literal["symbol_only", "with_children", "recursive"] | int = "symbol_only"
  ```

---

#### 8. `preview_lines` in `list_memories` (Story 12)
**Risk Level**: 🟡 MEDIUM
**Issue**: Magic number without clear semantics

**Current Interface**:
```python
def list_memories(
    include_metadata: bool = False,
    preview_lines: int = 3,  # ← Why 3?
)
```

**Problems**:
- **Arbitrary default**: Why 3? Not explained
- **Dependent parameter**: Only works if `include_metadata=True`
- **No token/char limit**: Agent could request 1000 lines by accident
- **No truncation indicator**: If file is 3 lines, how to tell vs. truncated?

**Agent Confusion Scenarios**:
```python
# Agent wants more context
list_memories(include_metadata=True, preview_lines=100)
# ← Gets huge output, maybe exceeds max_answer_chars

# Agent doesn't know it only affects metadata mode
list_memories(preview_lines=10)  # ← Does nothing

# Agent can't tell if preview is complete
# Is preview "Line 1\nLine 2\nLine 3" the full file or truncated?
```

**Recommendation**:
- **Rename and clarify**:
  ```python
  def list_memories(
      include_metadata: bool = True,  # ← New default
      preview: Literal["none", "small", "medium", "full"] = "small",
  )
  # Where: none=0 lines, small=3, medium=10, full=all (capped at 50)
  ```
- **Add truncation indicator**: Preview should end with `... (N more lines)` if truncated
- **Add token estimate**: Show preview tokens vs full file tokens

---

### LOW RISK: Clear and Well-Designed

#### 9. Token Estimation Metadata (Story 10)
**Risk Level**: 🟢 LOW
**Why It's Good**: Transparent, additive, self-documenting

**Interface**:
```json
{
  "results": [...],
  "_tokens": {
    "current": 450,
    "if_verbosity_normal": 850,
    "if_verbosity_detailed": 2300,
    "if_include_body": 1850
  }
}
```

**Strengths**:
- ✅ Clearly prefixed with `_` (metadata)
- ✅ Shows current + alternatives
- ✅ Helps agent make informed decisions
- ✅ Non-breaking (additive)

**Minor Improvement**: Add explanation field:
```json
{
  "_tokens": {
    "current": 450,
    "alternatives": {
      "verbosity_normal": 850,
      "include_body": 1850
    },
    "guidance": "Use verbosity='normal' for more detail"
  }
}
```

---

#### 10. Verbosity Control System (Story 9)
**Risk Level**: 🟢 LOW
**Why It's Good**: Three clear levels, sensible defaults

**Interface**:
```python
verbosity: Literal["minimal", "normal", "detailed"] = "normal"
```

**Strengths**:
- ✅ Clear names (not "v0", "v1", "v2")
- ✅ Sensible default (normal)
- ✅ Works across all tools
- ✅ Includes token estimates

**Note**: Could conflict with `output_mode` in search_for_pattern (both control output detail)

---

#### 11. Cache Metadata (Story 4)
**Risk Level**: 🟢 LOW
**Why It's Good**: Transparent, zero configuration

**Interface**:
```json
{
  "results": [...],
  "_cache": {
    "hit": true,
    "age_seconds": 45,
    "hash": "abc123"
  }
}
```

**Strengths**:
- ✅ Automatic (no agent config needed)
- ✅ Transparent about cache status
- ✅ Helps debug stale results
- ✅ Non-breaking

---

#### 12. Structural JSON Optimization (Story 1)
**Risk Level**: 🟢 LOW
**Why It's Good**: Invisible optimization

**Strengths**:
- ✅ Zero API changes
- ✅ Backward compatible
- ✅ Automatic savings
- ✅ No agent confusion possible

---

#### 13. Diff-Based Edit Responses (Story 2)
**Risk Level**: 🟢 LOW
**Why It's Good**: Clear response format options

**Interface**:
```python
response_format: Literal["diff", "summary", "full"] = "diff"
```

**Strengths**:
- ✅ Clear names
- ✅ Sensible default (diff = 70-90% savings)
- ✅ Self-documenting output
- ✅ Agent can always request "full" if needed

---

#### 14. Directory Tree Collapse (Story 3)
**Risk Level**: 🟢 LOW
**Why It's Good**: Two clear modes

**Interface**:
```python
format: Literal["list", "tree"] = "tree"
```

**Strengths**:
- ✅ Clear names
- ✅ Tree format includes expansion instructions
- ✅ Shows file counts (e.g., `src/ (47 files)`)
- ✅ Agent knows how to get details

---

#### 15. Symbol IDs for On-Demand Retrieval (Story 11)
**Risk Level**: 🟢 LOW
**Why It's Good**: Stable, self-explanatory

**Interface**:
```python
symbol_id: str  # Format: "name_path:relative_path:line_number"
# Example: "User/login:models.py:142"
```

**Strengths**:
- ✅ Human-readable format
- ✅ Self-documenting structure
- ✅ Stable across sessions (line number might change, but handled)
- ✅ Works across languages

**Note**: Line numbers can change with edits - this is documented and accepted trade-off

---

## Summary of Recommendations

### Immediate Action Required (HIGH RISK)

1. **`detail_level`**: Simplify to single clear enum or remove in favor of `include_body`
2. **`output_mode`**: Add type constraints, flip default to "summary", rename to avoid confusion
3. **`max_answer_chars`**: Deprecate and replace with token-aware truncation system

### Should Fix Soon (MEDIUM RISK)

4. **`include_metadata`**: Flip default to `True` (breaking but correct)
5. **`exclude_generated`**: Rename to positive `search_scope` with smart default
6. **`substring_matching`**: Unify into `match_mode` enum with multiple options
7. **`depth`**: Clarify semantics, add max limit, provide token estimates
8. **`preview_lines`**: Replace with enum (small/medium/full) and add truncation indicators

### Monitor and Document (LOW RISK)

9-15. Features are well-designed but should be documented clearly in CLAUDE.md or tool descriptions

---

## General Interface Principles (Derived)

Based on this analysis, here are the key principles Serena should follow:

### 1. **Default to Agent-Friendly Values**
- Most common use case = default
- Expensive operations = explicit opt-in
- Example: `search_scope="source_only"` (exclude generated by default)

### 2. **Prefer Enums Over Booleans**
- ❌ `exclude_generated: bool = False`
- ✅ `search_scope: Literal["all", "source_only"] = "source_only"`

### 3. **Make Dependent Parameters Obvious**
- ❌ `preview_lines` only works if `include_metadata=True` (hidden dependency)
- ✅ Combine into single `detail` parameter with clear options

### 4. **Always Provide Token Metadata**
- Every response should include `_tokens` field
- Show current + alternatives
- Include guidance on how to get more/less detail

### 5. **Use Positive Logic**
- ❌ `exclude_generated`, `disable_cache`, `hide_metadata`
- ✅ `search_scope`, `cache`, `include_metadata`

### 6. **Avoid Magic Numbers**
- ❌ `max_answer_chars=-1` (means "use config default")
- ✅ `max_tokens=None` (explicit, Pythonic)

### 7. **Type Everything Strictly**
- ❌ `output_mode: str = "detailed"`
- ✅ `output_mode: Literal["summary", "detailed"] = "summary"`

### 8. **Self-Documenting Outputs**
- Include expansion instructions: `"Use exclude_generated=false to include all files"`
- Show what was filtered: `"_excluded": {"node_modules": 847}`
- Provide next steps: `"Use get_symbol_body() to retrieve full source"`

### 9. **Performance Transparency**
- Show token costs for alternatives
- Warn about slow operations
- Estimate time for expensive queries

### 10. **Backward Compatibility via Versioning**
- When breaking changes are needed, version the tool
- Keep old version for 1-2 releases
- Clear migration path in docs

---

## Action Plan

### Phase 1: Critical Fixes (Do First)
- [ ] Fix `detail_level` ambiguity in `find_symbol`
- [ ] Add type constraints to `output_mode` in `search_for_pattern`
- [ ] Deprecate `max_answer_chars`, design replacement

### Phase 2: UX Improvements
- [ ] Flip `include_metadata` default in `list_memories`
- [ ] Rename `exclude_generated` to `search_scope`
- [ ] Unify `substring_matching` into `match_mode`

### Phase 3: Documentation
- [ ] Document all parameters with examples in docstrings
- [ ] Create CLAUDE.md section with tool usage guidance
- [ ] Add token cost estimates to all tools

### Phase 4: Long-term
- [ ] Implement consistent token-aware truncation
- [ ] Add performance hints to slow operations
- [ ] Consider tool versioning strategy for breaking changes

---

## Conclusion

The recently implemented token efficiency features (Stories 10-14) are generally well-designed with **LOW RISK** of agent confusion. However, **three HIGH RISK parameters** need immediate attention:

1. `detail_level` - ambiguous interaction with `include_body`
2. `output_mode` - wrong default and weak typing
3. `max_answer_chars` - dangerous footgun for agents

The **MEDIUM RISK parameters** are usable but could be improved with better defaults and clearer naming.

**Recommended approach**: Fix HIGH RISK issues immediately, batch MEDIUM RISK fixes into next sprint, and document LOW RISK features thoroughly.

**Overall Assessment**: 🟡 **MEDIUM RISK** - The interface is functional but has enough ambiguity that agents without CLAUDE.md guidance may misuse several features. Priority should be simplifying the HIGH RISK parameters before they become widely adopted patterns.
