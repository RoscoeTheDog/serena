# CLAUDE_MCP_INTEGRATION_SCHEMA.ref.md - MCP Server Integration Reference

> **⚠️ STATIC REFERENCE**: Read-only resource (references/)
> **Purpose**: Reference guide for MCP server integration patterns
> **Agent**: Use as context when populating instance/CLAUDE_INSTALL.md - NEVER copy this file

**Version**: 1.0.0 | **Created**: 2025-10-26 | **Purpose**: Reference guide for MCP server integration patterns
**Version**: 1.0.0 | **Created**: 2025-10-26 | **Purpose**: Reference guide for MCP server integration patterns

---

## Overview

This document provides detailed patterns and examples for integrating MCP (Model Context Protocol) servers with Claude Code CLI. Use this as a reference when implementing MCP server installation workflows.

**Audience**: AI agents implementing MCP server installation, developers creating MCP server documentation

---

## Installation States & Wizard Patterns

### State Detection

**Command**:
```bash
claude mcp list | grep {server-name}
```

**States**:

| State | Detection Pattern | User Experience |
|-------|------------------|-----------------|
| **Not Installed** | Server name not in output | Fresh installation flow |
| **User Scope (Global)** | In output + "User config" | Update/Repair/Reinstall/Cancel wizard |
| **Project Scope (Local)** | In output + "Local config" OR no "User config" mention | Migrate to global prompt |
| **Broken** | In output + "Disconnected" OR "Failed to connect" | Repair prompt |

### Wizard UI Patterns

#### Pattern 1: Update/Repair/Reinstall/Cancel (Existing User-Scoped Installation)

```
┌─────────────────────────────────────────────┐
│ MCP Server Installation Wizard             │
├─────────────────────────────────────────────┤
│                                             │
│ ✓ Found: gptr-mcp (User scope)            │
│   Status: Connected                         │
│   Command: C:\python313\python.exe          │
│   Entrypoint: C:\...\server.py              │
│   Credentials: 2 configured                 │
│                                             │
│ What would you like to do?                  │
│                                             │
│ [1] Update Configuration                    │
│     Modify credentials or file paths        │
│     Current config preserved, values changed│
│     Time: ~2 minutes                        │
│                                             │
│ [2] Repair Installation                     │
│     Diagnose and fix connection issues      │
│     Verifies paths, dependencies, connection│
│     Time: ~3-5 minutes                      │
│                                             │
│ [3] Reinstall Completely                    │
│     Remove existing, start fresh            │
│     Lose current config, full reconfiguration│
│     Time: ~5-10 minutes                     │
│                                             │
│ [4] Cancel                                  │
│     Keep current configuration unchanged    │
│                                             │
│ Enter choice [1-4]:                         │
└─────────────────────────────────────────────┘
```

**Implementation Notes**:
- Display masked credential counts, not values
- Show current paths to help user decision
- Estimate time for each option
- Use ASCII box drawing for visual clarity

#### Pattern 2: Migrate to Global (Project-Scoped Installation)

```
┌─────────────────────────────────────────────┐
│ Found: gptr-mcp (Project scope)            │
│                                             │
│ This server is only available in THIS       │
│ project directory. Claude Code CLI works    │
│ best with servers in USER (global) scope.   │
│                                             │
│ Migrate to User scope for global access?    │
│                                             │
│ [1] Migrate to User Scope (Recommended)    │
│     ✓ Available in all projects            │
│     ✓ Single configuration to maintain     │
│     ✓ Easier credential updates            │
│                                             │
│ [2] Keep Project-Scoped                     │
│     ⚠️  Only works in this project         │
│     ⚠️  Must reconfigure per project       │
│                                             │
│ [3] Cancel                                  │
│                                             │
│ Enter choice [1-3]:                         │
└─────────────────────────────────────────────┘
```

**Implementation Notes**:
- Explain benefits of user scope clearly
- Show trade-offs with visual indicators (✓, ⚠️)
- Recommend user scope as default choice

#### Pattern 3: Repair Broken Installation

```
┌─────────────────────────────────────────────┐
│ ⚠️  Found: gptr-mcp (Broken)               │
│     Status: Disconnected                    │
│                                             │
│ The server is configured but not working.   │
│ Common causes:                              │
│ - Files moved/deleted                       │
│ - Missing dependencies                      │
│ - Invalid credentials                       │
│                                             │
│ [1] Repair (Recommended)                    │
│     Diagnose and fix automatically          │
│     Preserves configuration where possible  │
│                                             │
│ [2] Reinstall                               │
│     Start fresh with new configuration      │
│                                             │
│ [3] Cancel                                  │
│     Leave broken (not recommended)          │
│                                             │
│ Enter choice [1-3]:                         │
└─────────────────────────────────────────────┘
```

**Implementation Notes**:
- Clearly indicate broken state with ⚠️
- List common causes to set expectations
- Recommend repair over reinstall when possible

---

## Credential Detection Patterns

### Language-Agnostic Environment Variable Patterns

**Python**:
```python
os.getenv("API_KEY")
os.environ.get("API_KEY")
os.environ.get("API_KEY", "default")
os.environ["API_KEY"]
environ["API_KEY"]
```

**Node.js/TypeScript**:
```javascript
process.env.API_KEY
process.env.API_KEY || 'default'
process.env['API_KEY']
const { API_KEY } = process.env
```

**Go**:
```go
os.Getenv("API_KEY")
os.LookupEnv("API_KEY")
val, ok := os.LookupEnv("API_KEY")
```

**Rust**:
```rust
env::var("API_KEY")
std::env::var("API_KEY")
env::var("API_KEY").unwrap()
env::var("API_KEY").unwrap_or_default()
```

**Ruby**:
```ruby
ENV["API_KEY"]
ENV['API_KEY']
ENV.fetch("API_KEY")
ENV.fetch("API_KEY", "default")
```

**PHP**:
```php
getenv("API_KEY")
$_ENV["API_KEY"]
$_ENV['API_KEY']
$_SERVER["API_KEY"]
```

**General Config Files**:
```
# Look for UPPERCASE_SNAKE_CASE in:
.env, .env.example, .env.template, example.env
config.json, config.example.json, settings.json
application.yml, config.yml
```

### Conventional Naming Recognition

**Sensitive Credentials** (Always mask):
```
Pattern: *_API_KEY, *_KEY, *_TOKEN, *_SECRET, *_PASSWORD
Examples:
- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- GITHUB_TOKEN
- GITHUB_PERSONAL_ACCESS_TOKEN
- JWT_SECRET
- DATABASE_PASSWORD
- OAUTH_CLIENT_SECRET

Display as: sk-****...****Qhm (first 4 + last 3 chars)
```

**Configuration Values** (OK to show):
```
Pattern: *_URL, *_ENDPOINT, *_HOST, *_PORT, *_TIMEOUT, *_MAX_*
Examples:
- DATABASE_URL
- API_ENDPOINT
- REDIS_HOST
- SERVER_PORT
- REQUEST_TIMEOUT
- MAX_CONNECTIONS

Display as: Full value (postgres://localhost:5432/db)
```

**Unknown Patterns** (Prompt user):
```
"Is {CREDENTIAL} a sensitive value (API key, token, password)? [Y/N]"

Y → Treat as sensitive (mask display)
N → Treat as configuration (show full value)
```

---

## Credential Elicitation Flow

### Step-by-Step Pattern

```
For each credential in [required_credentials]:

  ┌─ Step 1: Check System Environment ────────┐
  │                                            │
  │ Checking system environment for            │
  │ {CREDENTIAL}...                            │
  │                                            │
  │ # Windows (CMD)                            │
  │ > echo %{CREDENTIAL}%                      │
  │                                            │
  │ # Windows (PowerShell)                     │
  │ > $env:{CREDENTIAL}                        │
  │                                            │
  │ # macOS/Linux (Bash/Zsh)                   │
  │ > echo ${CREDENTIAL}                       │
  │                                            │
  └────────────────────────────────────────────┘

  Result: ✓ Found | ✗ Not found

  ┌─ Step 2: Elicit Value (if found) ─────────┐
  │                                            │
  │ ✓ {CREDENTIAL} found in system environment│
  │                                            │
  │ Use existing system value? [Y/N]           │
  │                                            │
  │ Y → Using existing value                   │
  │     (value not displayed for security)     │
  │                                            │
  │ N → Please enter new value:                │
  │     [Masked input: ●●●●●●●●●●●●]           │
  │     ✓ Received: sk-****...****Qhm         │
  │                                            │
  └────────────────────────────────────────────┘

  ┌─ Step 2: Elicit Value (if not found) ─────┐
  │                                            │
  │ ✗ {CREDENTIAL} not found in system        │
  │                                            │
  │ Please provide {CREDENTIAL}:               │
  │ [Masked input: ●●●●●●●●●●●●]               │
  │                                            │
  │ ✓ Received: sk-****...****Qhm             │
  │                                            │
  └────────────────────────────────────────────┘

  ┌─ Step 3: System Environment Setup ────────┐
  │                                            │
  │ Add {CREDENTIAL} to system environment     │
  │ variables for future use? [Y/N]            │
  │                                            │
  │ Benefits:                                  │
  │ ✓ Available to all applications           │
  │ ✓ Centralized credential management       │
  │ ✓ Easier to update across projects        │
  │                                            │
  │ Note: Claude Code CLI will still store     │
  │       the literal value in ~/.claude.json  │
  │                                            │
  └────────────────────────────────────────────┘

  If Y → Show platform-specific instructions

  ┌─ Step 4: Platform Instructions ───────────┐
  │                                            │
  │ Windows (PowerShell - Recommended):        │
  │                                            │
  │ [Environment]::SetEnvironmentVariable(     │
  │   "{CREDENTIAL}",                          │
  │   "your-value-here",                       │
  │   "User"                                   │
  │ )                                          │
  │                                            │
  │ Then restart terminal:                     │
  │ > exit                                     │
  │                                            │
  │ ─────────────────────────────────────────  │
  │                                            │
  │ macOS/Linux (Bash):                        │
  │                                            │
  │ echo 'export {CREDENTIAL}="value"' >> \    │
  │   ~/.bashrc                                │
  │ source ~/.bashrc                           │
  │                                            │
  │ ─────────────────────────────────────────  │
  │                                            │
  │ macOS/Linux (Zsh):                         │
  │                                            │
  │ echo 'export {CREDENTIAL}="value"' >> \    │
  │   ~/.zshrc                                 │
  │ source ~/.zshrc                            │
  │                                            │
  └────────────────────────────────────────────┘

End for-loop

┌─ Important Security Note ──────────────────┐
│                                            │
│ ⚠️  IMPORTANT: Environment Variable Behavior│
│                                            │
│ Claude Code CLI stores LITERAL VALUES in   │
│ ~/.claude.json (not variable references).  │
│                                            │
│ This means:                                │
│ • System env vars are READ ONCE at config  │
│ • Actual values STORED in ~/.claude.json   │
│ • Changing env vars later requires re-run  │
│                                            │
│ Security:                                  │
│ • ~/.claude.json contains sensitive data   │
│ • Never commit ~/.claude.json to git       │
│ • Protect: chmod 600 ~/.claude.json (Unix) │
│                                            │
└────────────────────────────────────────────┘
```

---

## Configuration Generation Patterns

### Platform-Specific Path Handling

**Windows**:
```bash
# Runtime detection
where python
where node
where python3

# Path format (double backslashes for JSON escaping)
"command": "C:\\python313\\python.exe"
"args": ["C:\\Users\\Admin\\Documents\\GitHub\\project\\server.py"]
```

**macOS/Linux**:
```bash
# Runtime detection
which python3
which node
which python

# Path format (forward slashes)
"command": "/usr/local/bin/python3"
"args": ["/Users/admin/Documents/GitHub/project/server.py"]
```

### Command Template

```bash
claude mcp add-json --scope user {server-name} '{
  "type": "stdio",
  "command": "{absolute-runtime-path}",
  "args": ["{absolute-entrypoint-path}"],
  "env": {
    "{CREDENTIAL_1}": "{actual-value-1}",
    "{CREDENTIAL_2}": "{actual-value-2}"
  }
}'
```

**Key Requirements**:
- ✅ **Always** use `--scope user` for global availability
- ✅ **Always** use absolute paths (no `~`, no `.`, no relative paths)
- ✅ **Always** escape backslashes in Windows paths (`C:\\` not `C:\`)
- ✅ **Always** use actual credential values (no `${VAR}` or `%VAR%`)
- ⚠️  Credentials are stored as **plaintext** in `~/.claude.json`

### Verification Pattern

```bash
# Step 1: Verify server appears in list
claude mcp list

Expected output line:
{server-name}: ✓ Connected (User scope)

# Step 2: Get detailed configuration
claude mcp get {server-name}

Expected output:
{server-name}:
  Scope: User config (available in all your projects)
  Status: ✓ Connected
  Type: stdio
  Command: {runtime-path}
  Args: {entrypoint-path}
  Environment:
    {CREDENTIAL_1}: {masked-value}
    {CREDENTIAL_2}: {masked-value}

# Step 3: Test in Claude Code CLI
# User must restart CLI if currently running
claude
/mcp

Expected: {server-name} listed with available tools
```

---

## Troubleshooting Patterns

### Diagnostic Commands

**Check if server is registered**:
```bash
claude mcp list | grep {server-name}

Not found → Run installation
Found → Check details with: claude mcp get {server-name}
```

**Check server scope**:
```bash
claude mcp get {server-name} | grep "Scope"

"User config" → ✓ Global (correct)
"Local config" OR no "User" → ⚠️ Project-scoped (need to migrate)
```

**Check connection status**:
```bash
claude mcp get {server-name} | grep "Status"

"Connected" → ✓ Working
"Disconnected" → ✗ Broken (need repair)
```

**Verify runtime exists**:
```bash
# Windows
C:\python313\python.exe --version
where python

# macOS/Linux
/usr/local/bin/python3 --version
which python3
```

**Verify entrypoint exists**:
```bash
# Windows
dir C:\Users\Admin\Documents\GitHub\project\server.py

# macOS/Linux
ls /Users/admin/Documents/GitHub/project/server.py
```

**Check debug logs**:
```bash
# macOS/Linux
tail -f ~/.claude/debug/*.txt | grep {server-name}

# Windows (PowerShell)
Get-Content -Path ~/.claude/debug/*.txt -Tail 50 -Wait | Select-String "{server-name}"
```

**Test server manually**:
```bash
# Run server directly to see errors
{runtime-path} {entrypoint-path}

# Should start without errors
# Press Ctrl+C to stop
```

### Common Issues & Resolutions

**Issue Matrix**:

| Symptom | Diagnosis | Resolution |
|---------|-----------|------------|
| Not in `/mcp` list | Not registered | Run installation |
| In list, project scope | Wrong scope | `claude mcp remove {name} -s local` then re-add with `--scope user` |
| Status: Disconnected | Runtime missing | Verify runtime path exists, update config |
| Status: Disconnected | Entrypoint missing | Verify entrypoint exists, update config |
| Status: Disconnected | Missing dependencies | Install dependencies: `pip install -r requirements.txt` |
| Status: Disconnected | Invalid credentials | Re-run installation, choose "Update Configuration" |
| Tools fail with auth error | Credential expired | Re-run installation, update credentials |
| Changes not taking effect | CLI not restarted | Exit and restart: `exit` then `claude` |

---

## Update & Maintenance Patterns

### Updating Credentials

**Recommended Flow**:
```
1. User: "Update MCP server configuration"
2. Agent: Reads INSTALL.md
3. Agent: Runs claude mcp list | grep {server-name}
4. Agent: Detects existing installation
5. Agent: Shows Update/Repair/Reinstall/Cancel wizard
6. User: Chooses [1] Update Configuration
7. Agent: Runs claude mcp get {server-name}
8. Agent: Parses current config
9. Agent: Shows masked credentials
10. For each credential:
    Agent: "Update {CREDENTIAL}? [Y/N]"
    If Y: "Enter new value:" [masked input]
    If N: Keep current (don't show value)
11. Agent: Generates new claude mcp add-json command
12. Agent: Executes: claude mcp remove {server-name} && claude mcp add-json ...
13. Agent: Verifies: claude mcp get {server-name}
14. Agent: "✓ Configuration updated! Restart Claude Code CLI."
```

### Repairing Installation

**Diagnostic Flow**:
```
1. Verify runtime path exists
   → Not found: Prompt for new runtime path

2. Verify entrypoint exists
   → Not found: Check if project moved, prompt for new path

3. Test connection manually
   → {runtime-path} {entrypoint-path}
   → Capture errors

4. Diagnose errors:
   → ModuleNotFoundError: Install dependencies
   → AuthenticationError: Update credentials
   → FileNotFoundError: Update paths
   → Other: Show error, suggest solutions

5. Apply fixes

6. Update configuration if needed

7. Verify: claude mcp get {server-name}
   → Status should be "Connected"
```

---

## Security Best Practices

### Credential Protection

**File Permissions**:
```bash
# macOS/Linux
chmod 600 ~/.claude.json
ls -la ~/.claude.json
# Should show: -rw------- (owner read/write only)

# Windows (PowerShell)
icacls $env:USERPROFILE\.claude.json /inheritance:r /grant:r "$env:USERNAME:(F)"
# Removes inheritance, grants full control to current user only
```

**Git Protection**:
```bash
# Add to global gitignore (if ~/.claude.json accidentally copied to project)
echo "~/.claude.json" >> ~/.gitignore_global
git config --global core.excludesfile ~/.gitignore_global

# Check if accidentally committed
git log --all --full-history -- "*/.claude.json"
# If found, remove from history (careful!)
```

**Credential Rotation**:
```
When rotating API keys:
1. Update credentials at provider (OpenAI, Tavily, etc.)
2. Re-run installation with new values
   → Choose "Update Configuration"
   → Provide new credential values
3. Test functionality immediately
4. Revoke old credentials at provider

Frequency:
- Quarterly for normal use
- Immediately if compromised
- After team member changes
```

---

## Examples by Language/Architecture

### Example 1: Python-based MCP Server (FastMCP)

**Detected From**:
- File: `server.py`
- Import: `from fastmcp import FastMCP`
- Runtime: Python 3.11+
- Dependencies: `requirements.txt`

**Configuration**:
```bash
# Windows
claude mcp add-json --scope user my-mcp-server '{
  "type":"stdio",
  "command":"C:\\python313\\python.exe",
  "args":["C:\\Users\\Admin\\Projects\\my-mcp-server\\server.py"],
  "env":{
    "OPENAI_API_KEY":"sk-proj-...",
    "API_ENDPOINT":"https://api.example.com"
  }
}'

# macOS/Linux
claude mcp add-json --scope user my-mcp-server '{
  "type":"stdio",
  "command":"/usr/local/bin/python3",
  "args":["/Users/admin/Projects/my-mcp-server/server.py"],
  "env":{
    "OPENAI_API_KEY":"sk-proj-...",
    "API_ENDPOINT":"https://api.example.com"
  }
}'
```

### Example 2: Node.js-based MCP Server

**Detected From**:
- File: `index.js` or `server.js`
- Import: `require('@modelcontextprotocol/sdk')`
- Runtime: Node.js 18+
- Dependencies: `package.json`

**Configuration**:
```bash
# Windows
claude mcp add-json --scope user node-mcp-server '{
  "type":"stdio",
  "command":"C:\\Program Files\\nodejs\\node.exe",
  "args":["C:\\Users\\Admin\\Projects\\node-mcp-server\\index.js"],
  "env":{
    "API_KEY":"abc123...",
    "DATABASE_URL":"postgres://localhost:5432/db"
  }
}'

# macOS/Linux
claude mcp add-json --scope user node-mcp-server '{
  "type":"stdio",
  "command":"/usr/local/bin/node",
  "args":["/Users/admin/Projects/node-mcp-server/index.js"],
  "env":{
    "API_KEY":"abc123...",
    "DATABASE_URL":"postgres://localhost:5432/db"
  }
}'
```

### Example 3: Go-based MCP Server (Compiled Binary)

**Detected From**:
- File: `main.go`
- Import: `import "github.com/modelcontextprotocol/..."`
- Runtime: Compiled binary
- Build: `go build -o mcp-server`

**Configuration**:
```bash
# Windows (after build)
claude mcp add-json --scope user go-mcp-server '{
  "type":"stdio",
  "command":"C:\\Users\\Admin\\Projects\\go-mcp-server\\mcp-server.exe",
  "args":[],
  "env":{
    "API_TOKEN":"token123..."
  }
}'

# macOS/Linux (after build)
claude mcp add-json --scope user go-mcp-server '{
  "type":"stdio",
  "command":"/Users/admin/Projects/go-mcp-server/mcp-server",
  "args":[],
  "env":{
    "API_TOKEN":"token123..."
  }
}'
```

---

## Template Metadata

**Version**: 1.0.0
**Created**: 2025-10-26
**Purpose**: Reference guide for MCP server integration patterns
**Maintained By**: Claude Code Tooling Project
**License**: Use freely

---

**End of CLAUDE_MCP_TEMPLATE.md**
