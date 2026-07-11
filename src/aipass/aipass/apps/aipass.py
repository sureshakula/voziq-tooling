# =================== AIPass ====================
# Name: aipass.py
# Description: AIPASS branch entry point — thin command router
# Version: 0.1.0
# Created: 2026-04-16
# Modified: 2026-04-16
# =============================================

"""
AIPASS Branch - Main Orchestrator

Auto-discovery architecture:
- Scans modules/ directory for .py files with handle_command()
- Routes commands to discovered modules automatically
- No manual imports or routing needed
"""

import os
import sys
import importlib
import importlib.metadata
from pathlib import Path
from typing import List, Any

# Windows terminals/pipes default to cp1252, which can't encode the Unicode
# Rich emits (✓/✗, box-drawing, arrows). PYTHONUTF8 only affects child
# interpreters, not this process's already-open stdout/stderr — so we also
# reconfigure the live streams to UTF-8 in place (Python 3.7+). Without this,
# `aipass init` scaffolds correctly but crashes printing its success banner
# with UnicodeEncodeError ('charmap') on Windows. Mirrors drone/cli.py.
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")  # for child subprocesses
    for _stream in (sys.stdout, sys.stderr):
        _reconfigure = getattr(_stream, "reconfigure", None)
        if _reconfigure is not None:
            _reconfigure(encoding="utf-8", errors="replace")

from aipass.prax import logger

# =============================================================================
# MODULE DISCOVERY
# =============================================================================

MODULES_DIR = Path(__file__).parent / "modules"


_import_failures: dict[str, Exception] = {}


def discover_modules() -> List[Any]:
    """Auto-discover modules in modules/ directory."""
    modules = []
    _import_failures.clear()

    if not MODULES_DIR.exists():
        return modules

    for file_path in MODULES_DIR.glob("*.py"):
        if file_path.name.startswith("_"):
            continue

        module_name = f"aipass.aipass.apps.modules.{file_path.stem}"

        try:
            module = importlib.import_module(module_name)
            if hasattr(module, "handle_command"):
                modules.append(module)
        except Exception as e:
            logger.error(f"[AIPASS] Failed to load module {module_name}: {e}")
            _import_failures[file_path.stem] = e

    return modules


def route_command(command: str, args: List[str], modules: List[Any]) -> bool:
    """Route command to appropriate module.

    Returns True on success. Raises on handler crash so callers can
    distinguish 'not found' (False) from 'found but broken'.
    """
    for module in modules:
        try:
            if module.handle_command(command, args):
                return True
        except Exception as e:
            mod_name = module.__name__.split(".")[-1]
            logger.error(f"[AIPASS] Module {mod_name} crashed: {e}")
            raise
    return False


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def main():
    """Main entry point - routes commands or shows help."""
    modules = discover_modules()
    args = sys.argv[1:]

    if len(args) > 0 and args[0] in ["--version", "-V"]:
        try:
            version = importlib.metadata.version("aipass")
        except importlib.metadata.PackageNotFoundError:
            logger.info("[AIPASS] Package metadata not found, version unknown")
            version = "unknown"
        print(f"aipass {version}")
        return 0

    show_root_help = len(args) == 0 or args[0] in ["--help", "-h"] or (args[0] == "help" and len(args) == 1)
    if show_root_help:
        print(f"AIPASS - {len(modules)} modules discovered")
        for module in modules:
            stem = module.__name__.split(".")[-1]
            name = getattr(module, "COMMAND", stem)
            desc = (module.__doc__ or "").strip().split("\n")[0] if module.__doc__ else "No description"
            print(f"  {name:20} {desc}")
        return 0

    command = args[0]
    remaining = args[1:] if len(args) > 1 else []

    # Subcommand --help guard: intercept before dispatch
    if remaining and remaining[0] in ("--help", "-h"):
        for module in modules:
            if module.handle_command(command, ["--help"]):
                return 0
        print(f"Unknown command: {command}")
        return 1

    try:
        if route_command(command, remaining, modules):
            return 0
    except Exception as e:
        print(f"Error: '{command}' crashed: {e}")
        logger.error(f"[AIPASS] '{command}' traceback", exc_info=True)
        return 1

    if command.startswith("@"):
        print(f"{command} is a drone routing target, not an aipass command.")
        print("aipass is your front-door CLI; drone is the agent router — two separate tools.")
        print()
        print(f"  Reach an agent:   drone {command} ...   ·  drone systems")
        print("  aipass commands:  aipass --help")
        return 1

    for stem, err in _import_failures.items():
        if command in (stem, stem.replace("_", "")):
            print(f"Error: '{command}' failed to load: {err}")
            return 1

    print(f"Unknown command: {command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
