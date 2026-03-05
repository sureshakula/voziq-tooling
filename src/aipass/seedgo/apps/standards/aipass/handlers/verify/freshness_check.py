#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: freshness_check.py - File Freshness Checker Handler
# Date: 2025-11-29
# Version: 0.1.0
# Category: seed/verify/handlers
#
# CHANGELOG (Max 5 entries):
#   - v0.1.0 (2025-11-29): Initial implementation - extracted from standards_verify module
#
# CODE STANDARDS:
#   - Handler implements checking logic, module orchestrates
#   - NO Prax logger in handlers (handlers don't log)
# =============================================

"""
File Freshness Checker Handler

Checks if documentation is up-to-date with recent code changes.
Validates modification times of key files.
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict


def check_file_freshness() -> Dict:
    """
    Check if documentation is up-to-date with recent code changes

    Returns:
        Dict with check results
    """
    seed_path = Path.home() / "seed"
    issues = []

    # Check if standards_audit.py exists
    audit_file = seed_path / "apps" / "modules" / "standards_audit.py"
    readme_file = seed_path / "README.md"
    local_json = seed_path / "SEED.local.json"

    if not audit_file.exists():
        issues.append("standards_audit.py not found")
        return {
            'name': 'File Freshness',
            'passed': False,
            'issues': issues,
            'score': 0
        }

    audit_mtime = datetime.fromtimestamp(audit_file.stat().st_mtime)

    # Check README.md freshness
    if readme_file.exists():
        readme_mtime = datetime.fromtimestamp(readme_file.stat().st_mtime)

        # If audit was modified today and README is more than 1 day old
        if audit_mtime.date() == datetime.now().date():
            if (datetime.now() - readme_mtime) > timedelta(days=1):
                issues.append(
                    f"README.md ({readme_mtime.date()}) may be outdated - "
                    f"standards_audit.py modified today"
                )
    else:
        issues.append("README.md not found")

    # Check if SEED.local.json was updated today
    if local_json.exists():
        local_mtime = datetime.fromtimestamp(local_json.stat().st_mtime)
        if local_mtime.date() != datetime.now().date():
            issues.append(
                f"SEED.local.json last updated {local_mtime.date()} "
                f"(not today)"
            )
    else:
        issues.append("SEED.local.json not found")

    return {
        'name': 'File Freshness',
        'passed': len(issues) == 0,
        'issues': issues,
        'checked': [
            f"SEED.local.json updated: {local_mtime.date()}" if local_json.exists() else "SEED.local.json: not found",
            f"README.md updated: {readme_mtime.date()}" if readme_file.exists() else "README.md: not found"
        ],
        'score': 100 if len(issues) == 0 else max(0, 100 - (len(issues) * 30))
    }
