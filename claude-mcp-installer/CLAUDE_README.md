# Claude MCP Installer Templates - Agent Entrypoint

**Version**: 3.0.0 | **Updated**: 2025-10-30 | **Purpose**: AI agent development entrypoint

---

## Schema (EXECUTE FIRST)

**CRITICAL**: Before processing ANY Claude documentation:

1. **Read claude-mcp-installer/CLAUDE_README.md first** (this file) - establishes all rules
2. **Detect migration state**:
   ```bash
   # Check if migration already run
   [ -d "claude-mcp-installer/instance" ] || \
   [ -f "claude-mcp-installer/CLAUDE_INSTALL.md" ] && echo "Migration complete" || echo "Fresh migration required"
   ```
3. **Setup .gitignore** (if not present in project root):
   ```bash
   cat >> .gitignore << 'EOF'
   # Generated Claude MCP Installer Documentation (platform-specific)
   claude-mcp-installer/instance/
   EOF
   ```

**Directory Structure**:
- `templates/` = Generators (copied to instance/ during migration)
- `references/` = Static resources (read-only, never copied)
- `instance/` = Generated files (mutable, platform-specific, gitignored)

**Naming Convention**:
- `.template.md` = Generator (will create mutable copy in instance/)
- `.ref.md` = Static reference (read-only, used as context)
- `.md` (no suffix) = Entrypoint or generated file

**File Index**:
```
GIT-TRACKED (claude-mcp-installer/):          GENERATED (claude-mcp-installer/instance/):
├── CLAUDE_README.md                          ├── CLAUDE_INSTALL.md
├── templates/                                └── CLAUDE_MIGRATE.md
│   ├── CLAUDE_INSTALL.template.md
│   ├── CLAUDE_MIGRATE.template.md
│   └── .gitignore.template
└── references/
    └── CLAUDE_MCP_INTEGRATION_SCHEMA.ref.md
```

---

## System

Living documentation structure:
```
claude-mcp-installer/
├── CLAUDE_README.md → agent entrypoint + policies
├── templates/ → generators (create mutable copies in instance/)
│   ├── CLAUDE_INSTALL.template.md
│   ├── CLAUDE_MIGRATE.template.md
│   └── .gitignore.template
├── references/ → static resources (read-only, never copied)
│   └── CLAUDE_MCP_INTEGRATION_SCHEMA.ref.md
└── instance/ → generated files (mutable, platform-specific, gitignored)
    ├── CLAUDE_INSTALL.md
    └── CLAUDE_MIGRATE.md
```

**Universal Application**: Templates work for any software project requiring environment setup/configuration.

---

## Policies (MANDATORY)

### P0: Directory-Based Separation + Template Immutability

**RULE**: templates/=generators | references/=static | instance/=mutable

**Detection**:
```bash
# Check if migration run
[ -d "claude-mcp-installer/instance" ] || [ -f "claude-mcp-installer/CLAUDE_INSTALL.md" ] → migration-complete
[ ! -d "claude-mcp-installer/instance" ] → fresh-migration-required
```

**Migration Workflow**:
```
Schema validation → create instance/ → copy templates/*.template.md to instance/*.md (strip .template suffix) → populate placeholders → edit instance/ files
⊗ NEVER edit templates/ files (immutable blueprints)
⊗ NEVER copy references/ files (read-only context)
✓ Generate instance/CLAUDE_INSTALL.md from templates/CLAUDE_INSTALL.template.md
✓ Update instance/ files locally (platform-specific)
✓ Commit templates/ or references/ changes only (if improving structure)
```

**File Roles**:
```
templates/*.template.md → Copied to instance/ during migration (stripped to .md)
references/*.ref.md → Read as context, NEVER copied
instance/*.md → Mutable, local-only, NEVER committed
```

**Commit Format (Template/Reference Updates Only)**:
```
docs(templates): [Title] (vX.Y.Z)

- [template structure change]
- [reference documentation update]
- Version: [old] → [new] ([version-type])
- Validation: [status-updates]
```

**Rationale**: directory-separation=clear-intent, templates=portable, instance=local

### P1: Update Trigger

**MUST update instance/CLAUDE_INSTALL.md when**:
```
code-change?(install|prereq|env|config|platform) → update-required
```

**Triggers**:
- install: procedures, options, steps
- prereq: Python version, dependencies, system requirements
- env: API keys, env vars, .env structure
- config: config files, settings, special permissions
- platform: OS support changes

### P2: Semantic Versioning

**Version Logic**:
```
breaks-existing-setup? → MAJOR (X.0.0)
adds-feature?(backward-compat) → MINOR (0.X.0)
fixes|clarifies?(no-breaking) → PATCH (0.0.X)
```

**MAJOR Examples**: Python3.10→3.11, removed-option, renamed-env-vars, config-structure-change
**MINOR Examples**: new-install-option, new-optional-dep, new-env-var(optional), enhanced-instructions
**PATCH Examples**: typos, clarifications, validation-badge-updates, broken-link-fixes

### P3: Installation Interaction

**RULE**: ALWAYS prompt for install choices, NEVER store preferences (no Graphiti memory)

**Rationale**: install=infrequent, control>convenience

### P4: Validation Tracking

**Badges**:
- ✅ Validated: tested+working (platform+date)
- ⚠️ Experimental: untested|partial
- ❌ Deprecated: no-longer-recommended

**Format**: `Option: Neo4j Aura ✅ [2025-10-25, W11+M14]`

**Update-When**: test-success | dep-version-change | user-issue | platform-change

### P5: MCP Server Configuration Detection

**RULE**: Detect MCP servers → check install state → elicit credentials → configure Claude Code CLI

**Update Trigger**:
```
Policy added/changed? → MINOR version (new feature, backward-compatible)
CLAUDE_INSTALL.md updated with confirmation prompts? → include in same commit
```

**Phase 0: Installation State Check** (Execute FIRST, before any detection):
```
Run: claude mcp list
Extract: {server-name} from README/directory/package-metadata
Search output for: {server-name}

NOT FOUND → fresh-install-flow (Phase 1)
FOUND (user scope) → prompt-wizard ↓
  "Already installed globally. What would you like to do?"
  [1] Update Configuration → load-config + prompt-changes + update
  [2] Repair Installation → verify-paths + test-connection + fix-issues
  [3] Reinstall Completely → remove + fresh-install-flow
  [4] Cancel → exit

FOUND (project scope) → prompt-migration
  "Found in project scope. Migrate to global (user) scope? [Y/N]"
  Y → remove-local + add-user-scope
  N → exit

FOUND (broken/disconnected) → prompt-repair
  "Installation found but not working. Repair? [Y/N]"
  Y → execute-repair-workflow
  N → exit
```

**Phase 1: MCP Project Detection** (If Phase 0 = not found):
```
detect-mcp-project?
├─ Search README.md for: "MCP", "Model Context Protocol", "mcp server"
├─ Search for MCP library imports (language-agnostic):
│  → Python: from fastmcp, from mcp, import mcp
│  → Node.js: require('@modelcontextprotocol/sdk'), import ... from '@modelcontextprotocol/sdk'
│  → Go: import "github.com/modelcontextprotocol/..."
│  → Rust: use mcp::
├─ Search for server entrypoints: server.py, server.js, index.js, main.go, server.ts
├─ Search config files for Claude Desktop mentions

MCP detected? → proceed-to-credential-detection
NOT MCP? → skip-P6 (continue standard workflow)
```

**Credential Detection** (README-first + broad fallback):
```
Primary: README.md
→ Search sections: ## Prerequisites, ## Configuration, ## Setup, ## Environment
→ Extract: Required credentials, optional credentials, descriptions

Secondary: .env.example / config files
→ Search: .env.example, .env.template, example.env, config.example.json
→ Extract: Credential names (keys without values)

Tertiary: Broad code search (all file types, all languages)
→ Python: os.getenv("X"), os.environ.get("X"), os.environ["X"]
→ Node.js: process.env.X
→ Go: os.Getenv("X"), os.LookupEnv("X")
→ Rust: env::var("X"), std::env::var("X")
→ Ruby: ENV["X"], ENV.fetch("X")
→ PHP: getenv("X"), $_ENV["X"]
→ Generic: UPPERCASE_SNAKE_CASE in any config file

Runtime Detection:
→ Python project (requirements.txt, *.py) → python or python3 → which/where
→ Node project (package.json, *.js/*.ts) → node or npx → which/where
→ Go project (go.mod, *.go) → compiled binary path
→ Rust project (Cargo.toml, *.rs) → compiled binary path

Entrypoint Detection:
→ Files matching: server.*, main.*, index.* (root or src/)
→ Files with MCP library imports
→ package.json "main" field
→ pyproject.toml [tool.poetry.scripts]
→ README run command
```

**Conventional Naming Recognition**:
```
Auto-recognize patterns:
→ *_API_KEY, *_KEY, *_TOKEN, *_SECRET, *_PASSWORD → sensitive (mask)
→ *_URL, *_ENDPOINT, *_HOST, *_PORT, *_TIMEOUT → configuration (OK to show)

Common credentials:
→ OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY
→ TAVILY_API_KEY, SERPER_API_KEY
→ GITHUB_TOKEN, GITHUB_PERSONAL_ACCESS_TOKEN
→ DATABASE_URL, POSTGRES_URL, MONGODB_URI

If pattern unknown:
→ "Is {CREDENTIAL} a sensitive value (API key, token, password)? [Y/N]"
```

**Credential Elicitation**:
```
For each required credential:

1. Check system environment
   → Run: echo $CREDENTIAL (Unix) or echo %CREDENTIAL% (Windows)
   → If found: "✓ {CREDENTIAL} found in system environment"
   → If not found: "✗ {CREDENTIAL} not found"

2. Elicit value
   If found in system:
     "Use existing system value for {CREDENTIAL}? [Y/N]"
     → Y: Use system value (don't show or re-enter)
     → N: "Enter new value:" [masked input]

   If not found in system:
     "Please provide {CREDENTIAL}:"
     [Masked input: ●●●●●●●●●●●●]
     → Display: "✓ Received: {first-4}****...****{last-4}"

3. System environment setup (optional)
   "Add {CREDENTIAL} to system environment variables? [Y/N]"
   → Y: Provide platform-specific instructions (PowerShell, GUI, Bash, Zsh)
   → N: Skip (stored only in ~/.claude.json)

4. Important note displayed:
   "⚠️  Claude Code CLI stores LITERAL VALUES in ~/.claude.json
       (not variable references like ${VAR} or %VAR%).
       If you change env vars later, you MUST re-run installation."
```

**Configuration Generation**:
```
Generate: claude mcp add-json --scope user {server-name} '{
  "type":"stdio",
  "command":"{absolute-runtime-path}",
  "args":["{absolute-entrypoint-path}"],
  "env":{
    "{CREDENTIAL_1}":"{actual-value}",
    "{CREDENTIAL_2}":"{actual-value}"
  }
}'

Execute → Verify: claude mcp get {server-name}
Update: instance/CLAUDE_INSTALL.md (add MCP Server Integration section)
```

**Update Trigger**:
```
MCP config added/changed? → MINOR version (new feature, backward-compatible)

Commit format (if git mode):
docs(install): Add Claude Code CLI integration (vX.Y.Z)

- Added MCP server configuration section
- Required credentials: {list}
- Optional credentials: {list}
- Platform support: {platforms}
- Validation: ⚠️ until tested
```

---

## Workflow

### Standard Cycle

**Template Mode** (templates exist):
```
code-change → assess-impact? → (no: done | yes: ↓)
→ update(instance/CLAUDE_INSTALL.md) - generated file, local only
→ determine-version-increment
→ update-validation-badges
→ commit templates only (if template structure improved)
⊗ NEVER commit generated instance/CLAUDE_INSTALL.md
```

### Decision Matrix

```
Changed?                  Update?   Version
────────────────────────  ────────  ───────
prereq                    YES       MINOR|MAJOR
api-keys|env-vars         YES       MINOR|MAJOR
install-steps             YES       MINOR|PATCH
dependencies              YES       MINOR|MAJOR
config-files              YES       MINOR|MAJOR
platform-support          YES       MAJOR
code-logic-only           NO        -
tests-only                NO        -
```

---


## Template Installation (Quick Start)

### Step 1: Copy to Project Root
```bash
cd /path/to/your-mcp-project
cp -r /path/to/claude-code-tooling/claude-mcp-installer .
```

**Directory Structure Created**:
```
your-mcp-project/
└── claude-mcp-installer/
    ├── CLAUDE_README.md
    ├── templates/
    │   ├── CLAUDE_INSTALL.template.md
    │   ├── CLAUDE_MIGRATE.template.md
    │   └── .gitignore.template
    └── references/
        └── CLAUDE_MCP_INTEGRATION_SCHEMA.ref.md
```

### Step 2: Run Migration
```
Agent: Point me to claude-mcp-installer/CLAUDE_README.md
Agent will:
1. Validate schema (check templates/, references/ exist)
2. Detect if migration already run (check for instance/ directory)
3. If fresh: Create instance/ directory
4. Copy templates/*.template.md → instance/*.md (strip .template suffix)
5. Populate placeholders with project-specific values
6. Setup .gitignore to ignore instance/ directory

Time: 5-15 minutes
Result: claude-mcp-installer/instance/ created with mutable, platform-specific docs
```

### Step 3: Start Development
- **For AI agents**: Read claude-mcp-installer/CLAUDE_README.md as entrypoint
- **For humans**: Follow claude-mcp-installer/instance/CLAUDE_INSTALL.md
- **Git**: Commit claude-mcp-installer/ (templates/references), gitignore instance/

---

## Examples (Compact)

### Ex1: New API Key (MINOR) - Git Mode
```
Change: Added ANTHROPIC_API_KEY
Update: instance/CLAUDE_INSTALL.md (prereq section + .env example)
Version: 1.2.0 → 1.3.0
Badge: ⚠️ until tested
Commit: docs(install): Add Anthropic API support (v1.3.0)
        - Added ANTHROPIC_API_KEY to prereqs
        - Updated .env example
        - Version: 1.2.0 → 1.3.0 (MINOR)
        - Validation: ⚠️ until tested
Push: IMMEDIATE
```

### Ex2: Python Version Bump (MAJOR) - Git Mode
```
Change: Python3.10+ → Python3.11+
Update: instance/CLAUDE_INSTALL.md (prereq + migration-note)
Version: 1.9.5 → 2.0.0
Badge: Update all platform validations
Commit: docs(install): BREAKING - Python 3.11+ required (v2.0.0)
        - Python3.10+ → Python3.11+
        - Added migration guide for Python upgrade
        - Version: 1.9.5 → 2.0.0 (MAJOR)
        - Validation: Updated all platform badges
Push: IMMEDIATE
```

### Ex3: Typo Fix (PATCH) - Template Mode
```
Change: Fixed Neo4j connection string typo
Update: instance/CLAUDE_INSTALL.md (local generated file)
Version: 1.3.2 → 1.3.3
Action: Update local file only (not committed, platform-specific)
```

---

## Quick Reference

### Update Decision

```
Changed:            Action:
prereq?         →   update (MINOR|MAJOR)
api|env?        →   update (MINOR|MAJOR)
install?        →   update (MINOR|PATCH)
deps?           →   update (MINOR|MAJOR)
config?         →   update (MINOR|MAJOR)
platform?       →   update (MAJOR)
code-only?      →   no-update
tests-only?     →   no-update
```

### Version Decision

```
breaks-setup?   →   MAJOR
adds-feature?   →   MINOR
fixes-docs?     →   PATCH
```

---

## Template Placeholders

### CLAUDE_INSTALL.md Placeholders

| Placeholder | Example | Description |
|-------------|---------|-------------|
| `[PROJECT_NAME]` | `gptr-mcp` | Your project's name |
| `[DATE]` | `2025-10-25` | Current date |
| `[BASE_PROJECT_NAME]` | `Data Pipeline Framework` | If derived from another project |
| `[BASE_REPO_URL]` | `https://github.com/upstream-org/original-project` | Base repository URL |
| `[YOUR_REPO_URL]` | `https://github.com/your-org/your-project` | Your repository URL |
| `[PYTHON_VERSION]` | `3.11` | Required Python version |
| `[DATABASE]` / `[LLM_PROVIDER]` | `Neo4j` / `OpenAI` | Technologies used |
| `[CLOUD_SERVICE_URL]` | `https://console.neo4j.io` | Cloud service URLs |
| `[DOCS_URL]` | `https://docs.gptr.dev` | Documentation URL |
| `[REPO_URL]` | `https://github.com/user/project` | Repository URL |

---

## Integration with CLAUDE.md (Runtime Docs)

Templates are **separate from** runtime documentation (CLAUDE.md):

| Document | Purpose | When Used | Location |
|----------|---------|-----------|----------|
| **CLAUDE.md** | Runtime agent instructions | Every session (auto-loaded) | Project root (agnostic) |
| **CLAUDE_README.md** | Development policies | Development sessions only | Project root (project-specific) |
| **CLAUDE_INSTALL.md** | Installation guide | Setup/onboarding | Project root (project-specific) |

**Workflow**:
1. CLAUDE.md loaded at session start (agent runtime behavior)
2. Agent navigates to project for development
3. Agent reads CLAUDE_README.md (development policies)
4. Agent updates CLAUDE_INSTALL.md as needed (installation docs)

---

## Attribution

**If Derived Project**: Keep base-project refs in CLAUDE_INSTALL.md, clarify project-specific vs upstream divergence

---

**Template**: v1.2.0 | **Maintained**: Claude Code Tooling Project | **License**: Use freely
