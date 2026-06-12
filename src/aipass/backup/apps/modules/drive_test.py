# =================== AIPass ====================
# Name: drive_test.py
# Description: Drive test module — verifies Google Drive connectivity via @api
# Version: 1.0.0
# Created: 2026-04-17
# Modified: 2026-06-12
# =============================================

"""Drive Test Module — tests Drive auth through @api gateway."""

import sys

from aipass.prax import logger
from aipass.cli.apps.modules import console

from aipass.backup.apps.handlers.json import json_handler


MODULE_NAME = "drive_test"
PRIMARY_COMMAND = "drive-test"


def print_introspection():
    """Display module info and connected handlers."""
    console.print(f"[bold cyan]{MODULE_NAME} Module[/bold cyan]")
    console.print(f"  Primary command: [yellow]{PRIMARY_COMMAND}[/yellow]")
    console.print("  Status: Phase 4 -- auth test via @api gateway")
    console.print("  Handlers: drive/client, drive/test")


def print_help():
    """Display help for this module."""
    print_introspection()


def run_drive_test() -> bool:
    """Test Drive auth through @api gateway.

    Creates a DriveClient, authenticates, tests folder access, and
    displays results.

    Returns:
        True if connectivity test passed, False otherwise.
    """
    from aipass.backup.apps.handlers.drive.client import DriveClient
    from aipass.backup.apps.handlers.drive.test import test_connectivity

    client = DriveClient()
    result = test_connectivity(client)

    if result["success"]:
        console.print("[green]Drive connectivity test PASSED[/green]")
        console.print(f"  Backup folder ID: {result['folder_id']}")
        logger.info("[backup] Drive test passed")
    else:
        console.print(f"[red]Drive connectivity test FAILED: {result['error']}[/red]")
        logger.warning(f"[backup] Drive test failed: {result['error']}")

    json_handler.log_operation(
        "drive_test_complete",
        {"success": result["success"]},
    )
    return result["success"]


def handle_command(command: str, args: list) -> bool:
    """Handle the drive-test command. Returns True if handled."""
    if command != PRIMARY_COMMAND:
        return False

    if not args:
        print_introspection()
        return True

    if args[0] in ("--help", "-h", "help"):
        print_help()
        return True

    if args[0] == "run":
        run_drive_test()
        return True

    # Default: run the test
    run_drive_test()
    return True


# =============================================

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print_introspection()
        sys.exit(0)
    result = handle_command(PRIMARY_COMMAND, sys.argv[1:])
    sys.exit(0 if result else 1)
