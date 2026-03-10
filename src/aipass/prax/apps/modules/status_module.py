# =================== AIPass ====================
# Name: status_module.py
# Description: PRAX Status Command
# Version: 1.0.0
# Created: 2025-11-15
# Modified: 2026-03-09
# =============================================

"""
PRAX Status Module

Implements the 'status' command using handle_command interface.
"""

import sys
from pathlib import Path
from typing import List

from aipass.prax.apps.modules.logger import get_system_status, system_logger as logger
from aipass.cli.apps.modules import console, header, success, error


def print_help():
    """Display module help and connected handlers"""
    console.print()
    console.print("[bold cyan]PRAX Status Module[/bold cyan]")
    console.print()
    console.print("[yellow]Connected Handlers:[/yellow]")
    console.print()

    console.print("  [cyan]prax/modules/[/cyan]")
    console.print("    [dim]- logger.py[/dim] (get_system_status, system_logger)")
    console.print()

    console.print("[dim]Run 'python3 status_module.py --help' for usage[/dim]")
    console.print()


def handle_command(command: str, args: List[str]) -> bool:
    """
    Handle status command

    Args:
        command: Command name
        args: Command arguments

    Returns:
        True if command was handled
    """
    if command != 'status':
        return False

    status = get_system_status()

    console.print("\n📊 PRAX System Status")
    console.print("=" * 60)
    console.print(f"Total Modules: {status['total_modules']}")
    console.print(f"Active Loggers: {status['individual_loggers']}")
    console.print(f"System Logs Dir: {status['system_logs_dir']}")
    console.print(f"Module Logs Dir: {status['module_logs_dir']}")
    console.print(f"Registry File: {status['registry_file']}")
    console.print(f"File Watcher: {'🟢 Active' if status['file_watcher_active'] else '🔴 Inactive'}")
    console.print(f"Logger Override: {'🟢 Active' if status['logger_override_active'] else '🔴 Inactive'}")
    console.print("=" * 60 + "\n")
    return True


def print_introspection():
    """Display module introspection info."""
    console.print()
    console.print("status_module Module")
    console.print("Implements the 'status' command to display PRAX system status dashboard")
    console.print()
    console.print("Connected Handlers:")
    console.print("  modules/")
    console.print("    - logger.py (get_system_status — returns module count, watcher, override status)")
    console.print("    - logger.py (system_logger — auto-routing logger for module log files)")
    console.print()


if __name__ == "__main__":
    # Show introspection when run without arguments
    if len(sys.argv) == 1:
        print_help()
        sys.exit(0)
