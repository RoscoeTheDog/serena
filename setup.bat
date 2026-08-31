@echo off
REM Thin setup wrapper for the serena fork (Windows).
REM Creates/refreshes the project venv with an EDITABLE install, so the MCP server
REM always runs the code in this working tree. Re-run after pulling changes only if
REM dependencies changed (pyproject.toml); code changes need only an MCP restart.
REM No admin privileges required (per-user venv, per-user MCP registration).

setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
    echo [ERROR] uv not found on PATH. Install it first: https://docs.astral.sh/uv/
    exit /b 1
)

echo [1/3] Syncing venv (editable install + dependencies, incl. dev extras)...
uv sync --all-extras
if errorlevel 1 (
    echo [ERROR] uv sync failed.
    echo [HINT] If the error mentions serena.exe being in use: a running serena MCP
    echo [HINT] server locks the entry point. Close sessions using serena, then re-run.
    exit /b 1
)

echo [2/3] Verifying entry point...
if not exist ".venv\Scripts\serena.exe" (
    echo [ERROR] .venv\Scripts\serena.exe not found after sync.
    exit /b 1
)
".venv\Scripts\serena.exe" --version >nul 2>nul

echo [3/3] Checking MCP registration...
where claude >nul 2>nul
if errorlevel 1 (
    echo [WARN] claude CLI not found; register the MCP server manually if needed.
    goto :done
)
claude mcp get serena >nul 2>nul
if errorlevel 1 (
    echo [INFO] serena is not registered as an MCP server. Register it with:
    echo   claude mcp add --scope user serena -- "%~dp0.venv\Scripts\serena.exe" start-mcp-server --context ide-assistant
) else (
    echo [OK] serena MCP server is registered.
)

:done
echo [OK] Setup complete. Restart the serena MCP server (or start a new session) to load new code.
exit /b 0
