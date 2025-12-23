# Manual Testing Guide for Auto-Onboarding

**Purpose**: Step-by-step manual testing for auto-onboarding after MCP restart
**Prerequisites**: MCP server restarted with Sessions 1-2 code changes
**Date**: 2025-11-03

---

## Setup Instructions

### 1. Restart MCP Server

The auto-onboarding code is implemented but requires an MCP server restart to take effect:

```bash
# Stop current MCP server (Ctrl+C or kill process)
# Restart via Claude Code or manually:
serena-mcp-server
```

### 2. Create Isolated Test Environment

**IMPORTANT**: Do not use production GitHub repositories for testing. Create an isolated test environment:

```bash
# Create test directory on desktop
mkdir ~/Desktop/test_serena_languages
cd ~/Desktop/test_serena_languages

# Clone sample repos for testing (examples)
git clone --depth 1 https://github.com/fastapi/fastapi.git python-fastapi
git clone --depth 1 https://github.com/sindresorhus/got.git typescript-got
git clone --depth 1 https://github.com/gorilla/mux.git go-mux
```

**Test Directory:** `C:\Users\Admin\Desktop\test_serena_languages\`

This isolates testing from your active development repositories.

### 3. Install Dependencies (if running pytest)

```bash
cd C:\Users\Admin\Documents\GitHub\serena
pip install -e ".[dev]"
```

### 4. Run Integration Tests (Optional)

After MCP restart:

```bash
pytest test/serena/tools/test_auto_onboarding_integration.py -v
```

---

## Manual Test Cases

### Test 1: Node.js Project with npm

**Setup:**
```bash
mkdir test_nodejs_project
cd test_nodejs_project
git init
git config user.email "test@test.com"
git config user.name "Test User"
```

Create `package.json`:
```json
{
  "name": "test-nodejs",
  "version": "1.0.0",
  "scripts": {
    "start": "node index.js",
    "test": "jest",
    "build": "webpack",
    "lint": "eslint ."
  },
  "dependencies": {
    "react": "^18.2.0",
    "express": "^4.18.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "jest": "^29.0.0",
    "eslint": "^8.0.0"
  }
}
```

Create `.eslintrc.json`:
```json
{
  "extends": "eslint:recommended",
  "rules": {
    "semi": ["error", "always"]
  }
}
```

**Test via MCP:**
```
User: Activate the project at [path to test_nodejs_project]
```

**Expected Results:**
- ✓ Project activated successfully
- ✓ Auto-onboarding message shows:
  - "Auto-onboarded project (created 4 memories)"
  - Detected tech stack: "Node.js/npm, React, TypeScript"
  - Found command sources
- ✓ Memories created:
  - `project_overview.md` - mentions tech stack
  - `suggested_commands.md` - includes npm scripts (start, test, build, lint)
  - `code_style_and_conventions.md` - mentions ESLint
  - `task_completion_checklist.md` - has testing/linting tasks

**Verify Memory Quality:**
```
User: Read memory project_overview.md
```
- Should show: Node.js/npm, React, TypeScript in tech stack
- Should mention platform (Windows)

```
User: Read memory suggested_commands.md
```
- Should list: `npm start`, `npm test`, `npm run build`, `npm run lint`
- Commands should be formatted clearly with descriptions

```
User: Read memory code_style_and_conventions.md
```
- Should mention ESLint configuration
- Should note `.eslintrc.json` presence

---

### Test 2: Python Poetry Project

**Setup:**
```bash
mkdir test_python_project
cd test_python_project
git init
git config user.email "test@test.com"
git config user.name "Test User"
```

Create `pyproject.toml`:
```toml
[tool.poetry]
name = "test-python"
version = "0.1.0"
description = "Test Python project"

[tool.poetry.dependencies]
python = "^3.11"
requests = "^2.31.0"
fastapi = "^0.100.0"

[tool.poetry.scripts]
start = "test_python.main:main"
test = "pytest tests/"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
select = ["E", "F", "I"]
```

**Test via MCP:**
```
User: Activate the project at [path to test_python_project]
```

**Expected Results:**
- ✓ Detected tech stack includes "Python/Poetry" or "Python"
- ✓ Memories created: 4 (overview, commands, code_style, checklist)
- ✓ Commands memory shows Poetry scripts: `poetry run start`, `poetry run test`
- ✓ Code style memory mentions Black and Ruff with line-length settings

---

### Test 3: Rust Cargo Project

**Setup:**
```bash
mkdir test_rust_project
cd test_rust_project
git init
git config user.email "test@test.com"
git config user.name "Test User"
```

Create `Cargo.toml`:
```toml
[package]
name = "test-rust"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
tokio = { version = "1.0", features = ["full"] }
```

**Test via MCP:**
```
User: Activate the project at [path to test_rust_project]
```

**Expected Results:**
- ✓ Detected tech stack: "Rust/Cargo"
- ✓ Commands memory includes standard Cargo commands:
  - `cargo build`, `cargo test`, `cargo run`, `cargo check`, `cargo clippy`, `cargo fmt`
- ✓ Checklist includes Rust-specific tasks

---

### Test 4: Project with Makefile

**Setup:**
```bash
mkdir test_make_project
cd test_make_project
git init
git config user.email "test@test.com"
git config user.name "Test User"
```

Create `Makefile`:
```makefile
.PHONY: all build test clean install

all: build test

build:
	@echo "Building project..."
	gcc -o app main.c

test:
	@echo "Running tests..."
	./run_tests.sh

clean:
	rm -f app *.o

install: build
	cp app /usr/local/bin/
```

**Test via MCP:**
```
User: Activate the project at [path to test_make_project]
```

**Expected Results:**
- ✓ Detected tech stack includes "Make"
- ✓ Commands memory lists Makefile targets: all, build, test, clean, install
- ✓ Commands show as `make build`, `make test`, etc.

---

### Test 5: Multi-Language Project (Node.js + Docker)

**Setup:**
```bash
mkdir test_multi_project
cd test_multi_project
git init
git config user.email "test@test.com"
git config user.name "Test User"
```

Create `package.json`:
```json
{
  "name": "multi-project",
  "version": "1.0.0",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  }
}
```

Create `Dockerfile`:
```dockerfile
FROM node:18
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
CMD ["npm", "start"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "3000:3000"
```

**Test via MCP:**
```
User: Activate the project at [path to test_multi_project]
```

**Expected Results:**
- ✓ Detected tech stack: "Node.js/npm, Docker, Docker Compose"
- ✓ Commands include both npm scripts and Docker commands
- ✓ Overview mentions multiple technologies

---

### Test 6: Already Onboarded Project (Skip Test)

**Setup:**
Use any project from Test 1-5 after it's already been onboarded once.

**Test via MCP:**
```
User: Activate the project at [path to previously activated project]
```

**Expected Results:**
- ✓ Project activates successfully
- ✓ **NO** auto-onboarding performed
- ✓ Message says: "Project already onboarded (N memories available)"
- ✓ No new memories created
- ✓ Existing memories still listed

**Verify:**
```
User: List available memories
```
- Should show same memories as before (not duplicated)

---

### Test 7: Minimal Project (No Config Files)

**Setup:**
```bash
mkdir test_minimal_project
cd test_minimal_project
git init
git config user.email "test@test.com"
git config user.name "Test User"
echo "# Minimal Project" > README.md
```

**Test via MCP:**
```
User: Activate the project at [path to test_minimal_project]
```

**Expected Results:**
- ✓ Project activates successfully (no crash)
- ✓ Auto-onboarding completes
- ✓ Tech stack shows "Unknown"
- ✓ Minimal memories created (at least overview and checklist)
- ✓ Commands memory may be empty or have generic suggestions

---

### Test 8: Malformed JSON (Error Handling)

**Setup:**
```bash
mkdir test_malformed_project
cd test_malformed_project
git init
git config user.email "test@test.com"
git config user.name "Test User"
```

Create `package.json` with invalid JSON:
```json
{
  "name": "test",
  "version": 1.0.0,
  "scripts": {
    "start": "node index.js"
}
```

**Test via MCP:**
```
User: Activate the project at [path to test_malformed_project]
```

**Expected Results:**
- ✓ Project activates successfully (graceful error handling)
- ✓ Auto-onboarding completes (may have partial detection)
- ✓ No crash or error message to user
- ✓ Tech stack may be "Unknown" or partial
- ✓ Memories still created with available information

---

### Test 9: TypeScript + Next.js Project (Framework Detection)

**Setup:**
```bash
mkdir test_nextjs_project
cd test_nextjs_project
git init
git config user.email "test@test.com"
git config user.name "Test User"
```

Create `package.json`:
```json
{
  "name": "nextjs-app",
  "version": "0.1.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/react": "^18.2.0",
    "eslint": "^8.0.0",
    "eslint-config-next": "^14.0.0"
  }
}
```

Create `.prettierrc`:
```json
{
  "semi": true,
  "singleQuote": true,
  "printWidth": 100
}
```

**Test via MCP:**
```
User: Activate the project at [path to test_nextjs_project]
```

**Expected Results:**
- ✓ Detected tech stack: "Node.js/npm, React, Next.js, TypeScript"
- ✓ Commands include all Next.js scripts: dev, build, start, lint
- ✓ Code style memory mentions both ESLint and Prettier
- ✓ Framework-specific patterns detected (Next.js recognized)

---

## Performance Testing

### Test 10: Measure Activation Overhead

**Goal**: Verify auto-onboarding adds <300ms overhead

**Manual Measurement:**
```
User: Activate the project at [path to test project] and tell me how long it took
```

Use MCP tool timing if available, or manually time the response.

**Expected:**
- Total activation time: <1 second for small projects
- Auto-onboarding overhead: <300ms (ideally <200ms)

**Profiling (if needed):**
```python
# Add to ActivateProjectTool._auto_onboard_project():
import time
start = time.perf_counter()
# ... existing code ...
end = time.perf_counter()
print(f"Auto-onboarding took {(end - start) * 1000:.1f}ms")
```

---

## Edge Case Testing

### Test 11: Large Makefile (>500 lines)

Create a Makefile with 600+ lines and many targets. Verify:
- ✓ Parsing completes without timeout
- ✓ Only first 500 lines parsed (or reasonable limit)
- ✓ Common targets detected

### Test 12: Empty package.json

Create `package.json`:
```json
{}
```

Verify:
- ✓ No crash
- ✓ Node.js/npm detected from file presence
- ✓ Commands memory notes "No scripts defined"

### Test 13: Permission Denied (File Read Error)

On Unix/Linux, create a project with unreadable config:
```bash
chmod 000 package.json
```

Verify:
- ✓ Activation succeeds
- ✓ Auto-onboarding handles error gracefully
- ✓ Partial detection still works for other files

---

## Acceptance Criteria Checklist

After completing manual tests:

- [ ] All 9 basic test scenarios pass (Tests 1-9)
- [ ] Performance is acceptable (<300ms overhead) - Test 10
- [ ] Edge cases handled gracefully (Tests 11-13)
- [ ] Memory quality is good (readable, accurate, useful)
- [ ] No false positives in tech stack detection
- [ ] No crashes or errors during any test
- [ ] Already-onboarded projects skip auto-onboarding correctly
- [ ] All detected information is accurate

---

## Bug Reporting Template

If issues found during testing, document as:

```markdown
### Bug #N: [Short Description]

**Test Case**: Test X - [Name]
**Steps to Reproduce**:
1. ...
2. ...

**Expected**: ...
**Actual**: ...
**Error Messages**: ...
**Impact**: High/Medium/Low
**Suggested Fix**: ...
```

---

## Next Steps After Testing

1. Mark integration test tasks complete in master plan
2. Document any bugs found
3. Fix critical bugs (blocking issues)
4. Update master plan with test results
5. Proceed to Session 4: Documentation & Rollout

---

**Testing Status**: Ready to begin after MCP restart
**Estimated Time**: 1-2 hours for full manual testing
**Date**: 2025-11-03
