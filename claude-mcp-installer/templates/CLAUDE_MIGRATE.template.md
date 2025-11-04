# CLAUDE_MIGRATE.template.md - Template Migration

> **⚠️ TEMPLATE FILE**: Platform-agnostic generator (templates/)
> **Generated**: `instance/CLAUDE_MIGRATE.md` (migration state, gitignored)
> **Agent**: Read `claude-mcp-installer/CLAUDE_README.md` first → Copy to instance/ → Execute workflow

**Version**: 1.2.0 | **Updated**: 2025-10-26 | **Purpose**: One-time template initialization with MCP server support
---

## Pre-Migration: Schema Validation (EXECUTE FIRST)

**CRITICAL**: Before executing any migration steps:

1. **Verify CLAUDE_README.md exists** (schema rules)
   ```bash
   [ -f "claude-mcp-installer/CLAUDE_README.md" ] || echo "ERROR: Schema not found"
   ```

2. **Verify directory structure**
   ```bash
   ls claude-mcp-installer/templates/*.template.md
   ls claude-mcp-installer/references/*.ref.md
   # Should exist: templates/ and references/ subdirectories
   ```

3. **Detect migration state**
   ```bash
   # Check if already migrated
   [ -d "claude-mcp-installer/instance" ] || \
   [ -f "claude-mcp-installer/CLAUDE_INSTALL.md" ] && \
   echo "Migration already complete" || echo "Fresh migration required"
   ```

4. **Create instance/ directory** (if fresh migration)
   ```bash
   mkdir -p claude-mcp-installer/instance
   echo "✅ Created instance/ directory"
   ```

5. **Copy templates to instance/**
   ```bash
   # Strip .template suffix when copying
   cp claude-mcp-installer/templates/CLAUDE_INSTALL.template.md \
      claude-mcp-installer/instance/CLAUDE_INSTALL.md
   cp claude-mcp-installer/templates/CLAUDE_MIGRATE.template.md \
      claude-mcp-installer/instance/CLAUDE_MIGRATE.md
   echo "✅ Created working copies in instance/"
   ```

6. **Setup .gitignore** (if git repo and .gitignore exists)
   ```bash
   if [ -d ".git" ] && [ -f ".gitignore" ]; then
       cat >> .gitignore << 'GITEOF'
# Generated Claude MCP Installer Documentation (platform-specific)
claude-mcp-installer/instance/
GITEOF
       echo "✅ Updated .gitignore"
   fi
   ```

**Validation Complete**: Proceed to populate instance/ files below


---

## Overview

One-time migration: generic templates → project-specific docs

**What**: Check-install-state → auto-detect → validate → prompt → replace → gen-v1.0.0 → record

**Role**: Migration wizard ONLY fills in documentation templates - does NOT install, configure, or modify the environment

**Scope Boundaries**:
- ✅ Agent READS project structure (files, configs, READMEs)
- ✅ Agent DETECTS project metadata (dependencies, credentials, MCP servers)
- ✅ Agent PROMPTS user for missing information
- ✅ Agent WRITES to documentation files (CLAUDE_INSTALL.md, CLAUDE_README.md, CLAUDE_INSTALL_CHANGELOG.md)
- ❌ Agent NEVER installs packages, modifies system config, or registers MCP servers
- ❌ Agent NEVER runs `claude mcp add`, `pip install`, or any mutation commands

**Responsibility Split**:
- **CLAUDE_MIGRATE.md** (this document): Information gathering → template population
- **CLAUDE_INSTALL.md** (installer document): User/agent follows to actually install/configure system

**MCP Support**: Detects MCP servers → validates credentials → prepares installation instructions (actual configuration happens in CLAUDE_INSTALL.md)

---

## Migration vs Installation

**This Document (CLAUDE_MIGRATE.md)**: ONE-TIME template initialization
- Gathers project information through file analysis
- Prompts user for configuration details
- Detects existing installations (for documentation reference)
- Fills in placeholders in CLAUDE_INSTALL.md
- NO system changes, NO installations, NO configurations

**Target Document (CLAUDE_INSTALL.md)**: REPEATABLE installation guide
- Created/updated by migration wizard
- Contains actual installation instructions
- Agent or user follows this to modify system
- Handles package installation, MCP server registration, environment setup

---

## Status

**Status**: `[PENDING_MIGRATION]`
**Migrated**: `[NOT_YET_MIGRATED]`
**By**: `[AGENT_INFO]`

> After migration, status auto-updates

---

## Pre-Check

**Required**:
- ✅ All templates copied (CLAUDE_README.md, CLAUDE_INSTALL.md, CLAUDE_INSTALL_CHANGELOG.md, this file)
- ✅ In project root
- ✅ Git init (if using)
- ✅ Time for prompts (5-15min)

---

## Workflow

### Phase 0: Installation State Check (MCP Projects Only)

**Purpose**: Detect existing MCP server installations before migration (wizard-style experience)

**IMPORTANT - MIGRATION SCOPE**: This phase ONLY detects and records installation state for documentation purposes. NO installation, configuration, or system changes are made during this phase. Detected state is used to populate CLAUDE_INSTALL.md with appropriate guidance.

**Detection Steps**:
```bash
# Step 1: Check if project is MCP server
→ Search README.md for: "MCP", "Model Context Protocol", "mcp server"
→ Search for MCP library imports (any language)
→ Look for server entrypoint files: server.py, index.js, main.go, etc.

# Step 2: If MCP detected, check installation state
→ Run: claude mcp list
→ Extract server name from: README, directory name, package.json, pyproject.toml
→ Search output for {server-name}

# Step 3: Determine installation state
```

**Installation States**:

| State | Detection | Documentation Action |
|-------|-----------|---------------------|
| **Not Installed** | Server not in `claude mcp list` | Record state → Proceed to Phase 1 (prepare fresh install docs) |
| **User Scope** | In list, scope=user | Record state → Prompt for docs: Update/Repair/Reinstall/Cancel |
| **Project Scope** | In list, scope=local | Record state → Prompt for docs: Migrate to user scope? |
| **Broken** | In list, status=disconnected | Record state → Prompt for docs: Repair installation? |

**Note**: During migration, these states are DETECTED and RECORDED to prepare appropriate installation documentation. No actual installation/configuration changes occur until user/agent follows CLAUDE_INSTALL.md.

**User Prompts by State**:

#### State: User Scope (Already Installed Globally)
```
┌─────────────────────────────────────────────┐
│ MCP Server Installation Wizard             │
├─────────────────────────────────────────────┤
│                                             │
│ ✓ Found: {server-name} (User scope)       │
│   Status: Connected                         │
│   Command: {current-command}                │
│   Entrypoint: {current-entrypoint}          │
│                                             │
│ What would you like to do?                  │
│                                             │
│ [1] Update Configuration                    │
│     Modify credentials or paths             │
│                                             │
│ [2] Repair Installation                     │
│     Verify files, test connection, fix      │
│                                             │
│ [3] Reinstall Completely                    │
│     Remove and fresh install                │
│                                             │
│ [4] Cancel                                  │
│     Keep current configuration              │
│                                             │
│ Choice [1-4]:                               │
└─────────────────────────────────────────────┘
```

**Workflow by Choice**:

**[1] Update Configuration**:
```
→ Run: claude mcp get {server-name}
→ Parse current config (command, args, env vars)
→ Show masked credentials: "OPENAI_API_KEY: sk-****...****"
→ For each credential:
   "Update {CREDENTIAL}? [Y/N]"
   If Y: "Enter new value:" → elicit
   If N: Keep current (don't show value)
→ Generate: claude mcp add-json with updated values
→ Execute: claude mcp remove {server-name} && claude mcp add-json ...
→ Verify: claude mcp get {server-name}
→ SKIP Phase 1-4 (update complete)
→ Record update in migration log
```

**[2] Repair Installation**:
```
→ Verify command path exists: Check file at {command}
→ Verify entrypoint exists: Check file at {args[0]}
→ Test connection: claude mcp get {server-name} → check status
→ Diagnose issues:
   Missing files → "Command/entrypoint not found. Update paths? [Y/N]"
   Connection failed → Test server manually, check error logs
   Credential errors → "Update credentials? [Y/N]"
→ Apply fixes, update config if needed
→ Verify: claude mcp list → status should be Connected
→ SKIP Phase 1-4 (repair complete)
→ Record repair in migration log
```

**[3] Reinstall Completely**:
```
→ Execute: claude mcp remove {server-name}
→ Verify: claude mcp list | grep {server-name} → should be empty
→ PROCEED to Phase 1 (fresh installation)
```

**[4] Cancel**:
```
→ Display: "Keeping existing configuration. No changes made."
→ EXIT migration
```

#### State: Project Scope (Local Only)
```
┌─────────────────────────────────────────────┐
│ Found: {server-name} (Project scope)       │
│                                             │
│ This server is only available in THIS       │
│ project. Migrate to USER scope for global  │
│ availability across all projects?           │
│                                             │
│ [1] Migrate to User Scope (Recommended)    │
│ [2] Keep Project-Scoped                     │
│ [3] Cancel                                  │
│                                             │
│ Choice [1-3]:                               │
└─────────────────────────────────────────────┘

[1] → Remove local config, add user config, SKIP Phase 1-4
[2] → Display warning, EXIT migration
[3] → EXIT migration
```

#### State: Broken (Disconnected)
```
┌─────────────────────────────────────────────┐
│ ⚠️  Found: {server-name} (Broken)          │
│     Status: Disconnected                    │
│                                             │
│ The server is configured but not working.   │
│                                             │
│ [1] Repair (Diagnose and fix issues)       │
│ [2] Reinstall (Remove and start fresh)     │
│ [3] Cancel                                  │
│                                             │
│ Choice [1-3]:                               │
└─────────────────────────────────────────────┘

[1] → Execute Repair workflow (see above)
[2] → Execute Reinstall workflow (see above)
[3] → EXIT migration
```

---

### Phase 1: Auto-Detect

#### 1.0: Project Type Detection

First determine if this is an MCP server project:

**MCP Indicators** (search for any):
- README mentions: "MCP", "Model Context Protocol", "mcp server", "claude desktop"
- MCP library imports (language-agnostic):
  - Python: `from fastmcp`, `from mcp`, `import mcp`
  - Node.js: `require('@modelcontextprotocol/sdk')`, `import ... from '@modelcontextprotocol/sdk'`
  - Go: `import "github.com/modelcontextprotocol/..."`
  - Rust: `use mcp::`
- Server entrypoint files: `server.py`, `server.js`, `index.js`, `main.go`, `server.ts`
- Config mentions: `.env.example` or README mentions Claude Desktop configuration

**If MCP detected** → Add Phase 1.6 (MCP-specific detection) to workflow

**If NOT MCP** → Skip Phase 1.6, continue with standard detection

#### 1.1-1.5: Standard Project Detection

**Sources → Values**:

| Source | Detects | Values Extracted |
|--------|---------|------------------|
| `git remote -v` | Repo info | `[YOUR_REPO_URL]`, `[BASE_REPO_URL]` (if upstream exists) |
| `setup.py` | Python project | `name=`, `python_requires=`, `install_requires=` → [PROJECT_NAME], [PYTHON_VERSION], deps |
| `pyproject.toml` | Python project | `[project]` name, requires-python, dependencies → same |
| `requirements.txt` | Dependencies | Package versions → DB (Neo4j, PostgreSQL, MongoDB), LLM (OpenAI, Anthropic), optional deps |
| `package.json` | Node project | name, engines.node → [PROJECT_NAME], version req |
| `Cargo.toml` | Rust project | [package] name, version → [PROJECT_NAME] |
| `README.md` | Docs | First heading, description, base-project refs |
| `.env.example` | Env vars | Required keys → API_KEY patterns, DATABASE_URL, service configs |
| `docker-compose.yml` | Containers | services.*.image → DB/service options |
| `Dockerfile` | Base image | FROM line → version hints |

#### 1.6: MCP Server Detection (If MCP Indicators Found)

**Purpose**: Detect MCP-specific configuration requirements for Claude Code CLI integration

**Primary Source: README.md** (most efficient):
```
Search README.md for sections:
→ ## Prerequisites, ## Configuration, ## Setup, ## Environment
→ ## Claude Desktop, ## MCP Server, ## Installation

Extract from README:
→ Required API keys/credentials (e.g., "OPENAI_API_KEY required")
→ Optional credentials (e.g., "ANTHROPIC_API_KEY optional")
→ Runtime requirements (e.g., "Python 3.11+", "Node.js 18+")
→ Server entrypoint (e.g., "Run python server.py")
```

**Secondary: .env.example / config files**:
```
Search for config templates:
→ .env.example, .env.template, example.env, config.example.json

Extract credential names (keys without values):
→ OPENAI_API_KEY=your-key-here → Extract "OPENAI_API_KEY"
→ DATABASE_URL=postgres://... → Extract "DATABASE_URL"
```

**Tertiary: Broad Code Search** (any language):
```
Search ALL files for environment variable patterns:

Python:
→ os.getenv("OPENAI_API_KEY")
→ os.environ.get("TAVILY_API_KEY")
→ os.environ["GITHUB_TOKEN"]

Node.js:
→ process.env.OPENAI_API_KEY
→ process.env.TAVILY_API_KEY

Go:
→ os.Getenv("OPENAI_API_KEY")
→ os.LookupEnv("TAVILY_API_KEY")

Rust:
→ env::var("OPENAI_API_KEY")
→ std::env::var("TAVILY_API_KEY")

Ruby:
→ ENV["OPENAI_API_KEY"]
→ ENV.fetch("TAVILY_API_KEY")

PHP:
→ getenv("OPENAI_API_KEY")
→ $_ENV["TAVILY_API_KEY"]

Generic:
→ Look for UPPERCASE_SNAKE_CASE in any config file
```

**Server Entrypoint Detection**:
```
Search for main server file:
→ Files matching: server.*, main.*, index.* (in root or src/)
→ Files with MCP library imports
→ Check package.json "main" field
→ Check pyproject.toml [tool.poetry.scripts]
→ Check README for run command
```

**Runtime Detection**:
```
Determine execution command:
→ Python project (requirements.txt, *.py) → python or python3
→ Node project (package.json, *.js/*.ts) → node or npx
→ Go project (go.mod, *.go) → compiled binary path
→ Rust project (Cargo.toml, *.rs) → compiled binary path

Find runtime path:
→ Windows: where python, where node
→ macOS/Linux: which python3, which node
```

**Extractable Values**:
- `[MCP_SERVER_NAME]` - From README heading, directory name, package metadata
- `[MCP_REQUIRED_CREDENTIALS]` - List of required env vars (from README → .env → code)
- `[MCP_OPTIONAL_CREDENTIALS]` - List of optional env vars
- `[MCP_RUNTIME_COMMAND]` - Absolute path to runtime (python.exe, node.exe, binary)
- `[MCP_SERVER_ENTRYPOINT]` - Absolute path to server file (server.py, index.js, etc.)

**Conventional Naming Recognition**:

Agent automatically recognizes these patterns:
- `*_API_KEY`, `*_KEY` → API credential (mask when displaying)
- `*_TOKEN`, `*_SECRET`, `*_PASSWORD` → Sensitive credential (mask)
- `*_URL`, `*_ENDPOINT`, `*_HOST` → Configuration value (OK to show)
- `*_PORT`, `*_TIMEOUT`, `*_MAX_*` → Configuration value (OK to show)

Common credentials auto-recognized:
- `OPENAI_API_KEY` → OpenAI API
- `ANTHROPIC_API_KEY` → Anthropic/Claude API
- `GROQ_API_KEY` → Groq API
- `TAVILY_API_KEY` → Tavily Search API
- `SERPER_API_KEY` → Serper Google Search API
- `GITHUB_TOKEN`, `GITHUB_PERSONAL_ACCESS_TOKEN` → GitHub auth
- `DATABASE_URL`, `POSTGRES_URL`, `MONGODB_URI` → Database connections

---

### Phase 2: Validation

Agent shows detected values:
```
🔍 Detected:
Project: analytics-platform (from setup.py)
  ✓ Confirm | ✗ Override

Repo: https://github.com/acme/analytics-platform
  ✓ Confirm | ✗ Override

Python: 3.9+
  ✓ Confirm | ✗ Specify

Deps:
  - PostgreSQL (psycopg2)
  - Redis (redis)
  - OpenAI (openai)
  ✓ Confirm all | ✗ Review
```

### Phase 3: Missing Info Prompts

**Q1: Derived Project?**
```
Is this derived from another project? [Y/N]
If Y:
  - Base project name? → [BASE_PROJECT_NAME]
  - Base repo URL? → [BASE_REPO_URL]
  - Key customizations? → description
```

**Q2: Install Options**
```
Which install methods to document?

Database:
[ ] Cloud (AWS RDS, Aura)
[x] Docker / Docker Compose
[ ] Local (Windows Service, Homebrew, apt)
[x] Other: Kubernetes

For each:
- Status? [✅Validated | ⚠️Experimental | ❌Deprecated]
- Platforms? [W | M | L]
```

**Q3: Platform Support**
```
Supported platforms:
[ ] Windows 10+
[x] Windows 11
[x] macOS 13+
[x] macOS 14+
[x] Ubuntu 20.04+
[x] Ubuntu 22.04+
[ ] Other Linux: _____
```

**Q4: Docs URLs**
```
External docs?
- Docs URL: [DOCS_URL] (e.g., https://docs.yourproject.io)
- Issues: (defaults to [REPO]/issues)
- Discussions: (defaults to [REPO]/discussions)
```

**Q5: MCP Server Credentials** (Only if MCP detected in Phase 1.6)
```
MCP Server Configuration Required

Detected credentials from README/code analysis:
[x] OPENAI_API_KEY (required - detected from README "Prerequisites")
[x] TAVILY_API_KEY (required - detected from .env.example)
[ ] ANTHROPIC_API_KEY (optional - detected from .env.example)

For each required credential:

Step 1: Check system environment
→ Run: echo $CREDENTIAL (macOS/Linux) or echo %CREDENTIAL% (Windows)
→ If found: "✓ {CREDENTIAL} found in system environment"
→ If not found: "✗ {CREDENTIAL} not found"

Step 2: Elicit value
If found in system:
  "Use existing value from system environment? [Y/N]"
  → Y: Use system value (don't ask for input)
  → N: "Enter new value for {CREDENTIAL}:"

If not found in system:
  "Please provide {CREDENTIAL}:"
  → User provides value
  → Mask display: "✓ {CREDENTIAL}: {first-4-chars}****...****{last-4-chars}"

Step 3: System environment setup (optional)
  "Add {CREDENTIAL} to system environment variables? [Y/N]"
  → Y: Provide platform-specific instructions (see below)
  → N: Skip (will be stored in ~/.claude.json only)

Step 4: Conventional naming inference
If credential name pattern not recognized:
  → "Is {CREDENTIAL} a sensitive value (API key, token, password)? [Y/N]"
  → Y: Treat as sensitive (mask when displaying)
  → N: Treat as configuration (OK to show)
```

**Platform-Specific Env Var Instructions** (if user wants to add to system):

Windows (PowerShell - Persistent):
```powershell
[Environment]::SetEnvironmentVariable("{CREDENTIAL}", "value", "User")
# Restart terminal for changes to take effect
```

Windows (GUI - Persistent):
```
1. Press Win+R, type: sysdm.cpl
2. Advanced tab → Environment Variables
3. User variables → New
4. Variable name: {CREDENTIAL}
5. Variable value: {value}
6. OK → OK → Restart terminal
```

macOS/Linux (Bash - Persistent):
```bash
# Add to ~/.bashrc or ~/.bash_profile
echo 'export {CREDENTIAL}="{value}"' >> ~/.bashrc
source ~/.bashrc
```

macOS/Linux (Zsh - Persistent):
```zsh
# Add to ~/.zshrc
echo 'export {CREDENTIAL}="{value}"' >> ~/.zshrc
source ~/.zshrc
```

**Important Note About Claude Code CLI**:
```
⚠️  Even if credentials are in system environment variables,
    Claude Code CLI stores LITERAL VALUES in ~/.claude.json
    (not variable references like ${VAR}).

    This means:
    - System env vars are READ ONCE at configuration time
    - Actual values are STORED in ~/.claude.json
    - If you change env vars later, must re-run installation

    Security: ~/.claude.json contains sensitive data
    → Never commit to git
    → Protect with file permissions (chmod 600)
```

---

### Phase 4: Update Templates

**MIGRATION SCOPE**: This phase ONLY updates documentation files with detected/elicited information. No system changes occur during migration. The files created/updated here will serve as guides for actual installation.

**Files Updated**:
1. **CLAUDE_INSTALL.md**: Replace all placeholders with project-specific values
   - About section: base-project, repo, customizations
   - Prerequisites: detected deps + validation
   - Options: detected install methods
   - **MCP Section** (if MCP detected): Generate Claude Code CLI integration section
2. **CLAUDE_README.md**: Update examples to match project
3. **CLAUDE_INSTALL_CHANGELOG.md**: Generate v1.0.0 entry

**What This Phase Does NOT Do**:
- ❌ Install packages or dependencies
- ❌ Configure MCP servers
- ❌ Modify system environment
- ❌ Run `claude mcp add` or similar commands

#### 4.1: MCP Section Generation (If MCP Detected)

**Add to CLAUDE_INSTALL.md after "Installation Options" section**:

```markdown
## Claude Code CLI Integration

**Purpose**: Configure this MCP server for global availability in Claude Code CLI

**Prerequisites**:
- Claude Code CLI installed (`claude --version`)
- Required credentials (see below)
- Project cloned to: {absolute-path}

### Installation Wizard

Agent will check for existing installation first.

#### Pre-Installation Check
```bash
# Checking for existing installation...
claude mcp list | grep {server-name}
```

**Status**: {Not Installed | Already Installed | Broken}

{If Already Installed → Show Update/Repair/Reinstall/Cancel wizard}
{If Not Installed → Proceed to Credential Discovery}

### Step 1: Credential Discovery

**Detected from README/code analysis**:
- Required: {list-of-required-credentials}
- Optional: {list-of-optional-credentials}

**Checking system environment**:
```bash
# macOS/Linux
echo ${CREDENTIAL}

# Windows
echo %CREDENTIAL%
```

**Results**:
{For each credential}
- {CREDENTIAL}: {Found ✓ | Not found ✗}

**Elicitation**:
{For each not-found credential}
Please provide {CREDENTIAL}: [masked input]
✓ Received: {first-4}****...****{last-4}

{For each found credential}
Use existing system value for {CREDENTIAL}? [Y/N]

**Optional: Add to System Environment**:
Would you like to add credentials to system environment variables? [Y/N]
{If Y → Show platform-specific instructions}

### Step 2: Configure MCP Server

**Generated Configuration**:
```bash
# Platform: {Windows|macOS|Linux}
# Runtime: {absolute-path-to-runtime}
# Entrypoint: {absolute-path-to-entrypoint}

claude mcp add-json --scope user {server-name} '{
  "type":"stdio",
  "command":"{runtime-path}",
  "args":["{entrypoint-path}"],
  "env":{
    "{CREDENTIAL_1}":"{actual-value}",
    "{CREDENTIAL_2}":"{actual-value}"
  }
}'
```

**Important Notes**:
- ⚠️ Credentials are stored as **literal values** in `~/.claude.json`
- ⚠️ Claude Code CLI does **NOT** read OS environment variables at runtime
- ⚠️ If credentials change, **must re-run** installation to update
- ✅ Use `--scope user` for **global** availability across all projects
- 🔒 `~/.claude.json` contains sensitive data - **never commit to git**

### Step 3: Verification

```bash
# List all MCP servers
claude mcp list

# Expected: {server-name} appears in list

# Get configuration details
claude mcp get {server-name}

# Expected output:
{server-name}:
  Scope: User config (available in all projects)
  Status: ✓ Connected
  Type: stdio
  Command: {runtime-path}
  Args: {entrypoint-path}
  Environment:
    {CREDENTIAL_1}: {masked-value}
    {CREDENTIAL_2}: {masked-value}
```

### Step 4: Post-Installation

**Fresh Installation**:
```
✓ Installation complete!

Next steps:
1. Restart Claude Code CLI (if running)
2. Run '/mcp' to see available MCP servers
3. Test tools: {list-of-tools}
```

**Update/Repair**:
```
✓ Configuration updated!

Changes:
- {CREDENTIAL_1}: Updated
- {CREDENTIAL_2}: Unchanged

Restart Claude Code CLI to apply changes.
```

### Troubleshooting

**Issue: Server not appearing in `/mcp` list**
- Check: `claude mcp list` → Should show {server-name}
- Check scope: `claude mcp get {server-name}` → Should be "User config"
- If project-scoped: Re-add with `--scope user`

**Issue: Connection failed**
- Check runtime path exists: `{runtime-path} --version`
- Check entrypoint exists: `ls {entrypoint-path}`
- Check logs: `tail -f ~/.claude/debug/*.txt | grep {server-name}`
- Test manually: `{runtime-path} {entrypoint-path}`

**Issue: Credential errors**
- Re-run installation to update credentials
- Verify credentials are valid (test with provider's API)
- Check for typos in credential values

### Updating Credentials

**To update credentials later**:
1. Re-run this installation (agent will detect existing)
2. Choose "Update Configuration"
3. Select which credentials to update
4. Provide new values
5. Agent will reconfigure automatically

**Manual update**:
```bash
# Remove existing
claude mcp remove {server-name}

# Re-add with new values
claude mcp add-json --scope user {server-name} '{...new-credentials...}'
```
```

**Placeholders to Replace**:
- `{server-name}` → From Phase 1.6 detection
- `{absolute-path}` → Current working directory
- `{list-of-required-credentials}` → From Phase 3.5
- `{list-of-optional-credentials}` → From Phase 3.5
- `{runtime-path}` → Detected runtime (python.exe, node.exe, etc.)
- `{entrypoint-path}` → Detected server file (server.py, index.js, etc.)
- `{list-of-tools}` → Parse from server code or README
- `{CREDENTIAL_*}` → Actual credential names from Phase 3.5

---

### Phase 5: Record Migration

**IMPORTANT - MIGRATION COMPLETE**: Migration completion means documentation is ready - NOT that software is installed. User or agent must now follow CLAUDE_INSTALL.md to perform actual installation and system configuration.

Append to this file:
```markdown
---

## Migration Record

**Completed**: 2025-10-25 14:30 UTC
**By**: Claude Code v4.5
**Session**: workspace-name

### Detected
**Git**: Repo https://github.com/acme/analytics, Base https://github.com/base/pipeline
**setup.py**: Name analytics-platform, Python 3.9+, Deps psycopg2+redis+openai+kafka
**.env.example**: OPENAI_API_KEY, DATABASE_URL, REDIS_URL, KAFKA_BROKERS

### User-Provided
**Derived**: Yes, from Data Pipeline Framework, customizations: real-time Kafka + ML serving
**Options**: PostgreSQL Docker ✅(W11+M14+U22), Redis Docker ✅(all), Kafka Docker ✅(W11+M14), Kafka Cloud ⚠️
**Platforms**: W11, M14, U22.04 fully tested
**Docs**: https://docs.analytics.acme.com, Issues: /issues

### Files
✅ CLAUDE_INSTALL.md - placeholders replaced
✅ CLAUDE_INSTALL_CHANGELOG.md - v1.0.0 generated
✅ CLAUDE_README.md - examples updated
✅ CLAUDE_MIGRATE.md - record appended

### Next
1. Review CLAUDE_INSTALL.md
2. Test install on all platforms
3. Update validation badges after testing
4. Start dev - CLAUDE_README.md is entrypoint
5. Living docs active

---

**Status**: ✅ COMPLETED
```

---

## Manual Migration

If manual preferred:

### S1: Find Placeholders
```bash
grep -r "\[.*\]" CLAUDE_*.md

# Common:
[PROJECT_NAME]
[BASE_PROJECT_NAME]
[BASE_REPO_URL]
[YOUR_REPO_URL]
[PYTHON_VERSION]
[DATABASE]
[LLM_PROVIDER]
[CLOUD_SERVICE_URL]
[DOCS_URL]
[DATE]
```

### S2: Replace
Use editor find-replace:
1. `[PROJECT_NAME]` → actual name
2. `[YOUR_REPO_URL]` → repo URL
3. Date placeholders → current date
4. etc.

### S3: Generate v1.0.0
Document current state in CLAUDE_INSTALL_CHANGELOG.md:
- List prereqs
- List options
- Mark validation status
- Document platforms

### S4: Update This File
Update status + add migration record

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Can't detect details | Missing/non-standard files | Ensure setup.py/pyproject.toml/package.json/README.md exists, or provide manually |
| Multiple Python versions | Conflicting specs | Agent shows all, choose most restrictive, fix inconsistent files after |
| Can't determine if derived | Ambiguous git remotes | Answer "No" for original, "Yes" for fork/derived, update later if needed |
| Too many deps | Large requirements | Agent categorizes Required vs Optional, review+correct, focus on prereqs not every package |

---

## Re-Running

Can re-run if project structure changed significantly or want to update detected values.

**To Re-Run**:
1. Agent reads this file
2. Sees existing record
3. Asks: "Migration completed [DATE]. Re-run?"
4. If yes: repeat workflow, append new record
5. If no: skip to normal dev

---

## Next Steps Post-Migration

1. **Verify**: Review CLAUDE_INSTALL.md accuracy
2. **Test**: Follow own install guide
3. **Update**: Mark paths ✅ after testing
4. **Develop**: Use CLAUDE_README.md as entrypoint
5. **Trust**: Living docs auto-update

**Living Documentation Active!** 🎉

Agent auto:
- Updates CLAUDE_INSTALL.md on env changes
- Increments semantic versions
- Logs in CLAUDE_INSTALL_CHANGELOG.md
- Tracks validation

---

**Template**: v1.2.0 | **Created**: 2025-10-25 | **Updated**: 2025-10-26 | **Purpose**: Bridge generic → project-specific + MCP server support | **Maintained**: Claude Code Tooling
