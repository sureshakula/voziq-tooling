"""
Drone CLI — command-line interface for aipass.drone.

Entry point: `drone` (wired via pyproject.toml console_scripts to cli.main).

Usage:
  drone                          Show available commands
  drone --help                   Show help
  drone --version                Show version
  drone systems                  List registered branches and modules
  drone @branch command [args]   Route command to branch
  drone @module command [args]   Route command to internal module
  drone @branch --help           Show help for branch or module

Zero external dependencies — stdlib only (sys).
"""

from __future__ import annotations

import sys

import aipass
from aipass.drone import (
    CommandExecutionError,
    BranchNotFoundError,
    get_help,
    list_branches,
    route_command,
)
from aipass.drone.modules import (
    is_module,
    list_modules,
    get_module_info,
    route_module_command,
    get_module_help,
)

_HELP_TEXT = """\
drone — AIPass command router

Usage:
  drone                          Show this help
  drone --help                   Show this help
  drone --version                Show version
  drone systems                  List registered branches and modules
  drone @target command [args]   Route command to branch or module
  drone @target --help           Show help for branch or module

Examples:
  drone systems
  drone @seedgo audit src/
  drone @seedgo check src/myfile.py
  drone @flow status
  drone @flow --help
"""


def main() -> None:
    """Entry point for the `drone` CLI command.

    Parses sys.argv manually and dispatches to the appropriate handler.
    Exits with the command's exit code on branch commands, 0 on success,
    1 on error.
    """
    args = sys.argv[1:]

    # No args or explicit --help
    if not args or args == ["--help"]:
        print(_HELP_TEXT, end="")
        sys.exit(0)

    # --version
    if args == ["--version"]:
        print(aipass.__version__)
        sys.exit(0)

    # systems — list registered branches
    if args[0] == "systems":
        _cmd_systems()
        return

    # @branch ... — route to a branch
    if args[0].startswith("@"):
        _cmd_branch(args)
        return

    # Unknown command
    print(f"drone: unknown command '{args[0]}'", file=sys.stderr)
    print("Run 'drone --help' for usage.", file=sys.stderr)
    sys.exit(1)


def _cmd_systems() -> None:
    """Handle `drone systems` — list registered branches and modules."""
    branches = list_branches()
    modules = list_modules()

    if not branches and not modules:
        print("No branches or modules registered.")
        sys.exit(0)

    if modules:
        print(f"Modules ({len(modules)}):")
        for name in modules:
            info = get_module_info(name)
            if info:
                print(f"  @{name}  {info.description}")
            else:
                print(f"  @{name}  (not available)")
        if branches:
            print()

    if branches:
        print(f"Branches ({len(branches)}):")
        for name in sorted(branches):
            print(f"  {name}")

    sys.exit(0)


def _cmd_branch(args: list[str]) -> None:
    """Handle `drone @target command [args]` or `drone @target --help`.

    Checks internal modules first (e.g. @seedgo), then falls back
    to branch registry for external branches.
    """
    target = args[0]
    rest = args[1:]
    module_name = target.lstrip("@")

    # Check if this is a registered internal module
    if is_module(module_name):
        _cmd_module(module_name, rest)
        return

    # Fall through to branch routing
    # drone @branch --help
    if not rest or rest == ["--help"]:
        try:
            result = get_help(target)
            if result.text:
                print(result.text, end="")
            else:
                print(f"No help available for {target}.")
        except BranchNotFoundError as exc:
            print(f"drone: {exc}", file=sys.stderr)
            sys.exit(1)
        except CommandExecutionError as exc:
            print(f"drone: {exc}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    # drone @branch command [args...]
    command = rest[0]
    cmd_args = rest[1:]

    try:
        result = route_command(target, command, args=cmd_args if cmd_args else None)
    except BranchNotFoundError as exc:
        print(f"drone: {exc}", file=sys.stderr)
        sys.exit(1)
    except CommandExecutionError as exc:
        print(f"drone: {exc}", file=sys.stderr)
        sys.exit(1)

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    sys.exit(result.exit_code)


def _cmd_module(name: str, args: list[str]) -> None:
    """Handle routing to an internal module (e.g. @seedgo)."""
    # drone @module --help (or no args)
    if not args or args == ["--help"]:
        help_text = get_module_help(name)
        if help_text:
            print(help_text, end="")
        else:
            print(f"No help available for @{name}.")
        sys.exit(0)

    command = args[0]
    cmd_args = args[1:] if len(args) > 1 else None

    try:
        result = route_module_command(name, command, cmd_args)
    except (ImportError, AttributeError) as exc:
        print(f"drone: module @{name} is registered but not available: {exc}", file=sys.stderr)
        sys.exit(1)

    if result.get("stdout"):
        print(result["stdout"], end="")
    if result.get("stderr"):
        print(result["stderr"], end="", file=sys.stderr)
    sys.exit(result.get("exit_code", 0))
