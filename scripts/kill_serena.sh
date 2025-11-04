#!/bin/bash
# Quick wrapper to kill Serena servers on Unix/Linux/macOS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python "$SCRIPT_DIR/kill_serena_servers.py" "$@"
