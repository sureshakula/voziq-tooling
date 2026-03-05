#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: help_check.py - Help Consistency Checker Handler
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
Help Consistency Checker Handler

Checks that seed.py help text doesn't mention removed flags.
Validates help documentation accuracy.
"""

import sys
from pathlib import Path
from typing import Dict

# Infrastructure
AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))

# Business logic imports
from seed.apps.handlers.file import file_handler
from seed.apps.handlers.config import ignore_handler


def check_help_consistency() -> Dict:
    """
    Check that seed.py help text doesn't mention removed flags

    Returns:
        Dict with check results
    """
    seed_file = Path.home() / "seed" / "apps" / "seed.py"
    issues = []

    if not seed_file.exists():
        return {
            'name': 'Help Consistency',
            'passed': False,
            'issues': ["seed.py not found"],
            'score': 0
        }

    # Read seed.py and check for removed flags in help text
    try:
        content = file_handler.read_file(str(seed_file))
        if content is None:
            return {
                'name': 'Help Consistency',
                'passed': False,
                'issues': ["Could not read seed.py"],
                'score': 0
            }

        # Check for mentions of removed flags in help section
        removed_flags = list(ignore_handler.get_deprecated_patterns().keys())

        for flag in removed_flags:
            if flag in content:
                # Check if it's in a help/documentation context
                for line_num, line in enumerate(content.split('\n'), 1):
                    if flag in line:
                        # Skip comments that explain removal
                        if "removed" in line.lower() or "deprecated" in line.lower():
                            continue
                        # Flag found in non-comment context
                        issues.append(
                            f"Line {line_num}: mentions {flag} "
                            f"(removed in audit v0.4.0)"
                        )

    except Exception as e:
        issues.append(f"Error reading file: {e}")

    return {
        'name': 'Help Consistency',
        'passed': len(issues) == 0,
        'issues': issues,
        'checked': [f"Scanned seed.py for: {', '.join(removed_flags)}"],
        'score': 100 if len(issues) == 0 else 0
    }
