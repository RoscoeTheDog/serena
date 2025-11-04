# Serena Utility Scripts

This directory contains utility scripts for managing Serena MCP servers.

## kill_serena_servers.py

Kill all running Serena MCP server instances. Useful when you need to restart servers or clean up stuck processes.

### Usage

```bash
# Safe dry run - see what would be killed
python scripts/kill_serena_servers.py --dry-run

# Gracefully terminate all Serena servers
python scripts/kill_serena_servers.py

# Force kill if processes won't terminate
python scripts/kill_serena_servers.py --force

# Show detailed process information
python scripts/kill_serena_servers.py --verbose --dry-run
```

### Quick Wrappers

**Windows:**
```cmd
scripts\kill_serena.bat
```

**Unix/Linux/macOS:**
```bash
./scripts/kill_serena.sh
```

### How It Works

The script uses **three detection methods** to reliably identify Serena MCP servers:

1. **Environment Variable** (Most Reliable)
   - Checks for `SERENA_MCP_SERVER=1` environment variable
   - Set automatically by Serena when the MCP server starts
   - **Validates** the process is actually Serena (not child processes like Pyright)
   - Child processes inherit env vars, so command line is double-checked
   - Works even if the command line is obscured

2. **Process Name** (If Available)
   - Checks if process name is `serena-mcp-server`
   - Requires `setproctitle` package (optional dependency)

3. **Command Line Pattern** (Fallback)
   - Python processes running:
     - `serena.mcp_server`
     - `-m serena`
     - `serena/mcp_server` or `serena\mcp_server`
     - Any command line containing both "serena" and "mcp"

### When to Use

- After making code changes to Serena that require a restart
- When a Serena server is stuck or hanging
- Before running tests to ensure clean environment
- When you can't differentiate which Python processes are Serena

### Notes

- Uses graceful termination (SIGTERM) by default
- Use `--force` for immediate kill (SIGKILL) if processes won't stop
- May require admin/sudo privileges on some systems
- After killing, MCP clients (like Claude Code) may need to be restarted to reconnect
