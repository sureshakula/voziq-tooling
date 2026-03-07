"""
Drone - Command Router & Discovery for AIPass

Routes commands to registered branches and internal modules.
Standard branch entry point (apps/drone.py pattern).
"""

# =================== META ====================
# Name: drone.py
# Description: Drone - Command Router & Discovery
# Version: 1.0.0
# Created: 2026-03-05
# Modified: 2026-03-05
# =============================================

import sys
from typing import List

from aipass.drone.apps.handlers.exceptions import (
    BranchNotFoundError,
    CommandExecutionError,
)
from aipass.drone.apps.modules.discovery import get_help
from aipass.drone.apps.modules.resolver import list_branches
from aipass.drone.apps.modules.router import route_command
from aipass.drone.apps.modules.module_registry import (
    is_module,
    list_modules,
    get_module_info,
    get_module_introspective,
    route_module_command,
    get_module_help,
)

VERSION = "1.0.0"


# =============================================================================
# HELP & INTROSPECTION
# =============================================================================

def show_help() -> None:
    """Display drone help."""
    print()
    print("Drone - Command Router & Discovery")
    print()
    print("Routes commands to AIPass branches and internal modules.")
    print()
    print("Usage:")
    print("  drone @target command [args]   Route command to branch or module")
    print("  drone @target --help           Show help for branch or module")
    print("  drone systems                  List registered branches and modules")
    print("  drone --help                   Show this help")
    print("  drone --version                Show version")
    print()
    print("Examples:")
    print("  drone @seedgo audit aipass")
    print("  drone @seedgo list")
    print("  drone @flow status")
    print("  drone systems")
    print()


def show_introspection() -> None:
    """Show discovery view (no args)."""
    print()
    print("Drone - Command Router & Discovery")
    print()

    modules = list_modules()
    branches = list_branches()

    if modules:
        print(f"Internal Modules ({len(modules)}):")
        for name in modules:
            info = get_module_info(name)
            if info:
                print(f"  @{name:<18} {info.description}")
            else:
                print(f"  @{name:<18} (not available)")
        if branches:
            print()

    if branches:
        print(f"Registered Branches ({len(branches)}):")
        for name in sorted(branches):
            print(f"  {name}")

    if not modules and not branches:
        print("No branches or modules registered.")

    print()
    print("Run 'drone --help' for usage information")
    print()


# =============================================================================
# COMMAND HANDLERS
# =============================================================================

def _handle_systems() -> int:
    """Handle `drone systems` — list registered branches and modules."""
    branches = list_branches()
    modules = list_modules()

    if not branches and not modules:
        print("No branches or modules registered.")
        return 0

    if modules:
        print(f"Modules ({len(modules)}):")
        for name in modules:
            info = get_module_info(name)
            if info:
                print(f"  @{name:<18} {info.description}")
            else:
                print(f"  @{name:<18} (not available)")
        if branches:
            print()

    if branches:
        print(f"Branches ({len(branches)}):")
        for name in sorted(branches):
            print(f"  {name}")

    return 0


def _handle_module(name: str, args: List[str]) -> int:
    """Handle routing to an internal module."""
    if not args:
        intro_text = get_module_introspective(name)
        if intro_text:
            print(intro_text, end="")
        else:
            print(f"No information available for @{name}.")
        return 0

    if args == ["--help"]:
        help_text = get_module_help(name)
        if help_text:
            print(help_text, end="")
        else:
            print(f"No help available for @{name}.")
        return 0

    command = args[0]
    cmd_args = args[1:] if len(args) > 1 else None

    try:
        result = route_module_command(name, command, cmd_args)
    except (ImportError, AttributeError) as exc:
        print(f"drone: module @{name} is registered but not available: {exc}", file=sys.stderr)
        return 1

    if result.get("stdout"):
        print(result["stdout"], end="")
    if result.get("stderr"):
        print(result["stderr"], end="", file=sys.stderr)
    return result.get("exit_code", 0)


def _handle_target(args: List[str]) -> int:
    """Handle `drone @target command [args]` or `drone @target --help`."""
    target = args[0]
    rest = args[1:]
    module_name = target.lstrip("@").lower()

    # Check if this is a registered internal module
    if is_module(module_name):
        return _handle_module(module_name, rest)

    # Fall through to branch routing
    if not rest or rest == ["--help"]:
        try:
            result = get_help(target)
            if result.text:
                print(result.text, end="")
            else:
                print(f"No help available for {target}.")
        except BranchNotFoundError as exc:
            print(f"drone: {exc}", file=sys.stderr)
            return 1
        except CommandExecutionError as exc:
            print(f"drone: {exc}", file=sys.stderr)
            return 1
        return 0

    # drone @branch command [args...]
    command = rest[0]
    cmd_args = rest[1:]

    # Long-running interactive commands bypass capture + timeout
    interactive = command in ("monitor",)

    try:
        result = route_command(
            target, command,
            args=cmd_args if cmd_args else None,
            interactive=interactive,
        )
    except BranchNotFoundError as exc:
        print(f"drone: {exc}", file=sys.stderr)
        return 1
    except CommandExecutionError as exc:
        print(f"drone: {exc}", file=sys.stderr)
        return 1

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.exit_code


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main() -> int:
    """Main entry point - routes commands or shows help."""
    args = sys.argv[1:]

    # No args -> introspection
    if not args:
        show_introspection()
        return 0

    # --version
    if args[0] in ["--version", "-V"]:
        print(f"drone v{VERSION}")
        return 0

    # --help
    if args[0] in ["--help", "-h", "help"]:
        show_help()
        return 0

    command = args[0]

    # systems — list branches and modules
    if command == "systems":
        return _handle_systems()

    # @target — route to branch or module
    if command.startswith("@"):
        return _handle_target(args)

    # Unknown command
    print(f"drone: unknown command '{command}'", file=sys.stderr)
    print("Run 'drone --help' for usage.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
