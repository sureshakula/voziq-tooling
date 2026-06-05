# =================== AIPass ====================
# Name: rm.py
# Description: Module orchestrator for contained safe-delete
# Version: 1.0.0
# Created: 2026-06-02
# Modified: 2026-06-02
# =============================================

"""Module orchestrator for contained safe-delete.

Thin orchestrator that delegates to rm_handler for path containment
checks and deletion. Provider-agnostic alternative to shell ``rm``.
"""

from __future__ import annotations

from aipass.prax import logger
from aipass.cli.apps.modules import console
from aipass.drone.apps.handlers.json import json_handler
from aipass.drone.apps.handlers.rm_handler import (
    safe_delete as _safe_delete,
)

DRONE_MODULE = {
    "name": "rm",
    "version": "1.0.0",
    "description": "Contained safe-delete (project + tmp)",
}


def safe_delete(paths: list[str]) -> list[tuple[str, bool, str]]:
    """Delete paths with containment checks.

    Returns list of ``(original_path, success, message)`` tuples.
    """
    logger.info("rm: requested deletion of %d path(s)", len(paths))
    return _safe_delete(paths)


def handle_command(command: str | None = None, args: list[str] | None = None) -> bool:
    """Entry point for ``drone rm`` module routing."""
    if not args:
        if command is None:
            print_introspection()
            return True
        args = []
    if command in ("--help", "-h") or (args and args[0] in ("--help", "-h")):
        print_help()
        return True

    json_handler.log_operation("rm_command", {"command": command, "args": args})

    paths: list[str] = []
    if command is not None:
        paths.append(command)
    if args:
        paths.extend(args)

    if not paths:
        print_help()
        return True

    results = _safe_delete(paths)
    ok = True
    for _path_str, success, message in results:
        if success:
            console.print(f"[green]✓[/green] {message}")
        else:
            console.print(f"[red]✗[/red] {message}")
            ok = False
    return ok


def print_introspection() -> None:
    """Display module overview (no args)."""
    console.print()
    console.print("[bold cyan]rm — Contained Safe-Delete[/bold cyan]")
    console.print()
    console.print("[dim]Deletes files and directories constrained to project root and system tmp.[/dim]")
    console.print()
    console.print("Run [green]'drone rm --help'[/green] for usage information")
    console.print()


def print_help() -> None:
    """Display help (--help flag)."""
    console.print("Usage: drone rm <path> [<path>...]")
    console.print()
    console.print("Contained safe-delete. Removes files and directories using pure Python")
    console.print("(shutil.rmtree), constrained to the project root and system temp directory.")
    console.print()
    console.print("[bold]Rules:[/bold]")
    console.print("  • Path must resolve under the project root or system temp dir")
    console.print("  • Cannot delete the project root or temp root itself")
    console.print("  • Symlinks are resolved; refuses if target escapes allowed roots")
    console.print("  • Nonexistent paths produce a clean error")
    console.print()
    console.print("[bold]Examples:[/bold]")
    console.print("  [green]drone rm /tmp/scratch_dir[/green]")
    console.print("  [green]drone rm build/ dist/[/green]")
    console.print("  [green]drone rm /tmp/aipass_test_abc123[/green]")
