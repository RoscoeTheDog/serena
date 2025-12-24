# Serena MCP Server - Automated Installation

> **For Claude Code**: This file contains complete installation instructions that Claude Code can execute automatically. Simply ask Claude Code to "read @INSTALL.md and install the Serena MCP server".

## Instructions for Future Agent Updates

**File Purpose**: The INSTALL.md file serves as a comprehensive, automated installation guide for setting up the Serena MCP server from the local directory in a **containerized and portable manner** while remaining **globally accessible** to Claude Code via `claude mcp list`.

**Core Requirements When Updating This File**:

### 🎯 **Cross-Platform Support**
- **Windows**: PowerShell, Command Prompt, Git Bash, WSL
- **macOS**: zsh, bash, fish shells
- **Linux**: bash, zsh, fish, sh shells
- **Detection Logic**: Automatically detect platform and available shells

### 🔄 **Graceful Degradation Hierarchy**
1. **Primary**: Full automated installation with environment detection
2. **Secondary**: Manual commands with platform-specific instructions
3. **Tertiary**: Basic installation with user-guided steps
4. **Fallback**: Error messages with troubleshooting links

### 📦 **Dependency Management**
- **Auto-Detection**: Check for required tools (uvx, Python, Node.js)
- **Default Locations**: Install dependencies to system defaults unless specified
- **Graceful Handling**: Provide alternative methods if standard installation fails
- **Version Verification**: Ensure minimum required versions are met

### 🔧 **Environment Variable Management**
- **Set Variables**: Use platform-appropriate methods for persistent environment variables
- **Shell Refresh**: Force shell environment reload with fallback methods:
  1. `source ~/.bashrc` / `source ~/.zshrc` / equivalent
  2. `exec $SHELL` to restart shell session
  3. Prompt user to open new terminal/shell
  4. **Final Fallback**: Instruct user to log out/in or restart machine

### 🏗️ **Installation Architecture**
- **Containerized**: All server files remain in project directory
- **Portable**: Installation works when project is moved/cloned
- **Global Registration**: Server appears in `claude mcp list` regardless of current directory
- **Self-Contained**: No pollution of global system directories

### 🛡️ **Error Handling Standards**
- **Validation**: Verify each step before proceeding
- **Rollback**: Provide cleanup instructions for failed installations
- **Clear Messaging**: User-friendly error messages with next steps
- **Logging**: Capture installation progress for debugging

### 🔒 **Security & Validation**
- **Token Security**: Never log or expose API keys in plain text
- **Binary Verification**: Validate built binaries before execution
- **File Permissions**: Set appropriate permissions for executables and config files
- **Input Sanitization**: Validate all user inputs and paths

### 📦 **Version & Conflict Management**
- **Existing Installation Detection**: Check for and handle existing installations gracefully
- **Version Compatibility**: Verify compatibility with current Claude Code version
- **Update Procedures**: Provide clear upgrade paths from previous versions
- **Rollback Support**: Enable reverting to previous working state on failure

### 🌐 **Network & Enterprise Support**
- **Proxy Detection**: Auto-detect and configure for corporate proxies
- **Offline Mode**: Support installation without internet access when possible
- **Administrator Privileges**: Handle elevation requests appropriately per platform
- **Firewall Considerations**: Document required network access and ports

### 📊 **User Experience & Feedback**
- **Progress Indicators**: Show installation progress with estimated completion times
- **Verbose Mode**: Provide detailed logging when `--verbose` or `--debug` flags used
- **Success Validation**: Include functional tests beyond just registration check
- **Clear Next Steps**: Provide actionable post-installation guidance

### 🔧 **Integration & Testing**
- **CI/CD Support**: Include flags for automated/headless installation
- **Health Checks**: Implement startup validation and connectivity tests
- **Performance Benchmarks**: Include optional performance validation
- **Log Management**: Define log locations, rotation, and cleanup procedures

### 🏗️ **Development Considerations**
- **Local Build Support**: Handle installation from local development builds
- **Debug Modes**: Support development/debug installation variants
- **Temporary File Cleanup**: Ensure proper cleanup of build artifacts and temp files
- **Parallel Installation**: Handle multiple concurrent installation attempts safely

**Always maintain backward compatibility and test across all supported platforms when making updates.**

# Serena MCP Server Installation Guide

This guide provides automated installation scripts for setting up the Serena MCP server globally on your system, making it accessible from both Claude Desktop and Claude Code CLI from any directory.

## Quick Installation

### Prerequisites

- **Python**: Python 3.11.x is recommended (uvx will handle this automatically)
- **uvx**: Install uv/uvx first: `curl -LsSf https://astral.sh/uv/install.sh | sh` (Unix) or `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows)
- **Node.js**: Required for the installation script (v20+)

### Automated Installation

1. **Clone or navigate to this repository**:
   ```bash
   cd /path/to/serena
   ```

2. **Run the installation script**:
   ```bash
   node scripts/install.js
   ```

3. **Verify installation**:
   ```bash
   claude mcp list
   ```
   You should see:
   ```
   serena: uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context claude-code - ✓ Connected
   ```

## What the Installation Does

The automated installation script:

### ✅ **System Dependencies Check**
- Verifies uvx is installed and accessible
- Checks Python availability (uvx handles Python 3.11 requirements automatically)
- Validates that the Serena server can be reached via uvx

### ✅ **Claude Desktop Configuration**
- Creates/updates `claude_desktop_config.json` in the appropriate location:
  - **Windows**: `%APPDATA%\Roaming\Claude\claude_desktop_config.json`
  - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - **Linux**: `~/.config/claude/claude_desktop_config.json`
- Backs up existing configuration before making changes

### ✅ **Claude Code CLI Configuration**
- Adds Serena MCP server globally with user scope using:
  ```bash
  claude mcp add serena uvx -s user -- --from git+https://github.com/oraios/serena serena start-mcp-server --context claude-code
  ```
- Handles existing server configurations gracefully
- Makes Serena available from any terminal/directory

## Manual Installation (Alternative)

If you prefer manual installation or the automated script doesn't work:

### Claude Code CLI (Manual)
```bash
claude mcp add serena uvx -s user -- --from git+https://github.com/oraios/serena serena start-mcp-server --context claude-code
```

### Claude Desktop (Manual)
Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "serena": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/oraios/serena",
        "serena", "start-mcp-server",
        "--context", "claude-code"
      ]
    }
  }
}
```

## Local Development Installation (Fork/Clone)

When working with a local clone or fork of Serena (e.g., for development, testing merged changes, or custom modifications), use the local venv approach instead of the remote git URL.

### Step 1: Create and Install to Local Virtual Environment

```bash
# Navigate to your local Serena repository
cd /path/to/serena

# Create virtual environment with uv
uv venv .venv

# Install Serena in editable mode (includes all dependencies)
uv pip install -e .
```

### Step 2: Configure Claude Code CLI

Edit `~/.claude.json` and add/update the `mcpServers.serena` entry to use the local venv executable:

**Windows:**
```json
{
  "mcpServers": {
    "serena": {
      "type": "stdio",
      "command": "C:/Users/YourUsername/path/to/serena/.venv/Scripts/serena.exe",
      "args": [
        "start-mcp-server",
        "--context",
        "ide-assistant"
      ],
      "env": {}
    }
  }
}
```

**macOS/Linux:**
```json
{
  "mcpServers": {
    "serena": {
      "type": "stdio",
      "command": "/path/to/serena/.venv/bin/serena",
      "args": [
        "start-mcp-server",
        "--context",
        "ide-assistant"
      ],
      "env": {}
    }
  }
}
```

### Step 3: Restart Claude Code

After updating the configuration, restart Claude Code to apply the changes. Verify with:
```bash
claude mcp list
```

You should see `serena` listed as connected.

### Updating After Code Changes

When you pull new changes or modify the Serena codebase locally, reinstall to update the venv:

```bash
cd /path/to/serena
uv pip install -e .
```

Then restart Claude Code to pick up the changes.

### Why Local Venv Instead of uvx?

- **Immediate updates**: Code changes are reflected immediately after reinstall (no uvx cache issues)
- **Development workflow**: Editable install (`-e .`) allows live code changes without full reinstall
- **Reliability**: Direct executable path avoids uvx path resolution issues on Windows
- **Debugging**: Easier to debug with local source code and venv

### Switching Back to Remote

To switch back to the upstream remote version:

```json
{
  "mcpServers": {
    "serena": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/oraios/serena",
        "serena",
        "start-mcp-server",
        "--context",
        "ide-assistant"
      ],
      "env": {}
    }
  }
}
```

## Configuration Options

The installation script supports optional configuration via `scripts/install-config.json`:

```json
{
  "embeddingProvider": "OpenAI",
  "embeddingModel": "text-embedding-3-small",
  "apiKeys": {
    "openai": ""
  },
  "verbose": false
}
```

**Note**: Serena uses uvx which manages its own dependencies, so additional API keys are typically not required for basic functionality.

## Verification

### Test Installation
```bash
# Run the verification script
node scripts/verify.js
```

### Manual Testing
```bash
# Check MCP servers are listed
claude mcp list

# Test from different directories
cd ~/Desktop
claude mcp list

cd /tmp
claude mcp list
```

Both tests should show Serena as connected.

## Troubleshooting

### uvx Not Found
Install uv/uvx first:
- **Unix/Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows**: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

### Python Version Issues
The Serena project requires Python 3.11.x, but uvx handles this automatically. You don't need to manually install Python 3.11 if uvx is working.

### Server Not Connecting
1. Verify uvx can access Serena:
   ```bash
   uvx --from git+https://github.com/oraios/serena serena --help
   ```

2. Check if the server starts manually:
   ```bash
   uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context claude-code
   ```

3. Remove and re-add the server:
   ```bash
   claude mcp remove serena -s user
   claude mcp add serena uvx -s user -- --from git+https://github.com/oraios/serena serena start-mcp-server --context claude-code
   ```

### Configuration Issues
- **Claude Desktop**: Restart Claude Desktop after installation
- **Claude Code CLI**: The server should be available immediately
- **Permissions**: Ensure you have write permissions to the Claude configuration directories

### Local Development Issues

If using a local fork/clone and the server won't connect:

1. **Verify the venv exists and has serena installed**:
   ```bash
   # Windows
   ls /path/to/serena/.venv/Scripts/serena.exe

   # macOS/Linux
   ls /path/to/serena/.venv/bin/serena
   ```

2. **Reinstall to ensure latest code**:
   ```bash
   cd /path/to/serena
   uv pip install -e .
   ```

3. **Test the server starts manually**:
   ```bash
   # Windows
   /path/to/serena/.venv/Scripts/serena.exe start-mcp-server --context ide-assistant

   # macOS/Linux
   /path/to/serena/.venv/bin/serena start-mcp-server --context ide-assistant
   ```
   The server should start and wait for input (Ctrl+C to stop).

4. **Check path format in ~/.claude.json**:
   - Windows paths should use forward slashes: `C:/Users/...` (not backslashes)
   - Paths must be absolute (not relative like `./serena`)

5. **Verify the JSON is valid**:
   ```bash
   python -m json.tool ~/.claude.json > /dev/null && echo "Valid JSON" || echo "Invalid JSON"
   ```

## Uninstallation

To remove Serena MCP server:

```bash
# Remove from Claude Code CLI
claude mcp remove serena -s user

# Manually edit Claude Desktop config to remove the serena section
```

## Architecture

This installation creates:

1. **Global Configuration**: Serena is configured with user scope (`-s user`) making it available from any directory
2. **Cross-Platform**: Works on Windows, macOS, and Linux
3. **uvx Integration**: Uses uvx to handle Python dependencies and Serena execution automatically
4. **Claude Code Context**: Configured with `--context claude-code` for optimal Claude integration

> **Migration Note**: If you previously used `--context ide-assistant`, it will continue to work with a deprecation warning. We recommend updating to `claude-code` for consistency with upstream naming conventions.

## Installation Features

✅ **Self-contained**: Server files managed by uvx automatically  
✅ **User-scoped**: Registered to user config, not global  
✅ **Portable**: Works when project is moved (uvx handles dependencies)  
✅ **Secure**: Uses standard uvx package management  
✅ **Cross-platform**: Works on Windows, macOS, and Linux
✅ **Agent-Ready**: Includes CLAUDE_INIT.md for optimized agent initialization

## Usage After Installation

Once installed, Serena provides semantic code analysis tools accessible through Claude Code CLI and Claude Desktop:

- **Symbol-based code navigation**: Find functions, classes, and variables by name
- **Reference analysis**: Find all references to specific code symbols  
- **Semantic code editing**: Make precise edits using symbol-level operations
- **Code structure understanding**: Navigate complex codebases efficiently
- **Project Memory**: Persistent knowledge system across sessions
- **LSP Integration**: 20+ programming languages supported

The Serena MCP server will automatically start when Claude accesses it, with uvx handling all Python environment requirements transparently.

## Agent Initialization (Recommended)

This repository includes `CLAUDE_INIT.md` - a template generator that creates ultra-compressed CLAUDE.md project instructions for Claude Code agents.

### Usage

After installing the Serena MCP server:

```bash
# Generate optimized agent instructions
read @CLAUDE_INIT.md
```

**What it does:**
- Detects all registered MCP servers (Serena, claude-context, notion-mcp, github-mcp)
- Extracts live metadata (project status, memory count, indexing status, etc.)
- Generates compressed CLAUDE.md with 135-155 tokens (80-82% reduction)
- Preserves 100% functionality with ultra-efficient notation

**Features:**
- **Auto-Detection**: Only includes available/registered MCPs
- **Live Metadata**: Real-time status extraction from each MCP
- **Fallback Safe**: Works even if some MCPs aren't registered
- **Token Optimized**: Compressed notation for maximum efficiency

This gives Claude Code agents immediate access to all Serena capabilities through compressed notation, dramatically improving efficiency while maintaining full functionality.

## Support

For issues with:
- **Serena functionality**: See the main [Serena README](README.md) and [documentation](docs/)
- **Installation scripts**: Check the verification output and troubleshooting steps above
- **MCP integration**: Refer to [Claude MCP documentation](https://docs.anthropic.com/claude/docs/mcp)
- **Agent optimization**: Use the included CLAUDE_INIT.md template generator