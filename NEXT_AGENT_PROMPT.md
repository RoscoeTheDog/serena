# Agent Handoff - LSP Timeout Bugfix Implementation

## 🎯 Your Mission

Implement a bugfix for the **find_symbol stalling issue** that causes 12+ minute hangs when querying symbols with `include_body=True`. This is a critical bug blocking agent operations.

---

## 📋 Implementation Plan

**READ THIS FIRST**: `implementation/LSP_TIMEOUT_BUGFIX.md`

This is a **living document** that you MUST update as you progress:
- ✅ Mark checkboxes as you complete tasks
- 📝 Update timestamps at the top
- 📊 Add entries to the Implementation Log
- 🔄 Update status fields when transitioning phases

---

## 🚀 Quick Start

### Step 1: Read the Plan
```bash
cat implementation/LSP_TIMEOUT_BUGFIX.md
```

### Step 2: Understand the Problem
- **Root Cause**: Pyright LSP hangs processing `request_document_symbols` with `include_body=True`
- **Current Behavior**: 235s timeout exists but errors are swallowed → silent retries → indefinite stall
- **Target File**: `src/solidlsp/ls.py`

### Step 3: Implementation Approach
**3 Phases in Single Session** (2-3 hours):

1. **Phase 1** (30 min): Add timeout error visibility
   - Catch `TimeoutError` in `request_document_symbols`
   - Log warnings clearly
   - Return empty result instead of hanging

2. **Phase 2** (1 hour): Optimize body retrieval
   - Add `_retrieve_symbol_body_from_filesystem()` method
   - Replace nested `open_file()` calls with filesystem reads
   - Add fallback to LSP if filesystem fails

3. **Phase 3** (30 min): Enhanced logging
   - Add timing instrumentation
   - Performance metrics

4. **Testing** (30-60 min): Comprehensive validation
   - Index entire serena codebase (155 files)
   - Test `find_symbol` with problematic files
   - Verify no regressions

---

## ⚠️ Critical Requirements

### 1. Update the Living Document
**MANDATORY** after each checkbox:
```markdown
# Update at top of implementation/LSP_TIMEOUT_BUGFIX.md
**Last Updated**: 2025-11-03 [TIME]
**Status**: [Phase X In Progress]

# Add to Implementation Log section
#### [TIME] - [PHASE] - [ACTION]
- **What**: [Description]
- **Result**: Success/Failure
- **Issues**: [Any problems]
- **Decisions**: [Deviations from plan]
- **Next**: [Next step]
```

### 2. Preserve Indexing Accuracy
- ✅ Serena MUST still index all files with bodies
- ✅ NO loss of precision or functionality
- ✅ Filesystem retrieval only AFTER LSP validates file
- ✅ Fallback to LSP if filesystem fails

### 3. Follow the Checklist
The plan has a complete checklist starting at line 311:
- Pre-Implementation (8 items)
- Phase 1 (4 items)
- Phase 2 (6 items)
- Phase 3 (3 items)
- Testing (6 items)
- Documentation (5 items)

**Mark each item as complete immediately after finishing it.**

---

## 🧪 Testing Commands

### Test find_symbol (should timeout gracefully, not hang)
```python
# Via serena MCP
find_symbol(
    name_path="SolidLanguageServer/__init__",
    relative_path="src/solidlsp/ls.py",
    include_body=True
)
```

### Test indexing (should complete successfully)
```bash
cd /c/Users/Admin/Documents/GitHub/serena
serena index .
# Should index all 155 files without hanging
```

### Verify logs
```bash
tail -100 ~/.serena/logs/$(date +%Y-%m-%d)/mcp_*.txt | grep -i "timeout\|error"
```

---

## 📊 Success Criteria

Before committing, verify:
1. ✅ `find_symbol` operations complete within 240s (never hang)
2. ✅ Timeout errors are logged with clear warnings
3. ✅ All 155 files in serena codebase index successfully
4. ✅ Symbol bodies match original implementation
5. ✅ Indexing performance improves by 10-30%
6. ✅ Failed files are logged, other files continue

---

## 🎯 Implementation Flow

```
START
  ↓
Update plan status → "Phase 1 In Progress"
  ↓
Phase 1: Timeout Visibility (30 min)
  - Read request_document_symbols() [line 955]
  - Add TimeoutError exception handling [line 988]
  - Test timeout behavior
  - ✅ Mark checkboxes, log progress
  ↓
Phase 2: Filesystem Optimization (1 hour)
  - Implement _retrieve_symbol_body_from_filesystem()
  - Update turn_item_into_symbol_with_children() [line 1026]
  - Test on small/large files
  - ✅ Mark checkboxes, log progress
  ↓
Phase 3: Enhanced Logging (30 min)
  - Add timing instrumentation
  - Add debug logs
  - ✅ Mark checkboxes, log progress
  ↓
Testing & Validation (30-60 min)
  - Run serena index .
  - Test find_symbol on ls.py
  - Verify no regressions
  - ✅ Mark checkboxes, log progress
  ↓
Documentation & Commit
  - Update code comments
  - Write commit message (template in plan)
  - Update plan status → "Complete"
  - Add final summary to Implementation Log
  - Commit
  ↓
END
```

---

## 📌 Key Reminders

### DO ✅
- ✅ Update the living document after EVERY checkbox
- ✅ Add Implementation Log entries for significant events
- ✅ Test after each phase before moving to next
- ✅ Preserve indexing accuracy (use filesystem AFTER LSP validates)
- ✅ Add fallback to LSP if filesystem fails
- ✅ Log timing metrics for performance tracking

### DON'T ❌
- ❌ Skip checkbox updates (they track your progress)
- ❌ Skip the Implementation Log (it documents discoveries)
- ❌ Break indexing accuracy (Serena's core value)
- ❌ Skip testing between phases
- ❌ Commit without updating plan to "Complete"

---

## 🔗 Related Commits

- **Previous fix**: `10f9924` - Rust analyzer timeout fix (60s timeout with fallback)
- **Plan commit**: `d065c4a` - This implementation plan

---

## 📝 Commit Message Template

When you're done, use this format:

```
fix: Add timeout handling and optimize body retrieval for find_symbol

Fixes indefinite stalling when find_symbol is called with include_body=True
on complex files. Previously, Pyright LSP timeouts were caught but errors
were swallowed, causing silent retries and 12+ minute hangs.

Changes:
- Phase 1: Add explicit TimeoutError handling in request_document_symbols
  - Log warnings clearly
  - Return empty result instead of hanging

- Phase 2: Optimize symbol body retrieval
  - Implement _retrieve_symbol_body_from_filesystem() method
  - Read bodies directly from filesystem after LSP validates file
  - Add fallback to LSP-based retrieval on errors
  - Avoids nested open_file() calls that caused issues

- Phase 3: Enhanced logging and metrics
  - Add timing instrumentation to track performance
  - Log detailed debug info for troubleshooting

Testing:
- All 155 files in serena codebase index successfully
- find_symbol with include_body=True completes within 240s
- Indexing performance improved by [X]%
- No regressions in symbol body accuracy

Fixes: Issue #2 - find_symbol stalling on Pyright LSP requests
Related: Issue #1 - Rust analyzer timeout (commit 10f9924)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 🆘 If You Get Stuck

1. **Check the plan**: All implementation details are in `implementation/LSP_TIMEOUT_BUGFIX.md`
2. **Review logs**: `~/.serena/logs/[DATE]/mcp_*.txt`
3. **Test incrementally**: Don't wait until the end to test
4. **Document issues**: Add to Implementation Log immediately
5. **Ask questions**: If something is unclear, document it in the log

---

## ✅ Ready to Start

You have everything you need:
- ✅ Complete implementation plan with step-by-step instructions
- ✅ Code examples for each phase
- ✅ Testing strategy and success criteria
- ✅ Living document protocol for tracking progress
- ✅ Commit message template

**Good luck! Remember to update the plan as you go!** 🚀
