#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: standards_verify.py - Seed Sync Verification Module
# Date: 2025-11-25
# Version: 0.1.0
# Category: seed/standards
#
# CHANGELOG (Max 5 entries):
#   - v0.1.0 (2025-11-25): Initial implementation - verify seed sync status
#
# CODE STANDARDS:
#   - Checks for deprecated patterns in codebase
#   - Verifies file freshness and consistency
#   - Validates help text accuracy
# =============================================

"""
Standards Verify Module

Verifies that seed branch is in sync with recent changes.
Checks for stale patterns, file freshness, and help consistency.

Run: python3 seed.py verify
"""

import sys
from pathlib import Path
from typing import List
from datetime import datetime

# =============================================================================
# INFRASTRUCTURE SETUP
# =============================================================================

AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))

# =============================================================================
# IMPORTS
# =============================================================================

# Prax logger (system-wide, always first)
from prax.apps.modules.logger import system_logger as logger

# JSON handler for tracking
from seed.apps.handlers.json import json_handler

# CLI services (display/output formatting)
from cli.apps.modules import console

# Verification orchestrator handler
from seed.apps.handlers.verify.orchestrator import run_verification


# =============================================================================
# COMMAND HANDLER
# =============================================================================

def handle_command(command: str, args: List[str]) -> bool:
    """
    Handle 'verify' command

    Args:
        command: Command name
        args: Additional arguments

    Returns:
        True if handled, False if not this module's command
    """
    if command != "verify":
        return False

    # Check for help flag
    if args and args[0] in ['--help', '-h', 'help']:
        print_help()
        return True

    # Log verification start
    json_handler.log_operation(
        "standards_verify_started",
        {"timestamp": datetime.now().isoformat()}
    )

    # Run verification
    result = run_verification()

    # Log completion
    json_handler.log_operation(
        "standards_verify_completed",
        {
            "passed": result['passed'],
            "total": result['total'],
            "score": result['score']
        }
    )

    return True


def print_help():
    """Print help information"""
    console.print()
    console.print("[bold cyan]Standards Verify Module[/bold cyan]")
    console.print("Seed Sync Verification - Check for stale patterns and outdated files")
    console.print()

    console.print("[yellow]COMMANDS:[/yellow]")
    console.print("  Commands: verify, --help")
    console.print()
    console.print("  [cyan]verify[/cyan]  - Run all verification checks")
    console.print()

    console.print("[yellow]USAGE:[/yellow]")
    console.print("  [dim]# Via drone[/dim]")
    console.print("  drone @seed verify")
    console.print()
    console.print("  [dim]# Direct execution[/dim]")
    console.print("  python3 seed.py verify")
    console.print("  python3 seed.py verify --help")
    console.print()

    console.print("[yellow]CHECKS PERFORMED:[/yellow]")
    console.print("  [green]1.[/green] Stale Pattern Check")
    console.print("     [dim]• Searches for deprecated flags (--verbose, --full)[/dim]")
    console.print("     [dim]• Reports file:line where found[/dim]")
    console.print()
    console.print("  [green]2.[/green] File Freshness Check")
    console.print("     [dim]• Compares modification dates of key files[/dim]")
    console.print("     [dim]• Checks if README.md is outdated[/dim]")
    console.print("     [dim]• Verifies SEED.local.json was updated today[/dim]")
    console.print()
    console.print("  [green]3.[/green] Help Consistency Check")
    console.print("     [dim]• Verifies seed.py doesn't mention removed flags[/dim]")
    console.print("     [dim]• Ensures help text is accurate[/dim]")
    console.print()
    console.print("  [green]4.[/green] Command Consistency Check")
    console.print("     [dim]• Validates flag documentation across module.py, handler, README[/dim]")
    console.print("     [dim]• Catches flags that exist but aren't documented everywhere[/dim]")
    console.print()
    console.print("  [green]5.[/green] Checker-Doc Sync Check")
    console.print("     [dim]• Verifies checker count matches README, SEED.id.json, seed.py[/dim]")
    console.print("     [dim]• Checks CODE_STANDARDS docs exist for each checker[/dim]")
    console.print("     [dim]• Validates trigger_check patterns match trigger_content docs[/dim]")
    console.print()

    console.print("[yellow]EXAMPLES:[/yellow]")
    console.print("  [dim]# Quick verification[/dim]")
    console.print("  python3 seed.py verify")
    console.print()
    console.print("  [dim]# Show help[/dim]")
    console.print("  python3 seed.py verify --help")
    console.print()

    console.print("[yellow]REFERENCE:[/yellow]")
    console.print("  Ensures seed branch stays in sync with recent changes.")
    console.print("  Detects stale patterns, outdated docs, and inconsistent help text.")
    console.print()


if __name__ == "__main__":
    # Handle help flag
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        print_help()
        sys.exit(0)

    # Confirm Prax logger connection
    logger.info("Prax logger connected to standards_verify")

    # Log standalone execution
    json_handler.log_operation(
        "verify_run",
        {"command": "standalone", "args": sys.argv[1:]}
    )

    # Run verification
    handle_command("verify", sys.argv[1:])
