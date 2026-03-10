# =================== AIPass ====================
# Name: run_module.py
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
from pathlib import Path
from typing import List

from aipass.prax.apps.modules.logger import start_continuous_logging, system_logger as logger
from aipass.cli.apps.modules import console, header, success, error


def print_help():
    """Display module help and connected handlers"""
    console.print()
    console.print("[bold cyan]PRAX Run Module[/bold cyan]")
    console.print()
    console.print("[yellow]Connected Handlers:[/yellow]")
    console.print()

    console.print("  [cyan]prax/modules/[/cyan]")
    console.print("    [dim]- logger.py[/dim] (start_continuous_logging, system_logger)")
    console.print()

    console.print("[dim]Run 'python3 run_module.py --help' for usage[/dim]")
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

    console.print("🚀 Starting PRAX continuous logging mode...")
    start_continuous_logging()
    return True


def print_introspection():
    """Display module introspection info."""
    console.print()
    console.print("run_module Module")
    console.print("Implements the 'run' command to start PRAX continuous logging mode")
    console.print()
    console.print("Connected Handlers:")
    console.print("  modules/")
    console.print("    - logger.py (start_continuous_logging — starts background logging loop)")
    console.print("    - logger.py (system_logger — auto-routing logger for module log files)")
    console.print()


if __name__ == "__main__":
    # Show introspection when run without arguments
    if len(sys.argv) == 1:
        print_help()
        sys.exit(0)
