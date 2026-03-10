# =================== AIPass ====================
# Name: passport.py
# Description: Passport command — thin CLI layer for granting birthright citizenship
# Version: 1.0.0
# Created: 2026-03-07
# Modified: 2026-03-07
# =============================================

"""Passport command orchestrator for branch lifecycle management.

Thin CLI module that parses arguments and delegates to the passport handler.
All implementation logic lives in apps/handlers/passport_ops.py.
"""

import argparse

from aipass.prax import logger
from aipass.cli.apps.modules import console

from aipass.spawn.apps.handlers.passport_ops import grant_passport


def print_introspection():
    """Display module introspection info."""
    console.print()
    console.print("passport Module")
    console.print("Grant birthright citizenship — minimal identity (.trinity/, .aipass/, README.md)")
    console.print()
    console.print("Connected Handlers:")
    console.print("  handlers/")
    console.print("    - passport_ops.py (grant_passport — create minimal citizen identity and register)")
    console.print()


def handle_command(command: str, args: list) -> bool:
    """Handle commands routed by the entry point.

    Args:
        command: The command string (e.g. "passport")
        args: List of arguments for the command

    Returns:
        True if command was handled, False otherwise.
    """
    if command == "passport":
        return handle_passport(args) == 0
    return False


def handle_passport(args: list[str]) -> int:
    """Parse args and execute passport grant.

    Args patterns:
        ["@dirname"]                    -> grant birthright to dirname
        ["@dirname", "--role", "X"]     -> with role
        ["@dirname", "--purpose", "X"]  -> with purpose

    Returns exit code (0=success, 1=failure).
    """
    if not args:
        console.print("[yellow]Usage: drone @spawn passport <@dirname> [--role ...] [--purpose ...][/yellow]")
        console.print()
        console.print("  [dim]Grant birthright citizenship to a directory[/dim]")
        console.print()
        console.print("  [green]@dirname[/green]     Directory to grant citizenship (created if needed)")
        console.print("  [yellow]--role[/yellow]       Role description for the passport")
        console.print("  [yellow]--purpose[/yellow]    Purpose description")
        return 1

    parser = argparse.ArgumentParser(prog="spawn passport", add_help=False)
    parser.add_argument("target")
    parser.add_argument("--role", default="")
    parser.add_argument("--purpose", default="")

    parsed = parser.parse_args(args)

    # Strip @ prefix if present
    target = parsed.target.lstrip("@")

    # Resolve relative to src/aipass/ (standard branch location)
    from pathlib import Path
    aipass_root = Path(__file__).parents[3]  # modules -> apps -> spawn -> aipass
    target_path = aipass_root / target

    result = grant_passport(
        target_path=str(target_path),
        role=parsed.role,
        purpose=parsed.purpose,
    )

    if result["success"]:
        console.print()
        console.print(f"[green]Passport granted: {result['branch_name']}[/green]")
        console.print(f"  Class: birthright")
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
