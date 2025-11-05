# .claude/ Directory Index

**Last Updated**: 2025-11-05 14:55
**Project**: Serena (Enhanced MCP Coding Agent)
**Organization**: EPHEMERAL-FS v3.3

## Purpose

This directory contains all agent-managed files following the EPHEMERAL-FS organizational schema from CLAUDE.md. All agent-created files MUST reside in categorized subdirectories, never in the project root.

## Directory Structure

| Category | Purpose | Files | Last Modified |
|----------|---------|-------|---------------|
| `implementation/` | Sprint tracking and task management | 1 active + archive | 2025-11-05 14:55 |

## Active Files

### implementation/index.md
- **Created**: 2025-11-05 14:55
- **Modified**: 2025-11-05 14:55
- **Size**: ~8.2 KB
- **Description**: Active sprint: "Remove Legacy .serena/ Directory Support" - 7 stories, status: active
- **Sprint Goal**: Remove backward compatibility code for legacy project-root `.serena/` directories

## Archives

### implementation/archive/2025-11-05-1455/
- **Archived**: 2025-11-05 14:55
- **Sprint**: Centralized Config Storage Refactor
- **Status**: Completed (6/6 stories)
- **Contents**: Previous sprint documentation and archive history

## Categories Explanation

### implementation/
Sprint and story tracking for structured development work. Uses living-document approach with inline status updates. Archives preserve historical sprint data.

## Security Notes

- Credential scanning enabled (dual-phase: file creation + pre-commit)
- All files scanned for: api_key, secret, password, token, bearer, auth_token patterns
- Credentials MUST be obfuscated: `sk-***REDACTED***` or `***PLACEHOLDER***`

## Restore Commands

```bash
# View current sprint
cat .claude/implementation/index.md

# View archived sprint
cat .claude/implementation/archive/2025-11-05-1455/index.md

# List all archives
ls -la .claude/implementation/archive/
```

## .gitignore Coverage

The `.claude/` directory is tracked in git but with selective ignores:
- Tracked: `implementation/`, `INDEX.md`, archive metadata
- Ignored: Temporary files, scratch work, test fixtures (when added)

---

**Note**: This INDEX.md is updated after batch operations (multiple file changes), not per-file. See CLAUDE.md EPHEMERAL-FS rules for details.
