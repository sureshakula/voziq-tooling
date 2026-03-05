#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: error_handling_standard.py - Error Handling Standards Module
# Date: 2025-11-21
# Version: 0.1.0
# Category: seed/standards
#
# CHANGELOG (Max 5 entries):
#   - v0.1.0 (2025-11-21): Initial standards module - error handling
#
# CODE STANDARDS:
#   - This module provides error handling standards when queried
# =============================================

"""
Error Handling Standards Module

Provides condensed error handling standards for AIPass branches.
Run directly or via: drone @seed error_handling
"""

import sys
from pathlib import Path
from typing import List

AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))  # For seed package imports

from prax.apps.modules.logger import system_logger as logger
from seed.apps.handlers.json import json_handler
from seed.apps.handlers.standards.error_handling_content import get_error_handling_standards

# Import CLI services (Rich console + display functions)
from cli.apps.modules import console, header


def print_introspection():
    """Display module info and connected handlers"""
    from pathlib import Path

    console.print()
    console.print("[bold cyan]Error Handling Standards Module[/bold cyan]")
    console.print()

    console.print("[yellow]Connected Handlers:[/yellow]")
    console.print()

    # Auto-discover handler files from handlers/standards/
    handlers_dir = Path(__file__).parent.parent / "handlers" / "standards"

    if handlers_dir.exists():
        # Only show files this module actually uses
        console.print("  [cyan]handlers/standards/[/cyan]")
        console.print("    [dim]- error_handling_content.py[/dim]")
        console.print()

    console.print("[dim]Run 'python3 error_handling_standard.py --help' for usage[/dim]")
    console.print()


def print_help():
    """Print drone-compliant help output"""
    console.print()
    console.print("[bold cyan]Error Handling Standards Module[/bold cyan]")
    console.print("Demonstrates AIPass error handling patterns (3-tier architecture)")
    console.print()

    console.print("[yellow]COMMANDS:[/yellow]")
    console.print("  Commands: error_handling, errors, error, --help")
    console.print()
    console.print("  [cyan]error_handling[/cyan]   - Display error handling standards")
    console.print("  [cyan]errors[/cyan]           - Display error handling standards (alias)")
    console.print("  [cyan]error[/cyan]            - Display error handling standards (alias)")
    console.print()

    console.print("[yellow]USAGE:[/yellow]")
    console.print("  drone @seed error_handling")
    console.print("  drone @seed errors")
    console.print("  drone @seed error")
    console.print("  python3 error_handling_standard.py")
    console.print("  python3 error_handling_standard.py --help")
    console.print()

    console.print("[yellow]EXAMPLES:[/yellow]")
    console.print("  [dim]# Via drone[/dim]")
    console.print("  drone @seed error_handling")
    console.print()
    console.print("  [dim]# Standalone[/dim]")
    console.print("  python3 error_handling_standard.py")
    console.print()

    console.print("[yellow]REFERENCE:[/yellow]")
    console.print("  /home/aipass/standards/CODE_STANDARDS/error_handling.md")
    console.print()


def handle_command(command: str, args: List[str]) -> bool:
    """Handle 'error_handling', 'errors', 'error' commands"""
    if command != "error_handling":
        return False

    # Log module usage - triggers JSON auto-creation
    json_handler.log_operation(
        "standard_displayed",
        {"command": command}
    )

    print_standard()
    return True


def print_standard():
    """Print error handling standards - orchestrates handler call"""
    console.print()
    header("Error Handling Standards")
    console.print()
    console.print(get_error_handling_standards())
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
    logger.info("Prax logger connected to error_handling_standard")

    # Log standalone execution - triggers JSON auto-creation
    json_handler.log_operation(
        "standard_displayed",
        {"command": "standalone"}
    )
    print_standard()
