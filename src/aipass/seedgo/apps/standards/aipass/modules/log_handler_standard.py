#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: log_handler_standard.py - Log Handler Standards Module
# Date: 2026-02-26
# Version: 1.0.0
# Category: seed/standards
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2026-02-26): Initial standards module - log handler rotation
#
# CODE STANDARDS:
#   - This module provides log handler standards when queried
# =============================================

"""
Log Handler Standards Module

Provides condensed log handler rotation standards for AIPass branches.
Run directly or via: drone @seed log_handler
"""

import sys
from pathlib import Path
from typing import List

AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))

from prax.apps.modules.logger import system_logger as logger
from seed.apps.handlers.json import json_handler
from seed.apps.handlers.standards.log_handler_content import get_log_handler_standards

from cli.apps.modules import console, header


def print_introspection():
    """Display module info and connected handlers"""
    console.print()
    console.print("[bold cyan]Log Handler Standards Module[/bold cyan]")
    console.print()

    console.print("[yellow]Connected Handlers:[/yellow]")
    console.print()

    handlers_dir = Path(__file__).parent.parent / "handlers" / "standards"

    if handlers_dir.exists():
        console.print("  [cyan]handlers/standards/[/cyan]")
        console.print("    [dim]- log_handler_content.py[/dim]")
        console.print("    [dim]- log_handler_check.py[/dim]")
        console.print()

    console.print("[dim]Run 'python3 log_handler_standard.py --help' for usage[/dim]")
    console.print()


def print_help():
    """Print drone-compliant help output"""
    console.print()
    console.print("[bold cyan]Log Handler Standards Module[/bold cyan]")
    console.print("Demonstrates AIPass log handler rotation patterns")
    console.print()

    console.print("[yellow]COMMANDS:[/yellow]")
    console.print("  Commands: log_handler, --help")
    console.print()
    console.print("  [cyan]log_handler[/cyan]   - Display log handler rotation standards")
    console.print()

    console.print("[yellow]USAGE:[/yellow]")
    console.print("  drone @seed log_handler")
    console.print("  python3 log_handler_standard.py")
    console.print("  python3 log_handler_standard.py --help")
    console.print()

    console.print("[yellow]EXAMPLES:[/yellow]")
    console.print("  [dim]# Via drone[/dim]")
    console.print("  drone @seed log_handler")
    console.print()
    console.print("  [dim]# Standalone[/dim]")
    console.print("  python3 log_handler_standard.py")
    console.print()


def handle_command(command: str, args: List[str]) -> bool:
    """Handle 'log_handler' command"""
    if command != "log_handler":
        return False

    json_handler.log_operation(
        "standard_displayed",
        {"command": command, "args": args}
    )

    print_standard()
    return True


def print_standard():
    """Print log handler standards - orchestrates handler call"""
    console.print()
    header("Log Handler Rotation Standards")
    console.print()
    console.print(get_log_handler_standards())
    console.print()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print_introspection()
        sys.exit(0)

    if sys.argv[1] in ['--help', '-h', 'help']:
        print_help()
        sys.exit(0)

    logger.info("Prax logger connected to log_handler_standard")

    json_handler.log_operation(
        "standard_displayed",
        {"command": "standalone"}
    )
    print_standard()
