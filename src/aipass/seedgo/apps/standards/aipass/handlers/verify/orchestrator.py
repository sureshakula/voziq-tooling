#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: orchestrator.py - Verification Orchestrator Handler
# Date: 2025-11-29
# Version: 0.1.0
# Category: seed/handlers/verify
#
# CHANGELOG (Max 5 entries):
#   - v0.1.0 (2025-11-29): Initial - orchestrates verification checks
#
# CODE STANDARDS:
#   - Pure handler - orchestrates check handlers
#   - Returns data dict, display handled separately
# =============================================

"""
Verification Orchestrator Handler

Runs all verification checks and formats display output.
Called by standards_verify module.
"""

import sys
from pathlib import Path
from typing import Dict

# =============================================================================
# INFRASTRUCTURE SETUP
# =============================================================================

AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))

# CLI services for display
from cli.apps.modules import console, header

# Check handlers
from seed.apps.handlers.verify.stale_check import check_stale_patterns
from seed.apps.handlers.verify.freshness_check import check_file_freshness
from seed.apps.handlers.verify.help_check import check_help_consistency
from seed.apps.handlers.verify.command_check import check_command_consistency
from seed.apps.handlers.verify.checker_sync import check_checker_sync


def run_verification() -> Dict:
    """
    Run all verification checks and display results

    Returns:
        Dict with all check results
    """
    console.print()
    header("SEED SYNC VERIFICATION")
    console.print()

    checks = [
        check_stale_patterns(),
        check_file_freshness(),
        check_help_consistency(),
        check_command_consistency(),
        check_checker_sync()
    ]

    # Print results
    console.print("[bold cyan]Running verification checks...[/bold cyan]")
    console.print()

    passed_count = 0
    total_count = len(checks)

    for check in checks:
        check_passed = check.get('passed', False)
        check_name = check.get('name', 'Unknown')

        if check_passed:
            console.print(f"[green]✓[/green] {check_name}")
            passed_count += 1
            # Show what was verified (even on pass)
            details = check.get('checked', [])
            for detail in details:
                console.print(f"  [dim]→ {detail}[/dim]")
        else:
            console.print(f"[red]✗[/red] {check_name}")

            # Show violations if present
            violations = check.get('violations', [])
            for violation in violations:
                pattern = violation.get('pattern', '')
                reason = violation.get('reason', '')
                location = violation.get('location', '')
                console.print(f"  [yellow]→[/yellow] {location}")
                console.print(f"    [dim]Pattern: {pattern} ({reason})[/dim]")

            # Show issues if present
            issues = check.get('issues', [])
            for issue in issues:
                console.print(f"  [yellow]→[/yellow] {issue}")

            # Show missing documentation (command consistency check)
            missing = check.get('missing', {})
            for flag, info in missing.items():
                desc = info.get('description', '')
                locations = info.get('missing_from', [])
                console.print(f"  [yellow]→[/yellow] {flag} ({desc})")
                console.print(f"    [dim]Missing from: {', '.join(locations)}[/dim]")

    console.print()
    console.print("─" * 70)
    console.print()

    # Summary
    score = int((passed_count / total_count) * 100) if total_count > 0 else 0

    if score == 100:
        console.print(f"[bold green]SUMMARY: {passed_count}/{total_count} checks passed ✓[/bold green]")
    else:
        console.print(f"[bold yellow]SUMMARY: {passed_count}/{total_count} checks passed[/bold yellow]")

    console.print()

    return {
        'checks': checks,
        'passed': passed_count,
        'total': total_count,
        'score': score
    }
