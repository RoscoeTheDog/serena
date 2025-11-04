# Server-Side Auto-Onboarding - Master Implementation Plan

**Status**: Ready to implement
**Estimated Total Effort**: 3-4 sessions (8-12 hours)
**Token Efficiency Gain**: 10,000-20,000 tokens saved per project activation
**Date Created**: 2025-11-03

---

## 📋 Master Task List

### Phase 1: Core Implementation (Sessions 1-2)

#### Session 1: ActivateProjectTool Modifications
- [x] 1.1 Read and understand current `ActivateProjectTool.apply()` implementation
- [x] 1.2 Add `_check_and_auto_onboard()` method to ActivateProjectTool
- [x] 1.3 Add `_auto_onboard_project()` method to ActivateProjectTool
- [x] 1.4 Add helper method wrappers (_detect_tech_stack, etc.)
- [x] 1.5 Update `apply()` to call auto-onboarding after activation
- [x] 1.6 Update result string to include onboarding status
- [x] 1.7 Verify ActivateProjectTool compiles and imports work
- [x] 1.8 Basic smoke test: activate a test project

**Document**: `PHASE_1_CORE_IMPLEMENTATION.md`
**Estimated**: 37k tokens

#### Session 2: Helper Functions Implementation
- [x] 2.1 Create `src/serena/tools/onboarding_helpers.py`
- [x] 2.2 Implement `detect_tech_stack()` function
- [x] 2.3 Implement `find_command_files()` function
- [x] 2.4 Implement `detect_code_style()` function
- [x] 2.5 Implement `generate_commands_memory()` function
- [x] 2.6 Implement `generate_completion_checklist()` function
- [x] 2.7 Implement helper utilities (read_json_safe, read_toml_safe, parse_makefile_targets)
- [x] 2.8 Add imports to `config_tools.py`
- [x] 2.9 Write unit tests for each helper function
- [x] 2.10 Verify all helpers work with mock projects

**Document**: `PHASE_1_HELPER_FUNCTIONS.md`
**Estimated**: 52k tokens

### Phase 2: Testing & Validation (Session 3)

- [ ] 3.1 Create integration test for auto-onboarding new project
- [ ] 3.2 Create integration test for skipping onboarded project
- [ ] 3.3 Manual test: Node.js project with package.json scripts
- [ ] 3.4 Manual test: Python project with pyproject.toml
- [ ] 3.5 Manual test: Rust project with Cargo.toml
- [ ] 3.6 Manual test: Multi-language project (detect dominant)
- [ ] 3.7 Manual test: Project with Makefile
- [ ] 3.8 Manual test: Project with code style configs (.eslintrc, .prettierrc)
- [ ] 3.9 Test error handling: malformed JSON/TOML files
- [ ] 3.10 Test error handling: missing files/permissions
- [ ] 3.11 Verify memory content quality for each test case
- [ ] 3.12 Fix any bugs discovered during testing
- [ ] 3.13 Performance test: measure activation overhead (<300ms)

**Document**: `PHASE_2_TESTING.md`
**Estimated**: 56k tokens

### Phase 3: Documentation & Rollout (Session 4)

- [ ] 4.1 Update README.md with auto-onboarding section
- [ ] 4.2 Update CHANGELOG.md with new feature entry
- [ ] 4.3 Update MCP server description/instructions
- [ ] 4.4 Create migration guide for existing projects
- [ ] 4.5 Update CLAUDE_INIT.md if needed
- [ ] 4.6 Add docstrings to all new functions
- [ ] 4.7 Create examples directory with sample auto-onboarded projects
- [ ] 4.8 Final review of all changes
- [ ] 4.9 Create comprehensive commit message
- [ ] 4.10 Optional: Update manual onboarding tools with deprecation notices

**Document**: `PHASE_3_DOCS_AND_ROLLOUT.md`
**Estimated**: 21k tokens

---

## 📚 Document Index

### Overview & Architecture
**File**: `AUTO_ONBOARDING_OVERVIEW.md`
**Purpose**: High-level problem statement, benefits analysis, and architecture overview
**Use When**: Starting implementation or explaining the feature to others
**Key Sections**:
- Problem Statement
- Current vs. Proposed Flow
- Benefits Analysis (token savings, performance)
- Architecture Diagram
- Success Criteria

### Phase 1 - Core Implementation
**File**: `PHASE_1_CORE_IMPLEMENTATION.md`
**Purpose**: Step-by-step guide for modifying ActivateProjectTool
**Use When**: Session 1 - Implementing auto-onboarding in config_tools.py
**Key Sections**:
- Current ActivateProjectTool.apply() analysis
- Code modifications needed
- _check_and_auto_onboard() implementation
- _auto_onboard_project() implementation
- Integration points
- Acceptance criteria for Session 1

### Phase 1 - Helper Functions
**File**: `PHASE_1_HELPER_FUNCTIONS.md`
**Purpose**: Complete implementation of onboarding_helpers.py
**Use When**: Session 2 - Creating helper functions module
**Key Sections**:
- Complete onboarding_helpers.py source code
- Function-by-function documentation
- Tech stack detection matrix
- Command file parsing logic
- Code style detection patterns
- Unit test examples

### Phase 2 - Testing
**File**: `PHASE_2_TESTING.md`
**Purpose**: Comprehensive testing strategy and test cases
**Use When**: Session 3 - Testing and validating implementation
**Key Sections**:
- Unit test suite structure
- Integration test examples
- Manual testing checklist (per project type)
- Edge case scenarios
- Error handling verification
- Performance benchmarks

### Phase 3 - Documentation & Rollout
**File**: `PHASE_3_DOCS_AND_ROLLOUT.md`
**Purpose**: Documentation updates and release preparation
**Use When**: Session 4 - Finalizing and documenting the feature
**Key Sections**:
- README.md updates
- CHANGELOG entry template
- MCP server description updates
- Migration guide for existing projects
- Deprecation notices for old tools
- Example commit message

---

## 🎯 Quick Start Guide

### For Implementation (Agent)

1. **Session 1**:
   - Read: `AUTO_ONBOARDING_OVERVIEW.md` + `PHASE_1_CORE_IMPLEMENTATION.md`
   - Execute: Tasks 1.1 - 1.8
   - Verify: ActivateProjectTool compiles, basic activation works

2. **Session 2**:
   - Read: `PHASE_1_HELPER_FUNCTIONS.md`
   - Execute: Tasks 2.1 - 2.10
   - Verify: All helper functions have unit tests passing

3. **Session 3**:
   - Read: `PHASE_2_TESTING.md`
   - Execute: Tasks 3.1 - 3.13
   - Verify: All tests pass, performance acceptable

4. **Session 4**:
   - Read: `PHASE_3_DOCS_AND_ROLLOUT.md`
   - Execute: Tasks 4.1 - 4.10
   - Verify: Documentation complete, ready to commit

### For Review (Human)

- **Overview First**: Read `AUTO_ONBOARDING_OVERVIEW.md` for context
- **Check Progress**: Review completed tasks in this master list
- **Dive Deep**: Reference specific phase documents for implementation details
- **Validate**: Use testing checklist from `PHASE_2_TESTING.md`

---

## 📊 Progress Tracking

### Session 1 Status
- [x] Started
- [x] Core implementation complete
- [x] Smoke tested (code verified, MCP restart required for live test)
- [x] Ready for Session 2

### Session 2 Status
- [x] Started
- [x] Helper functions complete
- [x] Unit tests written (require MCP restart to execute)
- [x] Ready for Session 3

### Session 3 Status
- [ ] Started
- [ ] Integration tests complete
- [ ] Manual testing complete
- [ ] Bugs fixed
- [ ] Performance validated
- [ ] Ready for Session 4

### Session 4 Status
- [ ] Started
- [ ] Documentation complete
- [ ] Ready to commit
- [ ] Implementation complete

---

## 🚨 Blockers & Dependencies

### Prerequisites
- [ ] Python 3.11+ (for tomllib) or tomli package installed
- [ ] Serena project successfully activated
- [ ] MCP server running
- [ ] Git repository clean (no uncommitted changes)

### Known Dependencies
- `onboarding_helpers.py` depends on `Project` class from `serena.project`
- `ActivateProjectTool` depends on `WriteMemoryTool` for memory creation
- TOML parsing requires `tomllib` (Python 3.11+) or `tomli` package

### Potential Blockers
- **Issue**: TOML parsing fails on Python <3.11
  - **Solution**: Add fallback to `tomli` package

- **Issue**: Large Makefile causes timeout
  - **Solution**: Limit Makefile parsing to first 500 lines

- **Issue**: Malformed package.json crashes detection
  - **Solution**: Use read_json_safe() with try/except

---

## 📈 Success Metrics

### Token Efficiency
- **Target**: Save 13,300 tokens per activation (96% reduction)
- **Measurement**: Compare manual vs. auto-onboarding token usage
- **Acceptance**: Achieve >10,000 token savings

### Performance
- **Target**: Auto-onboarding completes in <300ms
- **Measurement**: Time activation with/without auto-onboarding
- **Acceptance**: <500ms overhead (still 60x faster than manual)

### Coverage
- **Target**: 90%+ of common project types detected
- **Measurement**: Test against 20+ sample projects
- **Acceptance**: >18/20 projects successfully onboarded

### Quality
- **Target**: Zero false positives (incorrect tech stack)
- **Measurement**: Manual verification of detected information
- **Acceptance**: All detected info is accurate

---

## 🔄 Iteration Strategy

### After Session 1
- Smoke test activation on a simple project
- Verify no regression in existing functionality
- Confirm onboarding check works

### After Session 2
- Unit test all helper functions individually
- Test detection on mock projects
- Verify memory creation works

### After Session 3
- Full integration testing
- Manual testing on diverse projects
- Performance profiling
- Bug fix iteration

### After Session 4
- Final documentation review
- Create comprehensive commit
- Optional: Push to remote and create PR

---

## 💡 Tips for Implementation

### Session Management
- **Start fresh**: Begin each session by reading the master task list
- **Update progress**: Mark tasks complete as you go
- **Note blockers**: Document any issues encountered
- **Leave notes**: If interrupted, leave notes for next session

### Code Quality
- **Follow patterns**: Match existing Serena code style
- **Test early**: Write unit tests as you implement functions
- **Handle errors**: Use try/except with graceful fallbacks
- **Document**: Add docstrings to all new functions

### Testing
- **Test incrementally**: Don't wait until end to test
- **Use diverse projects**: Test on multiple languages/frameworks
- **Edge cases matter**: Test malformed files, missing files, etc.
- **Performance**: Profile if any operation takes >100ms

---

## 📝 Notes & Observations

### Design Decisions
- **Conservative detection**: Only detect high-confidence items
- **Fail gracefully**: Never block activation due to onboarding failure
- **Backward compatible**: Existing projects with memories unaffected
- **Opt-out option**: Can disable auto-onboarding via config (future)

### Alternative Approaches Rejected
- **LLM-based detection**: Too slow, token overhead defeats purpose
- **User prompting**: Extra friction, worse UX
- **Lazy onboarding**: Unpredictable, still requires tool calls

---

## 🎓 Learning Resources

### Relevant Serena Code
- `src/serena/tools/config_tools.py` - ActivateProjectTool
- `src/serena/tools/workflow_tools.py` - CheckOnboardingPerformedTool, OnboardingTool
- `src/serena/tools/memory_tools.py` - WriteMemoryTool, ListMemoriesTool
- `src/serena/project.py` - Project class, file operations

### Python Packages
- `tomllib` - Built-in TOML parser (Python 3.11+)
- `tomli` - Backport TOML parser (Python <3.11)
- `json` - Built-in JSON parser
- `pathlib` - Path operations

---

**Ready to begin implementation. Start with Session 1 using PHASE_1_CORE_IMPLEMENTATION.md**
