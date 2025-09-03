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
   serena: uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant - ✓ Connected
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
  claude mcp add serena uvx -s user -- --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant
  ```
- Handles existing server configurations gracefully
- Makes Serena available from any terminal/directory

## Manual Installation (Alternative)

If you prefer manual installation or the automated script doesn't work:

### Claude Code CLI (Manual)
```bash
claude mcp add serena uvx -s user -- --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant
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
        "--context", "ide-assistant"
      ]
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
   uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant
   ```

3. Remove and re-add the server:
   ```bash
   claude mcp remove serena -s user
   claude mcp add serena uvx -s user -- --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant
   ```

### Configuration Issues
- **Claude Desktop**: Restart Claude Desktop after installation
- **Claude Code CLI**: The server should be available immediately
- **Permissions**: Ensure you have write permissions to the Claude configuration directories

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
4. **IDE Assistant Context**: Configured with `--context ide-assistant` for optimal Claude integration

## Usage After Installation

Once installed, Serena provides semantic code analysis tools accessible through Claude Code CLI and Claude Desktop:

- **Symbol-based code navigation**: Find functions, classes, and variables by name
- **Reference analysis**: Find all references to specific code symbols  
- **Semantic code editing**: Make precise edits using symbol-level operations
- **Code structure understanding**: Navigate complex codebases efficiently

The Serena MCP server will automatically start when Claude accesses it, with uvx handling all Python environment requirements transparently.

## Support

For issues with:
- **Serena functionality**: See the main [Serena README](README.md) and [documentation](docs/)
- **Installation scripts**: Check the verification output and troubleshooting steps above
- **MCP integration**: Refer to [Claude MCP documentation](https://docs.anthropic.com/claude/docs/mcp)