# Merge Strategy: Config Module Upstream Sync

**Story**: 3 - Merge Upstream Config Module Changes
**Phase**: Implementation (3.i)
**Generated**: 2025-12-23
**Status**: EXECUTED
**Executed**: 2025-12-23 by Story 3.i.1 (Remediation)

---

## Executive Summary

This document consolidates the findings from diff analysis and presents a concrete, line-by-line merge strategy for integrating upstream changes into `context_mode.py` and `serena_config.py` while preserving our fork's critical architectural enhancements.

**Files Affected**: 2
**Merge Complexity**: HIGH (serena_config.py), MEDIUM (context_mode.py)
**Estimated Time**: 2-3 hours (with testing)

---

## File 1: context_mode.py

### Merge Strategy: SELECTIVE MERGE

**Complexity**: MEDIUM
**Risk Level**: LOW (well-defined fork enhancements)
**Confidence**: HIGH

### Changes to Apply

#### 1. Accept Upstream Import Additions

**Location**: Lines 6-24 (import section)
**Action**: ADD two upstream imports

**Current Fork**:
```python
from serena.config.serena_config import ToolInclusionDefinition
from serena.constants import (
    DEFAULT_CONTEXT,
    DEFAULT_MODES,
    INTERNAL_MODE_YAMLS_DIR,
    SERENAS_OWN_CONTEXT_YAMLS_DIR,
    SERENAS_OWN_MODE_YAMLS_DIR,
    USER_CONTEXT_YAMLS_DIR,
    USER_MODE_YAMLS_DIR,
)
```

**Proposed Merge**:
```python
from serena.config.serena_config import SerenaPaths, ToolInclusionDefinition  # ADD SerenaPaths
from serena.constants import (
    DEFAULT_CONTEXT,
    DEFAULT_MODES,
    INTERNAL_MODE_YAMLS_DIR,
    SERENA_FILE_ENCODING,  # ADD this constant
    SERENAS_OWN_CONTEXT_YAMLS_DIR,
    SERENAS_OWN_MODE_YAMLS_DIR,
    USER_CONTEXT_YAMLS_DIR,  # KEEP fork's addition
    USER_MODE_YAMLS_DIR,     # KEEP fork's addition
)
```

**Rationale**: Upstream's additions are safe and improve code consistency. Our USER_* imports are independent and compatible.

---

#### 2. Preserve Fork Enhancement: single_project Removal

**Location**: Line 149 (SerenaAgentContext.from_yaml)
**Action**: KEEP fork version unchanged

**Fork Code (PRESERVE)**:
```python
@classmethod
def from_yaml(cls, yaml_path: str | Path) -> Self:
    """Load a context from a YAML file."""
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    name = data.pop("name", Path(yaml_path).stem)
    if "tool_description_overrides" not in data:
        data["tool_description_overrides"] = {}
    data.pop("single_project", None)  # ← CRITICAL: Keep this line
    return cls(name=name, **data)
```

**Rationale**: This line provides backward compatibility with old YAML configs. Removing it would break loading of legacy context files.

---

#### 3. Preserve Fork Enhancement: Deprecation Mapping

**Location**: Lines 172-177 (SerenaAgentContext.from_name)
**Action**: KEEP fork version unchanged

**Fork Code (PRESERVE)**:
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

**Rationale**: This is a critical backward compatibility feature added in Story 2. Upstream doesn't have this because they didn't do the rename. We MUST preserve this.

---

### Summary: context_mode.py Changes

| Line Range | Change Type | Action |
|------------|-------------|--------|
| 13 | Import addition | Add `SerenaPaths` to import from serena_config |
| 18 | Import addition | Add `SERENA_FILE_ENCODING` to constants import |
| 22-23 | Import preservation | KEEP `USER_CONTEXT_YAMLS_DIR`, `USER_MODE_YAMLS_DIR` |
| 149 | Fork enhancement | PRESERVE `data.pop("single_project", None)` |
| 172-177 | Fork enhancement | PRESERVE deprecation mapping block |

**Total Changes**: 2 additions, 2 preservations
**Risk**: LOW

---

## File 2: serena_config.py

### Merge Strategy: FORK-FIRST with SELECTIVE CHERRY-PICK

**Complexity**: HIGH
**Risk Level**: MEDIUM (architectural divergence)
**Confidence**: MEDIUM (requires careful testing)

### Critical Decision: Storage Architecture

**Fork Architecture**: Centralized storage (`~/.serena/projects/{id}/project.yml`)
**Upstream Architecture**: In-project storage (`{project}/.serena/project.yml`)

**DECISION**: **PRESERVE FORK'S CENTRALIZED STORAGE**

**Rationale**:
1. Centralized storage is a deliberate architectural choice made in Story 1
2. Works with read-only projects
3. Cleaner separation of config from project code
4. Already implemented and working in production
5. Changing would be a breaking change for all existing fork users

---

### Changes to Apply

#### Phase 1: Safe Import Additions

**Location**: Lines 5-28 (imports)
**Action**: ADD upstream imports that don't conflict

**Add These Imports**:
```python
import dataclasses  # Upstream utility
from enum import Enum  # For LanguageBackend if we add it
from serena.util.general import get_dataclass_default  # Upstream helper
from serena.util.cli_util import ask_yes_no  # For interactive mode
```

**Keep Fork's Imports**:
```python
from serena.constants import (
    DEFAULT_ENCODING,  # Will rename to DEFAULT_SOURCE_FILE_ENCODING
    # ... keep all other fork imports
    SERENA_MANAGED_DIR_IN_HOME,  # CRITICAL: Fork needs this
)
```

---

#### Phase 2: Enhance SerenaPaths Class

**Location**: Lines 44-66
**Action**: Hybrid merge - keep fork's base, add upstream's enhancements

**Proposed Implementation**:
```python
@singleton
class SerenaPaths:
    """
    Provides paths to various Serena-related directories and files.
    """

    def __init__(self) -> None:
        # UPSTREAM ENHANCEMENT: Support SERENA_HOME env var
        home_dir = os.getenv("SERENA_HOME")
        if home_dir is None or home_dir.strip() == "":
            home_dir = SERENA_MANAGED_DIR_IN_HOME  # FORK: Use our constant
        else:
            home_dir = home_dir.strip()

        # FORK: Keep our attribute name
        self.user_config_dir: str = home_dir
        """
        the path to the user's Serena configuration directory, which is typically ~/.serena
        """

        # UPSTREAM ENHANCEMENT: Add new properties
        self.user_prompt_templates_dir: str = os.path.join(self.user_config_dir, "prompt_templates")
        """
        directory containing prompt templates defined by the user.
        Prompts defined by the user take precedence over Serena's built-in prompt templates.
        """

        self.user_contexts_dir: str = os.path.join(self.user_config_dir, "contexts")
        """
        directory containing contexts defined by the user.
        If a name of a context matches a name of a context in SERENAS_OWN_CONTEXT_YAMLS_DIR,
        the user context will override the default context definition.
        """

        self.user_modes_dir: str = os.path.join(self.user_config_dir, "modes")
        """
        directory containing modes defined by the user.
        If a name of a mode matches a name of a mode in SERENAS_OWN_MODES_YAML_DIR,
        the user mode will override the default mode definition.
        """

    def get_next_log_file_path(self, prefix: str) -> str:
        # FORK: Keep our implementation (uses user_config_dir)
        log_dir = os.path.join(self.user_config_dir, "logs", datetime.now().strftime("%Y-%m-%d"))
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, prefix + "_" + datetime_tag() + ".txt")

    # TODO: Paths from constants.py should be moved here
```

**Rationale**:
- ✅ SERENA_HOME env var is a useful addition (doesn't break anything)
- ✅ user_prompt_templates_dir, user_contexts_dir, user_modes_dir are safe additions
- ✅ Keeping user_config_dir name maintains fork's backward compatibility
- ✅ No conflicts with centralized storage pattern

---

#### Phase 3: ProjectConfig - Multi-Language Support

**Location**: ProjectConfig dataclass (lines 162-169)
**Action**: Add multi-language support while maintaining backward compatibility

**Current Fork**:
```python
@dataclass(kw_only=True)
class ProjectConfig(ToolInclusionDefinition, ToStringMixin):
    project_name: str
    language: Language  # Single language
    ignored_paths: list[str] = field(default_factory=list)
    # ...
    encoding: str = DEFAULT_ENCODING
```

**Proposed Merge**:
```python
@dataclass(kw_only=True)
class ProjectConfig(ToolInclusionDefinition, ToStringMixin):
    project_name: str
    languages: list[Language]  # UPSTREAM: Multi-language support
    ignored_paths: list[str] = field(default_factory=list)
    # ...
    encoding: str = DEFAULT_SOURCE_FILE_ENCODING  # UPSTREAM: Rename constant
```

**Migration Logic** (add to `_from_dict`):
```python
@classmethod
def _from_dict(cls, data: dict[str, Any]) -> Self:
    # Backward compatibility: handle single "language" field
    if "languages" not in data and "language" in data:
        data["languages"] = [data["language"]]
    elif "languages" in data and "language" not in data:
        pass  # Already using new format
    elif "languages" in data and "language" in data:
        # Both present: prefer languages, ignore language
        log.warning("Both 'language' and 'languages' specified, using 'languages'")

    # Remove old field if present
    data.pop("language", None)

    # ... rest of existing logic
```

**Rationale**:
- Upstream's multi-language support is a valuable feature
- Backward compatibility ensures old configs still load
- Migration logic is safe and explicit

---

#### Phase 4: CRITICAL - Preserve Centralized Storage

**Location**: Lines 221-292 (storage methods)
**Action**: PRESERVE FORK VERSION ENTIRELY, REJECT UPSTREAM

**Preserve These Methods** (lines 221-236):
```python
@classmethod
def rel_path_to_project_yml(cls, project_root: Path) -> Path:
    """
    Get path to project configuration file in centralized storage.

    NOTE: This method now returns an absolute path to the centralized config,
    not a relative path. The name is kept for backward compatibility.

    Args:
        project_root: Absolute path to project root

    Returns:
        Path to ~/.serena/projects/{project-id}/project.yml
    """
    from serena.constants import get_project_config_path
    return get_project_config_path(project_root)
```

**Preserve Load Method** (lines 266-292):
```python
@classmethod
def load(cls, project_root: Path | str, autogenerate: bool = False) -> Self:
    """
    Load a ProjectConfig instance from the path to the project root.

    Looks for config in centralized location (~/.serena/projects/{id}/project.yml).
    """
    project_root = Path(project_root).resolve()

    # Check centralized location
    centralized_path = cls.rel_path_to_project_yml(project_root)
    if centralized_path.exists():
        yaml_path = centralized_path
    else:
        # Config not found in centralized location
        if autogenerate:
            return cls.autogenerate(project_root)
        else:
            raise FileNotFoundError(
                f"Project configuration file not found.\n"
                f"Expected location: {centralized_path}"
            )

    with open(yaml_path, encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)
    if "project_name" not in yaml_data:
        yaml_data["project_name"] = project_root.name
    return cls._from_dict(yaml_data)
```

**REJECT These Upstream Methods**:
- ❌ `path_to_project_yml(project_root)` → returns in-project path
- ❌ `rel_path_to_project_yml()` (class method, no args) → returns relative path
- ❌ Any load() logic that checks in-project location

**Rationale**: Upstream's storage approach fundamentally conflicts with our centralized storage architecture. This is a deliberate fork divergence.

---

### Summary: serena_config.py Changes

| Component | Action | Risk |
|-----------|--------|------|
| Imports | Add dataclasses, Enum, get_dataclass_default, ask_yes_no | LOW |
| Constants | Rename DEFAULT_ENCODING → DEFAULT_SOURCE_FILE_ENCODING | LOW |
| SerenaPaths.__init__ | Add SERENA_HOME env var support | LOW |
| SerenaPaths properties | Add user_prompt_templates_dir, user_contexts_dir, user_modes_dir | LOW |
| ProjectConfig.languages | Add multi-language support with migration | MEDIUM |
| ProjectConfig.rel_path_to_project_yml | PRESERVE fork version | NONE |
| ProjectConfig.load | PRESERVE fork version | NONE |
| ToolInclusionDefinition | NO CHANGE (identical) | NONE |

**Total Fork Divergence**: HIGH (storage architecture)
**Total Upstream Adoption**: SELECTIVE (safe features only)

---

## Testing Plan

### Test Suite 1: context_mode.py

1. **Test deprecation mapping**:
   ```python
   context = SerenaAgentContext.from_name("ide-assistant")
   assert context.name == "claude-code"  # Should redirect
   ```

2. **Test single_project field removal**:
   - Create test YAML with `single_project: true`
   - Load via `from_yaml()`
   - Verify no error raised

3. **Test USER_*_DIR imports**:
   - Verify constants are accessible
   - Verify paths resolve correctly

---

### Test Suite 2: serena_config.py

1. **Test SERENA_HOME env var**:
   ```bash
   export SERENA_HOME=/custom/path
   # Verify SerenaPaths.user_config_dir == /custom/path
   ```

2. **Test multi-language support**:
   - Load old config with `language: python`
   - Verify migrates to `languages: [python]`
   - Create new config with `languages: [python, typescript]`
   - Verify loads correctly

3. **Test centralized storage (CRITICAL)**:
   - Create project at `/path/to/project`
   - Verify config saved to `~/.serena/projects/{id}/project.yml`
   - Verify config loads from centralized location
   - Verify autogenerate creates centralized config

4. **Test backward compatibility**:
   - Load old ProjectConfig with `language` field
   - Load old ProjectConfig with `DEFAULT_ENCODING`
   - Verify no errors

---

## Risk Mitigation

| Risk | Mitigation | Validation |
|------|------------|------------|
| Break centralized storage | Preserve fork's rel_path_to_project_yml and load methods entirely | Test config loading from centralized location |
| Break deprecation mapping | Preserve ide-assistant redirect in context_mode.py | Test loading ide-assistant context |
| Break backward compatibility | Add migration logic for language→languages | Test loading old configs |
| Introduce regressions | Run full test suite after merge | pytest with coverage |
| Fork divergence increases | Document divergence clearly | Update this file with rationale |

---

## Rollback Plan

If merge causes issues:

1. **Immediate**: `git revert <commit-hash>` to undo merge commit
2. **Verify**: Run test suite to confirm rollback success
3. **Investigate**: Identify specific failure cause
4. **Re-attempt**: Create targeted fix, re-test, re-commit

**Rollback Complexity**: LOW (single commit, clean revert)

---

## Acceptance Criteria Mapping

From plan.yaml:

### AC-3.d.1: Generate context_mode.py diff ✅
**Status**: COMPLETE
**Evidence**: `.claude/sprint/reports/config-module-diff-3.d.md`

### AC-3.d.2: Generate serena_config.py diff ✅
**Status**: COMPLETE
**Evidence**: `.claude/sprint/reports/serena-config-diff-3.d.md`

### AC-3.d.3: Check path resolution conflicts ✅
**Status**: COMPLETE
**Finding**: CRITICAL architectural divergence identified
**Decision**: Preserve fork's centralized storage pattern
**Evidence**: This merge strategy document

---

## HUMAN APPROVAL REQUIRED

This merge strategy document serves as the GATE checkpoint specified in the plan. **No merge execution will proceed without explicit approval.**

### Approval Form

**Reviewed by**: ___________________
**Date**: ___________________
**Time**: ___________________

**Decision**:
- [ ] **APPROVED** - Proceed with merge as specified
- [ ] **APPROVED WITH MODIFICATIONS** - See notes below
- [ ] **REJECTED** - Do not merge, reason: ___________________

**Modifications** (if applicable):
_____________________________________________________________________________
_____________________________________________________________________________
_____________________________________________________________________________

**Additional Notes**:
_____________________________________________________________________________
_____________________________________________________________________________
_____________________________________________________________________________

**Signature**: ___________________

---

## Execution Checklist (After Approval)

- [ ] Create backup branch: `git checkout -b backup/pre-config-merge`
- [ ] Apply context_mode.py changes (Phase 1)
- [ ] Apply serena_config.py changes (Phases 1-4)
- [ ] Run sanity check: `python -m py_compile src/serena/config/*.py`
- [ ] Run test suite: `pytest tests/config/ -v`
- [ ] Test centralized storage manually
- [ ] Test deprecation mapping manually
- [ ] Test multi-language detection
- [ ] Commit changes with detailed message
- [ ] Update sprint index
- [ ] Proceed to Story 3.t (testing phase)

---

**Document Version**: 1.0
**Generated by**: Story 3.i (Implementation Phase)
**Status**: AWAITING APPROVAL
**Next Phase**: Implementation execution (blocked until approval)
