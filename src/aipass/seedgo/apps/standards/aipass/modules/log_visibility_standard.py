"""
Log Visibility Standards Module

Provides condensed log visibility standards for AIPass branches.
Run directly or via: drone @seed log_visibility
"""

import sys
from pathlib import Path
from typing import List

from aipass.prax import logger
from handlers.json import json_handler
from handlers.standards.log_visibility_content import get_log_visibility_standards

from aipass.cli import console, header


def print_introspection():
    """Display module info and connected handlers"""
    console.print()
    console.print("[bold cyan]Log Visibility Standards Module[/bold cyan]")
    console.print()

    console.print("[yellow]Connected Handlers:[/yellow]")
    console.print()

    handlers_dir = Path(__file__).parent.parent / "handlers" / "standards"

    if handlers_dir.exists():
        console.print("  [cyan]handlers/standards/[/cyan]")
        console.print("    [dim]- log_visibility_content.py[/dim]")
        console.print("    [dim]- log_visibility_check.py[/dim]")
        console.print()

    console.print("[dim]Run 'python3 log_visibility_standard.py --help' for usage[/dim]")
    console.print()


def print_help():
    """Print drone-compliant help output"""
    console.print()
    console.print("[bold cyan]Log Visibility Standards Module[/bold cyan]")
    console.print("Demonstrates AIPass log visibility patterns")
    console.print()

    console.print("[yellow]COMMANDS:[/yellow]")
    console.print("  Commands: log_visibility, --help")
    console.print()
    console.print("  [cyan]log_visibility[/cyan]   - Display log visibility standards")
    console.print()

    console.print("[yellow]USAGE:[/yellow]")
    console.print("  drone @seed log_visibility")
    console.print("  python3 log_visibility_standard.py")
    console.print("  python3 log_visibility_standard.py --help")
    console.print()

    console.print("[yellow]EXAMPLES:[/yellow]")
    console.print("  [dim]# Via drone[/dim]")
    console.print("  drone @seed log_visibility")
    console.print()
    console.print("  [dim]# Standalone[/dim]")
    console.print("  python3 log_visibility_standard.py")
    console.print()


def handle_command(command: str, args: List[str]) -> bool:
    """Handle 'log_visibility' command"""
    if command != "log_visibility":
        return False

    json_handler.log_operation(
        "standard_displayed",
        {"command": command, "args": args}
    )

    print_standard()
    return True


def print_standard():
    """Print log visibility standards - orchestrates handler call"""
    console.print()
    header("Log Visibility Standards")
    console.print()
    console.print(get_log_visibility_standards())
    console.print()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print_introspection()
        sys.exit(0)

    if sys.argv[1] in ['--help', '-h', 'help']:
        print_help()
        sys.exit(0)

    logger.info("Prax logger connected to log_visibility_standard")

    json_handler.log_operation(
        "standard_displayed",
        {"command": "standalone"}
    )
    print_standard()
