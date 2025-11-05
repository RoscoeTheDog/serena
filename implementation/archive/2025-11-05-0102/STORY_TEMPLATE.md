# Story Template

Use this template when breaking down complex stories or adding new stories.

---

## Story X: [Story Title]
**Status**: `unassigned`
**Risk Level**: 🟢 Low | 🟡 Medium | 🔴 High
**Estimated Savings**: X-Y%
**Effort**: X days
**Dependencies**: [List story numbers, or "None"]

**Objective**: [One sentence description of what this story achieves]

**Scope**:
- [Key deliverable 1]
- [Key deliverable 2]
- [Key deliverable 3]

**Acceptance Criteria**:
- [ ] [Testable criterion 1]
- [ ] [Testable criterion 2]
- [ ] [Testable criterion 3]
- [ ] Unit tests pass
- [ ] Manual testing verified
- [ ] Backward compatibility maintained

**Files to Modify**:
- `path/to/file1.py` (brief description of changes)
- `path/to/file2.py` (brief description of changes)

**Files to Create**:
- `path/to/new_file.py` (purpose)

**Implementation Notes**:
```python
# Key code pattern or architecture notes
# Example:
def new_function(param: Type) -> ReturnType:
    """Purpose of function"""
    pass
```

**Test Strategy**:
- Unit tests: [What to test]
- Integration tests: [What to test]
- Manual testing: [Steps to verify]

**Rollback Plan**:
[If this story fails or needs to be reverted, what's the process?]

---

## Progress Log

### [YYYY-MM-DD HH:MM]
- [Progress update]

### [YYYY-MM-DD HH:MM]
- [Progress update]

---

## Risks & Mitigations

**Risk 1**: [Description]
- **Mitigation**: [How to handle it]
- **Likelihood**: Low/Medium/High
- **Impact**: Low/Medium/High

**Risk 2**: [Description]
- **Mitigation**: [How to handle it]
- **Likelihood**: Low/Medium/High
- **Impact**: Low/Medium/High

---

## Completion Checklist

- [ ] All acceptance criteria checked
- [ ] All files modified/created as planned
- [ ] Tests written and passing
- [ ] Manual testing completed
- [ ] Documentation updated (if needed)
- [ ] No regressions introduced
- [ ] Code reviewed (self-review or peer)
- [ ] Ready for production

---

## Notes

[Any additional context, discoveries during implementation, etc.]
