"""
CLI Flags Standards Module

Provides condensed CLI flags standards for AIPass branches.
Run directly or via: drone @seed cli_flags
"""

import sys
from pathlib import Path
from typing import List

from aipass.prax import logger
from handlers.json import json_handler
from handlers.standards.cli_flags_content import get_cli_flags_standards

from aipass.cli import console, header


def print_introspection():
    """Display module info and connected handlers"""
    console.print()
    console.print("[bold cyan]CLI Flags Standards Module[/bold cyan]")
    console.print()

    console.print("[yellow]Connected Handlers:[/yellow]")
    console.print()

    handlers_dir = Path(__file__).parent.parent / "handlers" / "standards"

    if handlers_dir.exists():
        console.print("  [cyan]handlers/standards/[/cyan]")
        console.print("    [dim]- cli_flags_content.py[/dim]")
        console.print("    [dim]- cli_flags_check.py[/dim]")
        console.print()

    console.print("[dim]Run 'python3 cli_flags_standard.py --help' for usage[/dim]")
    console.print()


def print_help():
    """Print drone-compliant help output"""
    console.print()
    console.print("[bold cyan]CLI Flags Standards Module[/bold cyan]")
    console.print("Demonstrates AIPass CLI flags conventions")
    console.print()

    console.print("[yellow]COMMANDS:[/yellow]")
    console.print("  Commands: cli_flags, --help")
    console.print()
    console.print("  [cyan]cli_flags[/cyan]   - Display CLI flags standards")
    console.print()

    console.print("[yellow]USAGE:[/yellow]")
    console.print("  drone @seed cli_flags")
    console.print("  python3 cli_flags_standard.py")
    console.print("  python3 cli_flags_standard.py --help")
    console.print()

    console.print("[yellow]EXAMPLES:[/yellow]")
    console.print("  [dim]# Via drone[/dim]")
    console.print("  drone @seed cli_flags")
    console.print()
    console.print("  [dim]# Standalone[/dim]")
    console.print("  python3 cli_flags_standard.py")
    console.print()


def handle_command(command: str, args: List[str]) -> bool:
    """Handle 'cli_flags' command"""
    if command != "cli_flags":
        return False

    json_handler.log_operation(
        "standard_displayed",
        {"command": command, "args": args}
    )

    print_standard()
    return True


def print_standard():
    """Print CLI flags standards - orchestrates handler call"""
    console.print()
    header("CLI Flags Standards")
    console.print()
    console.print(get_cli_flags_standards())
    console.print()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print_introspection()
        sys.exit(0)

    if sys.argv[1] in ['--help', '-h', 'help']:
        print_help()
        sys.exit(0)

    logger.info("Prax logger connected to cli_flags_standard")

    json_handler.log_operation(
        "standard_displayed",
        {"command": "standalone"}
    )
    print_standard()
