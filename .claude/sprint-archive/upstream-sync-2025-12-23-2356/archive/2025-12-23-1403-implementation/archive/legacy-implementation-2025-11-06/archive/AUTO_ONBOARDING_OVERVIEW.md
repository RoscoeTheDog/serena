# Server-Side Auto-Onboarding - Overview

**Part of**: AUTO_ONBOARDING_MASTER.md
**Session**: Reference/Overview (read before all sessions)
**Estimated Reading Time**: 5 minutes

---

## Problem Statement

Currently, Serena's project onboarding workflow is **inefficient and token-intensive**:

### Current Manual Workflow
```
User: "activate project X"
  ↓
Server: "Activated. Here's project info."
  ↓
Agent: calls check_onboarding_performed
  ↓
Server: "Not onboarded. Call onboarding tool."
  ↓
Agent: calls onboarding
  ↓
Server: "Here's onboarding instructions..." (600 token prompt)
  ↓
Agent: explores codebase (10-20k tokens)
  - list_dir calls (2,000 tokens)
  - read_file calls (5,000 tokens)
  - search patterns (3,000 tokens)
  ↓
Agent: writes multiple memories (2,000 tokens)
```

**Total Cost**:
- **Tokens**: 13,800 tokens
- **Tool Calls**: 8-12 calls
- **Time**: 30-60 seconds
- **User Experience**: Manual, requires agent exploration

### The Core Inefficiency

The server already has all the information needed to create basic onboarding memories:
- ✅ Project files (package.json, Makefile, etc.)
- ✅ Language detection (from .serena/project.yml)
- ✅ Directory structure
- ✅ Configuration files (.eslintrc, pyproject.toml, etc.)

**The agent doesn't need to explore** - the server can deterministically extract this information.

---

## Proposed Solution: Server-Side Auto-Onboarding

### New Workflow
```
User: "activate project X"
  ↓
Server:
  1. Activates project
  2. Checks if memories exist
  3. If no memories:
     - Analyzes package.json, Makefile, etc. (SERVER-SIDE)
     - Creates basic memories (SERVER-SIDE)
  4. Returns "Activated + Auto-onboarded (3 memories created)"
```

**New Cost**:
- **Tokens**: 500 tokens (just the activation response)
- **Tool Calls**: 1 call
- **Time**: <1 second
- **User Experience**: Automatic, zero overhead

### Token Savings
- **Per activation**: 13,300 tokens saved (96% reduction)
- **Per 10 projects**: 133,000 tokens saved
- **Per 100 projects**: 1,330,000 tokens saved

---

## Architecture Comparison

### Current Architecture
```
┌─────────────────────────────────────────┐
│  Agent (Client-Side)                    │
│  ┌──────────────────────────────────┐   │
│  │ 1. activate_project              │   │
│  │ 2. check_onboarding_performed    │   │
│  │ 3. onboarding (get prompt)       │   │
│  │ 4. list_dir, read_file (explore) │   │ <- 10-20k tokens
│  │ 5. write_memory x4               │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
           ↑↓ (8-12 tool calls)
┌─────────────────────────────────────────┐
│  Server (MCP)                           │
│  ┌──────────────────────────────────┐   │
│  │ ActivateProjectTool              │   │
│  │ CheckOnboardingPerformedTool     │   │
│  │ OnboardingTool (returns prompt)  │   │
│  │ WriteMemoryTool                  │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Proposed Architecture
```
┌─────────────────────────────────────────┐
│  Agent (Client-Side)                    │
│  ┌──────────────────────────────────┐   │
│  │ 1. activate_project              │   │ <- 500 tokens
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
           ↑↓ (1 tool call)
┌─────────────────────────────────────────┐
│  Server (MCP)                           │
│  ┌──────────────────────────────────┐   │
│  │ ActivateProjectTool              │   │
│  │   ├─> _check_and_auto_onboard()  │   │
│  │   ├─> _auto_onboard_project()    │   │ <- NEW
│  │   └─> onboarding_helpers.py      │   │ <- NEW
│  │       ├─> detect_tech_stack()    │   │
│  │       ├─> find_command_files()   │   │
│  │       ├─> detect_code_style()    │   │
│  │       └─> generate_memories()    │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

**Key Difference**: Everything happens server-side, no agent exploration needed.

---

## Benefits Analysis

### 1. Token Efficiency
| Metric | Current | Proposed | Savings |
|--------|---------|----------|---------|
| Per activation | 13,800t | 500t | 13,300t (96%) |
| Per 10 projects | 138,000t | 5,000t | 133,000t |
| Tool calls | 8-12 | 1 | 7-11 fewer |

### 2. Performance
| Metric | Current | Proposed | Improvement |
|--------|---------|----------|-------------|
| Onboarding time | 30-60s | <1s | 30-60x faster |
| Activation overhead | N/A | <300ms | Negligible |
| Network requests | 8-12 | 1 | 88-92% fewer |

### 3. User Experience
- **Automatic**: No manual onboarding step needed
- **Consistent**: Deterministic results every time
- **Instant**: Project ready to use immediately
- **Zero overhead**: No token cost for onboarding

### 4. Code Quality
- **Maintainable**: Centralized detection logic
- **Testable**: Pure functions, easy to unit test
- **Extensible**: Easy to add new detection patterns
- **Reliable**: No LLM variability

---

## What Gets Auto-Detected

### Tech Stack Detection
- **Package Managers**: npm, poetry, cargo, bundler, maven, gradle
- **Languages**: Detected from dependencies (TypeScript, etc.)
- **Frameworks**: React, Next.js, Vue, Angular, Django, Flask, Rails
- **Build Tools**: Make, Docker, Docker Compose
- **CI/CD**: GitHub Actions workflows

### Commands Detection
- **npm scripts**: From package.json
- **Makefile targets**: Parsed from Makefile
- **Poetry scripts**: From pyproject.toml
- **Standard commands**: cargo build/test, go build, etc.
- **GitHub Actions**: Workflow files detected

### Code Style Detection
- **JavaScript/TypeScript**: ESLint, Prettier
- **Python**: Black, Ruff, mypy
- **Universal**: EditorConfig
- **Framework-specific**: Configuration files

### Generated Memories
1. **project_overview.md**: Language, tech stack, platform
2. **suggested_commands.md**: All detected commands organized by source
3. **code_style_and_conventions.md**: Detected linters/formatters (if any)
4. **task_completion_checklist.md**: Test/lint commands from detected config

---

## Success Criteria

### Must Have (MVP)
- ✅ Auto-onboarding completes in <1 second
- ✅ 3-4 memories created automatically
- ✅ Zero token overhead (no LLM calls)
- ✅ Works for 90%+ of common project types (Node.js, Python, Rust, etc.)
- ✅ Backward compatible (existing projects unaffected)
- ✅ No activation failures due to onboarding

### Should Have
- ✅ Graceful degradation (partial detection acceptable)
- ✅ Error handling for malformed files
- ✅ Performance <300ms overhead
- ✅ Unit tests for all detection functions
- ✅ Integration tests for full workflow

### Nice to Have
- ⭕ Configuration option to disable auto-onboarding
- ⭕ Deep onboarding mode (optional LLM-enhanced)
- ⭕ README parsing for additional context
- ⭕ Framework-specific templates

---

## Implementation Phases

### Phase 1: Core Implementation (2 sessions)
**Goal**: Get basic auto-onboarding working
- Session 1: Modify ActivateProjectTool
- Session 2: Create onboarding_helpers.py with detection functions

**Deliverable**: Auto-onboarding works for Node.js and Python projects

### Phase 2: Testing & Validation (1 session)
**Goal**: Ensure reliability and correctness
- Unit tests for all helper functions
- Integration tests for activation workflow
- Manual testing on diverse project types
- Bug fixes

**Deliverable**: All tests pass, edge cases handled

### Phase 3: Documentation & Rollout (1 session)
**Goal**: Document and ship the feature
- Update README, CHANGELOG
- MCP server description updates
- Migration guide for existing projects
- Deprecation notices for old tools (optional)

**Deliverable**: Feature documented and ready to merge

---

## Risk Assessment

### Low Risk
- **Performance regression**: Detection is simple file I/O (<300ms)
- **Breaking changes**: Backward compatible by design
- **Security**: No external execution, just file reading

### Medium Risk
- **Incorrect detection**: Mitigated by conservative detection logic
- **Malformed files**: Mitigated by *_safe() parsing functions
- **Missing dependencies**: Mitigated by fallback to older TOML parser

### Mitigation Strategies
- **Conservative detection**: Only detect high-confidence items
- **Graceful degradation**: Partial detection is acceptable
- **Error handling**: Never fail activation due to onboarding error
- **Testing**: Comprehensive test suite on diverse projects
- **Opt-out option**: Allow disabling via config (future)

---

## Comparison to Alternatives

### Alternative A: LLM-Based Auto-Onboarding
**Pros**: More intelligent, can understand context
**Cons**: Token overhead (defeats purpose), slower, non-deterministic
**Decision**: ❌ Rejected

### Alternative B: User Prompt Before Onboarding
**Pros**: Explicit user control
**Cons**: Extra friction, worse UX
**Decision**: ❌ Rejected

### Alternative C: Lazy Onboarding (On-Demand)
**Pros**: Only onboard when needed
**Cons**: Unpredictable, still requires tool calls
**Decision**: ❌ Rejected

### Alternative D: Server-Side Auto-Onboarding
**Pros**: Zero overhead, instant, deterministic
**Cons**: Requires server-side implementation
**Decision**: ✅ **Selected** - Best balance of efficiency and UX

---

## Next Steps

1. **Read this overview** to understand the problem and solution
2. **Review PHASE_1_CORE_IMPLEMENTATION.md** for Session 1 implementation details
3. **Begin implementation** following the master task list in AUTO_ONBOARDING_MASTER.md
4. **Test incrementally** after each phase
5. **Document changes** as you implement

---

**Ready to proceed to Phase 1 implementation. See PHASE_1_CORE_IMPLEMENTATION.md**
