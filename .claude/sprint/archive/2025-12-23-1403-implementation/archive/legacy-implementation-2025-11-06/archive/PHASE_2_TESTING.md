# Phase 2: Testing & Validation

**Part of**: AUTO_ONBOARDING_MASTER.md
**Session**: Session 3
**Est. Time**: 3-4 hours
**Est. Tokens**: 56k tokens
**Prerequisites**: Sessions 1-2 complete, helpers implemented

---

## Session 3 Goals

- [ ] Create integration tests for auto-onboarding workflow
- [ ] Manual test across diverse project types
- [ ] Test edge cases and error handling
- [ ] Fix bugs discovered during testing
- [ ] Verify performance <300ms

**Deliverable**: Fully tested auto-onboarding, ready for production

---

## Integration Tests

### File: `test/serena/tools/test_auto_onboarding_integration.py`

```python
def test_auto_onboard_new_project():
    """Test that new project activation creates memories automatically."""
    # Create temp project
    # Activate project
    # Assert 3-4 memories created
    # Assert memory content correct

def test_skip_onboarding_for_existing():
    """Test that existing onboarded projects skip auto-onboarding."""
    # Activate project with existing memories
    # Assert no new memories created
    # Assert "already onboarded" in response
```

---

## Manual Testing Checklist

### Node.js Projects
- [ ] **Basic npm**: package.json with scripts
  - Expected: "Node.js/npm" detected, npm scripts in commands
- [ ] **React**: package.json with react dependency
  - Expected: "React" in tech stack
- [ ] **TypeScript**: package.json with typescript dependency
  - Expected: "TypeScript" in tech stack
- [ ] **Next.js**: package.json with next dependency
  - Expected: "Next.js" in tech stack
- [ ] **With ESLint**: .eslintrc.json present
  - Expected: ESLint in code style memory
- [ ] **With Prettier**: .prettierrc present
  - Expected: Prettier in code style memory

### Python Projects
- [ ] **Poetry**: pyproject.toml with tool.poetry
  - Expected: "Python/Poetry" detected, poetry scripts in commands
- [ ] **pip**: requirements.txt present
  - Expected: "Python/pip" detected
- [ ] **Black**: pyproject.toml with tool.black
  - Expected: Black in code style memory
- [ ] **Ruff**: pyproject.toml with tool.ruff
  - Expected: Ruff in code style memory

### Rust Projects
- [ ] **Cargo**: Cargo.toml present
  - Expected: "Rust/Cargo" detected, cargo commands in checklist

### Other Languages
- [ ] **Go**: go.mod present
- [ ] **Ruby**: Gemfile present
- [ ] **Java/Maven**: pom.xml present
- [ ] **Java/Gradle**: build.gradle present

### Build Tools
- [ ] **Makefile**: Targets extracted correctly
- [ ] **Docker**: Dockerfile detected
- [ ] **Docker Compose**: compose.yaml detected

### Multi-Language Projects
- [ ] **Node + Python**: Detects both, shows dominant
- [ ] **Rust + Docker**: Shows both in tech stack

---

## Edge Case Testing

### Malformed Files
- [ ] Invalid JSON in package.json
  - Expected: Graceful fallback, partial detection
- [ ] Invalid TOML in pyproject.toml
  - Expected: Graceful fallback, minimal detection
- [ ] Empty package.json
  - Expected: No crash, basic detection

### Missing Files
- [ ] Project with no config files
  - Expected: "Unknown" tech stack, basic memories created
- [ ] Permission denied on file read
  - Expected: Graceful error, activation succeeds

### Large Files
- [ ] Huge Makefile (>1000 lines)
  - Expected: Parse first 500 lines, no timeout
- [ ] Large package.json (>100 scripts)
  - Expected: All scripts detected, reasonable performance

---

## Performance Testing

### Benchmark
```bash
# Measure activation time
time activate_project /path/to/test-project
```

**Acceptance**: <300ms overhead for auto-onboarding

### Profile Hotspots
- File I/O operations
- JSON/TOML parsing
- Makefile regex matching
- Memory writes

**Optimization**: Cache file existence checks if needed

---

## Bug Fixes

Common bugs to watch for:

1. **TOML import error on Python <3.11**
   - Fix: Add tomli fallback

2. **Makefile parsing fails on Windows**
   - Fix: Handle CRLF line endings

3. **Memory content has incorrect formatting**
   - Fix: Verify markdown syntax

4. **Tech stack shows duplicates**
   - Fix: Use set() to deduplicate

---

## Acceptance Criteria

- [ ] All integration tests pass
- [ ] Manual tests complete for 5+ project types
- [ ] Edge cases handled gracefully
- [ ] Performance <300ms
- [ ] No false positives in detection
- [ ] Memory quality acceptable
- [ ] No activation failures

---

## Next Steps

After Session 3:
1. Mark tasks 3.1-3.13 complete
2. Proceed to Session 4: PHASE_3_DOCS_AND_ROLLOUT.md
3. Document the feature

---

**End of Session 3. Proceed to documentation and rollout.**
