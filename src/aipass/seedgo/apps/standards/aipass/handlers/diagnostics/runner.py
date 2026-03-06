"""
Branch Diagnostics Runner Handler

Runs diagnostics checks on individual branches.
"""

import sys
from pathlib import Path
from typing import Dict

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
