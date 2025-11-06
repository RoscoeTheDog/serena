# Migration Guide: Legacy .serena/ Directory to Centralized Storage

## Overview

Starting with version 0.2.0, Serena has removed support for legacy `.serena/` directories in project roots. All project-specific data (configurations and memories) is now stored in a centralized location under `~/.serena/projects/{project-id}/`.

This guide explains:
- **Why** migration is necessary
- **How** to migrate your existing projects
- **What** gets migrated
- **How** to verify migration success
- **How** to rollback if needed

## Why Migration is Necessary

### Previous Architecture (Legacy)

In earlier versions, Serena created a `.serena/` directory in every project root:

```
my-project/
├── .serena/
│   ├── project.yml        # Project configuration
│   ├── memories/          # Project-specific memories
│   └── .gitignore
└── ... (your project files)
```

### Problems with Legacy Architecture

1. **File Lock Issues**: Serena kept file handles open on `.serena/` directories, preventing cleanup
2. **Project Pollution**: Every project had a `.serena/` directory cluttering the workspace
3. **Scattered Backups**: Configuration and memories scattered across multiple projects
4. **Maintenance Complexity**: Dual-path logic in core modules added technical debt

### New Architecture (Centralized)

All project data is now stored in your home directory:

```
~/.serena/
├── serena_config.yml      # Global Serena configuration
└── projects/
    ├── {project-id-1}/
    │   ├── project.yml
    │   └── memories/
    ├── {project-id-2}/
    │   ├── project.yml
    │   └── memories/
    └── ...
```

### Benefits

1. ✅ **Clean Projects**: No `.serena/` pollution in project roots
2. ✅ **Easy Backups**: Single `~/.serena/` directory to backup
3. ✅ **No File Locks**: Serena no longer keeps handles open on project directories
4. ✅ **Better Organization**: All Serena data in one centralized location

## How to Migrate

### Automatic Migration (Recommended)

Serena provides a migration script that automatically discovers and migrates all legacy projects:

```bash
# From the serena repository directory
uv run python scripts/migrate_legacy_serena.py

# Or with uvx (from anywhere)
uvx --from git+https://github.com/oraios/serena serena migrate-legacy
```

#### Migration Options

```bash
# Dry-run mode (preview without making changes)
python scripts/migrate_legacy_serena.py --dry-run

# Search specific directories
python scripts/migrate_legacy_serena.py --search-paths ~/projects ~/work

# JSON output (for scripting)
python scripts/migrate_legacy_serena.py --format json

# Skip backup creation (not recommended)
python scripts/migrate_legacy_serena.py --no-backup
```

### Manual Migration

If you prefer to migrate manually:

1. **Identify your project ID**:
   ```bash
   # The project ID is based on the absolute path hash
   # For project at /home/user/my-project:
   # project-id = md5("/home/user/my-project")[:16]
   ```

2. **Create centralized directory**:
   ```bash
   mkdir -p ~/.serena/projects/{project-id}
   ```

3. **Copy project.yml**:
   ```bash
   cp /path/to/project/.serena/project.yml ~/.serena/projects/{project-id}/
   ```

4. **Copy memories**:
   ```bash
   cp -r /path/to/project/.serena/memories ~/.serena/projects/{project-id}/
   ```

5. **Backup legacy directory**:
   ```bash
   cd /path/to/project
   tar -czf .serena.backup-$(date +%Y%m%d-%H%M%S).tar.gz .serena/
   ```

6. **Remove legacy directory** (optional):
   ```bash
   rm -rf /path/to/project/.serena/
   ```

## What Gets Migrated

### Files Migrated

| Source | Destination | Description |
|--------|-------------|-------------|
| `{project}/.serena/project.yml` | `~/.serena/projects/{id}/project.yml` | Project configuration |
| `{project}/.serena/memories/*.md` | `~/.serena/projects/{id}/memories/*.md` | Memory files |

### Files NOT Migrated

- **Cache files**: Transient data, will be regenerated
- **Log files**: Session-specific, no longer needed
- **`.gitignore`**: No longer needed in centralized location

### Backup Creation

The migration script automatically creates a backup archive before migration:

```
{project_root}/.serena.backup-{timestamp}.tar.gz
```

This archive contains the complete `.serena/` directory and can be used for rollback.

## Verifying Migration Success

### 1. Check Migration Report

After running the migration script, review the output:

```
=== Migration Summary ===
Total projects found: 3
Successfully migrated: 3
Failed migrations: 0
Skipped (already migrated): 0

✅ All projects migrated successfully!

Backups created in project roots as .serena.backup-*.tar.gz
You can safely delete legacy .serena/ directories after verification.
```

### 2. Verify Centralized Storage

Check that your project data exists in centralized storage:

```bash
# List all migrated projects
ls ~/.serena/projects/

# Check specific project
ls ~/.serena/projects/{project-id}/
# Should see: project.yml, memories/
```

### 3. Activate Project in Serena

Activate your project and verify it works:

```python
# In your Serena client (Claude Code, etc.)
# Ask the agent to:
"Activate the project /path/to/my-project"
"List memories"
```

If you see your memories listed, migration was successful!

### 4. Check for Legacy Directories

Verify legacy directories are no longer in use:

```bash
# List any remaining .serena directories
find ~/projects -type d -name ".serena" 2>/dev/null
```

## Rollback Instructions

If you need to rollback to legacy storage:

### 1. Restore from Backup

```bash
cd /path/to/project
tar -xzf .serena.backup-{timestamp}.tar.gz
```

### 2. Downgrade Serena

```bash
# Install previous version (0.1.4 or earlier)
uvx --from git+https://github.com/oraios/serena@v0.1.4 serena start-mcp-server
```

### 3. Verify Legacy Structure

```bash
ls /path/to/project/.serena/
# Should see: project.yml, memories/, .gitignore
```

## Frequently Asked Questions

### Q: Will my existing projects stop working?

**A**: No, if you're using Serena 0.1.x or earlier. Starting with 0.2.0, you **must** migrate to continue using your projects.

### Q: What happens to my memories?

**A**: All memories are copied to `~/.serena/projects/{project-id}/memories/`. The migration script validates file integrity with checksums.

### Q: Can I migrate only some projects?

**A**: Yes! The migration script supports `--search-paths` to target specific directories:

```bash
python scripts/migrate_legacy_serena.py --search-paths ~/work-projects
```

### Q: What if migration fails for a project?

**A**: The script reports failures and continues with other projects. Check the error message, fix the issue (e.g., permissions), and re-run. The script skips already-migrated projects automatically.

### Q: How do I migrate projects on multiple machines?

**A**: Run the migration script on each machine, or copy `~/.serena/projects/` between machines:

```bash
# On machine 1
tar -czf serena-projects.tar.gz ~/.serena/projects/

# On machine 2
tar -xzf serena-projects.tar.gz -C ~/
```

### Q: Can I delete `.serena/` directories after migration?

**A**: Yes, after verifying migration success. Keep the backup archives (`.serena.backup-*.tar.gz`) for safety.

### Q: What about projects in `.gitignore`?

**A**: Legacy `.serena/` directories were already in `.gitignore`. After migration, you can add `/.serena/` and `/.serena.backup-*.tar.gz` to your project's `.gitignore` to ignore any leftover directories.

### Q: Do I need to update my MCP client configuration?

**A**: No! The `--project` path argument remains the same (project root path). Serena automatically resolves to centralized storage.

### Q: What if I have uncommitted changes in `.serena/`?

**A**: The migration script copies files, it doesn't use git. Any uncommitted changes in `.serena/` will be migrated. However, since `.serena/` is typically gitignored, this shouldn't be an issue.

### Q: How do I verify backup integrity?

**A**: Extract the backup to a temporary directory and compare:

```bash
mkdir /tmp/verify
tar -xzf .serena.backup-{timestamp}.tar.gz -C /tmp/verify
diff -r /tmp/verify/.serena {project}/.serena
```

### Q: Can I customize the backup location?

**A**: Currently, backups are always created in project roots. You can move them after migration:

```bash
mkdir -p ~/serena-backups
mv /path/to/project/.serena.backup-*.tar.gz ~/serena-backups/
```

## Troubleshooting

### Migration Script Fails with "Permission Denied"

**Cause**: Insufficient permissions to read legacy `.serena/` or write to `~/.serena/`

**Solution**:
```bash
# Fix permissions on legacy directory
chmod -R u+rw /path/to/project/.serena/

# Ensure ~/.serena/ is writable
chmod -R u+rw ~/.serena/
```

### Project Activation Fails After Migration

**Cause**: Project configuration is invalid or missing

**Solution**:
```bash
# Check configuration exists
cat ~/.serena/projects/{project-id}/project.yml

# If missing, restore from backup
tar -xzf /path/to/project/.serena.backup-{timestamp}.tar.gz .serena/project.yml -O > ~/.serena/projects/{project-id}/project.yml
```

### "Project Not Found" Error

**Cause**: Project ID mismatch (project path changed)

**Solution**:
```bash
# Re-activate project with current path
# In Serena client:
"Activate the project /current/path/to/project"
```

### Memories Not Showing Up

**Cause**: Memories directory not migrated or empty

**Solution**:
```bash
# Check memories exist
ls ~/.serena/projects/{project-id}/memories/

# If missing, restore from backup
tar -xzf /path/to/project/.serena.backup-{timestamp}.tar.gz .serena/memories -O | tar -xz -C ~/.serena/projects/{project-id}/
```

## Getting Help

If you encounter issues not covered in this guide:

1. **Check migration logs**: The script outputs detailed error messages
2. **Review backup archives**: Ensure backups were created successfully
3. **Report issues**: [GitHub Issues](https://github.com/oraios/serena/issues)
4. **Community support**: [Serena Discussions](https://github.com/oraios/serena/discussions)

## Summary Checklist

- [ ] Run migration script: `python scripts/migrate_legacy_serena.py`
- [ ] Review migration report (all projects migrated?)
- [ ] Verify centralized storage: `ls ~/.serena/projects/`
- [ ] Test project activation in Serena
- [ ] Check memories are accessible
- [ ] Keep backup archives for safety
- [ ] (Optional) Remove legacy `.serena/` directories after verification
- [ ] Update `.gitignore` to ignore legacy `.serena/` directories

## Next Steps

After successful migration:

1. **Update Serena**: Ensure you're using version 0.2.0 or later
2. **Backup centralized storage**: Add `~/.serena/` to your regular backups
3. **Remove legacy directories**: After verification, clean up old `.serena/` directories
4. **Enjoy cleaner projects**: No more `.serena/` pollution in project roots!

---

**Version**: 1.0.0
**Last Updated**: 2025-11-05
**Serena Version**: 0.2.0+
