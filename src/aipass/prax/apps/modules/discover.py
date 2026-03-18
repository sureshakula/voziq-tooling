# =================== AIPass ====================
# Name: discover.py
# Description: PRAX Discover Command
# Version: 1.0.0
# Created: 2025-11-15
# Modified: 2026-03-09
# =============================================

"""
PRAX Discover Module

Implements the 'discover' command using handle_command interface.
"""

import sys
from typing import List

from aipass.cli.apps.modules import console, error
from aipass.prax.apps.handlers.discovery.scanner import discover_python_modules
from aipass.prax.apps.handlers.json import json_handler


def print_help():
    """Drone-compliant help output - command syntax and examples"""
    console.print()
    console.print("[bold cyan]PRAX Discover - Scan Python Modules[/bold cyan]")
    console.print()

    console.print("[yellow]Purpose:[/yellow]")
    console.print("  Scan and register Python modules in the AIPass ecosystem")
    console.print()

    console.print("[yellow]Usage:[/yellow]")
    console.print("  drone @prax discover scan")
    console.print()

    console.print("[yellow]Subcommands:[/yellow]")
    console.print("  scan    Discover and register Python modules")
    console.print()

    console.print("[yellow]Examples:[/yellow]")
    console.print()
    console.print("  [dim]# Discover Python modules[/dim]")
    console.print("  $ drone @prax discover scan")
    console.print()


def handle_command(command: str, args: List[str]) -> bool:
    """
    Handle discover command

    Args:
        command: Command name
        args: Command arguments

    Returns:
        True if command was handled
    """
    if command != 'discover':
        return False

    if not args:
        print_introspection()
        return True

    if args[0] in ('--help', '-h', 'help'):
        print_help()
        return True

    if args[0] == 'scan':
        json_handler.log_operation("discover_command_executed", {"command": command})
        console.print("🔍 Discovering Python modules...")
        modules = discover_python_modules()
        console.print(f"✅ Discovered {len(modules)} modules")
        return True

    error(f"Unknown discover subcommand: {args[0]}")
    print_help()
    return True


def print_introspection():
    """Display module introspection - shows connected handlers"""
    console.print()
    console.print("[bold cyan]PRAX Discover Module[/bold cyan]")
    console.print()
    console.print("[yellow]Connected Handlers:[/yellow]")
    console.print()

    console.print("  [cyan]prax/modules/[/cyan]")
    console.print("    [dim]- logger.py[/dim] (system_logger)")
    console.print()

    console.print("  [cyan]prax/handlers/discovery/[/cyan]")
    console.print("    [dim]- scanner.py[/dim] (discover_python_modules)")
    console.print()

    console.print("[dim]Run 'drone @prax discover --help' for usage[/dim]")
    console.print()


if __name__ == "__main__":
    # Show introspection when run without arguments
    if len(sys.argv) == 1:
        print_help()
        sys.exit(0)
