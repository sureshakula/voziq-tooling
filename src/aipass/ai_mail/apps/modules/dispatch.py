# =================== AIPass ====================
# Name: dispatch.py
# Description: Dispatch Module
# Version: 3.0.0
# Created: 2026-02-02
# Modified: 2026-02-02
# =============================================

"""
Dispatch Module

Orchestrates dispatch commands: status tracking and daemon management.
Delegates all business logic to handlers.
"""

import sys
from pathlib import Path
from typing import List

from aipass.prax.apps.modules.logger import system_logger as logger
from aipass.cli.apps.modules import console
from aipass.ai_mail.apps.handlers.dispatch.status import (
    load_dispatch_log,
    check_pid_status,
    calculate_age
)


def print_help() -> None:
    """Print help for dispatch commands."""
    help_text = """
Dispatch Module - Agent dispatch management

COMMANDS:
  dispatch status    - Show last 5 dispatch spawns with current status
  dispatch daemon    - Start the continuous dispatch daemon
  dispatch wake      - Manually wake a branch (spawn agent without daemon)

WAKE:
  drone wake @branch                  - Wake branch with default inbox check
  drone wake @branch "custom msg"     - Wake branch with custom prompt
  ai_mail dispatch wake @branch       - Same, via ai_mail directly

DAEMON:
  The daemon polls branch inboxes for --dispatch emails and spawns agents.
  Run as: ai_mail dispatch daemon
  Or standalone: python3 apps/handlers/dispatch/daemon.py

  Kill switch: touch <repo_root>/.aipass/autonomous_pause
  Config: safety_config.json

EXAMPLE:
  ai_mail dispatch status

  DISPATCH STATUS
  ────────────────────────────────────
  @flow    PID 108957  RUNNING    2m ago
  @ai_mail PID 85997   COMPLETED  10m ago
  ────────────────────────────────────
  Active: 1  |  Total: 2
"""
    console.print(help_text)


def handle_command(command: str, args: List[str]) -> bool:
    """
    Handle dispatch commands.

    Args:
        command: Command name
        args: Command arguments

    Returns:
        True if command handled, False otherwise
    """
    if command != "dispatch":
        return False

    if args and args[0] in ['--help', '-h', 'help']:
        print_help()
        return True

    if not args:
        print_help()
        return True

    subcommand = args[0]

    if subcommand == "status":
        return _orchestrate_status()
    elif subcommand == "daemon":
        return _orchestrate_daemon()
    elif subcommand == "wake":
        return _orchestrate_wake(args[1:])
    else:
        console.print(f"[red]Unknown dispatch subcommand: {subcommand}[/red]")
        print_help()
        return False


def _orchestrate_status() -> bool:
    """Orchestrate dispatch status display."""
    logger.info("[dispatch] Showing dispatch status")

    dispatches = load_dispatch_log()

    if not dispatches:
        console.print("\n[dim]No dispatches recorded yet.[/dim]")
        return True

    recent = dispatches[-5:][::-1]

    console.print("\n[bold]DISPATCH STATUS[/bold]")
    console.print("─" * 50)

    active_count = 0
    for entry in recent:
        branch = entry.get("branch", "unknown")
        pid = entry.get("pid")
        timestamp = entry.get("timestamp", "")
        spawn_status = entry.get("status", "unknown")

        if spawn_status == "spawned" and pid:
            current_status = check_pid_status(pid)
        elif spawn_status == "failed":
            current_status = "FAILED"
        else:
            current_status = "UNKNOWN"

        if current_status == "RUNNING":
            active_count += 1

        age_str = calculate_age(timestamp)

        if current_status == "RUNNING":
            status_display = "[green]RUNNING[/green]"
        elif current_status == "COMPLETED":
            status_display = "[dim]COMPLETED[/dim]"
        elif current_status == "FAILED":
            status_display = "[red]FAILED[/red]"
        else:
            status_display = f"[yellow]{current_status}[/yellow]"

        pid_display = f"PID {pid}" if pid else "NO PID"
        console.print(f"  {branch:<12} {pid_display:<12} {status_display:<18} {age_str}")

    console.print("─" * 50)
    console.print(f"[dim]Active: {active_count}  |  Total: {len(recent)}[/dim]\n")

    return True


def _orchestrate_wake(args: List[str]) -> bool:
    """Orchestrate manual branch wake."""
    if not args or args[0] in ['--help', '-h', 'help']:
        console.print("\n[bold]Wake - Manual branch spawn[/bold]")
        console.print("  Usage: dispatch wake @branch [\"custom message\"]")
        console.print("  Or:    drone wake @branch [\"custom message\"]\n")
        return True

    # Parse --fresh and --sender flags
    use_fresh = "--fresh" in args
    use_sender = "@dev_central"
    filtered = []
    i = 0
    while i < len(args):
        if args[i] == "--fresh":
            i += 1
            continue
        if args[i] == "--sender" and i + 1 < len(args):
            use_sender = args[i + 1]
            i += 2
            continue
        filtered.append(args[i])
        i += 1

    if not filtered:
        console.print("[red]Missing branch argument[/red]")
        return False

    branch_email = filtered[0]
    custom_message = filtered[1] if len(filtered) > 1 else None

    logger.info(f"[dispatch] Manual wake requested for {branch_email}")
    console.print(f"\n⏳ Waking {branch_email}...")

    from aipass.ai_mail.apps.handlers.dispatch.wake import wake_branch
    dispatch_status, success = wake_branch(
        branch_email, custom_message, fresh=use_fresh, sender=use_sender
    )

    # Print step-by-step status
    console.print(dispatch_status.format())

    return success


def _orchestrate_daemon() -> bool:
    """Orchestrate daemon startup."""
    logger.info("[dispatch] Starting dispatch daemon")
    console.print("\n[bold]Starting dispatch daemon...[/bold]")

    from aipass.ai_mail.apps.handlers.dispatch.daemon import run_daemon
    run_daemon()
    return True


def print_introspection():
    """Display module introspection info."""
    console.print()
    console.print("dispatch Module")
    console.print("Orchestrates dispatch commands: status tracking, daemon management, and manual branch wake.")
    console.print()
    console.print("Connected Handlers:")
    console.print("  handlers/dispatch/")
    console.print("    - status.py (load_dispatch_log — load dispatch log entries)")
    console.print("    - status.py (check_pid_status — check if a spawned process is still running)")
    console.print("    - status.py (calculate_age — calculate age string from timestamp)")
    console.print("    - wake.py (wake_branch — manually wake a branch by spawning an agent)")
    console.print("    - daemon.py (run_daemon — start the continuous dispatch daemon)")
    console.print()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print_help()
        sys.exit(0)

    if sys.argv[1] in ['--help', '-h', 'help']:
        print_help()
        sys.exit(0)

    command = sys.argv[1]
    remaining_args = sys.argv[2:] if len(sys.argv) > 2 else []

    if handle_command(command, remaining_args):
        sys.exit(0)
    else:
        sys.exit(1)
