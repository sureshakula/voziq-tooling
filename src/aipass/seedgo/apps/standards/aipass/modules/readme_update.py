#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: readme_update.py - README Auto-Update Module
# Date: 2026-02-21
# Version: 1.0.0
# Category: seed/modules
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2026-02-21): Initial build (DPLAN-026 Phase 4)
#
# CODE STANDARDS:
#   - Module interface: handle_command(command, args) -> bool
#   - Auto-discovered by seed.py entry point
#   - Thin orchestrator - delegates to handlers
# =============================================

"""
README Auto-Update Module

On-demand updating of auto-generated README sections for any AIPass branch.
Uses readme_generator handler to produce content for sections marked with
<!-- AUTO:SECTION --> comment markers in README.md files.

Run: python3 seed.py readme update @branch
"""

import sys
from pathlib import Path
from typing import List

# =============================================================================
# INFRASTRUCTURE SETUP
# =============================================================================

AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))

# =============================================================================
# IMPORTS
# =============================================================================

# Prax logger (system-wide, always first)
from prax.apps.modules.logger import system_logger as logger

# JSON handler for tracking
from seed.apps.handlers.json import json_handler

# CLI services (display/output formatting)
from cli.apps.modules import console, header

# Handler (implementation)
from seed.apps.handlers.standards.readme_ops import (
    load_generator,
    resolve_targets,
    SECTION_NAMES,
)


# =============================================================================
# COMMAND HANDLER
# =============================================================================

def handle_command(command: str, args: List[str]) -> bool:
    """
    Handle 'readme' command.

    Args:
        command: Command name
        args: Additional arguments

    Returns:
        True if handled, False if not this module's command
    """
    if command != "readme":
        return False

    if "--help" in args or "-h" in args:
        print_help()
        return True

    # Subcommands: update, check
    subcommand = args[0] if args else "update"
    remaining_args = args[1:] if len(args) > 1 else []

    if subcommand == "update":
        _handle_update(remaining_args)
    elif subcommand == "check":
        _handle_check(remaining_args)
    else:
        # Maybe it's a branch name without subcommand: `seed readme @cortex`
        _handle_update(args)

    return True


# =============================================================================
# SUBCOMMAND ORCHESTRATION
# =============================================================================

def _handle_update(args: List[str]) -> None:
    """Orchestrate the 'update' subcommand"""
    generator = load_generator()
    if not generator:
        console.print("[red]Failed to load README generator[/red]")
        return

    branches, error = resolve_targets(args)
    if error:
        _print_target_error(error)
        return

    json_handler.log_operation(
        "readme_update_started",
        {"targets": [b['name'] for b in branches]}
    )

    total_updated = 0

    for branch in branches:
        branch_name = branch['name']
        branch_path = branch['path']

        console.print()
        console.print(f"[bold cyan]README Update: {branch_name}[/bold cyan]")

        readme_path = Path(branch_path) / 'README.md'
        if not readme_path.exists():
            console.print(f"  [yellow]No README.md found at {branch_path}[/yellow]")
            continue

        try:
            result = generator.update_readme_auto_sections(branch_path, dry_run=False)
            _print_result(result)
            if result.get('updated'):
                total_updated += 1
        except Exception as e:
            console.print(f"  [red]Error: {e}[/red]")
            logger.error(f"README update failed for {branch_name}: {e}")

    if len(branches) > 1:
        console.print()
        console.print(f"[dim]Updated {total_updated}/{len(branches)} READMEs[/dim]")

    json_handler.log_operation(
        "readme_update_completed",
        {"branches_processed": len(branches), "branches_updated": total_updated}
    )


def _handle_check(args: List[str]) -> None:
    """Orchestrate the 'check' subcommand (dry run)"""
    generator = load_generator()
    if not generator:
        console.print("[red]Failed to load README generator[/red]")
        return

    branches, error = resolve_targets(args)
    if error:
        _print_target_error(error)
        return

    for branch in branches:
        branch_name = branch['name']
        branch_path = branch['path']

        console.print()
        console.print(f"[bold cyan]README Check: {branch_name}[/bold cyan]")

        readme_path = Path(branch_path) / 'README.md'
        if not readme_path.exists():
            console.print(f"  [yellow]No README.md found at {branch_path}[/yellow]")
            continue

        try:
            result = generator.update_readme_auto_sections(branch_path, dry_run=True)
            _print_result(result, is_check=True)
        except Exception as e:
            console.print(f"  [red]Error: {e}[/red]")
            logger.error(f"README check failed for {branch_name}: {e}")


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def _print_target_error(error: str) -> None:
    """Display target resolution errors"""
    if error == "no_args":
        console.print("[yellow]Usage: seed readme update @branch[/yellow]")
        console.print("[dim]Use @all to update all branches[/dim]")
    elif error == "no_branches":
        console.print("[red]No branches found in registry[/red]")
    elif error.startswith("not_found:"):
        target = error.split(":", 1)[1]
        console.print(f"[red]Branch '{target}' not found in registry[/red]")


def _print_result(result: dict, is_check: bool = False) -> None:
    """Display formatted results of an update or check operation"""
    updated = result.get('updated', [])
    missing = result.get('missing_markers', [])
    errors = result.get('errors', [])

    if errors:
        for err in errors:
            console.print(f"  [red]Error: {err}[/red]")
        return

    for section_key, display_name in SECTION_NAMES.items():
        if section_key in updated:
            if is_check:
                console.print(f"  [yellow]Would update[/yellow] {display_name} - content differs")
            else:
                console.print(f"  [green]Updated[/green] {display_name}")
        elif section_key in missing:
            console.print(f"  [dim]Skipped[/dim]  {display_name} - no marker found")
        else:
            if is_check:
                console.print(f"  [green]Up to date[/green] {display_name}")


def print_help():
    """Print help information"""
    console.print()
    header("README Auto-Update")
    console.print()
    console.print("[yellow]USAGE:[/yellow]")
    console.print("  seed readme update @branch    Update auto-generated sections")
    console.print("  seed readme update @all       Update all branch READMEs")
    console.print("  seed readme check @branch     Dry run - show what would change")
    console.print()
    console.print("[yellow]AUTO-GENERATED SECTIONS:[/yellow]")
    console.print("  TREE          Directory structure")
    console.print("  MODULES       Module list from apps/modules/")
    console.print("  COMMANDS      Commands from --help output")
    console.print("  HEADER        Branch info from id.json")
    console.print("  LAST_UPDATED  Timestamp")
    console.print()
    console.print("[dim]Sections are marked with <!-- AUTO:NAME --> comments in README.md[/dim]")
    console.print("[dim]Commands: readme, --help[/dim]")


if __name__ == "__main__":
    # Handle help flag
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        print_help()
        sys.exit(0)

    # Confirm Prax logger connection
    logger.info("Prax logger connected to readme_update")

    # Log standalone execution
    json_handler.log_operation(
        "readme_update_run",
        {"command": "standalone", "args": sys.argv[1:]}
    )

    # Run command
    handle_command("readme", sys.argv[1:])
