#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: runner.py - Branch Diagnostics Runner Handler
# Date: 2025-11-29
# Version: 0.1.0
# Category: seed/handlers/diagnostics
#
# CHANGELOG (Max 5 entries):
#   - v0.1.0 (2025-11-29): Initial implementation - run diagnostics on branches
#
# CODE STANDARDS:
#   - Handlers implement, modules orchestrate
# =============================================

"""
Branch Diagnostics Runner Handler

Runs diagnostics checks on individual branches.
"""

import sys
from pathlib import Path
from typing import Dict

# Infrastructure
AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))


def run_branch_diagnostics(branch: Dict) -> Dict:
    """
    Run diagnostics on a single branch

    Args:
        branch: Dict with 'name', 'path'

    Returns:
        Dict with diagnostics results
    """
    # Import diagnostics checker
    from seed.apps.handlers.standards.diagnostics_check import check_branch

    branch_name = branch.get('name', 'UNKNOWN')
    branch_path = branch.get('path', '')

    result = check_branch(branch_path)
    result['branch'] = branch_name
    result['path'] = branch_path

    return result
