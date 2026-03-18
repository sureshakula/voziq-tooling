# =================== AIPass ====================
# Name: run.py
# Description: PRAX Run Command
# Version: 1.0.0
# Created: 2025-11-15
# Modified: 2026-03-09
# =============================================

"""
PRAX Run Module

Implements the 'run' command using handle_command interface.
"""

import sys
from typing import List

from aipass.prax.apps.modules.logger import start_continuous_logging
from aipass.cli.apps.modules import console, error
from aipass.prax.apps.handlers.json import json_handler


def print_help():
    """Drone-compliant help output - command syntax and examples"""
    console.print()
    console.print("[bold cyan]PRAX Run - Continuous Logging Mode[/bold cyan]")
    console.print()

    console.print("[yellow]Purpose:[/yellow]")
    console.print("  Start PRAX continuous logging mode for monitoring AIPass operations")
    console.print()

    console.print("[yellow]Usage:[/yellow]")
    console.print("  drone @prax run start")
    console.print()

    console.print("[yellow]Subcommands:[/yellow]")
    console.print("  start    Start continuous logging mode")
    console.print()

    console.print("[yellow]Examples:[/yellow]")
    console.print()
    console.print("  [dim]# Start continuous logging[/dim]")
    console.print("  $ drone @prax run start")
    console.print()


def handle_command(command: str, args: List[str]) -> bool:
    """
    Handle run command

    Args:
        command: Command name
        args: Command arguments

    Returns:
        True if command was handled
    """
    if command != 'run':
        return False

    if not args:
        print_introspection()
        return True

    if args[0] in ('--help', '-h', 'help'):
        print_help()
        return True

    if args[0] == 'start':
        json_handler.log_operation("run_command_executed", {"command": command})
        console.print("🚀 Starting PRAX continuous logging mode...")
        start_continuous_logging()
        return True

    error(f"Unknown run subcommand: {args[0]}")
    print_help()
    return True


def print_introspection():
    """Display module introspection - shows connected handlers"""
    console.print()
    console.print("[bold cyan]PRAX Run Module[/bold cyan]")
    console.print()
    console.print("[yellow]Connected Handlers:[/yellow]")
    console.print()

    console.print("  [cyan]prax/modules/[/cyan]")
    console.print("    [dim]- logger.py[/dim] (start_continuous_logging, system_logger)")
    console.print()

    console.print("[dim]Run 'drone @prax run --help' for usage[/dim]")
    console.print()


if __name__ == "__main__":
    # Show introspection when run without arguments
    if len(sys.argv) == 1:
        print_help()
        sys.exit(0)
