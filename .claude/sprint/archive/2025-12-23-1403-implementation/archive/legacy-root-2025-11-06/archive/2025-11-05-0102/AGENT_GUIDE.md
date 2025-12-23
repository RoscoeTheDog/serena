# Agent Quick Reference Guide

## 🚦 Status Transition Rules

```
unassigned → in_progress (when starting)
in_progress → completed (when finished successfully)
in_progress → error (when failed, requires user intervention)
error → in_progress (after user approves remediation)
in_progress → blocked (when external dependency needed)
blocked → in_progress (when dependency resolved)
unassigned → superseded (when story broken into sub-stories)
```

## 📋 Before You Start

```bash
# 1. Read index.md
# 2. Find next unassigned story
# 3. Immediately update status to in_progress
# 4. Begin work
```

## ✅ Story Completion Checklist

- [ ] All acceptance criteria checked off
- [ ] Implementation tested and working
- [ ] Files modified list is accurate
- [ ] Status updated to `completed`
- [ ] Sprint metrics updated
- [ ] Execution log entry added

## ❌ Error Handling Protocol

When encountering errors:

```markdown
### Story X: [Story Name]
**Status**: `error`

... existing story content ...

## Remediation Plan

**Root Cause**: [What went wrong]

**Proposed Fix**: [How to fix it]

**Impact Assessment**:
- Breaking changes: [Yes/No]
- Affects other stories: [List]
- Requires story reorganization: [Yes/No]

**Recommended Actions**:
1. [Action 1]
2. [Action 2]

**User Decision Required**: HALT - Awaiting approval to proceed
```

Then **STOP** and wait for user response.

## 📊 Updating Sprint Metrics

After completing a story:

```markdown
**Stories Completed**: X/10  (increment by 1)
```

## 🔍 Finding Your Next Story

Stories should be executed in sequence:
1. Complete all Phase 1 stories (1-4) first
2. Then Phase 2 stories (5-8)
3. Finally Phase 3 stories (9-10)

Exception: Stories marked as independent can be done in any order within phase.

## 📝 Inline Updates

Update the story section directly in index.md:

```markdown
### Story 1: Structural JSON Optimization
**Status**: `in_progress` ← UPDATE THIS

**Progress**:
- [x] Symbol results deduplicate file paths ← CHECK THESE
- [ ] Null/empty fields omitted with schema marker
...

**Implementation Log**:
- 2025-01-04 10:30: Started implementation
- 2025-01-04 11:45: Completed symbol.py modifications
- 2025-01-04 13:20: All unit tests passing
```

## 🎯 Single-Agent Rule

**ONLY ONE STORY** should be `in_progress` at any time.

If you see multiple stories in `in_progress` state, this is an error. Fix it before proceeding.

## 🔄 Story Breakdown

If a story is too complex, break it down:

1. Update parent story status to `superseded`
2. Add breakdown note to parent story
3. Create sub-stories: X.1, X.2, X.3, etc.
4. Set all sub-stories to `unassigned`
5. Update story index with new sub-stories

Example:
```markdown
### Story 5: Signature Mode with Complexity Warnings
**Status**: `superseded`

**Breakdown Reason**: Story too complex, split into implementation phases

**Sub-stories**:
- 5.1: Extract signatures without complexity (simple case)
- 5.2: Implement complexity analyzer
- 5.3: Integrate complexity warnings into responses

---

### Story 5.1: Extract Signatures Without Complexity
**Status**: `unassigned`
... details ...
```

## 📅 Execution Log Format

Add entries as you work:

```markdown
## Execution Log

### 2025-01-04
- 10:00: Story 1 started - Structural JSON Optimization
- 11:45: Story 1 - Modified symbol.py, added structural deduplication
- 13:20: Story 1 completed - All tests passing, 25% token reduction verified

### 2025-01-05
- 09:00: Story 2 started - Diff-Based Edit Responses
...
```

## 🏁 Sprint Completion

When all stories are `completed` or `blocked`:

1. Update sprint status to `completed`
2. Add completion timestamp
3. Write final summary section
4. Check all sprint completion checklist items
5. Update CHANGELOG.md
6. Update README.md if needed

## 💡 Tips

- **Read before you code**: Understand the full story scope
- **Update frequently**: Don't wait until end to update status
- **Be specific**: Implementation notes should be detailed
- **Test thoroughly**: Check all acceptance criteria
- **Ask for help**: Use `error` status if stuck, don't guess

## 🚫 Common Mistakes

- ❌ Starting story without updating status to `in_progress`
- ❌ Working on multiple stories simultaneously
- ❌ Marking story complete before checking all acceptance criteria
- ❌ Not updating sprint metrics after completion
- ❌ Continuing work when status is `error` (must wait for user)
- ❌ Breaking backward compatibility without explicit approval
