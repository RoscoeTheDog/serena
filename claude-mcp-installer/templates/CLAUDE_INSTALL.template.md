# [PROJECT_NAME] - Installation Guide

> **⚠️ TEMPLATE FILE**: Platform-agnostic generator (templates/)
> **Generated**: `instance/CLAUDE_INSTALL.md` (platform-specific, gitignored)
> **Agent**: Read `claude-mcp-installer/CLAUDE_README.md` first → Copy to instance/ → Populate placeholders

**Version**: 1.0.0 | **Updated**: [DATE] | **For**: AI-assisted + manual install



## TOC

[Overview](#overview) | [Prerequisites](#prerequisites) | [Options](#installation-options) | [MCP Integration](#mcp-server-integration) | [Setup](#step-by-step-setup) | [Environment](#environment-configuration) | [Validation](#validation) | [Troubleshooting](#troubleshooting) | [Support](#support)

---

## Overview

**About**:
- Base: [BASE_PROJECT_NAME] (if derived)
- Base Repo: `[BASE_REPO_URL]` (if applicable)
- This Repo: `[YOUR_REPO_URL]`
- Custom: [brief customizations]

**Philosophy**: Multi-path install, explicit choices (AI always prompts), platform-specific, validation-tracked, non-intrusive (user confirms all system changes)

**AI Installation Policy** (P7: Non-Intrusive Installation):
- ✅ **Agent ALWAYS prompts** before system/environment changes
- ✅ **User explicitly confirms** package installs, global config, system services
- ✅ **Transparent operations** - agent explains scope, impact, reversibility
- ✅ **Project-local changes** (venv, .env, project files) - OK without prompt
- ❌ **NEVER auto-install** packages or modify system without approval

**What Requires Confirmation**:
```
System Changes (PROMPT REQUIRED):
├─ Package installation (pip, npm, apt, brew)
├─ Global environment variables (system-wide)
├─ Service installation (databases, runtimes)
├─ MCP server registration (global Claude Code config)
└─ PATH modifications, registry edits

Project Changes (NO PROMPT NEEDED):
├─ .env file creation/editing (project-local)
├─ Virtual environment setup (project-local)
├─ Installing deps in active venv (project-scoped)
└─ Config files within project directory
```

---

## Prerequisites

### Required

#### Python [PYTHON_VERSION]+ ✅WML
- **Reason**: [PROJECT_NAME] requires Python [PYTHON_VERSION]+
- **Validation**: ✅W11, ✅M14, ✅U22.04
- **Install**:
  - W: [python.org](https://python.org/downloads/)
  - M: `brew install python@[PYTHON_VERSION]`
  - L: `sudo apt install python[PYTHON_VERSION] python[PYTHON_VERSION]-venv`
- **Verify**: `python --version` (should show [PYTHON_VERSION]+)

#### Git ✅WML
- **Install**:
  - W: [git-scm.com](https://git-scm.com/)
  - M: `brew install git` | Xcode CLI Tools
  - L: `sudo apt install git`

### Optional

#### [OPTIONAL_DEP] ⚠️
- **Reason**: [why needed]
- **Required-For**: [specific features]
- **Validation**: ⚠️ Needs testing

---

## Installation Options

Wizard-style: Choose per component. Agent prompts, never assumes.

### Database Setup

**Prompt**: "Which database method?"

#### Opt1: [DATABASE] Cloud ✅W11+M14
- **Best**: Quick, no local install
- **Pros**: Managed, no maintenance, remote-access
- **Cons**: Internet required, cost-after-free-tier
- **Time**: 5-10min
- **Validation**: ✅W11, ✅M14

#### Opt2: [DATABASE] Local ⚠️
- **Best**: Offline dev, full control
- **Pros**: No internet, free, full-control
- **Cons**: Local install + maintenance
- **Time**: 15-30min
- **Validation**: ⚠️ Needs validation

#### Opt3: [DATABASE] Docker ✅WML
- **Best**: Isolated env, easy cleanup
- **Pros**: Containerized, reproducible, easy-reset
- **Cons**: Docker required
- **Time**: 10-15min
- **Validation**: ✅ All platforms

---

## MCP Server Integration

> **Note**: This section applies only if this project is an MCP server. Skip if not applicable.

**Purpose**: Configure this MCP server for global availability in Claude Code CLI

**When to Use**: After completing base installation, use this to register the MCP server with Claude Code CLI for use across all projects.

### Prerequisites

- ✅ Claude Code CLI installed (`claude --version`)
- ✅ Base project dependencies installed (see [Step-by-Step Setup](#step-by-step-setup))
- ✅ Required credentials available (see below)

### Installation Wizard

**Agent will automatically check for existing installations** before proceeding.

#### Phase 1: Pre-Installation Check

**Automatic Detection**:
```bash
# Agent runs:
claude mcp list | grep [MCP_SERVER_NAME]
```

**Possible States**:

| State | Description | Action |
|-------|-------------|--------|
| **Not Installed** | Server not found in list | ✅ Proceed with fresh installation |
| **User Scope** | Already installed globally | ⚙️  Show Update/Repair/Reinstall/Cancel wizard |
| **Project Scope** | Installed locally only | 🔄 Prompt to migrate to global scope |
| **Broken** | In list but disconnected | 🔧 Prompt to repair installation |

**If Already Installed**:
```
┌─────────────────────────────────────────────┐
│ MCP Server Installation Wizard             │
├─────────────────────────────────────────────┤
│                                             │
│ ✓ Found: [MCP_SERVER_NAME] (User scope)   │
│   Status: Connected                         │
│   Command: [current-command]                │
│   Entrypoint: [current-entrypoint]          │
│                                             │
│ What would you like to do?                  │
│                                             │
│ [1] Update Configuration                    │
│     → Modify credentials or paths           │
│                                             │
│ [2] Repair Installation                     │
│     → Verify files, test connection, fix    │
│                                             │
│ [3] Reinstall Completely                    │
│     → Remove and fresh install              │
│                                             │
│ [4] Cancel                                  │
│     → Keep current configuration            │
│                                             │
│ Choice [1-4]:                               │
└─────────────────────────────────────────────┘
```

**Workflow by Choice**:

- **[1] Update** → Load current config, prompt for credential changes, update & verify
- **[2] Repair** → Verify paths exist, test connection, diagnose & fix issues
- **[3] Reinstall** → Remove existing, proceed to fresh installation
- **[4] Cancel** → Exit, keep current configuration unchanged

#### Phase 2: Credential Discovery (Fresh Install or Reinstall)

**Agent will detect required credentials from**:
1. README.md sections (Prerequisites, Configuration, Environment)
2. .env.example file (credential template)
3. Code search (environment variable patterns across all languages)

**Detected Credentials**:
```
Required:
- [CREDENTIAL_1]: [description-from-readme]
- [CREDENTIAL_2]: [description-from-readme]

Optional:
- [OPTIONAL_CREDENTIAL_1]: [description-from-readme]
```

**System Environment Check**:
```bash
# Agent checks system environment for each credential

# Windows (CMD)
echo %CREDENTIAL%

# Windows (PowerShell)
$env:CREDENTIAL

# macOS/Linux
echo $CREDENTIAL
```

**Results**:
```
✓ [CREDENTIAL_1]: Found in system environment
✗ [CREDENTIAL_2]: Not found in system environment
✗ [OPTIONAL_CREDENTIAL_1]: Not found (optional)
```

**Credential Elicitation**:

For each **not found** credential:
```
Please provide [CREDENTIAL_NAME]:
[Masked input: ●●●●●●●●●●●●]

✓ Received: sk-****...****Qhm
```

For each **found** credential:
```
Use existing system value for [CREDENTIAL_NAME]? [Y/N]
→ Y: Use system value (don't show or re-enter)
→ N: Enter new value: [masked input]
```

**Optional: Add to System Environment**:
```
Would you like to add credentials to system environment variables? [Y/N]

→ Y: Agent provides platform-specific instructions
→ N: Skip (credentials stored only in ~/.claude.json)
```

**Platform-Specific Instructions** (if user wants to add to system):

<details>
<summary><strong>Windows (PowerShell - Recommended)</strong></summary>

```powershell
# Set persistent user environment variable
[Environment]::SetEnvironmentVariable("[CREDENTIAL]", "value", "User")

# Restart terminal to apply changes
exit
```
</details>

<details>
<summary><strong>Windows (GUI Method)</strong></summary>

1. Press `Win+R`, type: `sysdm.cpl`, press Enter
2. Navigate to **Advanced** tab → **Environment Variables**
3. Under **User variables**, click **New**
4. Variable name: `[CREDENTIAL]`
5. Variable value: `[value]`
6. Click **OK** → **OK** → Restart terminal
</details>

<details>
<summary><strong>macOS/Linux (Bash)</strong></summary>

```bash
# Add to ~/.bashrc or ~/.bash_profile
echo 'export [CREDENTIAL]="value"' >> ~/.bashrc
source ~/.bashrc
```
</details>

<details>
<summary><strong>macOS/Linux (Zsh)</strong></summary>

```zsh
# Add to ~/.zshrc
echo 'export [CREDENTIAL]="value"' >> ~/.zshrc
source ~/.zshrc
```
</details>

**⚠️  Important Note About Environment Variables**:
```
Even if credentials are in system environment variables,
Claude Code CLI stores LITERAL VALUES in ~/.claude.json
(not variable references like ${VAR} or %VAR%).

This means:
- System env vars are READ ONCE at configuration time
- Actual values are STORED in ~/.claude.json
- If you change env vars later, you MUST re-run installation

Security Note:
- ~/.claude.json contains sensitive data
- Never commit ~/.claude.json to git
- Protect with file permissions: chmod 600 ~/.claude.json (Unix)
```

#### Phase 3: Configure MCP Server

**Auto-Generated Configuration**:

Agent automatically detects:
- **Platform**: Windows | macOS | Linux
- **Runtime Path**: Absolute path to Python/Node/Binary
- **Entrypoint Path**: Absolute path to server file
- **Server Name**: From README, directory name, or package metadata

**Command Generated**:

**Agent Workflow** (P7: Non-Intrusive Installation):
```
Agent: "About to add MCP server to global Claude Code configuration:

        Command: claude mcp add-json --scope user [MCP_SERVER_NAME]
        Scope: User-wide (available in all your projects)
        Location: ~/.claude.json

        Configuration:
        - Runtime: [ABSOLUTE_RUNTIME_PATH]
        - Entrypoint: [ABSOLUTE_ENTRYPOINT_PATH]
        - Credentials: [list of credential names - values masked]

        This is a SYSTEM CHANGE (modifies global config).

        Proceed? [Y/N]"

User: "Y"

Agent: [Executes command below]
```

```bash
claude mcp add-json --scope user [MCP_SERVER_NAME] '{
  "type":"stdio",
  "command":"[ABSOLUTE_RUNTIME_PATH]",
  "args":["[ABSOLUTE_ENTRYPOINT_PATH]"],
  "env":{
    "[CREDENTIAL_1]":"[actual-value]",
    "[CREDENTIAL_2]":"[actual-value]",
    "[OPTIONAL_CREDENTIAL_1]":"[actual-value-or-omitted]"
  }
}'
```

**Example (Python-based server on Windows)**:
```bash
claude mcp add-json --scope user gptr-mcp '{
  "type":"stdio",
  "command":"C:\\python313\\python.exe",
  "args":["C:\\Users\\Admin\\Documents\\GitHub\\gptr-mcp\\server.py"],
  "env":{
    "OPENAI_API_KEY":"sk-proj-...",
    "TAVILY_API_KEY":"tvly-..."
  }
}'
```

**Important Configuration Notes**:
- ✅ **Always use `--scope user`** for global availability across all projects
- ✅ **Use absolute paths** for both command and entrypoint (no relative paths)
- ⚠️  **Credentials are stored literally** in `~/.claude.json` (not as env var references)
- ⚠️  **Cannot use `${VAR}` or `%VAR%`** syntax - values are expanded at config time
- 🔒 **Security**: `~/.claude.json` contains plaintext credentials - never commit to git

#### Phase 4: Verification

**Verify Installation**:
```bash
# List all MCP servers
claude mcp list

# Should show:
[MCP_SERVER_NAME]: ✓ Connected (User scope)

# Get detailed configuration
claude mcp get [MCP_SERVER_NAME]

# Should show:
[MCP_SERVER_NAME]:
  Scope: User config (available in all your projects)
  Status: ✓ Connected
  Type: stdio
  Command: [runtime-path]
  Args: [entrypoint-path]
  Environment:
    [CREDENTIAL_1]: [masked-value]
    [CREDENTIAL_2]: [masked-value]
```

**Test in Claude Code CLI**:
```bash
# Restart Claude Code CLI (if currently running)
exit
claude

# Check MCP servers
/mcp

# Should list [MCP_SERVER_NAME] with available tools
```

#### Phase 5: Post-Installation

**For Fresh Installation**:
```
✅ Installation complete!

Summary:
- Server: [MCP_SERVER_NAME]
- Scope: User (global)
- Status: Connected
- Credentials configured: [list]

Next steps:
1. ✅ Restart Claude Code CLI (if running)
2. ✅ Run '/mcp' to see available MCP servers
3. ✅ Test tools: [list-of-available-tools]

Available tools:
- [tool-1]: [description]
- [tool-2]: [description]
- [tool-3]: [description]
```

**For Update**:
```
✅ Configuration updated!

Changes:
- [CREDENTIAL_1]: Updated
- [CREDENTIAL_2]: Unchanged

Restart Claude Code CLI to apply changes:
> exit
> claude
```

**For Repair**:
```
✅ Installation repaired!

Issues fixed:
- [issue-1]: [resolution]
- [issue-2]: [resolution]

Status: Connected
```

### Troubleshooting

#### Issue: Server not appearing in `/mcp` list

**Symptoms**: `/mcp` command doesn't show [MCP_SERVER_NAME]

**Diagnosis**:
```bash
# Check if server is registered
claude mcp list | grep [MCP_SERVER_NAME]

# If found, check details
claude mcp get [MCP_SERVER_NAME]
```

**Solutions**:
1. **Not in list at all** → Run installation again
2. **Project scope (local)** → Migrate to user scope:
   ```bash
   claude mcp remove [MCP_SERVER_NAME] -s local
   # Then re-run installation with --scope user
   ```
3. **Status: Disconnected** → See "Connection failed" issue below

#### Issue: Connection failed / Status: Disconnected

**Symptoms**: Server appears in list but shows "Disconnected" or "Failed to connect"

**Diagnosis**:
```bash
# Verify runtime exists
[runtime-command] --version

# Example (Python):
python --version
C:\python313\python.exe --version

# Verify entrypoint exists
ls [entrypoint-path]

# Example:
ls C:\Users\Admin\Documents\GitHub\[project]\server.py

# Check debug logs
tail -f ~/.claude/debug/*.txt | grep [MCP_SERVER_NAME]

# Test server manually
[runtime-command] [entrypoint-path]

# Example (Python):
python C:\Users\Admin\Documents\GitHub\[project]\server.py
# Should start without errors (Ctrl+C to stop)
```

**Common Causes & Fixes**:

1. **Missing dependencies**:
   ```
   Error: ModuleNotFoundError: No module named 'X'

   Fix: Install dependencies
   pip install -r requirements.txt
   ```

2. **Wrong runtime path**:
   ```
   Error: Command not found / File not found

   Fix: Update configuration with correct path
   - Option 1: Re-run installation (choose "Update")
   - Option 2: Manual update (see "Updating Credentials" below)
   ```

3. **Moved project directory**:
   ```
   Error: Entrypoint file not found

   Fix: Update entrypoint path
   - Re-run installation from new project location
   ```

4. **Invalid credentials**:
   ```
   Error: Authentication failed / API key invalid

   Fix: Update credentials
   - Re-run installation
   - Choose "Update Configuration"
   - Provide new credential values
   ```

#### Issue: Credential errors

**Symptoms**: Server connects but tools fail with authentication errors

**Verification**:
```bash
# Check stored credentials (masked)
claude mcp get [MCP_SERVER_NAME]

# Shows:
Environment:
  [CREDENTIAL]: [masked-value]
```

**Solution**:
```
# Re-run installation to update credentials
# Agent will detect existing installation
# Choose [1] Update Configuration
# Select credentials to update
# Provide new values
```

#### Issue: Changes not taking effect

**Symptoms**: Updated configuration but still using old values

**Solution**:
```bash
# Claude Code CLI must be restarted to reload config
exit

# Start new session
claude

# Verify changes applied
claude mcp get [MCP_SERVER_NAME]
```

### Updating Credentials Later

**If credentials change** (API key rotated, new service, etc.):

**Method 1: Re-run Installation (Recommended)**:
```
1. Navigate to project directory
2. Tell agent: "Read INSTALL.md and update MCP server configuration"
3. Agent detects existing installation
4. Choose [1] Update Configuration
5. For each credential: "Update? [Y/N]"
   → Y: Enter new value
   → N: Keep current
6. Agent reconfigures automatically
7. Restart Claude Code CLI
```

**Method 2: Manual Update**:
```bash
# Step 1: Remove existing configuration
claude mcp remove [MCP_SERVER_NAME]

# Step 2: Re-add with new credentials
claude mcp add-json --scope user [MCP_SERVER_NAME] '{
  "type":"stdio",
  "command":"[runtime-path]",
  "args":["[entrypoint-path]"],
  "env":{
    "[CREDENTIAL_1]":"[new-value]",
    "[CREDENTIAL_2]":"[new-value]"
  }
}'

# Step 3: Verify
claude mcp get [MCP_SERVER_NAME]

# Step 4: Restart Claude Code CLI
exit
claude
```

### Security Best Practices

1. **Protect ~/.claude.json**:
   ```bash
   # Unix/macOS
   chmod 600 ~/.claude.json

   # Windows (PowerShell)
   icacls $env:USERPROFILE\.claude.json /inheritance:r /grant:r "$env:USERNAME:(F)"
   ```

2. **Never commit credentials**:
   - Add to .gitignore: `~/.claude.json` (if accidentally copied)
   - Use `.env` files for local development
   - Keep API keys in environment variables when possible

3. **Rotate credentials regularly**:
   - Update MCP server config when rotating keys
   - Test after rotation to ensure functionality

4. **Use least-privilege credentials**:
   - API keys should have minimal required permissions
   - Create service-specific keys when possible

---

## Step-by-Step Setup

### S1: Clone

```bash
git clone [YOUR_REPO_URL]
cd [project-directory]
```

### S2: Virtual Environment

```bash
# Create
python -m venv venv

# Activate
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# Verify
where python                 # Windows
which python                 # macOS/Linux
```

### S3: Dependencies

**Agent Workflow** (P7: Non-Intrusive Installation):
```
Agent: "I need to install dependencies from requirements.txt:
        [Lists packages and versions from requirements.txt]

        This will run: pip install -r requirements.txt
        Scope: Project-local (in your active virtual environment)
        Impact: Adds packages to venv only (not system-wide)

        Proceed? [Y/N]"

User: "Y"

Agent: [Executes installation]
```

**Manual Installation**:
```bash
pip install -r requirements.txt
```

### S4: Database (Interactive)

**Prompt**: "Which method?" (see [Options](#installation-options))

#### If Opt1: Cloud

1. **Account**: Visit [CLOUD_URL], sign up, create instance
2. **Connection**: Copy URI (`neo4j+s://xxx.databases.neo4j.io`), username (`neo4j`), password
3. **Env** (see [Environment](#environment-configuration)):
   ```bash
   DATABASE_URI=neo4j+s://xxx.databases.neo4j.io
   DATABASE_USER=neo4j
   DATABASE_PASSWORD=your_password
   ```

#### If Opt2: Local

**W**:
1. Download installer from [URL]
2. Run, choose "Windows Service"
3. Set admin password
4. Verify: `sc query [SERVICE]`
5. Env: `DATABASE_URI=bolt://localhost:7687`, user/pass as set

**M**:
```bash
brew install [DATABASE]
brew services start [DATABASE]
# Env same as Windows local
```

**L**:
```bash
[LINUX_INSTALL_COMMANDS]
# Env same as Windows local
```

#### If Opt3: Docker

```bash
docker run -d \
  --name [PROJECT]-db \
  -p 7687:7687 -p 7474:7474 \
  -e [DATABASE]_AUTH=[DATABASE]/your_password \
  [DATABASE_DOCKER_IMAGE]

# Env
DATABASE_URI=bolt://localhost:7687
DATABASE_USER=[DATABASE]
DATABASE_PASSWORD=your_password
```

### S5: API Keys (Interactive)

**Prompt**: "Which LLM provider?"

#### [LLM_PROVIDER_1] ✅WML
1. Visit [PROVIDER_URL], sign up/login, create API key
2. Env: `[PROVIDER_1]_API_KEY=sk-xxxxx`

#### [LLM_PROVIDER_2] ⚠️
- Same process
- Env: `[PROVIDER_2]_API_KEY=xxxxx`

#### Optional: [OPTIONAL_SERVICE]
- **For**: [feature]
- **Setup**: [instructions]

---

## Environment Configuration

### Create .env

```bash
cp .env.example .env

# Edit
notepad .env                # Windows
nano .env                   # macOS/Linux
```

### Required Vars

```bash
# Database
DATABASE_URI=bolt://localhost:7687
DATABASE_USER=neo4j
DATABASE_PASSWORD=your_password

# LLM
[LLM_PROVIDER]_API_KEY=sk-your-key

# Optional
[OPTIONAL_SERVICE]_API_KEY=key  # Only if using [FEATURE]
```

### Platform-Specific

**W**: `DATA_PATH=C:\\Users\\Name\\Documents\\[PROJECT]\\data` (backslashes)
**M/L**: `DATA_PATH=/Users/Name/Documents/[PROJECT]/data` (forward-slashes)

---

## Validation

### Auto-Validation

```bash
python scripts/validate_install.py
```

**Expected**:
```
✅ Python: [PYTHON_VERSION]
✅ Dependencies: OK
✅ Database: OK
✅ API: [LLM_PROVIDER]
⚠️  Optional: [SERVICE] not configured (OK)
```

### Manual

```bash
# Database
python -c "from [MODULE] import db; db.test_connection()"

# LLM
python -c "from [MODULE] import llm; llm.test_api()"
```

---

## Troubleshooting

### Error→Fix Matrix

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: X` | Dep not installed | Verify venv active (`which python`), reinstall: `pip install -r requirements.txt --force-reinstall` |
| DB connection failed | DB not running / wrong creds | Cloud: verify URI/user/pass in .env<br>Local: Check service (`sc query [DB]` / `brew services list` / `systemctl status [DB]`)<br>Docker: `docker ps` |
| API key invalid | Wrong key / not activated | Verify in provider dashboard, check .env for spaces, verify permissions |
| Permission denied (W) | PowerShell execution policy | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `python` not found (W) | Not in PATH | Use `py` instead or add Python to PATH |
| SSL cert errors (M) | Cert issues | `pip install --upgrade certifi` |
| Missing build tools (L) | No compiler | `sudo apt install build-essential python3-dev` |

---

## Next Steps

After install:
1. **Docs**: [DOCS_URL]
2. **Examples**: `examples/` directory
3. **Community**: [DISCORD_URL]
4. **Contribute**: CONTRIBUTING.md

### For Devs

- Read `CLAUDE_README.md` (dev policies)
- Setup hooks: `pre-commit install`
- Run tests: `pytest tests/`

---

## Changelog

See [CLAUDE_INSTALL_CHANGELOG.md](./CLAUDE_INSTALL_CHANGELOG.md)

---

## Support

- Issues: `[REPO_URL]/issues`
- Discussions: `[REPO_URL]/discussions`
- Base: `[BASE_REPO_URL]` (if derived)

---

**Template**: v1.3.0 | **Guide**: v1.0.0
