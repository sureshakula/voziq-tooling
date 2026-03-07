# =================== META ====================
# Name: spawn.py
# Description: Entry point CLI for drone @spawn
# Version: 1.0.0
# Created: 2026-03-05
# Modified: 2026-03-07
# =============================================

"""
SPAWN Branch - Agent Creation System

Creates new AIPass agents from templates.
Provides CLI interface to the spawn_agent() workflow.
"""

import sys
import argparse

from aipass.prax.apps.modules.logger import system_logger as logger
from aipass.cli.apps.modules import console, header


def print_help():
    """Display Rich-formatted help."""
    console.print()
    header("SPAWN - Agent Creation System")
    console.print()
    console.print("[dim]Create new AIPass agents from templates[/dim]")
    console.print()
    console.print("[bold cyan]USAGE:[/bold cyan]")
    console.print()
    console.print("  [dim]drone @spawn create <target_path> [options][/dim]")
    console.print("  [dim]drone @spawn --help[/dim]")
    console.print()
    console.print("[bold cyan]COMMANDS:[/bold cyan]")
    console.print()
    console.print("  [green]create[/green]    Create a new agent from template")
    console.print()
    console.print("[bold cyan]OPTIONS:[/bold cyan]")
    console.print()
    console.print("  [yellow]--role[/yellow]        Agent role description")
    console.print("  [yellow]--traits[/yellow]      Agent personality traits")
    console.print("  [yellow]--purpose[/yellow]     Agent purpose (brief)")
    console.print("  [yellow]--template[/yellow]    Custom template directory")
    console.print("  [yellow]--registry[/yellow]    Path to AIPASS_REGISTRY.json")
    console.print()


def handle_create(args):
    """Handle the create command."""
    from aipass.spawn.apps.modules.core import _spawn_agent as spawn_agent

    if not args:
        console.print("[red]Error: target path required[/red]")
        console.print("[dim]Usage: drone @spawn create <target_path> [--role ...][/dim]")
        return 1

    parser = argparse.ArgumentParser(prog="spawn create", add_help=False)
    parser.add_argument("target_path")
    parser.add_argument("--role", default="")
    parser.add_argument("--traits", default="")
    parser.add_argument("--purpose", default="")
    parser.add_argument("--template", default=None)
    parser.add_argument("--registry", default=None)

    parsed = parser.parse_args(args)

    result = spawn_agent(
        target_path=parsed.target_path,
        role=parsed.role,
        traits=parsed.traits,
        purpose=parsed.purpose,
        template_dir=parsed.template,
        registry_path=parsed.registry,
    )

    if result["success"]:
        console.print()
        console.print(f"[green]Agent created: {result['branch_name']}[/green]")
        console.print(f"  Path: {result['path']}")
        console.print(f"  Files: {result['files_copied']}")
        console.print(f"  Registry: {'updated' if result['registry_updated'] else 'not updated'}")
        if result["validation_issues"]:
            console.print(f"  [yellow]Warnings: {len(result['validation_issues'])} unreplaced placeholders[/yellow]")
        console.print()
        return 0
    else:
        console.print(f"[red]Error: {result['error']}[/red]")
        return 1


def main():
    """Main entry point."""
    args = sys.argv[1:]

    if len(args) == 0 or args[0] in ["--help", "-h", "help"]:
        print_help()
        return 0

    if args[0] in ["--version", "-V"]:
        console.print("SPAWN v1.0.0")
        return 0

    command = args[0]
    remaining = args[1:] if len(args) > 1 else []

    if command == "create":
        return handle_create(remaining)

    console.print(f"[red]Unknown command: {command}[/red]")
    console.print("[dim]Run 'drone @spawn --help' for available commands[/dim]")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print("\n\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"SPAWN entry point error: {e}", exc_info=True)
        console.print(f"\nError: {e}")
        sys.exit(1)
