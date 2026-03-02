"""
Seed Go Command-Line Interface

Entry point: `seedgo` (wired via pyproject.toml console_scripts to cli.main).

Commands:
  seedgo init [--profile NAME]
      Initialize Seed Go in the current directory. Creates .seedgo/config.json
      and .seedgo/plugins/ via create_default_config(). Safe to run from any
      directory — does NOT require an existing .seedgo/ directory.

  seedgo check [FILE ...] [--format FORMAT] [--threshold N]
      Run checks on specified files, or on all project files if none given.
      Exits 0 if all checks pass, 1 if any fail.
      --format: human (default), json, github
      --threshold: Override the pass threshold (0-100)

  seedgo list
      List all discovered plugins (from all sources). Shows name, description,
      source, and file types. Useful for verifying plugins are loaded correctly.

All commands use find_project_root() to locate the nearest .seedgo/ directory
walking up from cwd. `init` is the only command that works without one.

Zero external dependencies — stdlib only (argparse, sys, os, pathlib).
"""

import argparse
import os
import sys
from pathlib import Path

from .config import ConfigError, create_default_config, find_project_root
from .discovery import discover_plugins
from .reporter import report_results
from .runner import run_checks


def main() -> None:
    """Entry point for the `seedgo` CLI command.

    Parses command-line arguments and dispatches to the appropriate handler.
    All errors are caught and reported cleanly — never shows a raw traceback.

    Exit codes:
        0 — success (or checks passed)
        1 — failure (checks failed, config error, or usage error)
    """
    parser = argparse.ArgumentParser(
        prog="seedgo",
        description="Portable, plugin-based code standards checker.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  seedgo init                    # Set up .seedgo/ in current directory\n"
            "  seedgo init --profile python-basic\n"
            "  seedgo check                   # Check all project files\n"
            "  seedgo check src/main.py       # Check a specific file\n"
            "  seedgo check --format json     # Machine-readable output\n"
            "  seedgo check --format github   # GitHub Actions annotations\n"
            "  seedgo list                    # Show available plugins\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # -----------------------------------------------------------------------
    # seedgo init
    # -----------------------------------------------------------------------
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize Seed Go in the current directory.",
        description="Creates .seedgo/config.json and .seedgo/plugins/ in the current directory.",
    )
    init_parser.add_argument(
        "--profile",
        default=None,
        metavar="NAME",
        help="Starter profile name to embed in config (e.g., python-basic, python-strict).",
    )

    # -----------------------------------------------------------------------
    # seedgo check
    # -----------------------------------------------------------------------
    check_parser = subparsers.add_parser(
        "check",
        help="Run checks on files (or all project files if none specified).",
        description="Run all discovered plugins against the specified files.",
    )
    check_parser.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help="Files to check. If omitted, checks all files under the project root.",
    )
    check_parser.add_argument(
        "--format",
        choices=["human", "json", "github"],
        default="human",
        help="Output format: human (default), json, or github (Actions annotations).",
    )
    check_parser.add_argument(
        "--threshold",
        type=int,
        default=None,
        metavar="N",
        help="Override the pass threshold (0-100). Defaults to value in config (75).",
    )
    check_parser.add_argument(
        "--plugin",
        action="append",
        metavar="NAME",
        dest="plugins",
        help="Run only this plugin (may be repeated for multiple plugins).",
    )

    # -----------------------------------------------------------------------
    # seedgo list
    # -----------------------------------------------------------------------
    subparsers.add_parser(
        "list",
        help="List all available plugins discovered from all sources.",
        description="Discovers and lists plugins from built-ins, installed packages, and .seedgo/plugins/.",
    )

    # -----------------------------------------------------------------------
    # Dispatch
    # -----------------------------------------------------------------------
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "init":
        _cmd_init(args)
    elif args.command == "check":
        _cmd_check(args)
    elif args.command == "list":
        _cmd_list(args)
    else:
        parser.print_help()
        sys.exit(1)


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------


def _cmd_init(args: argparse.Namespace) -> None:
    """Handle `seedgo init [--profile NAME]`.

    Creates .seedgo/config.json and .seedgo/plugins/ in the current working
    directory. Prints a success message. Exits 1 on error.
    """
    project_root = os.getcwd()
    profile = getattr(args, "profile", None)

    try:
        config_path = create_default_config(project_root, profile=profile)
        print(f"Seed Go initialized.")
        print(f"  Config: {config_path}")
        print(f"  Plugins: {str(Path(config_path).parent / 'plugins')}")
        if profile:
            print(f"  Profile: {profile}")
        print("")
        print("Next steps:")
        print("  1. Add plugins to .seedgo/plugins/")
        print("  2. Run: seedgo check")
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def _cmd_check(args: argparse.Namespace) -> None:
    """Handle `seedgo check [FILE ...] [--format FORMAT] [--threshold N]`.

    Locates the project root, runs all applicable checks, formats and prints
    the output. Exits 0 if checks pass, 1 if they fail.
    """
    cwd = os.getcwd()

    # Locate project root (walk up from cwd looking for .seedgo/)
    project_root = find_project_root(cwd)
    if project_root is None:
        print(
            "Error: No .seedgo/ directory found. Run `seedgo init` first.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Resolve explicit file arguments to absolute paths
    files: list[str] | None = None
    if args.files:
        files = []
        for f in args.files:
            fp = Path(f)
            if not fp.is_absolute():
                fp = Path(cwd) / fp
            if not fp.exists():
                print(f"Warning: File not found: {fp}", file=sys.stderr)
                continue
            files.append(str(fp.resolve()))
        if not files:
            print("Error: None of the specified files exist.", file=sys.stderr)
            sys.exit(1)

    try:
        results, overall = run_checks(
            project_root=project_root,
            files=files,
            plugins=getattr(args, "plugins", None),
        )

        # Apply CLI threshold override AFTER run_checks (re-evaluate pass)
        if args.threshold is not None:
            overall["threshold"] = args.threshold
            error_count = overall.get("error_count", 0)
            overall["passed"] = overall["overall_score"] >= args.threshold and error_count == 0

        output = report_results(results, overall, format=args.format)
        print(output)

    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0 if overall.get("passed", True) else 1)


def _cmd_list(_args: argparse.Namespace) -> None:
    """Handle `seedgo list`.

    Discovers all plugins and prints a formatted table showing:
      name, description, source, file types.

    Exits 0 always (listing is informational).
    """
    cwd = os.getcwd()
    project_root = find_project_root(cwd)

    # Discover plugins (project_root may be None if no .seedgo/ found)
    plugins = discover_plugins(project_root)

    if not plugins:
        print("No plugins found.")
        print("")
        print("Add plugins to .seedgo/plugins/ or install plugin packages.")
        sys.exit(0)

    print(f"Found {len(plugins)} plugin(s):\n")

    col_name = max(len(p["name"]) for p in plugins) + 2
    col_source = max(len(p["source"]) for p in plugins) + 2

    header = (
        f"  {'NAME':<{col_name}}{'SOURCE':<{col_source}}{'FILE TYPES':<20}  DESCRIPTION"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))

    for plugin in plugins:
        module = plugin["module"]
        name = plugin["name"]
        source = plugin["source"]
        description = getattr(module, "PLUGIN_DESCRIPTION", "")
        file_types = getattr(module, "FILE_TYPES", ["*"])
        types_str = ", ".join(file_types)

        print(f"  {name:<{col_name}}{source:<{col_source}}{types_str:<20}  {description}")

    sys.exit(0)
