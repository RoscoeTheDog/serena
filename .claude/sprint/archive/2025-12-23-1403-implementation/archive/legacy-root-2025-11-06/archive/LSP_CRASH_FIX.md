# LSP Crash Fix Documentation

**Date:** 2025-11-03
**Issue:** Language Server Protocol (LSP) crash during initialization
**Status:** ✅ FIXED

---

## Problem Summary

After implementing auto-onboarding, LSP-dependent tools (find_symbol, get_symbols_overview, etc.) were crashing with:

```
LanguageServerTerminatedException: Language server stdout read process terminated unexpectedly
```

**Impact:**
- All symbol-based operations failed
- Auto-onboarding worked correctly (memories created, project.yml exists)
- Only LSP-dependent tools were affected

---

## Root Cause Analysis

### Investigation Steps

1. **Enabled Debug Logging**
   - Set `log_level: 10` (DEBUG) in `~/.serena/serena_config.yml`
   - Set `trace_lsp_communication: true`
   - Accessed web dashboard at `http://localhost:24282/dashboard/`

2. **Reproduced Crash**
   - Activated python-fastapi project
   - Called `find_symbol` tool
   - Captured detailed error logs

3. **Found Root Cause in Logs**
   ```
   ERROR [LSP-stderr-reader] C:\python313\python.exe: Error while finding module specification for 'pyright.langserver'
   (ModuleNotFoundError: No module named 'pyright')
   ```

### Root Cause

**Pyright was not installed in the Python environment used by the MCP server.**

**Details:**
- Serena's MCP server runs with global Python: `C:\python313\python.exe`
- Pyright is declared in `pyproject.toml` as a dependency
- But pyright was NOT installed in the global Python environment
- When LSP tries to start: `python -m pyright.langserver --stdio`
- Python can't find the module → Process terminates immediately
- LSP stdout reader detects termination → `LanguageServerTerminatedException`

**Why This Happened:**
- Serena was likely installed with `pip install serena` (editable install)
- Dependencies were installed in a virtual environment (`.venv`)
- But the MCP server runs with global Python, not the venv
- Pyright was not available in the global Python's site-packages

---

## Solution

### Fix Applied

**Install pyright in the global Python environment:**

```bash
pip install "pyright>=1.1.396,<2"
```

**Result:**
```
Successfully installed nodeenv-1.9.1 pyright-1.1.407
```

### Verification

**Test 1: serena project**
```python
find_symbol(name_path="ActivateProjectTool", relative_path="src/serena/tools/config_tools.py", depth=1)
```
✅ **SUCCESS** - Returned class with 8 methods

**Test 2: python-fastapi project**
```python
get_symbols_overview(relative_path="fastapi/__init__.py")
```
✅ **SUCCESS** - Returned symbol overview

**No more LSP crashes!**

---

## Lessons Learned

### 1. Environment Mismatch

**Problem:** MCP server runs with global Python, but dependencies installed in venv

**Solution Options:**
- **Option A (Applied):** Install pyright globally
- **Option B:** Configure MCP to use venv Python
- **Option C:** Bundle pyright with serena installation

**Chosen:** Option A - Quick fix for immediate testing

### 2. Better Error Messages

**Current Error:**
```
LanguageServerTerminatedException: Language server stdout read process terminated unexpectedly
```

**Improved Error (Suggestion):**
```
LanguageServerTerminatedException: Language server stdout read process terminated unexpectedly
Stderr output: ModuleNotFoundError: No module named 'pyright'
Hint: Install pyright with: pip install "pyright>=1.1.396,<2"
```

**Implementation:** Capture stderr output and include in exception message

### 3. Debug Logging is Essential

**What Helped:**
- `trace_lsp_communication: true` showed exact LSP commands
- `log_level: 10` (DEBUG) showed detailed error messages
- Web dashboard (`http://localhost:24282/dashboard/`) provided real-time logs

**Recommendation:** Document debug logging setup in troubleshooting guide

---

## Related Issues

### Connection to Auto-Onboarding Bug

**Initially Suspected:** Auto-onboarding was causing LSP crash by not creating project.yml

**Actual Cause:** Two separate issues:
1. **Project.yml missing** - Fixed in `src/serena/tools/config_tools.py:28-39`
2. **Pyright not installed** - Fixed by installing pyright globally

**Why Confusion?**
- Both issues manifested after auto-onboarding
- Both caused "LanguageServerTerminatedException"
- But root causes were different

---

## Recommendations for Production

### 1. Dependency Management

**Problem:** Pyright dependency not enforced for MCP server

**Solutions:**
- Add installation check at MCP server startup
- Provide clear error message if pyright missing
- Document pyright as required dependency
- Consider bundling pyright with serena

### 2. Better Error Handling

**Current:** Generic "LanguageServerTerminatedException"

**Improved:**
```python
try:
    self.server.start()
except LanguageServerTerminatedException as e:
    stderr_output = self.server.get_stderr_output()
    if "ModuleNotFoundError" in stderr_output:
        module_name = extract_module_name(stderr_output)
        raise LanguageServerDependencyError(
            f"Language server dependency '{module_name}' not found. "
            f"Install with: pip install {module_name}"
        ) from e
    raise
```

### 3. Installation Documentation

**Add to README.md:**

```markdown
## Installation

### For MCP Server Usage

If using Serena as an MCP server, ensure pyright is installed globally:

```bash
pip install serena
pip install "pyright>=1.1.396,<2"  # Required for Python LSP
```

### Troubleshooting LSP Issues

If you see "LanguageServerTerminatedException", check:
1. Pyright installed: `python -m pyright --version`
2. Debug logs: Set `log_level: 10` in `~/.serena/serena_config.yml`
3. Web dashboard: http://localhost:24282/dashboard/
```

### 4. CI/CD Testing

**Add test to verify:**
- Pyright can be imported: `python -m pyright.langserver --version`
- LSP initialization succeeds on fresh environment
- Test with and without venv activation

---

## Timeline

| Time | Event |
|------|-------|
| 20:41 | LSP crash discovered during auto-onboarding testing |
| 21:05 | Enabled debug logging and LSP tracing |
| 21:10 | Reproduced crash, captured debug logs |
| 21:15 | Identified root cause: `ModuleNotFoundError: No module named 'pyright'` |
| 21:20 | Installed pyright globally |
| 21:25 | Verified fix: LSP working on multiple projects |
| 21:30 | Documented fix and recommendations |

---

## Conclusion

**Status:** ✅ LSP crash is fully resolved

**Fix:** Install pyright in global Python environment

**Impact:** All Serena LSP-dependent tools now work correctly

**Follow-up:** Consider implementing recommendations for production deployment
