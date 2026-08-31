#!/usr/bin/env sh
# Thin setup wrapper for the serena fork (POSIX).
# Creates/refreshes the project venv with an EDITABLE install, so the MCP server
# always runs the code in this working tree. Re-run after pulling changes only if
# dependencies changed (pyproject.toml); code changes need only an MCP restart.
# No admin/root privileges required (per-user venv, per-user MCP registration).

set -e
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
    echo "[ERROR] uv not found on PATH. Install it first: https://docs.astral.sh/uv/"
    exit 1
fi

echo "[1/3] Syncing venv (editable install + dependencies, incl. dev extras)..."
if ! uv sync --all-extras; then
    echo "[ERROR] uv sync failed."
    echo "[HINT] If the error mentions serena.exe being in use: a running serena MCP"
    echo "[HINT] server locks the entry point. Close sessions using serena, then re-run."
    exit 1
fi

echo "[2/3] Verifying entry point..."
SERENA_BIN=".venv/bin/serena"
[ -x "$SERENA_BIN" ] || SERENA_BIN=".venv/Scripts/serena.exe"  # Git Bash on Windows
if [ ! -x "$SERENA_BIN" ]; then
    echo "[ERROR] serena entry point not found after sync."
    exit 1
fi
"$SERENA_BIN" --version >/dev/null 2>&1 || true

echo "[3/3] Checking MCP registration..."
if ! command -v claude >/dev/null 2>&1; then
    echo "[WARN] claude CLI not found; register the MCP server manually if needed."
else
    if claude mcp get serena >/dev/null 2>&1; then
        echo "[OK] serena MCP server is registered."
    else
        echo "[INFO] serena is not registered as an MCP server. Register it with:"
        echo "  claude mcp add --scope user serena -- \"$(pwd)/$SERENA_BIN\" start-mcp-server --context ide-assistant"
    fi
fi

echo "[OK] Setup complete. Restart the serena MCP server (or start a new session) to load new code."
