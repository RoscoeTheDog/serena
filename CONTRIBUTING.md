# Contributing to Serena

Serena is under active development. We are just discovering what it can do and where the limitations lie.

Feel free to share your learnings by opening new issues, feature requests and extensions.

## Developer Environment Setup

**IMPORTANT: Always Use Virtual Environment** - To prevent global Python namespace pollution, you MUST use the virtual environment for all development work. Never install packages globally with `pip install`.

You can have a local setup via `uv` or a docker interpreter-based setup.
The repository is also configured to seamlessly work within a GitHub Codespace. See the instructions
for the various setup scenarios below.

Independently of how the setup was done, the virtual environment can be
created and activated via `uv` (see below), and the various tasks like formatting, testing, and documentation building
can be executed using `poe`. For example, `poe format` will format the code, including the
notebooks. Just run `poe` to see the available commands.

### Python (uv) setup

**Prerequisites**: Python 3.11 or 3.12 (specified in `.python-version` file)

You can install a virtual environment with the required as follows

1. **Verify Python version**: The project requires Python 3.11.x or 3.12.x. Check your version:
   ```bash
   python --version
   ```
   If you have Python 3.13 or another incompatible version, use `uv` to manage the correct version automatically (see below).

2. **Create virtual environment** with correct Python version:
   ```bash
   # uv will automatically use Python 3.11 as specified in .python-version
   uv venv
   ```

3. **Activate the environment** (REQUIRED before any `pip` or `uv` commands):
    * On Linux/Unix/macOS or Windows with Git Bash: `source .venv/bin/activate`
    * On Windows outside of Git Bash: `.venv\Scripts\activate.bat` (in cmd/ps) or `source .venv/Scripts/activate` (in git-bash)

4. **Verify activation** - Your prompt should show `(serena)` prefix:
   ```bash
   which python  # Should show .venv/bin/python or .venv\Scripts\python.exe
   python --version  # Should show Python 3.11.x
   ```

5. **Install dependencies**:
   ```bash
   uv pip install --all-extras -r pyproject.toml -e .
   ```

### Alternative: Using `uv run` (Recommended)

Instead of manually activating the virtual environment, you can use `uv run` which automatically manages the virtual environment for you:

```bash
# Runs commands in the virtual environment automatically
uv run pytest
uv run poe format
uv run serena --help
```

This approach ensures you're always using the correct Python version and virtual environment without manual activation.

## Running Tools Locally

The Serena tools (and in fact all Serena code) can be executed without an LLM, and also without
any MCP specifics (though you can use the mcp inspector, if you want).

An example script for running tools is provided in [scripts/demo_run_tools.py](scripts/demo_run_tools.py).

## Adding a New Supported Language

See the corresponding [memory](.serena/memories/adding_new_language_support_guide.md).