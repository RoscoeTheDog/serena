# Scripts Directory

This directory contains utility scripts for Serena development, installation, and maintenance.

## Installation & Configuration

### `install.js`
Node.js script for automated Serena installation and configuration.
- Detects platform and environment
- Configures MCP server settings
- Sets up initial project structure

**Usage**:
```bash
node scripts/install.js
```

### `verify.js`
Verification script to validate Serena installation and configuration.
- Checks dependencies
- Verifies MCP server configuration
- Tests basic functionality

**Usage**:
```bash
node scripts/verify.js
```

### `install-config.json`
Configuration file for the installation script containing platform-specific settings.

## Migration & Legacy Support

### `migrate_legacy_serena.py`
Migration script for moving from legacy `.serena/` project-root storage to centralized `~/.serena/projects/` storage.
- Migrates memories, configuration, and cache
- Creates backups before migration
- Supports dry-run mode for testing

**Usage**:
```bash
# Dry run (preview changes)
python scripts/migrate_legacy_serena.py --dry-run /path/to/project

# Actual migration
python scripts/migrate_legacy_serena.py /path/to/project
```

**Related**: See Story 1 from the legacy-serena-removal sprint (commit 413df77)

## Process Management

### `kill_serena_servers.py`
Python script to terminate all running Serena MCP server processes.
- Cross-platform support
- Finds processes by name and command line
- Graceful shutdown with fallback to forced termination

**Usage**:
```bash
python scripts/kill_serena_servers.py
```

### `kill_serena.sh`
Unix/Linux/macOS shell script for terminating Serena processes.

**Usage**:
```bash
./scripts/kill_serena.sh
```

### `kill_serena.bat`
Windows batch script for terminating Serena processes.

**Usage**:
```cmd
scripts\kill_serena.bat
```

## Development & Testing

### `demo_run_tools.py`
Demonstration script showing how to run Serena tools programmatically without MCP.
- Examples of tool usage
- Useful for testing and development
- No LLM required

**Usage**:
```bash
python scripts/demo_run_tools.py
```

### `gen_prompt_factory.py`
Generates the `PromptFactory` class from Jinja2 prompt templates.
- Auto-generates typed Python class from YAML templates
- Part of the interprompt system
- Run after modifying prompt templates

**Usage**:
```bash
python scripts/gen_prompt_factory.py
```

### `print_tool_overview.py`
Prints an overview of all available Serena tools.
- Lists tool names and descriptions
- Useful for documentation generation

**Usage**:
```bash
python scripts/print_tool_overview.py
```

### `print_mode_context_options.py`
Displays available modes and contexts for Serena configuration.
- Lists all built-in modes
- Shows available contexts
- Helps with MCP server configuration

**Usage**:
```bash
python scripts/print_mode_context_options.py
```

### `mcp_server.py`
Simple script to start the Serena MCP server directly.
- Alternative to `uv run serena start-mcp-server`
- Useful for development and debugging

**Usage**:
```bash
python scripts/mcp_server.py
```

### `agno_agent.py`
Integration script for running Serena with the Agno framework.
- Enables Serena to work with any LLM via Agno
- Provides agent-mode functionality

**Usage**:
```bash
python scripts/agno_agent.py
```

## Platform Support

Most Python scripts are cross-platform (Windows, macOS, Linux). Shell scripts (`.sh`) are for Unix-like systems, and batch scripts (`.bat`) are for Windows.

For process management, use the appropriate script for your platform:
- **Windows**: `kill_serena.bat` or `kill_serena_servers.py`
- **Unix/Linux/macOS**: `kill_serena.sh` or `kill_serena_servers.py`

## Contributing

When adding new scripts:
1. Add appropriate documentation to this README
2. Include usage examples
3. Add cross-platform support where applicable
4. Use descriptive filenames
5. Add executable permissions for shell scripts (`chmod +x`)
