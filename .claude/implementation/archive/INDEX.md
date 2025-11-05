# Implementation Archive Index

## Archives

### 2025-11-05-1455 - Centralized Config Storage Refactor
**Archived**: 2025-11-05 14:55
**Status**: Completed
**Sprint Goal**: Migrate project-specific data from `{project_root}/.serena/` to centralized `~/.serena/projects/{project-id}/`

**Stories Completed**: 6/6
- Story 1: Design centralized storage schema (completed)
- Story 2: Implement Path Resolution Helpers (completed)
- Story 3: Add MCP Config Management Tools (completed)
- Story 4: Refactor ProjectConfig to Use Centralized Paths (completed)
- Story 5: Refactor MemoriesManager to Use Centralized Paths (completed)
- Story 6: Update Project Initialization Logic (completed)

**Duration**: Nov 4-5, 2025
**Outcome**: Successfully migrated to centralized storage with full backward compatibility

**Restore Command**:
```bash
# To view archived sprint details:
cat .claude/implementation/archive/2025-11-05-1455/index.md
```

---

**Archive Structure**:
```
archive/
└── 2025-11-05-1455/
    ├── index.md       # Centralized Config Storage Refactor sprint
    └── archive/       # Historical archives from old sprints
```
