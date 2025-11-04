# Implementation Sprint: Token Efficiency Enhancements

**Sprint Goal**: Reduce client token consumption by 50-75% while maintaining 100% accuracy

**Start Date**: 2025-01-04
**Target Completion**: TBD
**Status**: `in_progress`

---

## Sprint Overview

This sprint implements safe, high-impact token efficiency improvements for Serena's tool outputs. Focus is on Tier 1 (safe, high-impact) and Tier 2 (safe with guardrails) enhancements from the risk assessment.

**Success Metrics**:
- 50-75% reduction in average tool output tokens
- Zero accuracy degradation
- Full backward compatibility
- LLM always has path to more detail when needed

---

## Story Index

### Phase 1: Foundation (Safe, Zero Risk)
- **1** - Structural JSON Optimization [`unassigned`]
- **2** - Diff-Based Edit Responses [`unassigned`]
- **3** - Directory Tree Collapse [`unassigned`]
- **4** - Cache with Hash Validation [`unassigned`]

### Phase 2: Intelligent Summarization (Low Risk with Guardrails)
- **5** - Signature Mode with Complexity Warnings [`unassigned`]
- **6** - Semantic Truncation with Section Inventory [`unassigned`]
- **7** - Smart Snippet Selection [`unassigned`]
- **8** - Pattern Search Summaries [`unassigned`]

### Phase 3: Universal Controls (Infrastructure)
- **9** - Verbosity Control System [`unassigned`]
- **10** - Token Estimation Framework [`unassigned`]

---

## Story Details

### Story 1: Structural JSON Optimization
**Status**: `unassigned`
**Risk Level**: 🟢 Low
**Estimated Savings**: 20-30%
**Effort**: 2 days

**Objective**: Reduce JSON redundancy by factoring out repeated values and eliminating null fields.

**Scope**:
- Factor out repeated file paths in symbol lists
- Omit null/empty values with schema markers
- Group metadata fields
- Maintain full semantic clarity

**Acceptance Criteria**:
- [ ] Symbol results deduplicate file paths
- [ ] Null/empty fields omitted with `_schema` marker
- [ ] All tools updated with new JSON structure
- [ ] LLM can parse new format without confusion
- [ ] Unit tests verify correctness

**Files to Modify**:
- `src/serena/tools/symbol_tools.py`
- `src/serena/tools/file_tools.py`
- `src/serena/symbol.py`

**Implementation Notes**:
```python
# BEFORE:
{
  "symbols": [
    {"name": "User", "kind": "Class", "file": "models.py", "line": 10, "parent": null},
    {"name": "login", "kind": "Method", "file": "models.py", "line": 15, "parent": null}
  ]
}

# AFTER:
{
  "_schema": "structured_v1",
  "file": "models.py",
  "symbols": [
    {"name": "User", "kind": "Class", "line": 10},
    {"name": "login", "kind": "Method", "line": 15}
  ]
}
```

---

### Story 2: Diff-Based Edit Responses
**Status**: `unassigned`
**Risk Level**: 🟢 Low
**Estimated Savings**: 70-90%
**Effort**: 2 days

**Objective**: Return concise diffs instead of full file content for edit confirmations.

**Scope**:
- Add `response_format` parameter to edit tools
- Generate unified diffs for changes
- Include verification summary
- Allow LLM to request full result if needed

**Acceptance Criteria**:
- [ ] `replace_symbol_body` returns diff by default
- [ ] `insert_after_symbol` returns diff
- [ ] `insert_before_symbol` returns diff
- [ ] Format includes syntax validation status
- [ ] `response_format="full"` option available
- [ ] Diffs are correctly formatted and parseable

**Files to Modify**:
- `src/serena/tools/symbol_tools.py` (InsertAfterSymbolTool, InsertBeforeSymbolTool, ReplaceSymbolBodyTool)
- `src/serena/code_editor.py` (if diff generation needed)

**Implementation Notes**:
```python
def apply(self, ..., response_format: Literal["diff", "full", "summary"] = "diff"):
    # Perform edit
    result = self._perform_edit(...)

    if response_format == "diff":
        return self._format_diff_response(old_content, new_content)
    elif response_format == "summary":
        return self._format_summary_response(changes)
    else:
        return self._format_full_response(new_content)
```

---

### Story 3: Directory Tree Collapse
**Status**: `unassigned`
**Risk Level**: 🟢 Low
**Estimated Savings**: 60-80%
**Effort**: 1-2 days

**Objective**: Return collapsed directory tree for recursive listings with on-demand expansion.

**Scope**:
- Add `format` parameter to `list_dir` tool
- Implement tree format with file counts
- Show collapsed directories with expansion instructions
- Maintain full listing as default for compatibility

**Acceptance Criteria**:
- [ ] `list_dir(recursive=true, format="tree")` returns collapsed tree
- [ ] Each directory shows file count
- [ ] Expansion instructions clear
- [ ] Default behavior unchanged (backward compatible)
- [ ] gitignore awareness maintained

**Files to Modify**:
- `src/serena/tools/file_tools.py` (ListDirTool)

**Implementation Notes**:
```python
# format="tree":
"""
src/
  auth/ (12 files)
  models/ (8 files)
  utils/ (5 files)
test/ (45 files)

Expand with: list_dir("src/auth", recursive=false)
"""
```

---

### Story 4: Cache with Hash Validation
**Status**: `unassigned`
**Risk Level**: 🟢 Low
**Estimated Savings**: 80-100% on cache hits
**Effort**: 3-4 days

**Objective**: Implement file-hash-based caching for symbol and search results.

**Scope**:
- Add cache key generation (file path + content hash)
- Cache symbol overview results
- Cache find_symbol results
- Automatic invalidation on file changes
- Return cache metadata in responses

**Acceptance Criteria**:
- [ ] Symbol queries return cache keys
- [ ] Subsequent queries check cache validity
- [ ] File edits invalidate cache automatically
- [ ] Cache hit returns minimal response
- [ ] Cache miss returns full result + new key
- [ ] Memory usage stays reasonable (LRU eviction)

**Files to Modify**:
- `src/serena/symbol.py` (add caching layer)
- `src/serena/tools/symbol_tools.py` (use cache)
- New file: `src/serena/util/symbol_cache.py`

**Implementation Notes**:
```python
# Response includes cache key:
{
  "cache_key": "models.py:sha256:abc123...",
  "timestamp": "2024-01-04T10:30:00Z",
  "symbols": [...]
}

# Next query with cache key:
find_symbol(..., cache_key="models.py:sha256:abc123...")
# Returns: {"status": "cache_valid", "use_cached": true}
```

---

### Story 5: Signature Mode with Complexity Warnings
**Status**: `unassigned`
**Risk Level**: 🟡 Medium (requires guardrails)
**Estimated Savings**: 70-90%
**Effort**: 3-4 days

**Objective**: Add signature-only mode with intelligent warnings when full body needed.

**Scope**:
- Add `detail_level` parameter to find_symbol
- Extract signatures without full bodies
- Implement complexity analysis
- Provide explicit guidance when full body recommended
- Token estimation for full retrieval

**Acceptance Criteria**:
- [ ] `detail_level="signature"` returns signature + docstring only
- [ ] Complexity scoring implemented (cyclomatic, nesting depth)
- [ ] High complexity triggers warning
- [ ] Token estimates included
- [ ] Explicit recommendation to LLM when to use full body
- [ ] Zero false positives (complex code always flagged)

**Files to Modify**:
- `src/serena/tools/symbol_tools.py` (FindSymbolTool)
- `src/serena/symbol.py` (add signature extraction)
- New file: `src/serena/util/complexity_analyzer.py`

**Implementation Notes**:
```python
# Returns:
{
  "name": "process_payment",
  "signature": "def process_payment(amount: Decimal, card: Card) -> Result:",
  "docstring": "Process payment with fraud detection...",
  "complexity": {
    "score": 8.5,
    "level": "high",
    "flags": ["nested_loops", "exception_handling", "external_api_calls"]
  },
  "recommendation": "complexity_high_suggest_full_body",
  "tokens_estimate": {
    "signature": 45,
    "full_body": 850
  }
}
```

---

### Story 6: Semantic Truncation with Section Inventory
**Status**: `unassigned`
**Risk Level**: 🟡 Medium (requires guardrails)
**Estimated Savings**: 60-85%
**Effort**: 3-4 days

**Objective**: Intelligent truncation on semantic boundaries with inventory of omitted sections.

**Scope**:
- Parse code into semantic units (functions, classes, methods)
- Truncate on complete unit boundaries only
- Provide inventory of truncated sections
- Easy retrieval of specific sections

**Acceptance Criteria**:
- [ ] Never splits functions/classes mid-definition
- [ ] Truncated output includes section inventory
- [ ] Each truncated section has token estimate
- [ ] Clear instructions for retrieving specific sections
- [ ] Works across all supported languages

**Files to Modify**:
- `src/serena/tools/tools_base.py` (_limit_length method)
- `src/serena/text_utils.py` (add semantic parsing)
- New file: `src/serena/util/semantic_truncator.py`

**Implementation Notes**:
```python
{
  "included_sections": [
    {"type": "class", "name": "PaymentProcessor", "lines": "1-45"},
    {"type": "method", "name": "validate_card", "lines": "10-30"}
  ],
  "truncated_sections": [
    {"type": "method", "name": "process_payment", "lines": "46-89", "tokens": 450},
    {"type": "method", "name": "refund_payment", "lines": "90-120", "tokens": 320}
  ],
  "total_truncated_tokens": 770,
  "retrieval_hint": "Use find_symbol('PaymentProcessor/process_payment', include_body=true)"
}
```

---

### Story 7: Smart Snippet Selection
**Status**: `unassigned`
**Risk Level**: 🟢 Low
**Estimated Savings**: 40-70%
**Effort**: 2-3 days

**Objective**: Return concise but sufficient context for references, with adjustable detail.

**Scope**:
- Add `context_lines` parameter to find_referencing_symbols
- Extract usage pattern (just the call)
- Provide minimal snippet by default
- Allow context expansion on demand

**Acceptance Criteria**:
- [ ] Default context_lines=1 (configurable)
- [ ] Extract just the usage pattern (method call)
- [ ] Full line included for context
- [ ] Easy to request more context
- [ ] Works for all reference types (calls, imports, etc.)

**Files to Modify**:
- `src/serena/tools/symbol_tools.py` (FindReferencingSymbolsTool)

**Implementation Notes**:
```python
def apply(self, ..., context_lines: int = 1, extract_pattern: bool = True):
    # Returns:
    {
      "reference": "auth.py:142",
      "usage_pattern": "authenticate(user, password)",  # Extracted
      "full_line": "    result = authenticate(user, password)",
      "context_available": true,
      "request_more": "Use context_lines=3 for more context"
    }
```

---

### Story 8: Pattern Search Summaries
**Status**: `unassigned`
**Risk Level**: 🟡 Medium (requires guardrails)
**Estimated Savings**: 60-80%
**Effort**: 3 days

**Objective**: Two-phase pattern search with summary first, details on demand.

**Scope**:
- Add `output_mode` parameter to search_for_pattern
- Summary mode: counts + preview only
- Detailed mode: full matches (current behavior)
- Batch retrieval of specific matches

**Acceptance Criteria**:
- [ ] `output_mode="summary"` returns counts + first 10 matches
- [ ] `output_mode="detailed"` returns all (current behavior)
- [ ] Summary includes clear expansion instructions
- [ ] Backward compatible (detailed is default)
- [ ] Deduplication for repeated patterns

**Files to Modify**:
- `src/serena/tools/file_tools.py` (SearchForPatternTool)

**Implementation Notes**:
```python
# output_mode="summary":
{
  "total_matches": 47,
  "by_file": {
    "auth.py": 12,
    "models.py": 8,
    "api.py": 15,
    "... (5 more files)": 12
  },
  "preview": [
    {"file": "auth.py", "line": 142, "snippet": "TODO: Add rate limiting"},
    # ... first 10 matches only
  ],
  "full_results_available": "Use output_mode='detailed' to see all 47 matches"
}
```

---

### Story 9: Verbosity Control System
**Status**: `unassigned`
**Risk Level**: 🟢 Low (infrastructure)
**Estimated Savings**: 30-50% (automatic optimization)
**Effort**: 3-4 days

**Objective**: Universal verbosity parameter with automatic optimization and transparency.

**Scope**:
- Add `verbosity` parameter to Tool base class
- Implement auto mode with heuristics
- Track query patterns per session
- Always return verbosity metadata in responses

**Acceptance Criteria**:
- [ ] All tools support verbosity parameter
- [ ] Auto mode detects exploration vs implementation phases
- [ ] Responses include verbosity_used and upgrade instructions
- [ ] LLM can always override to get more detail
- [ ] Session state tracking works correctly

**Files to Modify**:
- `src/serena/tools/tools_base.py` (Tool base class)
- `src/serena/agent.py` (session tracking)
- All tool implementations (use base verbosity)

**Implementation Notes**:
```python
class Tool:
    def apply(self, ..., verbosity: Literal["minimal", "normal", "detailed", "auto"] = "auto"):
        effective_verbosity = self._resolve_verbosity(verbosity)
        result = self._generate_result(effective_verbosity)

        return self._add_metadata(result, {
            "verbosity_used": effective_verbosity,
            "verbosity_reason": "exploration_phase",
            "upgrade_available": effective_verbosity != "detailed",
            "estimated_tokens_full": 3500
        })
```

---

### Story 10: Token Estimation Framework
**Status**: `unassigned`
**Risk Level**: 🟢 Low (infrastructure)
**Estimated Savings**: N/A (enabler)
**Effort**: 2-3 days

**Objective**: Provide accurate token estimates for all tool outputs before retrieval.

**Scope**:
- Extend existing TokenCountEstimator
- Add estimation methods for different verbosity levels
- Include in all tool responses
- Support for different tokenizers (Claude, GPT, etc.)

**Acceptance Criteria**:
- [ ] All tools return token estimates
- [ ] Estimates within 10% accuracy
- [ ] Support for signature vs full body estimates
- [ ] Fast estimation (< 10ms overhead)
- [ ] Works with existing analytics module

**Files to Modify**:
- `src/serena/analytics.py` (extend TokenCountEstimator)
- `src/serena/tools/tools_base.py` (add estimation calls)

**Implementation Notes**:
```python
# Add to every response:
{
  "data": {...},
  "_tokens": {
    "current": 450,
    "if_verbosity_normal": 850,
    "if_verbosity_detailed": 2300,
    "if_include_body": 1850
  }
}
```

---

## Execution Log

### 2025-01-04
- Sprint initialized
- 10 stories defined (4 Phase 1, 4 Phase 2, 2 Phase 3)
- Risk assessment completed
- Ready to begin Phase 1 implementation

---

## Sprint Metrics

**Target Token Reduction**: 50-75%
**Stories Completed**: 0/10
**Current Phase**: 1 (Foundation)
**Estimated Total Effort**: 25-32 days

---

## Notes & Decisions

### Design Principles
1. **Backward Compatibility**: All changes must be opt-in or transparent
2. **Transparency First**: LLM always knows what detail level is being used
3. **Easy Upgrade Path**: One parameter change to get more detail
4. **Zero Accuracy Loss**: Complex code always flagged, full detail always available
5. **Progressive Disclosure**: Summary → Detail → Full body workflow

### Dependencies
- Stories 1-4 (Phase 1) are independent, can be parallelized
- Story 9 (Verbosity Control) should complete before Phase 2
- Story 10 (Token Estimation) supports all others but not blocking

### Risks & Mitigations
- **Risk**: LLM doesn't request more detail when needed
- **Mitigation**: Explicit recommendations in responses, complexity warnings
- **Risk**: Breaking changes to existing clients
- **Mitigation**: All new features opt-in, default behavior unchanged

---

## Sprint Completion Checklist

- [ ] All Phase 1 stories completed
- [ ] All Phase 2 stories completed
- [ ] All Phase 3 stories completed
- [ ] Integration tests pass
- [ ] Manual testing with Claude Code/Desktop
- [ ] Token savings verified (>50% reduction)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] README.md updated with new features
