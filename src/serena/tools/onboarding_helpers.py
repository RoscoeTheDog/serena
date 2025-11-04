"""
Helper functions for automatic project onboarding.

These functions detect tech stacks, parse command files, and generate
memory content for newly activated projects.
"""

import json
import re
from typing import Any


def detect_tech_stack(project) -> str:
    """
    Detect tech stack from project files.

    Detects package managers, frameworks, and build tools by checking
    for configuration files.

    :param project: Project instance
    :return: Comma-separated string of detected technologies
    """
    detected = []

    # Package managers
    if project.relative_path_exists("package.json"):
        pkg_json = read_json_safe(project, "package.json")
        if pkg_json:
            detected.append("Node.js/npm")

            # Detect frameworks from dependencies
            deps = {**pkg_json.get("dependencies", {}), **pkg_json.get("devDependencies", {})}
            if "react" in deps:
                detected.append("React")
            if "next" in deps:
                detected.append("Next.js")
            if "vue" in deps:
                detected.append("Vue")
            if "@angular/core" in deps:
                detected.append("Angular")
            if "typescript" in deps:
                detected.append("TypeScript")

    if project.relative_path_exists("yarn.lock"):
        if "Node.js/npm" not in detected:
            detected.append("Node.js/Yarn")

    if project.relative_path_exists("pnpm-lock.yaml"):
        if "Node.js/npm" not in detected:
            detected.append("Node.js/pnpm")

    # Python
    if project.relative_path_exists("pyproject.toml"):
        pyproject = read_toml_safe(project, "pyproject.toml")
        if pyproject and "tool" in pyproject and "poetry" in pyproject["tool"]:
            detected.append("Python/Poetry")
        else:
            detected.append("Python")

    if project.relative_path_exists("setup.py"):
        if "Python" not in detected and "Python/Poetry" not in detected:
            detected.append("Python/setuptools")

    if project.relative_path_exists("requirements.txt"):
        if not any("Python" in d for d in detected):
            detected.append("Python/pip")

    if project.relative_path_exists("Pipfile"):
        detected.append("Python/pipenv")

    # Rust
    if project.relative_path_exists("Cargo.toml"):
        detected.append("Rust/Cargo")

    # Ruby
    if project.relative_path_exists("Gemfile"):
        detected.append("Ruby/Bundler")

    # Java/Kotlin
    if project.relative_path_exists("pom.xml"):
        detected.append("Java/Maven")

    if project.relative_path_exists("build.gradle") or project.relative_path_exists("build.gradle.kts"):
        detected.append("Java/Gradle")

    # Go
    if project.relative_path_exists("go.mod"):
        detected.append("Go")

    # Build tools
    if project.relative_path_exists("Makefile"):
        detected.append("Make")

    if project.relative_path_exists("Dockerfile"):
        detected.append("Docker")

    if project.relative_path_exists("docker-compose.yml") or project.relative_path_exists("docker-compose.yaml"):
        detected.append("Docker Compose")

    return ", ".join(detected) if detected else "Unknown"


def find_command_files(project) -> dict[str, Any]:
    """
    Find command definitions from configuration files.

    Parses package.json scripts, Makefile targets, pyproject.toml scripts,
    and other command sources.

    :param project: Project instance
    :return: Dict mapping source names to command dictionaries
    """
    commands = {}

    # Parse package.json scripts
    if project.relative_path_exists("package.json"):
        pkg_json = read_json_safe(project, "package.json")
        if pkg_json and "scripts" in pkg_json:
            commands["npm"] = pkg_json["scripts"]

    # Parse Makefile targets
    if project.relative_path_exists("Makefile"):
        targets = parse_makefile_targets(project, "Makefile")
        if targets:
            commands["make"] = targets

    # Parse pyproject.toml scripts (Poetry)
    if project.relative_path_exists("pyproject.toml"):
        pyproject = read_toml_safe(project, "pyproject.toml")
        if pyproject and "tool" in pyproject:
            if "poetry" in pyproject["tool"] and "scripts" in pyproject["tool"]["poetry"]:
                commands["poetry"] = pyproject["tool"]["poetry"]["scripts"]

    # Standard Cargo commands (implied by Cargo.toml)
    if project.relative_path_exists("Cargo.toml"):
        commands["cargo"] = {
            "build": "Build the project",
            "test": "Run tests",
            "run": "Run the project",
            "check": "Check for errors without building",
            "clippy": "Run Clippy linter",
            "fmt": "Format code"
        }

    # Standard Go commands (implied by go.mod)
    if project.relative_path_exists("go.mod"):
        commands["go"] = {
            "build": "Build the project",
            "test": "Run tests",
            "run": "Run the project",
            "fmt": "Format code",
            "vet": "Report suspicious constructs"
        }

    return commands


def detect_code_style(project) -> str:
    """
    Detect code style configuration from project files.

    Detects linters, formatters, and style guides.

    :param project: Project instance
    :return: Markdown string describing style configuration, or empty string
    """
    style_info = []

    # JavaScript/TypeScript linters and formatters
    if project.relative_path_exists(".eslintrc") or \
       project.relative_path_exists(".eslintrc.js") or \
       project.relative_path_exists(".eslintrc.json") or \
       project.relative_path_exists(".eslintrc.yml"):
        style_info.append("- **ESLint**: JavaScript/TypeScript linting configured")

    if project.relative_path_exists(".prettierrc") or \
       project.relative_path_exists(".prettierrc.js") or \
       project.relative_path_exists(".prettierrc.json") or \
       project.relative_path_exists("prettier.config.js"):
        style_info.append("- **Prettier**: Code formatting configured")

    # Python linters and formatters
    if project.relative_path_exists("pyproject.toml"):
        pyproject = read_toml_safe(project, "pyproject.toml")
        if pyproject and "tool" in pyproject:
            if "black" in pyproject["tool"]:
                style_info.append("- **Black**: Python code formatting configured")
            if "ruff" in pyproject["tool"]:
                style_info.append("- **Ruff**: Python linting configured")
            if "mypy" in pyproject["tool"]:
                style_info.append("- **mypy**: Python type checking configured")
            if "isort" in pyproject["tool"]:
                style_info.append("- **isort**: Python import sorting configured")

    if project.relative_path_exists(".flake8"):
        style_info.append("- **Flake8**: Python linting configured")

    if project.relative_path_exists(".pylintrc") or project.relative_path_exists("pylintrc"):
        style_info.append("- **Pylint**: Python linting configured")

    # EditorConfig
    if project.relative_path_exists(".editorconfig"):
        style_info.append("- **EditorConfig**: Cross-editor style settings configured")

    if not style_info:
        return ""

    return f"""# Code Style and Conventions

## Auto-Detected Configuration

{chr(10).join(style_info)}

## Notes

These configurations were automatically detected. Review the actual config files
for specific rules and settings.
"""


def generate_commands_memory(commands: dict, project) -> str:
    """
    Generate suggested_commands.md content.

    :param commands: Dict of commands from find_command_files()
    :param project: Project instance
    :return: Markdown content for suggested_commands.md
    """
    sections = []

    # Add commands by source
    if "npm" in commands:
        npm_cmds = []
        for script, cmd in commands["npm"].items():
            npm_cmds.append(f"- `npm run {script}` - {cmd if isinstance(cmd, str) else 'Run ' + script}")
        sections.append(f"""## npm Scripts

{chr(10).join(npm_cmds)}
""")

    if "make" in commands:
        make_cmds = []
        for target, desc in commands["make"].items():
            desc_str = f" - {desc}" if desc else ""
            make_cmds.append(f"- `make {target}`{desc_str}")
        sections.append(f"""## Make Targets

{chr(10).join(make_cmds)}
""")

    if "poetry" in commands:
        poetry_cmds = []
        for script, cmd in commands["poetry"].items():
            poetry_cmds.append(f"- `poetry run {script}` - {cmd if isinstance(cmd, str) else 'Run ' + script}")
        sections.append(f"""## Poetry Scripts

{chr(10).join(poetry_cmds)}
""")

    if "cargo" in commands:
        cargo_cmds = []
        for cmd, desc in commands["cargo"].items():
            cargo_cmds.append(f"- `cargo {cmd}` - {desc}")
        sections.append(f"""## Cargo Commands

{chr(10).join(cargo_cmds)}
""")

    if "go" in commands:
        go_cmds = []
        for cmd, desc in commands["go"].items():
            go_cmds.append(f"- `go {cmd}` - {desc}")
        sections.append(f"""## Go Commands

{chr(10).join(go_cmds)}
""")

    # Add common git commands
    sections.append("""## Common Development Commands

- `git status` - Check git status
- `git diff` - View changes
- `git add .` - Stage all changes
- `git commit -m "message"` - Commit changes
- `git push` - Push to remote
""")

    auto_detected = "\n".join(sections) if sections[:-1] else "_No project-specific commands detected._\n"

    return f"""# Suggested Commands for {project.project_name}

## Auto-Detected Commands

{auto_detected}

{sections[-1] if sections else ""}"""


def generate_completion_checklist(commands: dict) -> str:
    """
    Generate task_completion_checklist.md content.

    :param commands: Dict of commands from find_command_files()
    :return: Markdown content for task_completion_checklist.md
    """
    checklist_items = []

    # Detect test commands
    has_tests = False
    test_cmd = None

    if "npm" in commands:
        if "test" in commands["npm"]:
            has_tests = True
            test_cmd = "`npm test`"

    if "make" in commands:
        if "test" in commands["make"]:
            has_tests = True
            test_cmd = "`make test`"

    if "cargo" in commands:
        has_tests = True
        test_cmd = "`cargo test`"

    if "go" in commands:
        has_tests = True
        test_cmd = "`go test`"

    if has_tests:
        checklist_items.append(f"- [ ] Tests pass ({test_cmd})")
    else:
        checklist_items.append("- [ ] Tests pass (if applicable)")

    # Detect lint/format commands
    has_lint = False
    lint_cmd = None

    if "npm" in commands:
        if "lint" in commands["npm"]:
            has_lint = True
            lint_cmd = "`npm run lint`"

    if "make" in commands:
        if "lint" in commands["make"]:
            has_lint = True
            lint_cmd = "`make lint`"

    if "cargo" in commands:
        has_lint = True
        lint_cmd = "`cargo clippy`"

    if has_lint:
        checklist_items.append(f"- [ ] Code is linted ({lint_cmd})")
    else:
        checklist_items.append("- [ ] Code is properly formatted")

    # Add standard checklist items
    checklist_items.append("- [ ] No syntax or type errors")
    checklist_items.append("- [ ] Code follows project conventions")
    checklist_items.append("- [ ] Git commit created with descriptive message")

    return f"""# Task Completion Checklist

## When You Complete a Task

{chr(10).join(checklist_items)}

## Notes

This checklist was auto-generated based on detected project configuration.
Adjust as needed for specific tasks.
"""


# Helper utilities

def read_json_safe(project, relative_path: str) -> dict | None:
    """
    Safely read and parse a JSON file.

    :param project: Project instance
    :param relative_path: Path relative to project root
    :return: Parsed JSON dict or None if error
    """
    try:
        if project.relative_path_exists(relative_path):
            content = project.read_file(relative_path)
            return json.loads(content)
    except Exception:
        pass
    return None


def read_toml_safe(project, relative_path: str) -> dict | None:
    """
    Safely read and parse a TOML file.

    Uses tomllib (Python 3.11+) with fallback to tomli for older versions.

    :param project: Project instance
    :param relative_path: Path relative to project root
    :return: Parsed TOML dict or None if error
    """
    try:
        if project.relative_path_exists(relative_path):
            content = project.read_file(relative_path)
            try:
                import tomllib  # Python 3.11+
                return tomllib.loads(content)
            except ImportError:
                try:
                    import tomli  # Fallback for older Python
                    return tomli.loads(content)
                except ImportError:
                    pass
    except Exception:
        pass
    return None


def parse_makefile_targets(project, relative_path: str) -> dict[str, str]:
    """
    Parse Makefile to extract targets and their descriptions.

    Looks for targets (lines matching "target:") and extracts descriptions
    from comments above the target.

    :param project: Project instance
    :param relative_path: Path to Makefile
    :return: Dict mapping target names to descriptions
    """
    targets = {}
    try:
        if not project.relative_path_exists(relative_path):
            return targets

        content = project.read_file(relative_path)
        lines = content.split("\n")

        # Limit to first 500 lines for performance
        lines = lines[:500]

        for i, line in enumerate(lines):
            # Match target lines (e.g., "test:" or "build:")
            # Exclude lines with = (variable assignments) and lines starting with #
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            match = re.match(r'^([a-zA-Z0-9_-]+):\s*(.*)$', stripped)
            if match:
                target = match.group(1)
                # Skip special targets
                if target in [".PHONY", ".DEFAULT_GOAL", ".SILENT"]:
                    continue

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
