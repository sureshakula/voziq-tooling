"""
Skill Format Standards Module

Provides SKILL.md format compliance standards for AIPass skills.
Run directly or via: seedgo skill_format
"""

# =================== META ====================
# Name: skill_format_standard.py
# Description: Skill Format Standards Module
# Version: 1.0.0
# Created: 2026-03-07
# Modified: 2026-03-07
# =============================================


import sys
from pathlib import Path
from typing import List

from aipass.prax import logger
from aipass.seedgo.apps.standards.skills.handlers.standards.skill_format_content import get_skill_format_standards

from aipass.cli import console, header


def print_introspection():
    """Display module info and connected handlers"""
    console.print()
    console.print("[bold cyan]Skill Format Standards Module[/bold cyan]")
    console.print()

    console.print("[yellow]Connected Handlers:[/yellow]")
    console.print()

    handlers_dir = Path(__file__).parent.parent / "handlers" / "standards"

    if handlers_dir.exists():
        console.print("  [cyan]handlers/standards/[/cyan]")
        console.print("    [dim]- skill_format_content.py[/dim]")
        console.print("    [dim]- skill_format_check.py[/dim]")
        console.print()

    console.print("[dim]Run 'python3 skill_format_standard.py --help' for usage[/dim]")
    console.print()


def print_help():
    """Print drone-compliant help output"""
    console.print()
    console.print("[bold cyan]Skill Format Standards Module[/bold cyan]")
    console.print("Validates SKILL.md format compliance")
    console.print()

    console.print("[yellow]COMMANDS:[/yellow]")
    console.print("  Commands: skill_format, --help")
    console.print()
    console.print("  [cyan]skill_format[/cyan] - Display skill format standards")
    console.print()

    console.print("[yellow]USAGE:[/yellow]")
    console.print("  seedgo skill_format")
    console.print("  python3 skill_format_standard.py")
    console.print("  python3 skill_format_standard.py --help")
    console.print()

    console.print("[yellow]REFERENCE:[/yellow]")
    console.print("  See: seedgo standards pack (skills)")
    console.print()


def handle_command(command: str, args: List[str]) -> bool:
    """Handle 'skill_format' command"""
    if command != "skill_format":
        return False

    print_standard()
    return True


def print_standard():
    """Print skill format standards - orchestrates handler call"""
    console.print()
    header("Skill Format Standards")
    console.print()
    console.print(get_skill_format_standards())
    console.print()
    console.print("-" * 70)
    console.print()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print_introspection()
        sys.exit(0)

    if sys.argv[1] in ['--help', '-h', 'help']:
        print_help()
        sys.exit(0)

    logger.info("Prax logger connected to skill_format_standard")
    print_standard()
