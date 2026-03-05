#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: trigger_standard.py - Trigger Standards Module
# Date: 2025-12-04
# Version: 0.1.0
# Category: seed/standards
#
# CHANGELOG (Max 5 entries):
#   - v0.1.0 (2025-12-04): Initial standards module - trigger event bus
#
# CODE STANDARDS:
#   - This module provides trigger standards when queried
# =============================================

"""
Trigger Standards Module

Provides condensed trigger event bus standards for AIPass branches.
Run directly or via: drone @seed trigger
"""

import sys
from pathlib import Path
from typing import List

# Infrastructure
AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))

from prax.apps.modules.logger import system_logger as logger
from seed.apps.handlers.json import json_handler
from seed.apps.handlers.standards.trigger_content import get_trigger_standards

# Import CLI services (Rich console + display functions)
from cli.apps.modules import console, header


def print_introspection():
    """Display module info and connected handlers"""
    console.print()
    console.print("[bold cyan]Trigger Standards Module[/bold cyan]")
    console.print()

    console.print("[yellow]Connected Handlers:[/yellow]")
    console.print()

    console.print("  [cyan]handlers/standards/[/cyan]")
    console.print("    [dim]- trigger_content.py[/dim]")
    console.print("    [dim]- trigger_check.py[/dim]")
    console.print()

    console.print("[dim]Run 'python3 trigger_standard.py --help' for usage[/dim]")
    console.print()


def print_help():
    """Print drone-compliant help output"""
    console.print()
    console.print("[bold cyan]Trigger Standards Module[/bold cyan]")
    console.print("Demonstrates AIPass event bus patterns")
    console.print()

    console.print("[yellow]COMMANDS:[/yellow]")
    console.print("  Commands: trigger, events, --help")
    console.print()
    console.print("  [cyan]trigger[/cyan] - Display trigger event bus standards")
    console.print("  [cyan]events[/cyan]  - Display trigger event bus standards (alias)")
    console.print()

    console.print("[yellow]USAGE:[/yellow]")
    console.print("  drone @seed trigger")
    console.print("  python3 trigger_standard.py")
    console.print("  python3 trigger_standard.py --help")
    console.print()

    console.print("[yellow]EXAMPLES:[/yellow]")
    console.print("  [dim]# Via drone[/dim]")
    console.print("  drone @seed trigger")
    console.print("  drone @seed events")
    console.print()
    console.print("  [dim]# Standalone[/dim]")
    console.print("  python3 trigger_standard.py")
    console.print()

    console.print("[yellow]REFERENCE:[/yellow]")
    console.print("  /home/aipass/seed/standards/CODE_STANDARDS/trigger.md")
    console.print()


def handle_command(command: str, args: List[str]) -> bool:
    """Handle 'trigger' command"""
    if command != "trigger":
        return False

    # Log module usage
    json_handler.log_operation(
        "standard_displayed",
        {"command": command}
    )

    print_standard()
    return True


def print_standard():
    """Print trigger standards - orchestrates handler call"""
    console.print()
    header("Trigger Standards")
    console.print()
    console.print(get_trigger_standards())
    console.print()
    console.print("-" * 70)
    console.print()


if __name__ == "__main__":
    # Show introspection when run without arguments
    if len(sys.argv) == 1:
        print_introspection()
        sys.exit(0)

    # Handle help flag (drone compliance)
    if sys.argv[1] in ['--help', '-h', 'help']:
        print_help()
        sys.exit(0)

    # Confirm Prax logger connection
    logger.info("Prax logger connected to trigger_standard")
