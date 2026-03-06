"""
Standards Audit Module

Scans all AIPass branches and generates compliance dashboard.
Shows per-branch scores, system-wide metrics, and top issues.

Run: python3 seed.py audit
"""

import sys
from pathlib import Path
from typing import List
from collections import defaultdict

# =============================================================================
# INFRASTRUCTURE SETUP
# =============================================================================

# IMPORTS
# =============================================================================

# Prax logger (system-wide, always first)
from aipass.prax import logger
# JSON handler for tracking
from handlers.json import json_handler

# CLI services (display/output formatting)
from aipass.cli import console, header

# Audit handlers (implementation)
from handlers.audit.discovery import discover_branches, _is_branch_private
from handlers.audit.branch_audit import audit_branch
from handlers.audit.bypass_audit import audit_bypasses
from handlers.audit.display import print_branch_summary, print_system_summary, print_bypass_audit

# Bypass system - import from checklist
from modules.standards_checklist import load_bypass_rules

# Drone services for @ resolution
from aipass.drone.apps.modules import normalize_branch_arg


# =============================================================================
# COMMAND HANDLER
# =============================================================================

def handle_command(command: str, args: List[str]) -> bool:
    """
    Handle 'audit' command

    Args:
        command: Command name
        args: Additional arguments

    Returns:
        True if handled, False if not this module's command
    """
    if command != "audit":
        return False

    # Parse arguments
    specific_branch = None
    show_bypasses = False

    for arg in args:
        if arg in ['--show-bypasses', '--bypasses', '-b']:
            show_bypasses = True
        elif not arg.startswith('-'):
            specific_branch = normalize_branch_arg(arg)

    # Handle --show-bypasses mode
    if show_bypasses:
        _bp_include_private = specific_branch is not None and _is_branch_private(specific_branch)
        branches = discover_branches(include_private=_bp_include_private)
        if specific_branch:
            branches = [b for b in branches if b['name'] == specific_branch]

        # Load bypass rules for each branch
        bypass_rules_map = {}
        for branch in branches:
            branch_path = Path(branch['path'])
            bypass_rules_map[branch['name']] = load_bypass_rules(str(branch_path))

        bypass_results = audit_bypasses(branches, bypass_rules_map)
        print_bypass_audit(bypass_results)
        return True

    # =========================================================================
    # PRIVATE BRANCH ACCESS CONTROL
    # =========================================================================
    # If targeting a private branch directly, only allow audit from inside
    # that branch's directory. This enforces isolation per DPLAN-035.
    if specific_branch and _is_branch_private(specific_branch):
        # Resolve branch path from registry to check CWD
        import json as _json
        _registry_path = Path.home() / "BRANCH_REGISTRY.json"
        _branch_path = None
        if _registry_path.exists():
            try:
                with open(_registry_path, 'r', encoding='utf-8') as _f:
                    _reg = _json.load(_f)
                for _b in _reg.get('branches', []):
                    if _b.get('name', '').upper() == specific_branch.upper():
                        _branch_path = Path(_b['path'])
                        break
            except (ValueError, IOError):
                pass

        # Also check PRIVATE_BRANCH_REGISTRY for path
        if _branch_path is None:
            _priv_path = Path.home() / "PRIVATE_BRANCH_REGISTRY.json"
            if _priv_path.exists():
                try:
                    with open(_priv_path, 'r', encoding='utf-8') as _f:
                        _priv = _json.load(_f)
                    for _b in _priv.get('branches', []):
                        if _b.get('name', '').upper() == specific_branch.upper():
                            _branch_path = Path(_b['path'])
                            break
                except (ValueError, IOError):
                    pass

        if _branch_path is not None:
            cwd = Path.cwd()
            is_internal = cwd == _branch_path or cwd.is_relative_to(_branch_path)
            if not is_internal:
                console.print(
                    f"[red]Branch '{specific_branch}' is private "
                    f"— audit access restricted to internal use only[/red]"
                )
                return True

    # Log audit start
    json_handler.log_operation(
        "standards_audit_started",
        {"specific_branch": specific_branch}
    )

    # Discover branches
    # When targeting a specific private branch from inside its CWD,
    # include private branches in discovery so we can find it
    _include_private = specific_branch is not None and _is_branch_private(specific_branch)
    console.print()
    header("AIPASS BRANCH STANDARDS AUDIT")
    console.print()

    branches = discover_branches(include_private=_include_private)

    if specific_branch:
        branches = [b for b in branches if b['name'] == specific_branch]
        if not branches:
            console.print(f"[red]Branch '{specific_branch}' not found[/red]")
            return True

    console.print(f"[dim]Discovered {len(branches)} branches to audit...[/dim]")

    # Audit all branches (always full - checks all files)
    audit_results = []
    for branch in branches:
        console.print(f"[dim]Auditing {branch['name']}...[/dim]", end="\r")

        # Load bypass rules for this branch
        branch_path = Path(branch['path'])
        bypass_rules = load_bypass_rules(str(branch_path))

        result = audit_branch(branch, bypass_rules)
        audit_results.append(result)

    console.print(" " * 50, end="\r")  # Clear progress line

    # Calculate system-wide averages for each standard
    standard_scores = defaultdict(list)
    for result in audit_results:
        for standard, score in result['scores'].items():
            standard_scores[standard].append(score)

    system_averages = {
        standard: int(sum(scores) / len(scores))
        for standard, scores in standard_scores.items()
    }

    overall_system_avg = int(sum(r['average'] for r in audit_results) / len(audit_results)) if audit_results else 0

    # Print results with system averages
    for result in audit_results:
        print_branch_summary(result, system_averages, overall_system_avg)

    # Print system summary (unless specific branch)
    if not specific_branch:
        print_system_summary(audit_results)

    # Log completion
    json_handler.log_operation(
        "standards_audit_completed",
        {
            "branches_audited": len(audit_results),
            "average_compliance": int(sum(r['average'] for r in audit_results) / len(audit_results)) if audit_results else 0
        }
    )

    return True


def print_help():
    """Print help information"""
    console.print()
    console.print("[bold cyan]Standards Audit Module[/bold cyan]")
    console.print("Branch-wide Standards Audit - Check compliance across all branches")
    console.print()

    console.print("[yellow]COMMANDS:[/yellow]")
    console.print("  Commands: audit, --help")
    console.print()
    console.print("  [cyan]audit[/cyan]                    - Full audit of all branches")
    console.print("  [cyan]audit [branch][/cyan]           - Full audit of specific branch")
    console.print("  [cyan]audit --show-bypasses[/cyan]    - Show all bypassed files and their current state")
    console.print("  [cyan]audit [branch] -b[/cyan]        - Show bypasses for specific branch")
    console.print()

    console.print("[yellow]USAGE:[/yellow]")
    console.print("  [dim]# Via drone[/dim]")
    console.print("  drone @seed audit")
    console.print("  drone @seed audit cortex")
    console.print()
    console.print("  python3 seed.py audit")
    console.print("  python3 seed.py audit cortex")
    console.print("  python3 seed.py audit --help")
    console.print()

    console.print("[yellow]EXAMPLES:[/yellow]")
    console.print("  [dim]# Full system audit (all branches, all files)[/dim]")
    console.print("  python3 seed.py audit")
    console.print()
    console.print("  [dim]# Full audit of specific branch[/dim]")
    console.print("  python3 seed.py audit cortex")
    console.print()

    console.print("[yellow]REFERENCE:[/yellow]")
    console.print("  Scans all AIPass branches and generates compliance dashboard.")
    console.print("  Shows per-branch scores, system-wide metrics, and top issues.")
    console.print()


if __name__ == "__main__":
    # Handle help flag
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        print_help()
        sys.exit(0)

    # Confirm Prax logger connection
    logger.info("Prax logger connected to standards_audit")

    # Log standalone execution
    json_handler.log_operation(
        "audit_run",
        {"command": "standalone", "args": sys.argv[1:]}
    )

    # Run audit
    handle_command("audit", sys.argv[1:])
