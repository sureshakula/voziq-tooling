#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: bypass_audit.py - Bypass Audit Handler
# Date: 2025-11-29
# Version: 1.0.0
# Category: seed/handlers/audit
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2025-11-29): Extracted from standards_audit.py module
#
# CODE STANDARDS:
#   - Implementation handler for bypass auditing
#   - Checks bypassed files without bypass rules
# =============================================

"""
Bypass Audit Handler

Audits all bypassed files to see their current state.
"""

import sys
from pathlib import Path
from typing import List, Dict

# =============================================================================
# INFRASTRUCTURE SETUP
# =============================================================================

AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))

# =============================================================================
# IMPORTS
# =============================================================================

from seed.apps.handlers.standards import imports_check
from seed.apps.handlers.standards import architecture_check
from seed.apps.handlers.standards import naming_check
from seed.apps.handlers.standards import cli_check
from seed.apps.handlers.standards import handlers_check
from seed.apps.handlers.standards import modules_check
from seed.apps.handlers.standards import documentation_check
from seed.apps.handlers.standards import json_structure_check
from seed.apps.handlers.standards import testing_check
from seed.apps.handlers.standards import error_handling_check
from seed.apps.handlers.standards import encapsulation_check


# =============================================================================
# PUBLIC API
# =============================================================================

def audit_bypasses(branches: List[Dict], bypass_rules_map: Dict[str, list]) -> List[Dict]:
    """
    Audit all bypassed files WITHOUT applying bypass rules.
    Shows actual current state of bypassed files.

    Args:
        branches: List of branch dicts
        bypass_rules_map: Dict mapping branch name to bypass rules

    Returns:
        List of bypass audit results
    """
    bypass_results = []

    for branch in branches:
        branch_path = Path(branch['path'])
        bypass_rules = bypass_rules_map.get(branch['name'], [])

        if not bypass_rules:
            continue

        for bypass in bypass_rules:
            file_rel = bypass.get('file', '')
            standard = bypass.get('standard', '')
            reason = bypass.get('reason', '')

            file_path = branch_path / file_rel
            if not file_path.exists():
                bypass_results.append({
                    'branch': branch['name'],
                    'file': file_rel,
                    'standard': standard,
                    'reason': reason,
                    'status': 'file_missing',
                    'current_score': None,
                    'would_pass': None
                })
                continue

            # Run the specific standard check WITHOUT bypass
            checker = None
            if standard == 'imports':
                checker = imports_check
            elif standard == 'architecture':
                checker = architecture_check
            elif standard == 'naming':
                checker = naming_check
            elif standard == 'cli':
                checker = cli_check
            elif standard == 'handlers':
                checker = handlers_check
            elif standard == 'modules':
                checker = modules_check
            elif standard == 'documentation':
                checker = documentation_check
            elif standard == 'json_structure':
                checker = json_structure_check
            elif standard == 'testing':
                checker = testing_check
            elif standard == 'error_handling':
                checker = error_handling_check
            elif standard == 'encapsulation':
                checker = encapsulation_check

            if checker:
                try:
                    # Run WITHOUT bypass rules
                    result = checker.check_module(str(file_path), bypass_rules=[])
                    current_score = result.get('score', 0)
                    would_pass = result.get('passed', False)

                    # Get specific violations
                    violations = []
                    for check in result.get('checks', []):
                        if not check.get('passed', False):
                            violations.append(check.get('message', 'Unknown'))

                    bypass_results.append({
                        'branch': branch['name'],
                        'file': file_rel,
                        'standard': standard,
                        'reason': reason,
                        'status': 'checked',
                        'current_score': current_score,
                        'would_pass': would_pass,
                        'violations': violations
                    })
                except Exception as e:
                    bypass_results.append({
                        'branch': branch['name'],
                        'file': file_rel,
                        'standard': standard,
                        'reason': reason,
                        'status': 'error',
                        'error': str(e)
                    })
            else:
                bypass_results.append({
                    'branch': branch['name'],
                    'file': file_rel,
                    'standard': standard,
                    'reason': reason,
                    'status': 'unknown_standard'
                })

    return bypass_results
