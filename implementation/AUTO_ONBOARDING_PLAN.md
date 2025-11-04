# Server-Side Auto-Onboarding Implementation Plan

**Status**: Ready to implement
**Estimated Effort**: 2-3 hours
**Token Efficiency Gain**: 10,000-20,000 tokens saved per project activation
**Date Created**: 2025-11-03

---

## Quick Start (TL;DR)

**What**: Automatically perform basic project onboarding server-side during `activate_project` without requiring agent exploration.

**Why**: Eliminate 10-20k token overhead and 3+ tool calls currently needed for manual onboarding workflow.

**How**: Modify `ActivateProjectTool.apply()` to detect onboarding status and auto-create basic memories from deterministic file analysis.

**Impact**:
- 🚀 Zero token overhead (no agent exploration needed)
- 💾 Single tool call instead of 3+ (check → onboard → explore → write)
- ⚡ Instant onboarding (server-side file analysis)
- 🎯 Consistent results (deterministic detection)

---

## Overview

Currently, project onboarding requires:
1. Agent calls `activate_project`
2. Agent calls `check_onboarding_performed`
3. Server responds "not onboarded, call onboarding tool"
4. Agent calls `onboarding` tool
5. Agent receives onboarding prompt
6. Agent explores codebase (10-20k tokens)
7. Agent writes multiple memories

**This is wasteful** because the server has all the information needed to create basic memories without any LLM exploration.

---

## Benefits Analysis

### Current Manual Flow (Token Cost)
```
activate_project:                500 tokens
check_onboarding_performed:      300 tokens
onboarding tool call:            400 tokens
onboarding prompt:               600 tokens
agent exploration:            10,000 tokens
  - list_dir calls:            2,000 tokens
  - read_file calls:           5,000 tokens
  - search patterns:           3,000 tokens
write_memory calls (x4):       2,000 tokens
-------------------------------------------
TOTAL:                        13,800 tokens
Tool calls: 8-12
Time: 30-60 seconds
```

### Proposed Auto-Onboarding Flow (Token Cost)
```
activate_project (enhanced):     500 tokens
  - includes auto-onboarding
  - returns ready-to-use memories
-------------------------------------------
TOTAL:                           500 tokens
Tool calls: 1
Time: <1 second
```

**Savings**: 13,300 tokens (96% reduction), 7-11 fewer tool calls

---

## Architecture Overview

### Current Architecture
```
ActivateProjectTool
  └─> activate_project_from_path_or_name()
       └─> load_project_from_path_or_name()
            └─> Project.load() or ProjectConfig.autogenerate()
                 └─> create .serena/project.yml

Agent then manually:
  └─> CheckOnboardingPerformedTool
       └─> list_memories() == 0?
            └─> OnboardingTool
                 └─> returns prompt for agent to explore
                      └─> agent explores and writes memories
```

### Proposed Architecture
```
ActivateProjectTool
  └─> activate_project_from_path_or_name()
       └─> load_project_from_path_or_name()
            └─> Project.load() or ProjectConfig.autogenerate()
                 └─> create .serena/project.yml
       └─> _check_and_auto_onboard()  [NEW]
            └─> list_memories() == 0?
                 └─> _auto_onboard_project()  [NEW]
                      └─> _detect_tech_stack()
                      └─> _find_command_files()
                      └─> _detect_code_style()
                      └─> _write_onboarding_memories()
```

---

## Implementation Phases

## Phase 1: Core Auto-Onboarding (Essential)

**Goal**: Automatically create basic memories from deterministic file analysis.

### Files to Modify

#### 1. `src/serena/tools/config_tools.py` (ActivateProjectTool)

**Modifications**:
- Add `_check_and_auto_onboard()` method
- Add `_auto_onboard_project()` method
- Call auto-onboarding in `apply()` after activation

**Location**: After line 48 (end of `apply()` method)

```python
def apply(self, project: str) -> str:
    """Activates the project with the given name."""
    active_project = self.agent.activate_project_from_path_or_name(project)

    # ... existing parent project handling ...

    # NEW: Check and auto-onboard if needed
    onboarding_status = self._check_and_auto_onboard(active_project)

    # Build result string
    if active_project.is_newly_created:
        result_str = (
            f"Created and activated a new project with name '{active_project.project_name}' "
            f"at {active_project.project_root}, language: {active_project.project_config.language.value}. "
            "You can activate this project later by name.\n"
            f"The project's Serena configuration is in {active_project.path_to_project_yml()}. "
            "In particular, you may want to edit the project name and the initial prompt."
        )
        if used_parent:
            result_str = f"Using parent project at {active_project._used_parent_path}\n" + result_str
    else:
        result_str = (
            f"Activated existing project with name '{active_project.project_name}' "
            f"at {active_project.project_root}, language: {active_project.project_config.language.value}"
        )
        if used_parent:
            result_str = (
                f"Using parent project at {active_project._used_parent_path} "
                f"(requested: {active_project._requested_path})\n" + result_str
            )

    # Add onboarding status
    if onboarding_status["performed"]:
        result_str += "\n\n" + onboarding_status["message"]

    if active_project.project_config.initial_prompt:
        result_str += f"\n\nAdditional project information:\n {active_project.project_config.initial_prompt}"

    result_str += (
        f"\n\nAvailable memories:\n {json.dumps(list(self.memories_manager.list_memories()))}"
        + " You should not read these memories directly, but rather use the `read_memory` tool to read them later if needed for the task."
    )
    result_str += f"\n\nAvailable tools:\n {json.dumps(self.agent.get_active_tool_names())}"

    # Clean up temporary attributes
    if used_parent:
        delattr(active_project, '_used_parent_path')
        delattr(active_project, '_requested_path')

    return result_str

def _check_and_auto_onboard(self, project: Project) -> dict:
    """
    Check if project needs onboarding and perform it automatically if needed.

    :param project: the activated project
    :return: dict with 'performed' (bool) and 'message' (str)
    """
    from .memory_tools import ListMemoriesTool

    list_memories_tool = self.agent.get_tool(ListMemoriesTool)
    memories = json.loads(list_memories_tool.apply())

    if len(memories) == 0:
        # No memories exist - perform auto-onboarding
        return self._auto_onboard_project(project)
    else:
        return {
            "performed": False,
            "message": f"Project already onboarded ({len(memories)} memories available)"
        }

def _auto_onboard_project(self, project: Project) -> dict:
    """
    Automatically onboard a project by analyzing files and creating basic memories.

    :param project: the project to onboard
    :return: dict with 'performed' (bool) and 'message' (str)
    """
    from .memory_tools import WriteMemoryTool
    import platform

    write_memory = self.agent.get_tool(WriteMemoryTool)

    # Detect tech stack
    tech_stack = self._detect_tech_stack(project)

    # Find command files
    commands = self._find_command_files(project)

    # Detect code style hints
    style_info = self._detect_code_style(project)

    # Create project overview memory
    overview = f"""# {project.project_name}

**Language**: {project.language}
**Location**: {project.project_root}
**Tech Stack**: {tech_stack}
**Platform**: {platform.system()}

## Auto-Detected Information

This project was automatically onboarded. The information below was detected from
configuration files and project structure. You may want to supplement this with
additional information as you work with the project.
"""

    write_memory.apply(
        memory_name="project_overview.md",
        content=overview
    )

    # Create suggested commands memory
    commands_md = self._generate_commands_memory(commands, project)
    write_memory.apply(
        memory_name="suggested_commands.md",
        content=commands_md
    )

    # Create code style memory if detected
    if style_info:
        write_memory.apply(
            memory_name="code_style_and_conventions.md",
            content=style_info
        )

    # Create task completion checklist
    completion_checklist = self._generate_completion_checklist(commands)
    write_memory.apply(
        memory_name="task_completion_checklist.md",
        content=completion_checklist
    )

    memories_created = 4 if style_info else 3

    return {
        "performed": True,
        "message": (
            f"✓ Auto-onboarded project (created {memories_created} memories)\n"
            f"  - Detected tech stack: {tech_stack}\n"
            f"  - Found {len(commands)} command sources\n"
            "  - Use `read_memory` to view detailed information"
        )
    }
```

#### 2. Create `src/serena/tools/onboarding_helpers.py` (NEW FILE)

**Purpose**: Helper functions for tech stack detection and file analysis.

```python
"""
Helper functions for automatic project onboarding.
"""

import json
import os
import re
from pathlib import Path
from typing import Any

from serena.project import Project


def detect_tech_stack(project: Project) -> str:
    """
    Detect tech stack from project files.

    :param project: the project to analyze
    :return: comma-separated string of detected technologies
    """
    stack = []

    # Package managers & languages
    if project.relative_path_exists("package.json"):
        pkg_json = read_json_safe(project, "package.json")
        if pkg_json:
            stack.append("Node.js/npm")
            # Detect frameworks from dependencies
            deps = {**pkg_json.get("dependencies", {}), **pkg_json.get("devDependencies", {})}
            if "react" in deps:
                stack.append("React")
            if "next" in deps:
                stack.append("Next.js")
            if "vue" in deps:
                stack.append("Vue.js")
            if "@angular/core" in deps:
                stack.append("Angular")
            if "typescript" in deps:
                stack.append("TypeScript")

    if project.relative_path_exists("Cargo.toml"):
        stack.append("Rust/Cargo")

    if project.relative_path_exists("pyproject.toml"):
        pyproject = read_toml_safe(project, "pyproject.toml")
        if pyproject:
            if "tool" in pyproject and "poetry" in pyproject["tool"]:
                stack.append("Python/Poetry")
            else:
                stack.append("Python")
    elif project.relative_path_exists("requirements.txt"):
        stack.append("Python/pip")

    if project.relative_path_exists("go.mod"):
        stack.append("Go")

    if project.relative_path_exists("Gemfile"):
        stack.append("Ruby/Bundler")

    if project.relative_path_exists("pom.xml"):
        stack.append("Java/Maven")
    elif project.relative_path_exists("build.gradle") or project.relative_path_exists("build.gradle.kts"):
        stack.append("Java/Gradle")

    if project.relative_path_exists("Cargo.toml"):
        stack.append("Rust")

    # Build tools
    if project.relative_path_exists("Makefile"):
        stack.append("Make")

    if project.relative_path_exists("docker-compose.yml") or project.relative_path_exists("compose.yaml"):
        stack.append("Docker Compose")

    if project.relative_path_exists("Dockerfile"):
        stack.append("Docker")

    return ", ".join(stack) if stack else "Unknown"


def find_command_files(project: Project) -> dict[str, Any]:
    """
    Find command definitions from standard configuration files.

    :param project: the project to analyze
    :return: dict mapping source type to commands
    """
    commands = {}

    # package.json scripts
    pkg_json = read_json_safe(project, "package.json")
    if pkg_json and "scripts" in pkg_json:
        commands["npm"] = pkg_json["scripts"]

    # Makefile targets
    if project.relative_path_exists("Makefile"):
        commands["make"] = parse_makefile_targets(project, "Makefile")

    # pyproject.toml scripts
    pyproject = read_toml_safe(project, "pyproject.toml")
    if pyproject:
        if "tool" in pyproject and "poetry" in pyproject["tool"]:
            if "scripts" in pyproject["tool"]["poetry"]:
                commands["poetry"] = pyproject["tool"]["poetry"]["scripts"]

    # Cargo.toml (Rust)
    cargo = read_toml_safe(project, "Cargo.toml")
    if cargo:
        # Rust doesn't have scripts like npm, but we can note common commands
        commands["cargo"] = {
            "build": "cargo build",
            "test": "cargo test",
            "run": "cargo run"
        }

    # GitHub Actions workflows
    workflows_dir = ".github/workflows"
    if project.relative_path_exists(workflows_dir):
        try:
            workflow_files = project.gather_source_files(workflows_dir)
            if workflow_files:
                commands["github-actions"] = {
                    "workflows": [os.path.basename(f) for f in workflow_files]
                }
        except Exception:
            pass

    return commands


def detect_code_style(project: Project) -> str:
    """
    Detect code style configuration from common config files.

    :param project: the project to analyze
    :return: markdown string describing code style, or empty string if none detected
    """
    style_parts = []

    # ESLint
    if project.relative_path_exists(".eslintrc.json") or \
       project.relative_path_exists(".eslintrc.js") or \
       project.relative_path_exists(".eslintrc"):
        style_parts.append("- **Linting**: ESLint configured")

    # Prettier
    if project.relative_path_exists(".prettierrc") or \
       project.relative_path_exists(".prettierrc.json") or \
       project.relative_path_exists("prettier.config.js"):
        style_parts.append("- **Formatting**: Prettier configured")

    # Python: Black, Ruff, mypy
    pyproject = read_toml_safe(project, "pyproject.toml")
    if pyproject and "tool" in pyproject:
        if "black" in pyproject["tool"]:
            style_parts.append("- **Python Formatting**: Black")
        if "ruff" in pyproject["tool"]:
            style_parts.append("- **Python Linting**: Ruff")
        if "mypy" in pyproject["tool"]:
            style_parts.append("- **Python Type Checking**: mypy")

    # EditorConfig
    if project.relative_path_exists(".editorconfig"):
        style_parts.append("- **Editor Config**: .editorconfig present")

    if not style_parts:
        return ""

    return f"""# Code Style and Conventions

## Auto-Detected Configuration

{chr(10).join(style_parts)}

## Notes

This information was auto-detected from configuration files. For detailed
style guidelines, check the project's README or CONTRIBUTING files.
"""


def generate_commands_memory(commands: dict[str, Any], project: Project) -> str:
    """
    Generate the suggested_commands.md memory content.

    :param commands: dict of command sources
    :param project: the project
    :return: markdown content for suggested_commands.md
    """
    content = f"""# Suggested Commands for {project.project_name}

## Auto-Detected Commands

"""

    if "npm" in commands:
        content += "### npm scripts (from package.json)\n\n"
        for script, cmd in commands["npm"].items():
            content += f"- `npm run {script}` - {cmd}\n"
        content += "\n"

    if "make" in commands:
        content += "### Makefile targets\n\n"
        for target, description in commands["make"].items():
            desc_str = f" - {description}" if description else ""
            content += f"- `make {target}`{desc_str}\n"
        content += "\n"

    if "poetry" in commands:
        content += "### Poetry scripts (from pyproject.toml)\n\n"
        for script, cmd in commands["poetry"].items():
            content += f"- `poetry run {script}` - {cmd}\n"
        content += "\n"

    if "cargo" in commands:
        content += "### Cargo commands (Rust)\n\n"
        for cmd, full_cmd in commands["cargo"].items():
            content += f"- `{full_cmd}`\n"
        content += "\n"

    if "github-actions" in commands:
        content += "### GitHub Actions workflows\n\n"
        content += f"- Workflows: {', '.join(commands['github-actions']['workflows'])}\n\n"

    if not commands:
        content += "_No command files detected. Check README for manual instructions._\n\n"

    content += """
## Common Development Commands

These are typically useful regardless of detected configuration:

- `git status` - Check git status
- `git diff` - View changes
- Testing: Check package.json, Makefile, or README for test commands
- Linting: Check for .eslintrc, .ruff.toml, or similar configuration files
"""

    return content


def generate_completion_checklist(commands: dict[str, Any]) -> str:
    """
    Generate task completion checklist based on detected commands.

    :param commands: dict of command sources
    :return: markdown content for task_completion_checklist.md
    """
    content = """# Task Completion Checklist

## When You Complete a Task

Before marking a task as done, consider running:

"""

    # Add detected test commands
    test_commands = []
    if "npm" in commands:
        if "test" in commands["npm"]:
            test_commands.append("`npm test`")
        if "lint" in commands["npm"]:
            test_commands.append("`npm run lint`")

    if "make" in commands:
        if "test" in commands["make"]:
            test_commands.append("`make test`")
        if "lint" in commands["make"]:
            test_commands.append("`make lint`")

    if "poetry" in commands:
        # Poetry typically uses pytest
        test_commands.append("`poetry run pytest`")

    if "cargo" in commands:
        test_commands.append("`cargo test`")
        test_commands.append("`cargo clippy` (linting)")

    if test_commands:
        content += "### Auto-Detected Commands\n\n"
        for cmd in test_commands:
            content += f"- [ ] Run {cmd}\n"
        content += "\n"

    content += """### General Checklist

- [ ] All tests pass
- [ ] Code is properly formatted (check for prettier/black/rustfmt)
- [ ] No linting errors
- [ ] Changes are documented (if applicable)
- [ ] Git commit created with descriptive message
"""

    return content


# Helper functions

def read_json_safe(project: Project, relative_path: str) -> dict | None:
    """Safely read and parse a JSON file."""
    try:
        if project.relative_path_exists(relative_path):
            content = project.read_file(relative_path)
            return json.loads(content)
    except Exception:
        pass
    return None


def read_toml_safe(project: Project, relative_path: str) -> dict | None:
    """Safely read and parse a TOML file."""
    try:
        if project.relative_path_exists(relative_path):
            import tomllib  # Python 3.11+
            content = project.read_file(relative_path)
            return tomllib.loads(content)
    except Exception:
        try:
            import tomli  # Fallback for older Python
            content = project.read_file(relative_path)
            return tomli.loads(content)
        except Exception:
            pass
    return None


def parse_makefile_targets(project: Project, relative_path: str) -> dict[str, str]:
    """
    Parse Makefile to extract targets and their descriptions.

    :return: dict mapping target name to description (or empty string)
    """
    targets = {}
    try:
        content = project.read_file(relative_path)
        lines = content.split("\n")

        for i, line in enumerate(lines):
            # Match target lines (e.g., "test:" or "build:")
            match = re.match(r'^([a-zA-Z0-9_-]+):\s*(.*)$', line.strip())
            if match:
                target = match.group(1)
                # Look for comment above target
                description = ""
                if i > 0:
                    prev_line = lines[i-1].strip()
                    if prev_line.startswith("#"):
                        description = prev_line.lstrip("#").strip()
                targets[target] = description
    except Exception:
        pass

    return targets
```

#### 3. Update `src/serena/tools/config_tools.py` imports

**Location**: Top of file

```python
from serena.tools.onboarding_helpers import (
    detect_tech_stack,
    find_command_files,
    detect_code_style,
    generate_commands_memory,
    generate_completion_checklist,
)
```

#### 4. Add helper methods to `ActivateProjectTool`

```python
def _detect_tech_stack(self, project: Project) -> str:
    """Wrapper for tech stack detection."""
    return detect_tech_stack(project)

def _find_command_files(self, project: Project) -> dict:
    """Wrapper for command file detection."""
    return find_command_files(project)

def _detect_code_style(self, project: Project) -> str:
    """Wrapper for code style detection."""
    return detect_code_style(project)

def _generate_commands_memory(self, commands: dict, project: Project) -> str:
    """Wrapper for commands memory generation."""
    return generate_commands_memory(commands, project)

def _generate_completion_checklist(self, commands: dict) -> str:
    """Wrapper for completion checklist generation."""
    return generate_completion_checklist(commands)
```

---

## Phase 2: Deprecate Manual Onboarding Tools (Optional)

**Goal**: Mark old onboarding tools as deprecated but keep them for backward compatibility.

### Files to Modify

#### 1. `src/serena/tools/workflow_tools.py`

**Update docstrings**:

```python
class CheckOnboardingPerformedTool(Tool):
    """
    [DEPRECATED] Checks whether project onboarding was already performed.

    NOTE: As of version X.X.X, onboarding is performed automatically during
    project activation. This tool is maintained for backward compatibility
    but is no longer necessary.
    """
    # ... existing implementation ...

class OnboardingTool(Tool):
    """
    [DEPRECATED] Performs onboarding (identifying project structure and tasks).

    NOTE: As of version X.X.X, onboarding is performed automatically during
    project activation. This tool is maintained for backward compatibility
    and can be used to re-onboard a project if needed.
    """
    # ... existing implementation ...
```

---

## Phase 3: Enhanced Detection (Future)

**Goal**: Add deeper analysis capabilities for complex projects.

### Potential Enhancements

1. **README parsing**: Extract commands from README ## Commands section
2. **CI/CD analysis**: Parse GitHub Actions/GitLab CI for test/deploy commands
3. **Framework detection**: Detect Django, Flask, Rails, etc. and add framework-specific commands
4. **Dependency analysis**: Parse lock files for version information
5. **Documentation detection**: Find Sphinx, JSDoc, or other doc generation tools

---

## Testing Strategy

### Unit Tests

Create `test/serena/tools/test_onboarding_helpers.py`:

```python
def test_detect_tech_stack_nodejs():
    """Test Node.js project detection."""
    # Create mock project with package.json
    # Assert "Node.js/npm" in tech_stack

def test_detect_tech_stack_python():
    """Test Python project detection."""
    # Create mock project with pyproject.toml
    # Assert "Python/Poetry" in tech_stack

def test_find_command_files_npm():
    """Test npm scripts detection."""
    # Create mock package.json
    # Assert scripts are correctly extracted

def test_find_command_files_makefile():
    """Test Makefile target detection."""
    # Create mock Makefile
    # Assert targets are correctly parsed
```

### Integration Tests

Create `test/serena/tools/test_auto_onboarding.py`:

```python
def test_auto_onboarding_on_new_project():
    """Test that new project activation creates memories automatically."""
    # Activate new project
    # Assert 3-4 memories were created
    # Assert memories contain expected content

def test_auto_onboarding_skipped_for_existing():
    """Test that existing onboarded projects skip auto-onboarding."""
    # Activate project with existing memories
    # Assert no new memories created
    # Assert "already onboarded" in response
```

### Manual Testing

1. **New JavaScript project**:
   ```bash
   mkdir test-js-project
   cd test-js-project
   npm init -y
   # Add scripts to package.json
   ```
   - Activate project
   - Verify `suggested_commands.md` contains npm scripts

2. **New Python project**:
   ```bash
   mkdir test-py-project
   cd test-py-project
   poetry init
   ```
   - Activate project
   - Verify `project_overview.md` shows "Python/Poetry"

3. **Existing onboarded project**:
   - Activate project that already has memories
   - Verify no duplicate memories created

---

## Error Handling

### Edge Cases

1. **Malformed JSON/TOML files**: Use `*_safe()` functions that catch exceptions
2. **Missing dependencies**: Check for `tomllib` vs `tomli` for TOML parsing
3. **Permission errors**: Catch file read errors and continue with partial detection
4. **Large files**: Limit file reading to known config files only

### Fallback Behavior

If auto-onboarding fails:
- Log error but don't fail activation
- Return message: "Auto-onboarding unavailable, use `onboarding` tool manually"
- Ensure project is still activated successfully

---

## Configuration Options

### Project-Level Configuration (Future)

Add to `.serena/project.yml`:

```yaml
auto_onboard: true  # Enable/disable auto-onboarding (default: true)
onboarding_depth: basic  # basic | full (default: basic)
```

### User-Level Configuration (Future)

Add to Serena global config:

```yaml
default_auto_onboard: true
```

---

## Migration Path

### For Existing Projects

- Projects with existing memories: No change, auto-onboarding skipped
- Projects without memories: Auto-onboarded on next activation

### For New Projects

- All new projects auto-onboarded immediately on first activation
- Users can still use `onboarding` tool for re-onboarding

---

## Performance Metrics

### Expected Performance

- **File I/O**: ~10-20 file existence checks (<1ms each)
- **JSON/TOML parsing**: ~5-10ms per file
- **Memory writes**: ~50ms per memory (3-4 memories)
- **Total overhead**: ~200-300ms added to activation

### Comparison

- Manual onboarding: 30-60 seconds
- Auto-onboarding: <1 second
- **Speedup**: 30-60x faster

---

## Documentation Updates

### Files to Update

1. **README.md**: Add section on auto-onboarding
2. **docs/onboarding.md**: Update to explain auto vs manual onboarding
3. **CHANGELOG.md**: Add entry for auto-onboarding feature
4. **MCP server description**: Update to mention auto-onboarding

### Example README Addition

```markdown
## Automatic Project Onboarding

Serena now automatically onboards projects when you activate them for the first time.
This creates basic memory files containing:

- Project overview (language, tech stack, platform)
- Suggested commands (detected from package.json, Makefile, etc.)
- Code style configuration (ESLint, Prettier, Black, etc.)
- Task completion checklist

No manual onboarding is required! The agent can immediately start working with
the project using the auto-generated memories.
```

---

## Rollout Plan

### Version 1.0 (Phase 1)

- Implement core auto-onboarding
- Add onboarding_helpers.py
- Update ActivateProjectTool
- Write tests
- Update documentation

### Version 1.1 (Phase 2)

- Deprecate manual onboarding tools
- Add configuration options
- Enhanced error handling

### Version 1.2 (Phase 3)

- Enhanced detection (README parsing, CI/CD analysis)
- Framework-specific templates
- Deep onboarding mode

---

## Success Criteria

- [ ] Auto-onboarding completes in <1 second
- [ ] 3-4 memories created automatically
- [ ] No token overhead (zero LLM calls)
- [ ] Works for 90%+ of common project types
- [ ] Backward compatible with existing projects
- [ ] Tests pass with >90% coverage
- [ ] Documentation updated

---

## Risks & Mitigation

### Risk: Incorrect Detection

**Mitigation**:
- Be conservative in detection (only add high-confidence items)
- Allow manual `onboarding` tool for complex projects
- Add config option to disable auto-onboarding

### Risk: Performance Regression

**Mitigation**:
- Profile file I/O operations
- Cache file existence checks
- Limit number of files read

### Risk: Breaking Changes

**Mitigation**:
- Keep backward compatibility
- Make auto-onboarding opt-out, not opt-in
- Provide clear migration guide

---

## Alternative Approaches Considered

### Approach A: LLM-Based Auto-Onboarding

**Pros**: More intelligent, can understand context
**Cons**: Token overhead, slower, non-deterministic
**Decision**: Rejected - defeats the purpose of saving tokens

### Approach B: User Prompt for Onboarding

**Pros**: Explicit user control
**Cons**: Extra friction, worse UX
**Decision**: Rejected - auto-onboarding is better default

### Approach C: Lazy Onboarding (on-demand)

**Pros**: Only onboard when needed
**Cons**: Unpredictable behavior, still requires tool calls
**Decision**: Rejected - upfront onboarding is more predictable

---

## Appendix: File Detection Matrix

| Project Type | Detection File | Tech Stack String | Commands Source |
|--------------|----------------|-------------------|-----------------|
| Node.js | package.json | "Node.js/npm" | package.json scripts |
| TypeScript | package.json + typescript dep | "Node.js/npm, TypeScript" | package.json scripts |
| React | package.json + react dep | "Node.js/npm, React" | package.json scripts |
| Python/Poetry | pyproject.toml + tool.poetry | "Python/Poetry" | pyproject.toml scripts |
| Python/pip | requirements.txt | "Python/pip" | Makefile or README |
| Rust | Cargo.toml | "Rust/Cargo" | cargo (standard) |
| Go | go.mod | "Go" | Makefile or README |
| Ruby | Gemfile | "Ruby/Bundler" | Rakefile or README |
| Java/Maven | pom.xml | "Java/Maven" | mvn (standard) |
| Java/Gradle | build.gradle(.kts) | "Java/Gradle" | gradle (standard) |
| Docker | Dockerfile | "Docker" | Makefile or compose |

---

**Ready to implement when approved.**
