# Bug Report: Missing project.yml Causes LSP Server Crash

**Date Discovered**: 2025-11-03
**Severity**: High
**Status**: Fixed
**Affects**: Auto-onboarding feature (Sessions 1-2)

---

## Summary

When a registered project's `.serena/` directory is deleted and the project is reactivated, the auto-onboarding process creates `.serena/memories/` but fails to create `.serena/project.yml`. This causes the LSP server to crash, breaking all symbol-based Serena tools.

---

## Reproduction Steps

### Prerequisites
- Serena MCP server running
- A project already registered in the MCP server configuration
- Auto-onboarding code loaded (Sessions 1-2 implemented)

### Steps to Reproduce
1. Activate a project (e.g., `activate_project("C:\path\to\project")`)
2. Verify project is registered and working
3. **Delete** the `.serena/` directory: `rm -rf .serena`
4. **Reactivate** the same project: `activate_project("C:\path\to\project")`
5. Attempt to use any symbol-based tool (e.g., `read_memory`, `find_symbol`)

### Expected Behavior
- Project activates successfully
- Auto-onboarding creates both memories AND `project.yml`
- LSP server initializes correctly
- Symbol tools work normally

### Actual Behavior
- Auto-onboarding creates `.serena/memories/` with memory files
- **No `project.yml` is created**
- LSP server fails to initialize with error:
  ```
  Error processing request initialize with params...
  (caused by LanguageServerTerminatedException: Language server stdout read process terminated unexpectedly)
  ```
- All symbol-based tools fail with the same LSP error
- Only non-LSP tools work (bash, read_file, write_file, etc.)

---

## Root Cause Analysis

### The Problem Chain

1. **Project Registration State**
   - When a project is first activated, it gets registered in MCP server's config
   - Registration includes: project name, path, language, etc.
   - Registration persists across MCP restarts

2. **Activation Flow for Registered Projects**
   ```
   activate_project(path)
   └─> activate_project_from_path_or_name(path)
       └─> load_project_from_path_or_name(path, autogenerate=True)
           ├─> Check if registered by name: YES → return existing
           └─> SKIPS: add_project_from_path()
               └─> SKIPS: ProjectConfig.load(autogenerate=True)
                   └─> WOULD HAVE CALLED: ProjectConfig.autogenerate(save_to_disk=True)
                       └─> WOULD HAVE CREATED: .serena/project.yml
   ```

3. **Auto-onboarding Creates Partial Structure**
   ```
   _auto_onboard_project()
   └─> write_memory.apply(name, content)
       └─> MemoriesManager.__init__(project_root)
           └─> self._memory_dir.mkdir(parents=True, exist_ok=True)
               └─> CREATES: .serena/memories/
   ```
   - Creates `.serena/memories/` directory
   - Writes memory files successfully
   - But never triggers `project.yml` creation

4. **LSP Server Expects Complete Structure**
   - LSP initialization checks for `.serena/project.yml`
   - File is missing → server crashes
   - All subsequent LSP requests fail

### Why This Happens

The issue occurs because of an **assumption mismatch**:

- **Assumption**: Registered projects always have complete `.serena/` structure
- **Reality**: `.serena/` directory can be deleted while registration persists
- **Consequence**: Activation skips project file creation for registered projects

---

## Impact Assessment

### Severity: High
- Breaks all symbol-based tools (find_symbol, read_memory, etc.)
- Requires MCP server restart to recover
- No clear error message to user
- Data is not lost (memories are created, just LSP fails)

### Likelihood: Medium
- Requires specific sequence: register → delete .serena → reactivate
- Common scenarios:
  - Developer cleaning up directories
  - Git operations (switching branches, clean checkout)
  - Manual directory cleanup
  - Testing/development workflow

### Affected Use Cases
1. **Development/Testing**: Repeatedly deleting `.serena/` to test auto-onboarding
2. **Branch Switching**: `.gitignore` excludes `.serena/`, but switching branches might remove it
3. **Directory Cleanup**: Users manually cleaning project directories
4. **CI/CD**: Automated cleanup scripts

---

## The Fix

### Implementation Location
**File**: `src/serena/tools/config_tools.py`
**Method**: `ActivateProjectTool.apply()`
**Lines**: 28-39

### Code Changes

```python
def apply(self, project: str) -> str:
    """
    Activates the project with the given name.

    :param project: the name of a registered project to activate or a path to a project directory
    """
    active_project = self.agent.activate_project_from_path_or_name(project)

    # Ensure project.yml exists (in case project was registered but .serena was deleted)
    from pathlib import Path
    project_yml_path = Path(active_project.path_to_project_yml())
    if not project_yml_path.exists():
        # Regenerate project.yml from existing project config
        from serena.config.serena_config import ProjectConfig
        ProjectConfig.autogenerate(
            active_project.project_root,
            project_name=active_project.project_name,
            project_language=active_project.language,
            save_to_disk=True
        )

    # ... rest of method
```

### Fix Strategy
**Defensive Programming**: Always verify `project.yml` exists after activation

- **When**: Immediately after `activate_project_from_path_or_name()`
- **Check**: Does `project.yml` exist at expected path?
- **Action**: If missing, regenerate from existing `project_config`
- **Impact**: Prevents LSP crash regardless of how project was activated

### Why This Works
1. Uses existing `project_config` from registered project
2. Calls `autogenerate()` with exact same parameters
3. Only creates missing file, doesn't modify existing config
4. Handles both new and registered projects uniformly
5. Zero performance impact (only runs when file is missing)

---

## Testing Strategy

### Unit Test (Not Feasible)
Testing this bug in unit tests is challenging because:
- Requires MCP server state (registered projects)
- Requires LSP server lifecycle
- Integration-level issue, not unit-level

### Integration Test Approach

**File**: `test/serena/tools/test_auto_onboarding_integration.py`

Add new test case:
```python
def test_reactivate_registered_project_after_serena_deletion(tmp_path):
    """
    Test that project.yml is created when reactivating a registered project
    whose .serena directory was deleted.

    Regression test for Bug: Missing project.yml Causes LSP Server Crash
    """
    # Setup: Create project structure
    project_root = tmp_path / "test_project"
    project_root.mkdir()
    (project_root / "main.py").write_text("print('hello')")

    # Step 1: Activate project (first time - creates registration)
    agent = MockAgent()
    activate_tool = ActivateProjectTool(agent)
    result1 = activate_tool.apply(str(project_root))

    # Verify .serena created with project.yml
    serena_dir = project_root / ".serena"
    project_yml = serena_dir / "project.yml"
    assert project_yml.exists(), "project.yml should exist after first activation"

    # Step 2: Simulate .serena deletion (but keep registration)
    shutil.rmtree(serena_dir)
    assert not serena_dir.exists(), ".serena should be deleted"

    # Step 3: Reactivate project (registration exists, .serena deleted)
    result2 = activate_tool.apply(str(project_root))

    # Verify: project.yml is recreated
    assert serena_dir.exists(), ".serena should be recreated"
    assert project_yml.exists(), "project.yml should be recreated automatically"

    # Verify: project.yml has correct content
    import yaml
    with open(project_yml) as f:
        config = yaml.safe_load(f)
    assert config["project_name"] == "test_project"
    assert config["language"] == "python"

    # Verify: LSP server can initialize (would fail before fix)
    # This is implicit - if project.yml exists, LSP won't crash
```

### Manual Testing Checklist

#### Test Case 1: Fresh Project (Baseline)
- [ ] Delete `.serena/` from a fresh project
- [ ] Activate project
- [ ] Verify `.serena/project.yml` is created
- [ ] Verify LSP tools work (`find_symbol`, `read_memory`)
- [ ] **Expected**: All works correctly

#### Test Case 2: Registered Project with Deleted .serena (Bug Scenario)
- [ ] Activate a project to register it
- [ ] Verify `.serena/project.yml` exists
- [ ] **Delete** `.serena/` directory
- [ ] Restart MCP server (to load fix)
- [ ] Reactivate the same project
- [ ] **Verify**: `.serena/project.yml` is recreated automatically
- [ ] **Verify**: LSP tools work without errors
- [ ] **Expected**: No LSP crash, all tools functional

#### Test Case 3: Registered Project with Existing .serena (No Regression)
- [ ] Activate a project (with existing `.serena/project.yml`)
- [ ] Reactivate the same project
- [ ] Verify `.serena/project.yml` unchanged
- [ ] Verify LSP tools work
- [ ] **Expected**: No changes, no side effects

#### Test Case 4: Registered Project with Partial .serena (Edge Case)
- [ ] Activate a project
- [ ] Delete only `project.yml` (keep `.serena/memories/`)
- [ ] Reactivate project
- [ ] **Verify**: `project.yml` is recreated
- [ ] **Verify**: Existing memories unchanged
- [ ] **Expected**: Only missing file recreated

### Performance Testing
- [ ] Measure activation time with fix: Should add <10ms (only when file missing)
- [ ] Measure activation time without missing file: Should be identical to before fix
- [ ] **Expected**: No noticeable performance impact

---

## Verification Steps

### After Implementing Fix

1. **Code Review**
   - [x] Fix implemented in `config_tools.py:28-39`
   - [x] Uses `ProjectConfig.autogenerate()` correctly
   - [x] Checks `project_yml_path.exists()` before recreating
   - [x] Placed before auto-onboarding check (correct order)

2. **Static Analysis**
   - [ ] No new linting errors
   - [ ] Type hints correct (`Path`, `ProjectConfig`)
   - [ ] Imports at correct scope (function-level imports OK here)

3. **Manual Testing** (Requires MCP Restart)
   - [x] Created `.serena/project.yml` manually (workaround for current session)
   - [ ] Restart MCP server to load fix
   - [ ] Run Test Case 2 (main bug scenario)
   - [ ] Run Test Case 4 (edge case)
   - [ ] Verify no LSP crashes

4. **Integration Testing**
   - [ ] Add regression test to `test_auto_onboarding_integration.py`
   - [ ] Run full test suite: `pytest test/serena/tools/test_auto_onboarding_integration.py -v`
   - [ ] All tests pass

---

## Lessons Learned

### Design Insights

1. **Defensive Programming**: Always verify critical files exist, even if "they should"
2. **State Synchronization**: Registration state and filesystem state can diverge
3. **Error Messages**: LSP crashes give cryptic errors; better to prevent than debug
4. **Testing Edge Cases**: Test scenarios where state is inconsistent

### Architectural Considerations

1. **project.yml as Critical Dependency**
   - LSP server requires it
   - Should be treated as mandatory for activated projects
   - Consider: Health check at activation?

2. **Registration vs. Filesystem**
   - Registration is in-memory/config file
   - Filesystem is volatile (can be deleted)
   - Need to handle desync gracefully

3. **Auto-onboarding Responsibilities**
   - Should auto-onboarding ensure ALL project files exist?
   - Currently only creates memories
   - Fix delegates `project.yml` to activation layer (correct choice)

### Future Improvements

1. **Health Check Tool**
   - Add tool to verify project structure integrity
   - Report missing/corrupt files
   - Offer to repair

2. **Better Error Messages**
   - Catch LSP init failures
   - Provide actionable error: "Missing project.yml, run health check"

3. **Atomic Project Creation**
   - Ensure all required files created together
   - Use transaction-like pattern
   - Rollback on partial failure

4. **Documentation**
   - Document `.serena/` structure requirements
   - Explain relationship between registration and filesystem
   - Warn about manual directory manipulation

---

## Related Issues

### Potential Similar Bugs

1. **Missing cache directory**: Does LSP need `.serena/cache/`?
2. **Corrupted project.yml**: What if file exists but is malformed?
3. **Permission issues**: What if `.serena/` is read-only?
4. **Network drives**: Does this work on network/shared drives?

### Follow-up Tasks

- [ ] Audit all places where `.serena/` structure is assumed
- [ ] Add comprehensive structure validation
- [ ] Consider making `project.yml` creation atomic with registration
- [ ] Document `.serena/` directory structure in README

---

## References

### Code Locations

- **Bug Fix**: `src/serena/tools/config_tools.py:28-39`
- **Activation Flow**: `src/serena/agent.py:585-607` (`activate_project_from_path_or_name`)
- **Project Loading**: `src/serena/agent.py:541-583` (`load_project_from_path_or_name`)
- **Config Generation**: `src/serena/config/serena_config.py:177-217` (`ProjectConfig.autogenerate`)
- **Memory Manager**: `src/serena/agent.py:63-86` (`MemoriesManager`)

### Related Documents

- **Implementation Plan**: `implementation/AUTO_ONBOARDING_MASTER.md`
- **Manual Testing Guide**: `implementation/MANUAL_TESTING_GUIDE.md`
- **Integration Tests**: `test/serena/tools/test_auto_onboarding_integration.py`

---

## Changelog

**2025-11-03**
- Bug discovered during live testing of auto-onboarding feature
- Root cause identified: Registered projects skip `project.yml` creation
- Fix implemented: Defensive check in `ActivateProjectTool.apply()`
- Documented in this report
- Awaiting MCP restart for verification

---

**End of Bug Report**
