# =================== AIPass ====================
# Name: shutdown.py
# Description: PRAX Shutdown Command
# Version: 1.0.0
# Created: 2025-11-15
# Modified: 2026-03-09
# =============================================

"""
PRAX Shutdown Module

Implements the 'shutdown' command using handle_command interface.
"""

import sys
from typing import List

from aipass.prax.apps.modules.logger import shutdown_logging_system
from aipass.cli.apps.modules import console, error
from aipass.prax.apps.handlers.json import json_handler


def print_help():
    """Drone-compliant help output - command syntax and examples"""
    console.print()
    console.print("[bold cyan]PRAX Shutdown - Stop Logging System[/bold cyan]")
    console.print()

    console.print("[yellow]Purpose:[/yellow]")
    console.print("  Cleanly stop the PRAX logging system")
    console.print()

    console.print("[yellow]Usage:[/yellow]")
    console.print("  drone @prax shutdown now")
    console.print()

    console.print("[yellow]Subcommands:[/yellow]")
    console.print("  now    Shut down the PRAX logging system")
    console.print()

    console.print("[yellow]Examples:[/yellow]")
    console.print()
    console.print("  [dim]# Shut down logging system[/dim]")
    console.print("  $ drone @prax shutdown now")
    console.print()


def handle_command(command: str, args: List[str]) -> bool:
    """
    Handle shutdown command

    Args:
        command: Command name
        args: Command arguments

    Returns:
        True if command was handled
    """
    if command != 'shutdown':
        return False

    if not args:
        print_introspection()
        return True

    if args[0] in ('--help', '-h', 'help'):
        print_help()
        return True

    if args[0] == 'now':
        json_handler.log_operation("shutdown_command_executed", {"command": command})
        console.print("🛑 Shutting down PRAX logging system...")
        shutdown_logging_system()
        console.print("✅ PRAX logging system shutdown complete")
        return True

    error(f"Unknown shutdown subcommand: {args[0]}")
    print_help()
    return True


def print_introspection():
    """Display module introspection - shows connected handlers"""
    console.print()
    console.print("[bold cyan]PRAX Shutdown Module[/bold cyan]")
    console.print()
    console.print("[yellow]Connected Handlers:[/yellow]")
    console.print()

    console.print("  [cyan]prax/modules/[/cyan]")
    console.print("    [dim]- logger.py[/dim] (shutdown_logging_system, system_logger)")
    console.print()

    console.print("[dim]Run 'drone @prax shutdown --help' for usage[/dim]")
    console.print()


if __name__ == "__main__":
    # Show introspection when run without arguments
    if len(sys.argv) == 1:
        print_help()
        sys.exit(0)
