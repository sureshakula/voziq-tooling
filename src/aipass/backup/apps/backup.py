# =================== AIPass ====================
# Name: backup.py
# Description: BACKUP Branch — main orchestrator with auto-discovery
# Version: 1.0.0
# Created: 2026-04-16
# Modified: 2026-04-23
# =============================================

"""BACKUP Branch - Main Orchestrator

Auto-discovery architecture:
- Scans modules/ directory for .py files with handle_command()
- Routes commands to discovered modules automatically
- Accepts project paths or registered project names
"""

import importlib
import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("AIPASS_BRANCH_NAME", "backup")

from aipass.prax import logger
from aipass.cli.apps.modules import console

VERSION = "1.0.0"
MODULE_NAME = "backup"
MODULES_DIR = Path(__file__).parent / "modules"


def print_introspection():
    """Display entry point info."""
    console.print(f"[bold cyan]{MODULE_NAME}[/bold cyan] v{VERSION}")
    console.print("  Type: entry point (auto-discovery router)")
    console.print(f"  Modules dir: {MODULES_DIR}")


def discover_modules() -> list[Any]:
    """Auto-discover modules in modules/ directory."""
    modules = []

    if not MODULES_DIR.exists():
        return modules

    for file_path in MODULES_DIR.glob("*.py"):
        if file_path.name.startswith("_"):
            continue

        module_name = f"aipass.backup.apps.modules.{file_path.stem}"

        try:
            module = importlib.import_module(module_name)
            if hasattr(module, "handle_command"):
                modules.append(module)
        except Exception as e:
            logger.error(f"[BACKUP] Failed to load module {module_name}: {e}")

    return modules


def route_command(command: str, args: list[str], modules: list[Any]) -> bool:
    """Route command to appropriate module."""
    for module in modules:
        try:
            if module.handle_command(command, args):
                return True
        except Exception as e:
            logger.error(f"[BACKUP] Module {module.__name__} error: {e}")
    return False


def main():
    """Main entry point - routes commands or shows help."""
    args = sys.argv[1:]

    if args and args[0] in ("--version", "-V"):
        console.print(f"backup {VERSION}")
        return 0

    modules = discover_modules()

    if len(args) == 0 or args[0] in ["--help", "-h", "help"]:
        console.print(f"[bold]BACKUP[/bold] v{VERSION} — {len(modules)} modules")
        console.print("")
        for module in modules:
            name = module.__name__.split(".")[-1]
            doc = (module.__doc__ or "").strip().split("\n")[0]
            desc = doc if doc else "No description"
            console.print(f"  [yellow]{name:20}[/yellow] {desc}")
        console.print("")
        console.print("[dim]Usage: backup <command> <project_path|@name>[/dim]")
        return 0

    command = args[0]

    if command == "backup" and len(args) > 1:
        from aipass.backup.apps.modules.register import resolve_project

        target = args[1]
        project_root = resolve_project(target)
        if project_root is None:
            console.print(f"[red]Error:[/red] Cannot resolve project: {target}")
            return 1
        remaining = [project_root] + args[2:]
        mode = "snapshot"
        if "--versioned" in args:
            mode = "versioned"
            remaining = [r for r in remaining if r != "--versioned"]
        elif "--all" in args:
            mode = "all"
            remaining = [r for r in remaining if r != "--all"]

        if route_command(mode, remaining, modules):
            return 0
        console.print(f"[red]Error:[/red] Unknown mode: {mode}")
        return 1

    remaining = args[1:] if len(args) > 1 else []

    if remaining and remaining[0].startswith("@"):
        from aipass.backup.apps.modules.register import resolve_project

        resolved = resolve_project(remaining[0])
        if resolved is None:
            console.print(f"[red]Error:[/red] Cannot resolve project: {remaining[0]}")
            return 1
        remaining = [resolved] + remaining[1:]

    if route_command(command, remaining, modules):
        return 0

    console.print(f"[red]Unknown command:[/red] {command}")
    return 1


# =============================================

if __name__ == "__main__":
    sys.exit(main())
