"""
Skills Standards Pack - Entry Point

Auto-discovery architecture:
- Scans modules/ directory for .py files with handle_command()
- Routes commands to discovered modules automatically
- No manual imports or routing needed
"""

# =================== META ====================
# Name: pack_entry.py
# Description: Skills Standards Pack - Entry Point
# Version: 1.0.0
# Created: 2026-03-07
# Modified: 2026-03-07
# =============================================


import sys
import importlib.util
from pathlib import Path
from typing import List, Any

from aipass.prax import logger
from aipass.cli import console, header

# =============================================================================
# MODULE DISCOVERY
# =============================================================================

MODULES_DIR = Path(__file__).parent / "modules"
VERSION = "1.0.0"


def discover_modules() -> List[Any]:
    """Auto-discover modules in modules/ directory."""
    modules = []

    if not MODULES_DIR.exists():
        return modules

    for file_path in sorted(MODULES_DIR.glob("*.py")):
        if file_path.name.startswith("_"):
            continue

        try:
            spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "handle_command"):
                modules.append(module)
        except Exception as e:
            logger.error(f"[SKILLS] Failed to load module {file_path.stem}: {e}")

    return modules


def route_command(command: str, args: List[str], modules: List[Any]) -> bool:
    """Route command to appropriate module."""
    for module in modules:
        try:
            if module.handle_command(command, args):
                return True
        except Exception as e:
            logger.error(f"[SKILLS] Module {module.__name__} error: {e}")
    return False


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point - routes commands or shows help."""
    modules = discover_modules()
    args = sys.argv[1:]

    if not args or args[0] in ["--help", "-h", "help"]:
        header("Skills Standards Pack")
        console.print()
        console.print(f"  {len(modules)} modules discovered")
        console.print()
        for module in modules:
            name = getattr(module, "__name__", "unknown").split(".")[-1]
            desc = (module.__doc__ or "").strip().split("\n")[0] if module.__doc__ else "No description"
            console.print(f"  {name:20} {desc}")
        console.print()
        return 0

    if args[0] in ["--version", "-V"]:
        console.print(f"skills-standards v{VERSION}")
        return 0

    command = args[0]
    remaining = args[1:] if len(args) > 1 else []

    if route_command(command, remaining, modules):
        return 0

    console.print(f"Unknown command: {command}")
    console.print("Run 'skills --help' for available commands")
    return 1


if __name__ == "__main__":
    sys.exit(main())
