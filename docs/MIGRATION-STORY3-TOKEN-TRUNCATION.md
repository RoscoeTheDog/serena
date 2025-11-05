# Migration Guide: Story 3 - Token-Aware Truncation System

**Status**: Implementation Complete (Core System)
**Version**: 2.0.0 (Breaking changes in next major version)
**Date**: 2025-11-04

## Overview

Story 3 replaces the ambiguous `max_answer_chars` parameter with a clear, token-aware truncation system featuring three modes: `error`, `summary`, and `paginate`.

## Key Changes

### What's New

1. **New Parameter**: `max_tokens: int | None = None`
   - Token-based limit (not character-based)
   - `None` = no limit
   - Uses `FastTokenEstimator` for accurate calculation

2. **New Parameter**: `truncation: Literal["error", "summary", "paginate"] = "error"`
   - `"error"` (default): Fail fast with actionable suggestions
   - `"summary"`: Return truncated content with expansion hints
   - `"paginate"`: Return first page with cursor for next page

3. **New Metadata**: `_truncation` field in responses
   - `total_available`: Total tokens available
   - `returned`: Tokens actually returned
   - `truncated`: Boolean flag
   - `strategy`: Truncation strategy used
   - `expansion_hint`: How to get full content
   - `narrowing_suggestions`: Tool-specific suggestions

### What's Deprecated

1. **Parameter**: `max_answer_chars: int = -1`
   - Still works but shows deprecation warning
   - Will be removed in v2.0.0
   - Automatically converted to `max_tokens` (chars / 4)

## Migration Strategy

### Phase 1: Backward Compatibility (Current)

All tools continue to work with `max_answer_chars`. No immediate action required.

```python
# OLD API (still works)
find_symbol("User", max_answer_chars=10000)

# NEW API (recommended)
find_symbol("User", max_tokens=2500, truncation="error")
```

### Phase 2: Tool Updates (In Progress)

Tool authors should update their tools to use the new system.

### Phase 3: Deprecation Warnings (Next Release)

Tools using `max_answer_chars` will show deprecation warnings in responses:

```json
{
  "results": [...],
  "_deprecated": {
    "parameter": "max_answer_chars",
    "replacement": "max_tokens",
    "removal_version": "2.0.0",
    "migration": "Use max_tokens=N instead of max_answer_chars=N*4"
  }
}
```

### Phase 4: Removal (v2.0.0)

The `max_answer_chars` parameter will be removed entirely.

## For Tool Authors

### Step 1: Add New Parameters

Update your tool's `apply()` signature:

```python
def apply(
    self,
    # ... existing parameters ...
    max_answer_chars: int = -1,  # Keep for backward compatibility
    max_tokens: int | None = None,  # NEW
    truncation: Literal["error", "summary", "paginate"] = "error",  # NEW
) -> str:
```

### Step 2: Resolve Max Tokens

Use the helper method to resolve the token limit:

```python
# At the start of your apply() method
resolved_max_tokens = self._resolve_max_tokens(
    max_tokens=max_tokens,
    max_answer_chars=max_answer_chars,
)
```

### Step 3: Prepare Narrowing Suggestions

Create tool-specific suggestions for narrowing queries:

```python
narrowing_suggestions = []

# Example for find_symbol
if not relative_path:
    narrowing_suggestions.append("Use relative_path='src/' to search in specific directory")
if depth > 1:
    narrowing_suggestions.append(f"Use depth=1 instead of depth={depth}")
if substring_matching:
    narrowing_suggestions.append("Use substring_matching=False for exact matches")
if not include_kinds:
    narrowing_suggestions.append("Use include_kinds=[5] to filter by symbol type (e.g., 5=class)")
```

### Step 4: Handle Truncation

Use `_handle_truncation()` before returning results:

```python
# Generate your result (as dict or string)
result = {"results": symbol_list, ...}

# Handle truncation
result, truncation_metadata = self._handle_truncation(
    content=result,
    max_tokens=resolved_max_tokens,
    truncation=truncation,
    narrowing_suggestions=narrowing_suggestions,
)

# Add truncation metadata to response
if truncation_metadata is not None:
    return self._add_token_metadata(
        result=result,
        truncation_metadata=truncation_metadata,
    )
else:
    return json.dumps(result) if isinstance(result, dict) else result
```

### Step 5: Add Deprecation Warning (Optional)

If `max_answer_chars` was used, add deprecation info:

```python
if max_answer_chars != -1 and max_tokens is None:
    if isinstance(result, dict):
        result["_deprecated"] = {
            "parameter": "max_answer_chars",
            "replacement": "max_tokens",
            "removal_version": "2.0.0",
            "migration": f"Use max_tokens={max_answer_chars // 4} instead of max_answer_chars={max_answer_chars}",
        }
```

## Complete Example

Here's a complete example for updating a tool:

```python
class FindSymbolTool(Tool, ToolMarkerSymbolicRead):
    def apply(
        self,
        name_path: str,
        depth: int = 0,
        relative_path: str = "",
        # ... other parameters ...
        max_answer_chars: int = -1,  # DEPRECATED
        max_tokens: int | None = None,  # NEW
        truncation: Literal["error", "summary", "paginate"] = "error",  # NEW
    ) -> str:
        # Step 1: Resolve max_tokens from old/new parameters
        resolved_max_tokens = self._resolve_max_tokens(
            max_tokens=max_tokens,
            max_answer_chars=max_answer_chars,
        )

        # Step 2: Build narrowing suggestions
        narrowing_suggestions = []
        if not relative_path:
            narrowing_suggestions.append("Use relative_path='src/' to narrow search scope")
        if depth > 1:
            narrowing_suggestions.append(f"Use depth=1 instead of depth={depth}")

        # Step 3: Execute tool logic
        symbols = self._find_symbols(name_path, depth, relative_path)
        result = {
            "_schema": "structured_v1",
            "symbols": [s.to_dict() for s in symbols],
            "count": len(symbols),
        }

        # Step 4: Add deprecation warning if needed
        if max_answer_chars != -1 and max_tokens is None:
            result["_deprecated"] = {
                "parameter": "max_answer_chars",
                "replacement": "max_tokens",
                "removal_version": "2.0.0",
                "migration": f"Use max_tokens={max_answer_chars // 4}",
            }

        # Step 5: Handle truncation
        result, truncation_metadata = self._handle_truncation(
            content=result,
            max_tokens=resolved_max_tokens,
            truncation=truncation,
            narrowing_suggestions=narrowing_suggestions,
        )

        # Step 6: Add metadata and return
        return self._add_token_metadata(
            result=result,
            truncation_metadata=truncation_metadata,
        )
```

## Tool-Specific Narrowing Suggestions

### find_symbol

```python
narrowing_suggestions = []
if not relative_path:
    narrowing_suggestions.append("Use relative_path='src/models' to search specific directory")
if depth > 1:
    narrowing_suggestions.append(f"Use depth=1 to get only immediate children")
if substring_matching:
    narrowing_suggestions.append("Use substring_matching=False for exact name matches")
if not include_kinds:
    narrowing_suggestions.append("Use include_kinds=[5,12] to filter by type (5=class, 12=function)")
```

### list_dir

```python
narrowing_suggestions = []
if recursive:
    narrowing_suggestions.append("Use recursive=False to avoid deep directory traversal")
if not relative_path or relative_path == ".":
    narrowing_suggestions.append("Use relative_path='src' to target specific subdirectory")
```

### search_for_pattern

```python
narrowing_suggestions = []
if not relative_path:
    narrowing_suggestions.append("Use relative_path='src' to search in specific directory")
if result_format == "detailed":
    narrowing_suggestions.append("Use result_format='summary' for token-efficient overview")
if len(pattern) < 5:
    narrowing_suggestions.append("Make search pattern more specific to reduce matches")
```

### get_symbols_overview

```python
narrowing_suggestions = []
if os.path.isdir(file_path):
    narrowing_suggestions.append("Target a specific file instead of entire directory")
# Overview tool is typically small, may not need suggestions
```

### find_referencing_symbols

```python
narrowing_suggestions = []
if mode == "full":
    narrowing_suggestions.append("Use mode='summary' or mode='count' for fewer tokens")
if context_lines > 1:
    narrowing_suggestions.append(f"Use context_lines=1 instead of context_lines={context_lines}")
```

## Testing Your Migration

### Unit Tests

```python
def test_backward_compatibility():
    """Test that max_answer_chars still works."""
    result = tool.apply(name="User", max_answer_chars=10000)
    assert "_deprecated" in json.loads(result)

def test_new_api_error_mode():
    """Test error mode raises TruncationError."""
    with pytest.raises(TruncationError) as exc:
        tool.apply(name="*", max_tokens=100, truncation="error")
    assert "narrowing_suggestions" in exc.value.to_dict()

def test_new_api_summary_mode():
    """Test summary mode truncates intelligently."""
    result = tool.apply(name="*", max_tokens=500, truncation="summary")
    data = json.loads(result)
    assert data["_truncation"]["truncated"] is True
    assert "expansion_hint" in data["_truncation"]

def test_new_api_paginate_mode():
    """Test paginate mode provides cursor."""
    result = tool.apply(name="*", max_tokens=500, truncation="paginate")
    data = json.loads(result)
    assert "next_page" in data["_truncation"]
```

### Integration Tests

```python
def test_large_result_set_with_error():
    """Test realistic scenario with error mode."""
    # This should raise TruncationError with helpful suggestions
    pass

def test_large_result_set_with_summary():
    """Test realistic scenario with summary mode."""
    # This should return truncated results with metadata
    pass
```

## FAQs

### Q: Do I need to update all tools immediately?

**A**: No. The old `max_answer_chars` API continues to work via backward compatibility layer. However, updating is recommended for better UX.

### Q: What if my tool doesn't have `max_answer_chars`?

**A**: You can still adopt the new system. Add `max_tokens` and `truncation` parameters and use `_handle_truncation()`.

### Q: How do I know what max_tokens value is reasonable?

**A**: Use `FastTokenEstimator` to estimate your typical output:
```python
estimator = self._get_token_estimator()
typical_tokens = estimator.estimate_json(typical_result)
# Set max_tokens to 2-3x typical for headroom
```

### Q: Can I customize truncation behavior?

**A**: Yes! Override `_handle_truncation()` in your tool class for custom logic. The base implementation provides sensible defaults.

### Q: Should I use error, summary, or paginate as default?

**A**: Use `"error"` as default (fail-fast with guidance). Let agents opt into `"summary"` or `"paginate"` when they expect large results.

## Reference

- **Story 3 Spec**: `implementation/index.md` (lines 137-218)
- **Implementation**: `src/serena/tools/tools_base.py` (lines 308-451)
- **Token Estimator**: `src/serena/util/token_estimator.py`
- **Tests**: `test/serena/tools/test_story3_truncation.py`

## Support

For questions or issues with migration:
1. Check existing tool implementations (find_symbol, get_symbols_overview)
2. Review test cases for usage patterns
3. Consult the Story 3 implementation notes in index.md
