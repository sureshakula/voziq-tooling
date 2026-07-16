# =================== AIPass ====================
# Name: trust.py
# Description: Trust management — aipass trust / aipass revoke commands
# Version: 1.0.0
# Created: 2026-07-15
# Modified: 2026-07-15
# =============================================

"""
aipass trust / revoke — manage the trusted-project registry (DPLAN-0244)

Enrollment controls which projects have their .aipass/hooks.json loaded
by the hook engine. Projects created via `aipass init` auto-enroll;
these commands handle manual enrollment and revocation.
"""

from __future__ import annotations

from pathlib import Path

from aipass.cli.apps.modules import console, error, success
from aipass.hooks.apps.handlers.config.trust_registry import enroll, revoke
from aipass.prax import logger

COMMAND = "trust"
_COMMAND_REVOKE = "revoke"


def _print_help() -> None:
    console.print()
    console.print("[bold cyan]aipass trust / revoke[/bold cyan] — trusted-project registry")
    console.print()
    console.print("[yellow]USAGE:[/yellow]")
    console.print("  [green]aipass trust <path>[/green]    [dim]# Enroll a project (requires .aipass/hooks.json)[/dim]")
    console.print("  [green]aipass revoke <path>[/green]   [dim]# Remove a project from the registry[/dim]")
    console.print()


def _handle_trust(args: list[str]) -> bool:
    if not args or args[0] in ("--help", "-h"):
        _print_help()
        return True
    target = Path(args[0]).resolve()
    if not target.is_dir():
        error(f"Not a directory: {target}")
        return True
    hooks_path = target / ".aipass" / "hooks.json"
    if not hooks_path.is_file():
        error(f"No .aipass/hooks.json found in {target}")
        return True
    if enroll(str(target)):
        success(f"Enrolled {target}")
        logger.info("[AIPASS] trust: enrolled %s", target)
    else:
        error(f"Failed to enroll {target}")
    return True


def _handle_revoke(args: list[str]) -> bool:
    if not args or args[0] in ("--help", "-h"):
        _print_help()
        return True
    target = Path(args[0]).resolve()
    if revoke(str(target)):
        success(f"Revoked {target}")
        logger.info("[AIPASS] revoke: removed %s", target)
    else:
        console.print(f"[dim]{target} was not in the registry.[/dim]")
    return True


def handle_command(command: str, args: list[str]) -> bool:
    """Route trust/revoke subcommands. Returns True if handled."""
    if command == COMMAND:
        return _handle_trust(args)
    if command == _COMMAND_REVOKE:
        return _handle_revoke(args)
    return False
