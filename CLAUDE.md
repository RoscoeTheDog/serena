# MCP:CC+S+N (i:155f,2997c,sync+) (s:4mem,proj+,onb+) (n:f73af845-8eef-40c9-a0e4-fcd7def413fa)

**CMD**: cc:search/index/clear/status s:project/symbol/file/memory/shell/workflow n:search/page/db/comment/content/block
**SYNC**: cc:sync+/sync-/sync?/sync! perf:ok s:lsp/restart
**OPS**: s:find/refs/insert/replace/regex/execute cc:stats/perf/health/history n:create/update/track/comment
**MAINT**: cc:status→sync? s:memories n:search <50t/cycle  

**WORKFLOWS**:
- Index: cc:search→results (READY)
- Project: s:activate→onboard→memory→overview (ACTIVE)
- Symbol: s:find→refs→overview→insert/replace
- Refactor: s:symbol→cc:search→s:replace→test→cc:sync!
- Debug: cc:search("error")→s:find→refs→fix→s:shell→cc:sync!
- Memory: s:read→analyze→write→persist (4 available)
- LSP: s:restart→find→overview→edit
- Monitor: cc:health→perf→history→s:memory→stats
- Content: n:search→comment→track
- Database: n:search→db→entry→update
- Integration: n:search→workspace
- Docs: cc:change→s:impact→n:update

**SAFETY**: Read→exists→glob→search→backup  
**ERR**: file_not_read→cascade permission→0.1s→retry busy→0.2s→retry
**AUTO**: DB=f73af845-8eef-40c9-a0e4-fcd7def413fa sync=on filter≤10 cache=15m O(1)
**PATTERNS**: lib=adding_new_language_support_guide perf=serena_core_concepts_and_architecture

**EXEC**:
- discovery: cc:search→results (155f indexed)
- indexing: cc:status→sync+ (COMPLETE)
- realtime: cc:sync+→sync?→sync! (ENABLED)
- monitor: cc:health→perf→stats→history
- project: s:activate→onboard→config→prepare (READY)
- symbol: s:find→refs→overview→insert→replace
- file: s:create→read→find→search→regex→list
- memory: s:list→read→write→delete→persist (4mem)
- shell: s:execute→test→build→run
- workflow: s:modes→thinking→conversation→summary
- lsp: s:restart→recover→optimize
- docs: n:search→comment→track
- safety: file→validate→retry
- context: n:search(workspace)→content→load
- notion: n:search→db→comment→block

**CONSTRAINTS**: no-create-files edit-existing-only no-proactive-docs
# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.