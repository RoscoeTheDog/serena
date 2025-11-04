#!/usr/bin/env python3
"""
Kill Serena MCP Server Instances

This script identifies and terminates all running Serena MCP server processes.
It searches for Python processes running the Serena MCP server entry point.

Usage:
    python scripts/kill_serena_servers.py [--dry-run] [--force] [--verbose]

Options:
    --dry-run    Show what would be killed without actually killing
    --force      Force kill (SIGKILL) instead of graceful termination (SIGTERM)
    --verbose    Show detailed process information
"""

import argparse
import os
import sys
import psutil
from pathlib import Path


def find_serena_processes(verbose=False):
    """
    Find all Serena MCP server processes.

    Returns:
        list: List of psutil.Process objects that are Serena servers
    """
    serena_processes = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'exe']):
        try:
            cmdline = proc.info['cmdline']
            if not cmdline:
                continue

            # Convert cmdline to string for searching
            cmdline_str = ' '.join(cmdline)

            # Identify Serena processes by looking for:
            # 1. Python process
            # 2. Running serena module or mcp_server
            # 3. Or running from serena directory
            is_python = proc.info['name'] and 'python' in proc.info['name'].lower()
            is_serena = any([
                'serena' in cmdline_str.lower() and 'mcp' in cmdline_str.lower(),
                'serena.mcp_server' in cmdline_str,
                'serena/mcp_server' in cmdline_str,
                'serena\\mcp_server' in cmdline_str,
                '-m serena' in cmdline_str,
                'serena-mcp' in cmdline_str,
            ])

            if is_python and is_serena:
                serena_processes.append(proc)
                if verbose:
                    print(f"  Found: PID={proc.info['pid']}, CMD={cmdline_str[:100]}")

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return serena_processes


def kill_processes(processes, force=False, dry_run=False, verbose=False):
    """
    Kill the given processes.

    Args:
        processes: List of psutil.Process objects
        force: If True, use SIGKILL instead of SIGTERM
        dry_run: If True, don't actually kill anything
        verbose: If True, show detailed information
    """
    if not processes:
        print("✅ No Serena server processes found.")
        return

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Found {len(processes)} Serena server process(es):\n")

    for proc in processes:
        try:
            cmdline = ' '.join(proc.cmdline())
            print(f"  PID {proc.pid}: {cmdline[:80]}...")

            if verbose:
                try:
                    print(f"    - Exe: {proc.exe()}")
                    print(f"    - CWD: {proc.cwd()}")
                    print(f"    - Status: {proc.status()}")
                    print(f"    - Created: {proc.create_time()}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            print(f"  PID {proc.pid}: <access denied or process gone>")

    if dry_run:
        print(f"\n[DRY RUN] Would {'force kill (SIGKILL)' if force else 'terminate (SIGTERM)'} {len(processes)} process(es)")
        return

    print(f"\n{'Force killing (SIGKILL)' if force else 'Terminating (SIGTERM)'} {len(processes)} process(es)...")

    killed = 0
    failed = 0

    for proc in processes:
        try:
            if force:
                proc.kill()  # SIGKILL
            else:
                proc.terminate()  # SIGTERM

            killed += 1
            print(f"  ✅ {'Killed' if force else 'Terminated'} PID {proc.pid}")
        except psutil.NoSuchProcess:
            print(f"  ⚠️  PID {proc.pid} already gone")
        except psutil.AccessDenied:
            print(f"  ❌ PID {proc.pid} access denied (try running as admin/sudo)")
            failed += 1
        except Exception as e:
            print(f"  ❌ PID {proc.pid} error: {e}")
            failed += 1

    print(f"\n✅ Successfully {'killed' if force else 'terminated'}: {killed}")
    if failed > 0:
        print(f"❌ Failed: {failed}")
        sys.exit(1)


def main():
    # Fix encoding for Windows console
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    parser = argparse.ArgumentParser(
        description="Kill all Serena MCP server instances",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show what would be killed (safe)
  python scripts/kill_serena_servers.py --dry-run

  # Gracefully terminate Serena servers
  python scripts/kill_serena_servers.py

  # Force kill if processes won't terminate
  python scripts/kill_serena_servers.py --force

  # Show detailed process information
  python scripts/kill_serena_servers.py --verbose --dry-run
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be killed without actually killing'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force kill (SIGKILL) instead of graceful termination (SIGTERM)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed process information'
    )

    args = parser.parse_args()

    print("🔍 Searching for Serena MCP server processes...")

    processes = find_serena_processes(verbose=args.verbose)

    kill_processes(
        processes,
        force=args.force,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    if not args.dry_run and processes:
        print("\n💡 Tip: You may need to restart your MCP client (Claude Code) for it to reconnect.")


if __name__ == '__main__':
    main()
