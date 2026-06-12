# =================== AIPass ====================
# Name: settings.py
# Description: Settings module — opens the PyQt5 settings UI for a project
# Version: 0.1.0
# Created: 2026-04-17
# Modified: 2026-04-17
# =============================================

"""Settings Module — thin CLI wrapper delegating to handlers.

Stub scaffold awaiting Phase 3 handler implementations.
"""

import sys

from aipass.prax import logger
from aipass.cli.apps.modules import console
from aipass.backup.apps.handlers.json import json_handler


MODULE_NAME = "settings"
PRIMARY_COMMAND = "settings"


def print_introspection():
    """Display module info and connected handlers."""
    console.print(f"[bold cyan]{MODULE_NAME} Module[/bold cyan]")
    console.print(f"  Primary command: [yellow]{PRIMARY_COMMAND}[/yellow]")
    console.print("  Status: stub scaffold, awaiting Phase 3 implementation")
    console.print("  Planned handlers: ui/settings_window")


def print_help():
    """Display help for this module."""
    print_introspection()


def handle_command(command: str, args: list) -> bool:
    """Handle the settings command. Returns True if handled."""
    if command != PRIMARY_COMMAND:
        return False

    if not args:
        print_introspection()
        return True

    if args[0] in ("--help", "-h", "help"):
        print_introspection()
        return True

    logger.info(f"[backup] {MODULE_NAME} stub invoked with args={args} — awaiting Phase 3")
    json_handler.log_operation(f"{MODULE_NAME}_stub_invoked", {"args": args})
    return True


# =============================================

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print_introspection()
        sys.exit(0)
    result = handle_command(sys.argv[1], sys.argv[2:])
    sys.exit(0 if result else 1)
