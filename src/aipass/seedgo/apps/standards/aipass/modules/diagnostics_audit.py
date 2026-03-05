#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: diagnostics_audit.py - System-wide Type Error Diagnostics
# Date: 2025-11-28
# Version: 0.1.0
# Category: seed/modules
#
# CHANGELOG (Max 5 entries):
#   - v0.1.0 (2025-11-28): Initial implementation - pyright system scan
#
# CODE STANDARDS:
#   - Module orchestrates, handlers implement
# =============================================

"""
System-wide Type Error Diagnostics

Runs pyright on all AIPass branches to detect type errors,
undefined variables, and other static analysis issues.

Usage:
    drone @seed diagnostics           # All branches
    drone @seed diagnostics flow      # Specific branch
"""

import sys
from pathlib import Path
from typing import Dict, List

# Infrastructure
AIPASS_ROOT = Path.home() / "aipass_core"
SEED_ROOT = Path.home() / "seed"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))

# Prax logger (system-wide)
from prax.apps.modules.logger import system_logger as logger

# CLI service
from cli.apps.modules import console
from cli.apps.modules.display import header

# JSON handler for logging
from seed.apps.handlers.json import json_handler

# Drone services for @ resolution
from drone.apps.modules import normalize_branch_arg

# Diagnostics handlers
from seed.apps.handlers.diagnostics import discover_branches, run_branch_diagnostics


def print_branch_diagnostics(result: Dict):
    """Print diagnostics for a single branch"""
    branch = result['branch']
    errors = result.get('total_errors', 0)
    warnings = result.get('total_warnings', 0)
    files_analyzed = result.get('total_files', 0)
    files_with_errors = result.get('files_with_errors', 0)

    # Status icon
    if errors == 0:
        status = "[green]✓[/green]"
        color = "green"
    elif errors < 10:
        status = "[yellow]⚠[/yellow]"
        color = "yellow"
    else:
        status = "[red]✗[/red]"
        color = "red"

    console.print()
    console.print(f"{status} [bold]{branch}[/bold]")
    console.print(f"  Files: {files_analyzed} analyzed, {files_with_errors} with errors")
    console.print(f"  [{color}]Errors: {errors}[/{color}]  Warnings: {warnings}")

    # Show top files with errors (clickable paths)
    if files_with_errors > 0:
        console.print("  [dim]Top files with errors:[/dim]")
        for file_result in result.get('results', [])[:5]:
            if file_result['errors'] > 0:
                file_path = file_result['file']
                file_errors = file_result['errors']
                console.print(f"    [red]✗[/red] {file_path} [dim]({file_errors} errors)[/dim]")

                # Show first 3 errors per file
                for diag in file_result['diagnostics'][:3]:
                    line = diag['line']
                    msg = diag['message'][:60] + "..." if len(diag['message']) > 60 else diag['message']
                    console.print(f"      [dim]L{line}:[/dim] {msg}")


def print_system_summary(all_results: List[Dict]):
    """Print system-wide diagnostics summary"""
    total_branches = len(all_results)
    total_errors = sum(r.get('total_errors', 0) for r in all_results)
    total_warnings = sum(r.get('total_warnings', 0) for r in all_results)
    total_files = sum(r.get('total_files', 0) for r in all_results)
    files_with_errors = sum(r.get('files_with_errors', 0) for r in all_results)

    clean_branches = sum(1 for r in all_results if r.get('total_errors', 0) == 0)
    branches_with_errors = total_branches - clean_branches

    console.print()
    console.print("─" * 70)
    console.print("[bold]SYSTEM DIAGNOSTICS SUMMARY:[/bold]")
    console.print(f"  Total branches:        {total_branches}")
    console.print(f"  Clean branches:        {clean_branches} [green]✓[/green]")
    console.print(f"  Branches with errors:  {branches_with_errors} [red]✗[/red]")
    console.print()
    console.print(f"  Files analyzed:        {total_files}")
    console.print(f"  Files with errors:     {files_with_errors}")
    console.print(f"  Total errors:          [red]{total_errors}[/red]")
    console.print(f"  Total warnings:        [yellow]{total_warnings}[/yellow]")
    console.print()

    # Top branches by error count
    if branches_with_errors > 0:
        console.print("[bold]BRANCHES BY ERROR COUNT:[/bold]")
        sorted_results = sorted(all_results, key=lambda x: x.get('total_errors', 0), reverse=True)
        for result in sorted_results[:10]:
            if result.get('total_errors', 0) > 0:
                branch = result['branch']
                errors = result['total_errors']
                console.print(f"  {branch:15} [red]{errors:4} errors[/red]")

    console.print("─" * 70)
    console.print()


def handle_command(command: str, args: List[str]) -> bool:
    """
    Handle 'diagnostics' command

    Args:
        command: Command name
        args: Additional arguments

    Returns:
        True if handled, False if not this module's command
    """
    if command != "diagnostics":
        return False

    try:
        # Parse arguments
        specific_branch = None

        for arg in args:
            if arg == '--help' or arg == '-h':
                print_help()
                return True
            if not arg.startswith('-'):
                specific_branch = normalize_branch_arg(arg)

        # Log start
        json_handler.log_operation(
            "diagnostics_audit_started",
            {"specific_branch": specific_branch}
        )

        # Header
        console.print()
        header("AIPASS TYPE ERROR DIAGNOSTICS")
        console.print()
        console.print("[dim]Running pyright on all branches (this may take a moment)...[/dim]")

        # Discover branches
        branches = discover_branches()

        if specific_branch:
            branches = [b for b in branches if b['name'] == specific_branch]
            if not branches:
                console.print(f"[red]Branch '{specific_branch}' not found[/red]")
                return True

        console.print(f"[dim]Found {len(branches)} branches to scan...[/dim]")

        # Run diagnostics on all branches
        all_results = []
        for branch in branches:
            console.print(f"[dim]Scanning {branch['name']}...[/dim]", end="\r")
            result = run_branch_diagnostics(branch)
            all_results.append(result)

        console.print(" " * 50, end="\r")  # Clear progress

        # Print results
        for result in all_results:
            print_branch_diagnostics(result)

        # Print system summary (unless specific branch)
        if not specific_branch:
            print_system_summary(all_results)

        # Log completion
        total_errors = sum(r.get('total_errors', 0) for r in all_results)
        json_handler.log_operation(
            "diagnostics_audit_completed",
            {
                "branches_scanned": len(all_results),
                "total_errors": total_errors
            }
        )

        return True

    except Exception as e:
        logger.error(f"Diagnostics audit failed: {e}")
        console.print(f"[red]Error during diagnostics audit: {e}[/red]")
        return False


def print_introspection():
    """Display module info when run without arguments (Seed pattern)"""
    console.print()
    console.print("[bold cyan]Diagnostics Audit Module[/bold cyan]")
    console.print()
    console.print("[dim]System-wide type error detection using pyright[/dim]")
    console.print()
    console.print("[yellow]Commands:[/yellow] diagnostics")
    console.print()
    console.print("[dim]Run 'drone @seed diagnostics --help' for usage[/dim]")
    console.print()


def print_help():
    """Print help information"""
    console.print()
    console.print("[bold cyan]Diagnostics Audit Module[/bold cyan]")
    console.print("System-wide type error detection using pyright")
    console.print()

    console.print("[yellow]COMMANDS:[/yellow]")
    console.print("  Commands: diagnostics, --help")
    console.print()
    console.print("  [cyan]diagnostics[/cyan]           - Scan all branches for type errors")
    console.print("  [cyan]diagnostics [branch][/cyan]  - Scan specific branch")
    console.print()

    console.print("[yellow]USAGE:[/yellow]")
    console.print("  [dim]# Via drone[/dim]")
    console.print("  drone @seed diagnostics")
    console.print("  drone @seed diagnostics flow")
    console.print()
    console.print("  python3 seed.py diagnostics")
    console.print("  python3 seed.py diagnostics cortex")
    console.print()

    console.print("[yellow]WHAT IT CHECKS:[/yellow]")
    console.print("  - Type errors (Pylance/pyright)")
    console.print("  - Undefined variables")
    console.print("  - Import errors")
    console.print("  - Argument type mismatches")
    console.print()


if __name__ == "__main__":
    # Handle help flag or no arguments
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']):
        print_help()
        sys.exit(0)

    # Confirm Prax logger connection
    logger.info("Prax logger connected to diagnostics_audit")

    # Log standalone execution
    json_handler.log_operation(
        "diagnostics_run",
        {"command": "standalone", "args": sys.argv[1:]}
    )

    # Run diagnostics
    handle_command("diagnostics", sys.argv[1:])
