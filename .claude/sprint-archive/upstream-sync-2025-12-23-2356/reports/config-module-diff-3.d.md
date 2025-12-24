# Side-by-Side Diff: context_mode.py (Fork vs Upstream)

**Generated**: 2025-12-23
**Story**: 3.i - Implementation: Merge Upstream Config Module Changes
**Purpose**: GATE checkpoint - Human review required before merge
**Status**: AWAITING APPROVAL

---

## Executive Summary

This document presents a side-by-side comparison of `context_mode.py` between our fork and upstream. The analysis identifies **3 critical fork enhancements** that MUST be preserved during merge, and **2 upstream changes** that need evaluation for incorporation.

**Conflict Severity**: MEDIUM
**Merge Complexity**: MEDIUM
**Action Required**: Human approval of merge strategy

---

## Critical Fork Enhancements (MUST PRESERVE)

### 1. Deprecation Mapping (Lines 172-177)

**Location**: `SerenaAgentContext.from_name()` method
**Purpose**: Backwards compatibility for ide-assistant → claude-code rename
**Marker**: `[FORK-PRESERVE]`

**Fork Code** (OURS):
```python
@classmethod
def from_name(cls, name: str) -> Self:
    """Load a registered Serena context."""
    # Handle deprecation mapping
    if name == "ide-assistant":
        log.warning(
            "Context 'ide-assistant' is deprecated. Please use 'claude-code' instead. "
            "Automatically redirecting to 'claude-code' for backwards compatibility."
        )
        name = "claude-code"

    context_path = cls.get_path(name)
    return cls.from_yaml(context_path)
```

**Upstream Code**:
```python
@classmethod
def from_name(cls, name: str) -> Self:
    """Load a registered Serena context."""
    context_path = cls.get_path(name)
    return cls.from_yaml(context_path)
```

**Merge Decision**: **PRESERVE FORK VERSION** - This is critical for backwards compatibility after Story 2 rename

---

### 2. single_project Field Removal (Line 149)

**Location**: `SerenaAgentContext.from_yaml()` method
**Purpose**: Backwards compatibility - removes obsolete field before dataclass instantiation
**Marker**: `[FORK-PRESERVE]`

**Fork Code** (OURS):
```python
@classmethod
def from_yaml(cls, yaml_path: str | Path) -> Self:
    """Load a context from a YAML file."""
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    name = data.pop("name", Path(yaml_path).stem)
    # Ensure backwards compatibility for tool_description_overrides
    if "tool_description_overrides" not in data:
        data["tool_description_overrides"] = {}
    # Remove single_project field (used for context behavior, not part of dataclass)
    data.pop("single_project", None)  # <-- FORK ENHANCEMENT
    return cls(name=name, **data)
```

**Upstream Code**: (same except missing `data.pop("single_project", None)` line)

**Merge Decision**: **PRESERVE FORK VERSION** - Critical for backward compatibility with old YAML configs

---

### 3. USER_MODE_YAMLS_DIR and USER_CONTEXT_YAMLS_DIR imports (Lines 22-23)

**Location**: Import statements
**Purpose**: Support for user-defined custom modes/contexts
**Marker**: `[FORK-PRESERVE]`

**Fork Code** (OURS):
```python
from serena.constants import (
    DEFAULT_CONTEXT,
    DEFAULT_MODES,
    INTERNAL_MODE_YAMLS_DIR,
    SERENAS_OWN_CONTEXT_YAMLS_DIR,
    SERENAS_OWN_MODE_YAMLS_DIR,
    USER_CONTEXT_YAMLS_DIR,  # <-- FORK ENHANCEMENT
    USER_MODE_YAMLS_DIR,      # <-- FORK ENHANCEMENT
)
```

**Upstream Code**:
```python
from serena.constants import (
    DEFAULT_CONTEXT,
    DEFAULT_MODES,
    INTERNAL_MODE_YAMLS_DIR,
    SERENA_FILE_ENCODING,     # <-- UPSTREAM ADDITION
    SERENAS_OWN_CONTEXT_YAMLS_DIR,
    SERENAS_OWN_MODE_YAMLS_DIR,
    # Missing USER_CONTEXT_YAMLS_DIR and USER_MODE_YAMLS_DIR
)
```

**Merge Decision**: **MERGE BOTH** - Keep fork's USER_* imports AND add upstream's SERENA_FILE_ENCODING

---

## Upstream Changes (Needs Evaluation)

### 1. SERENA_FILE_ENCODING Import

**Change Type**: New import
**Marker**: `[UPSTREAM-SAFE]`

**Description**: Upstream added `SERENA_FILE_ENCODING` constant import, likely for standardizing file encoding across the codebase.

**Impact**: Low - This is a safe addition that improves code consistency
**Decision**: **ACCEPT** - Add this import to our fork

---

### 2. SerenaPaths Import Addition

**Change Type**: Import modification
**Marker**: `[UPSTREAM-SAFE]`

**Fork Import**:
```python
from serena.config.serena_config import ToolInclusionDefinition
```

**Upstream Import**:
```python
from serena.config.serena_config import SerenaPaths, ToolInclusionDefinition
```

**Impact**: Low - Upstream explicitly imports SerenaPaths (may be used elsewhere in upstream version)
**Decision**: **ACCEPT** - This is safe and improves explicit imports

---

## Line-by-Line Conflict Analysis

| Line Range | Section | Fork Version | Upstream Version | Conflict | Resolution |
|------------|---------|--------------|------------------|----------|------------|
| 1-5 | File header | Same | Same | NONE | Keep as-is |
| 6-10 | Imports | `from dataclasses import dataclass, field` | Missing `field` import | MINOR | Keep fork (field used in line 133) |
| 13-15 | Imports | `from serena.config.serena_config import ToolInclusionDefinition` | `from serena.config.serena_config import SerenaPaths, ToolInclusionDefinition` | MINOR | **ACCEPT UPSTREAM** - Add SerenaPaths import |
| 16-24 | Imports | Includes `USER_CONTEXT_YAMLS_DIR`, `USER_MODE_YAMLS_DIR` | Includes `SERENA_FILE_ENCODING` | MEDIUM | **MERGE BOTH** - Combine all three |
| 145-150 | from_yaml | Has `data.pop("single_project", None)` | Missing this line | CRITICAL | **PRESERVE FORK** - Backward compatibility |
| 172-177 | from_name | Has deprecation mapping | Missing deprecation | CRITICAL | **PRESERVE FORK** - ide-assistant redirect |
| Rest | Other | Same | Same | NONE | Keep as-is |

---

## Recommended Merge Strategy

### Step 1: Accept Safe Upstream Changes
- Add `SERENA_FILE_ENCODING` to imports (line ~18)
- Add `SerenaPaths` to serena_config import (line ~13)

### Step 2: Preserve Critical Fork Enhancements
- **KEEP** deprecation mapping in `from_name()` (lines 172-177)
- **KEEP** `data.pop("single_project", None)` in `from_yaml()` (line 149)
- **KEEP** `USER_CONTEXT_YAMLS_DIR` and `USER_MODE_YAMLS_DIR` imports (lines 22-23)

### Step 3: Verify No Other Upstream Changes
Review rest of file for any other upstream modifications we should consider

---

## Merge Execution Plan

1. **Backup current fork version** (git-tracked, safe to proceed)
2. **Apply upstream imports** (SERENA_FILE_ENCODING, SerenaPaths)
3. **Verify fork enhancements intact** (deprecation mapping, single_project removal)
4. **Run unit tests** to confirm backward compatibility
5. **Commit with clear message** documenting merge decisions

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Lose deprecation mapping | HIGH | Low (we're careful) | Verify lines 172-177 after merge |
| Lose single_project removal | HIGH | Low (we're careful) | Verify line 149 after merge |
| Break backward compatibility | HIGH | Low (tests will catch) | Run existing test suite |
| Merge conflicts in tests | MEDIUM | Medium | Review test files separately |

---

## Approval Section

**GATE Checkpoint**: This merge strategy must be approved before execution.

**Approver**: ___________________
**Date**: ___________________
**Approval Status**: [ ] APPROVED  [ ] REJECTED  [ ] NEEDS REVISION

**Notes**:
_____________________________________________________________________________
_____________________________________________________________________________

---

## Next Steps (After Approval)

1. Execute merge following strategy above
2. Run test suite: `pytest tests/config/test_context_mode.py -v`
3. Verify deprecation mapping works: Test `ide-assistant` → `claude-code` redirect
4. Verify single_project field removal: Test loading old YAML configs
5. Commit changes with detailed message
6. Proceed to Story 3.t (testing phase)

---

**Generated by**: Story 3.i (Implementation Phase)
**Diff Method**: git diff + manual analysis
**Pattern Source**: .claude/sprint/reports/conflict-analysis.md
