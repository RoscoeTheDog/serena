# Implementation Sprint Management

This directory contains living documentation for implementation sprints.

## Structure

- **index.md** - Primary tracking document with all stories and current status
- **archive/** - Historical implementation documents from completed work
- **stories/** - (Created on demand) Detailed breakdown documents for complex stories

## Agent Workflow

### Before Starting Work
1. Read `index.md` to understand current sprint state
2. Find next `unassigned` story in sequence
3. Update story status to `in_progress` immediately
4. Begin implementation

### During Work
1. Update story inline in `index.md` as progress occurs
2. Check off acceptance criteria as completed
3. Add notes to story's "Implementation Notes" section
4. If errors occur, set status to `error` and create Remediation Plan

### After Completing Work
1. Update story status to `completed` immediately
2. Check off sprint completion checklist items if applicable
3. Move to next story in sequence
4. Update sprint metrics

### On Error
1. Set story status to `error`
2. Add `## Remediation Plan` section to story with:
   - Root cause analysis
   - Proposed fix
   - Impact assessment
3. **HALT** and wait for user approval
4. On approval: reorganize stories if needed, continue
5. On rejection: wait for user guidance

## Status Values

- `unassigned` - Not yet started (default for new stories)
- `in_progress` - Currently being worked on (only ONE at a time)
- `completed` - Successfully finished and verified
- `error` - Failed, needs remediation plan and user approval
- `blocked` - Waiting on external dependency
- `superseded` - Replaced by breakdown stories (when story split into sub-stories)

## Story Numbering

- Major stories: `1`, `2`, `3`
- Sub-stories: `1.1`, `1.2`, `1.3`
- Tasks: `1.1.1`, `1.1.2`, `1.1.3`
- Inserted stories use next sequential number

## Sprint Completion

Sprint is complete when:
- All stories in `completed` or `blocked` state
- No stories in `in_progress` or `error` state
- All acceptance criteria checked
- Sprint completion checklist 100% checked
- index.md contains final summary with timestamp

## Archive Policy

When starting a new sprint:
1. Archive old .md files to `archive/{YYYY-MM-DD-HHmm}/`
2. Create archive README explaining what was archived
3. Start fresh with new `index.md`

## Current Sprint

**Token Efficiency Enhancements Sprint**
- Start: 2025-01-04
- Status: In Progress
- Stories: 10 total (4 Phase 1, 4 Phase 2, 2 Phase 3)
- Target: 50-75% token reduction, zero accuracy loss

See `index.md` for full details.
