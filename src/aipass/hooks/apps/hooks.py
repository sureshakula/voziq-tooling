# =================== AIPass ====================
# Name: hooks.py
# Version: 1.1.0
# Description: Hook infrastructure — drone entry point
# Branch: hooks
# Layer: apps
# Created: 2026-05-18
# Modified: 2026-05-19
# =============================================

"""
HOOKS Branch - Main Orchestrator

Auto-discovery architecture:
- Scans modules/ directory for .py files with handle_command()
- Routes commands to discovered modules automatically
- No manual imports or routing needed
"""

import os
import sys
import importlib
from pathlib import Path
from typing import Any

os.environ.setdefault("AIPASS_BRANCH_NAME", "hooks")

from aipass.prax.apps.modules.logger import system_logger as logger  # noqa: E402
from aipass.cli.apps.modules import err_console  # noqa: E402

CONSOLE = err_console

# =============================================================================
# MODULE DISCOVERY
# =============================================================================

MODULES_DIR = Path(__file__).parent / "modules"


def discover_modules() -> list[Any]:
    """Auto-discover modules in modules/ directory."""
    modules = []

    if not MODULES_DIR.exists():
        return modules

    for file_path in sorted(MODULES_DIR.glob("*.py")):
        if file_path.name.startswith("_"):
            continue

        module_names = [
            f"aipass.hooks.apps.modules.{file_path.stem}",
            f"apps.modules.{file_path.stem}",
        ]

        loaded = False
        for module_name in module_names:
            try:
                module = importlib.import_module(module_name)
                if hasattr(module, "handle_command"):
                    modules.append(module)
                loaded = True
                break
            except (ImportError, ModuleNotFoundError) as e:
                logger.info("[HOOKS] Module %s not found: %s", module_name, e)
                continue
            except Exception as e:
                logger.error("[HOOKS] Failed to load module %s: %s", module_name, e)
                loaded = True
                break

        if not loaded:
            logger.error("[HOOKS] Could not import module %s", file_path.stem)

    return modules


def print_introspection():
    """Print branch introspection — discovered modules and capabilities."""
    modules = discover_modules()
    CONSOLE.print("[bold cyan]HOOKS[/bold cyan] — Hook Infrastructure for AIPass")
    CONSOLE.print(f"  Modules discovered: {len(modules)}")
    for module in modules:
        name = module.__name__.split(".")[-1]
        desc = (module.__doc__ or "").strip().split("\n")[0] if module.__doc__ else "No description"
        CONSOLE.print(f"  {name:20} {desc}")


def print_help():
    """Print CLI help — usage instructions and available commands."""
    modules = discover_modules()
    CONSOLE.print("[bold cyan]HOOKS[/bold cyan] — Usage")
    CONSOLE.print()
    CONSOLE.print("  drone @hooks <command> [args...]")
    CONSOLE.print()
    CONSOLE.print("[bold]COMMANDS:[/bold]")
    for module in modules:
        name = module.__name__.split(".")[-1]
        desc = (module.__doc__ or "").strip().split("\n")[0] if module.__doc__ else "No description"
        CONSOLE.print(f"  {name:20} {desc}")
    CONSOLE.print()
    CONSOLE.print("[bold]BRIDGES:[/bold]")
    CONSOLE.print("  claude             Claude Code bridge (provider settings entry point)")
    CONSOLE.print()
    CONSOLE.print("[bold]FLAGS:[/bold]")
    CONSOLE.print("  --help, -h           Show this help message")
    CONSOLE.print("  --version, -V        Show version")


def route_command(command: str, args: list[str], modules: list[Any]) -> bool:
    """Route command to appropriate module."""
    for module in modules:
        try:
            if module.handle_command(command, args):
                return True
        except Exception as e:
            logger.error("[HOOKS] Module %s error: %s", module.__name__, e)
    return False


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def handle_command(command: str, args: list) -> bool:
    """Entry point for drone routing."""
    modules = discover_modules()

    if command in ["--help", "-h", "help"]:
        print_help()
        return True

    if command in ["--version", "-V"]:
        CONSOLE.print("hooks 1.1.0")
        return True

    return route_command(command, args, modules)


def main() -> int:
    """Main entry point — routes commands or shows help."""
    args = sys.argv[1:]

    if not args:
        print_introspection()
        return 0

    if handle_command(args[0], args[1:]):
        return 0

    CONSOLE.print(f"Unknown command: {args[0]}. Try: drone @hooks --help")
    return 1


if __name__ == "__main__":
    sys.exit(main())
