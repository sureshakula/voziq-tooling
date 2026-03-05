#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: branch_audit.py - Branch Audit Handler
# Date: 2025-11-29
# Version: 1.0.0
# Category: seed/handlers/audit
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2025-11-29): Extracted from standards_audit.py module
#
# CODE STANDARDS:
#   - Implementation handler for branch auditing
#   - Runs all standard checkers on branch files
# =============================================

"""
Branch Audit Handler

Audits a single branch for standards compliance.
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
from seed.apps.handlers.standards import trigger_check
from seed.apps.handlers.standards import log_level_check
from seed.apps.handlers.standards import cli_flags_check
from seed.apps.handlers.standards import log_handler_check
from seed.apps.handlers.standards import log_visibility_check
from seed.apps.handlers.standards import permission_flags_check
from seed.apps.handlers.standards import readme_check
from seed.apps.handlers.standards import diagnostics_check
from seed.apps.handlers.config import ignore_handler


# =============================================================================
# PUBLIC API
# =============================================================================

def audit_branch(branch: Dict[str, str], bypass_rules: list) -> Dict:
    """
    Audit a branch - checks ALL Python files (audit = comprehensive by definition)

    Args:
        branch: Dict with 'name', 'path', 'entry_file'
        bypass_rules: List of bypass rules for this branch

    Returns:
        Dict with audit results and scores
    """
    file_path = branch['entry_file']
    branch_path = Path(branch['path'])

    # Audit checks ALL Python files in apps/ (not just entry point)
    all_file_results = []
    apps_dir = branch_path / 'apps'

    # Get ignore patterns from handler - don't audit archived/backup/artifact files
    audit_ignore_patterns = ignore_handler.get_audit_ignore_patterns()

    if apps_dir.exists():
        for py_file in apps_dir.rglob('*.py'):
            # Skip __init__.py
            if py_file.name == '__init__.py':
                continue
            # Skip files in ignored directories
            file_path_str = str(py_file).lower()
            if any(pattern in file_path_str for pattern in audit_ignore_patterns):
                continue
            all_file_results.append({
                'file': str(py_file),
                'name': py_file.name
            })

    # Run all checkers
    checkers = {
        'imports': imports_check,
        'architecture': architecture_check,
        'naming': naming_check,
        'cli': cli_check,
        'handlers': handlers_check,
        'modules': modules_check,
        'documentation': documentation_check,
        'json_structure': json_structure_check,
        'testing': testing_check,
        'error_handling': error_handling_check,
        'encapsulation': encapsulation_check,
        'trigger': trigger_check,
        'log_level': log_level_check,
        'cli_flags': cli_flags_check,
        'log_handler': log_handler_check,
        'log_visibility': log_visibility_check,
        'permission_flags': permission_flags_check,
        'readme': readme_check
    }

    results = {}
    scores = {}

    for name, checker in checkers.items():
        try:
            result = checker.check_module(file_path, bypass_rules=bypass_rules)
            results[name] = result
            scores[name] = result.get('score', 0)
        except Exception as e:
            results[name] = {
                'passed': False,
                'score': 0,
                'error': str(e)
            }
            scores[name] = 0

    # Calculate average score
    avg_score = int(sum(scores.values()) / len(scores)) if scores else 0

    # Check CLI standard on ALL files (audit = comprehensive)
    cli_violations = []
    cli_scores = []
    if all_file_results:
        for file_info in all_file_results:
            try:
                cli_result = cli_check.check_module(file_info['file'], bypass_rules=bypass_rules)
                cli_scores.append(cli_result.get('score', 0))
                if not cli_result.get('passed', True):
                    # Found a violation
                    failed_checks = [c for c in cli_result.get('checks', []) if not c.get('passed', False)]
                    cli_violations.append({
                        'file': file_info['name'],
                        'path': file_info['file'],
                        'score': cli_result.get('score', 0),
                        'issues': [c.get('message', 'Unknown') for c in failed_checks]
                    })
            except Exception:
                pass

    # Update CLI score to reflect ALL files, not just entry point
    if cli_scores:
        scores['cli'] = int(sum(cli_scores) / len(cli_scores))
        # Recalculate average with updated CLI score
        avg_score = int(sum(scores.values()) / len(scores)) if scores else 0

    # Check MODULES standard on ALL files in apps/modules/ (thin orchestration + business logic)
    modules_violations = []
    modules_scores = []
    modules_dir = Path(branch['path']) / 'apps' / 'modules'
    if modules_dir.exists():
        for py_file in modules_dir.glob('*.py'):
            if py_file.name == '__init__.py':
                continue
            try:
                modules_result = modules_check.check_module(str(py_file), bypass_rules=bypass_rules)
                modules_scores.append(modules_result.get('score', 0))
                # Check for thin orchestration AND business logic violations
                for check in modules_result.get('checks', []):
                    # Capture thin orchestration violations
                    if check['name'] == 'Thin orchestration' and not check['passed']:
                        modules_violations.append({
                            'file': py_file.name,
                            'path': str(py_file),
                            'score': modules_result.get('score', 0),
                            'message': check.get('message', 'Unknown')
                        })
                    # Capture business logic violations
                    elif check['name'] == 'No business logic' and not check['passed']:
                        modules_violations.append({
                            'file': py_file.name,
                            'path': str(py_file),
                            'score': modules_result.get('score', 0),
                            'message': check.get('message', 'Unknown')
                        })
            except Exception:
                pass

    # Update modules score to reflect ALL module files
    if modules_scores:
        scores['modules'] = int(sum(modules_scores) / len(modules_scores))
        # Recalculate average with updated modules score
        avg_score = int(sum(scores.values()) / len(scores)) if scores else 0

    # Check ENCAPSULATION on ALL files (cross-branch/package handler imports)
    encapsulation_violations = []
    encapsulation_scores = []
    if all_file_results:
        for file_info in all_file_results:
            try:
                encap_result = encapsulation_check.check_module(file_info['file'], bypass_rules=bypass_rules)
                encapsulation_scores.append(encap_result.get('score', 0))
                if not encap_result.get('passed', True):
                    failed_checks = [c for c in encap_result.get('checks', []) if not c.get('passed', False)]
                    encapsulation_violations.append({
                        'file': file_info['name'],
                        'path': file_info['file'],
                        'score': encap_result.get('score', 0),
                        'issues': [c.get('message', 'Unknown') for c in failed_checks]
                    })
            except Exception:
                pass

    # Update encapsulation score to reflect ALL files
    if encapsulation_scores:
        scores['encapsulation'] = int(sum(encapsulation_scores) / len(encapsulation_scores))
        avg_score = int(sum(scores.values()) / len(scores)) if scores else 0

    # Check ERROR_HANDLING on ALL files (3-tier: entry/modules/handlers)
    error_handling_violations = []
    error_handling_scores = []
    if all_file_results:
        for file_info in all_file_results:
            try:
                eh_result = error_handling_check.check_module(file_info['file'], bypass_rules=bypass_rules)
                eh_score = eh_result.get('score', 0)
                # Only count if checks were actually run (not skipped entry points)
                if eh_result.get('checks', []):
                    error_handling_scores.append(eh_score)
                if not eh_result.get('passed', True):
                    failed_checks = [c for c in eh_result.get('checks', []) if not c.get('passed', False)]
                    if failed_checks:  # Only add if there are actual failures
                        error_handling_violations.append({
                            'file': file_info['name'],
                            'path': file_info['file'],
                            'score': eh_score,
                            'issues': [c.get('message', 'Unknown') for c in failed_checks]
                        })
            except Exception:
                pass

    # Update error_handling score to reflect ALL files
    if error_handling_scores:
        scores['error_handling'] = int(sum(error_handling_scores) / len(error_handling_scores))
        avg_score = int(sum(scores.values()) / len(scores)) if scores else 0

    # Check TRIGGER on ALL files (event bus patterns)
    trigger_violations = []
    trigger_scores = []
    if all_file_results:
        for file_info in all_file_results:
            try:
                trig_result = trigger_check.check_module(file_info['file'], bypass_rules=bypass_rules)
                trig_score = trig_result.get('score', 0)
                if trig_result.get('checks', []):
                    trigger_scores.append(trig_score)
                if not trig_result.get('passed', True):
                    failed_checks = [c for c in trig_result.get('checks', []) if not c.get('passed', False)]
                    if failed_checks:
                        trigger_violations.append({
                            'file': file_info['name'],
                            'path': file_info['file'],
                            'score': trig_score,
                            'issues': [c.get('message', 'Unknown') for c in failed_checks]
                        })
            except Exception:
                pass

    # Update trigger score to reflect ALL files
    if trigger_scores:
        scores['trigger'] = int(sum(trigger_scores) / len(trigger_scores))
        avg_score = int(sum(scores.values()) / len(scores)) if scores else 0

    # Check LOG_LEVEL on ALL files (ERROR vs WARNING hygiene)
    log_level_violations = []
    log_level_scores = []
    if all_file_results:
        for file_info in all_file_results:
            try:
                ll_result = log_level_check.check_module(file_info['file'], bypass_rules=bypass_rules)
                ll_score = ll_result.get('score', 0)
                if ll_result.get('checks', []):
                    log_level_scores.append(ll_score)
                if not ll_result.get('passed', True):
                    failed_checks = [c for c in ll_result.get('checks', []) if not c.get('passed', False)]
                    if failed_checks:
                        log_level_violations.append({
                            'file': file_info['name'],
                            'path': file_info['file'],
                            'score': ll_score,
                            'issues': [c.get('message', 'Unknown') for c in failed_checks]
                        })
            except Exception:
                pass

    # Update log_level score to reflect ALL files
    if log_level_scores:
        scores['log_level'] = int(sum(log_level_scores) / len(log_level_scores))
        avg_score = int(sum(scores.values()) / len(scores)) if scores else 0

    # Check JSON_STRUCTURE on json_handler.py files (for misconfiguration)
    # Note: Only check json_handler.py files, not all handlers - handlers legitimately
    # read JSON files directly for config/registry purposes. The three-JSON pattern
    # (json_handler) is for module state persistence, not all JSON operations.
    json_structure_violations = []
    json_structure_scores = []
    if all_file_results:
        for file_info in all_file_results:
            file_path = file_info['file']
            # Only check json_handler.py files for configuration issues
            if 'json_handler' not in file_info['name']:
                continue
            try:
                json_result = json_structure_check.check_module(file_path, bypass_rules=bypass_rules)
                json_score = json_result.get('score', 0)
                checks = json_result.get('checks', [])
                if checks and not any('skipped' in c.get('message', '').lower() for c in checks):
                    json_structure_scores.append(json_score)
                if not json_result.get('passed', True):
                    failed_checks = [c for c in checks if not c.get('passed', False)]
                    if failed_checks:
                        json_structure_violations.append({
                            'file': file_info['name'],
                            'path': file_path,
                            'score': json_score,
                            'issues': [c.get('message', 'Unknown') for c in failed_checks]
                        })
            except Exception:
                pass

    # Update json_structure score if we found json_handler files
    if json_structure_scores:
        scores['json_structure'] = int(sum(json_structure_scores) / len(json_structure_scores))
        avg_score = int(sum(scores.values()) / len(scores)) if scores else 0

    # Check LOG_HANDLER on ALL files (RotatingFileHandler required)
    log_handler_violations = []
    log_handler_scores = []
    if all_file_results:
        for file_info in all_file_results:
            try:
                lh_result = log_handler_check.check_module(file_info['file'], bypass_rules=bypass_rules)
                lh_score = lh_result.get('score', 0)
                if lh_result.get('checks', []):
                    log_handler_scores.append(lh_score)
                if not lh_result.get('passed', True):
                    failed_checks = [c for c in lh_result.get('checks', []) if not c.get('passed', False)]
                    if failed_checks:
                        log_handler_violations.append({
                            'file': file_info['name'],
                            'path': file_info['file'],
                            'score': lh_score,
                            'issues': [c.get('message', 'Unknown') for c in failed_checks]
                        })
            except Exception:
                pass

    # Update log_handler score to reflect ALL files
    if log_handler_scores:
        scores['log_handler'] = int(sum(log_handler_scores) / len(log_handler_scores))
        avg_score = int(sum(scores.values()) / len(scores)) if scores else 0

    # Check LOG_VISIBILITY on ALL files (prax system_logger required)
    log_visibility_violations = []
    log_visibility_scores = []
    if all_file_results:
        for file_info in all_file_results:
            try:
                lv_result = log_visibility_check.check_module(file_info['file'], bypass_rules=bypass_rules)
                lv_score = lv_result.get('score', 0)
                if lv_result.get('checks', []):
                    log_visibility_scores.append(lv_score)
                if not lv_result.get('passed', True):
                    failed_checks = [c for c in lv_result.get('checks', []) if not c.get('passed', False)]
                    if failed_checks:
                        log_visibility_violations.append({
                            'file': file_info['name'],
                            'path': file_info['file'],
                            'score': lv_score,
                            'issues': [c.get('message', 'Unknown') for c in failed_checks]
                        })
            except Exception:
                pass

    # Update log_visibility score to reflect ALL files
    if log_visibility_scores:
        scores['log_visibility'] = int(sum(log_visibility_scores) / len(log_visibility_scores))
        avg_score = int(sum(scores.values()) / len(scores)) if scores else 0

    # Check PERMISSION_FLAGS on ALL files (no --skip-permissions)
    permission_flags_violations = []
    permission_flags_scores = []
    if all_file_results:
        for file_info in all_file_results:
            try:
                pf_result = permission_flags_check.check_module(file_info['file'], bypass_rules=bypass_rules)
                pf_score = pf_result.get('score', 0)
                if pf_result.get('checks', []):
                    permission_flags_scores.append(pf_score)
                if not pf_result.get('passed', True):
                    failed_checks = [c for c in pf_result.get('checks', []) if not c.get('passed', False)]
                    if failed_checks:
                        permission_flags_violations.append({
                            'file': file_info['name'],
                            'path': file_info['file'],
                            'score': pf_score,
                            'issues': [c.get('message', 'Unknown') for c in failed_checks]
                        })
            except Exception:
                pass

    # Update permission_flags score to reflect ALL files
    if permission_flags_scores:
        scores['permission_flags'] = int(sum(permission_flags_scores) / len(permission_flags_scores))
        avg_score = int(sum(scores.values()) / len(scores)) if scores else 0

    # Run TYPE ERROR diagnostics on the branch (pyright)
    diagnostics_result = diagnostics_check.check_branch(str(branch_path))
    type_errors = diagnostics_result.get('total_errors', 0)
    type_error_files = diagnostics_result.get('results', [])

    # Type check score: binary - 100% if 0 errors, 0% if any errors
    scores['type_check'] = 100 if type_errors == 0 else 0
    avg_score = int(sum(scores.values()) / len(scores)) if scores else 0

    # Check for deprecated DOCUMENTS/ directory (should be docs/)
    deprecated_patterns = []
    documents_dir = branch_path / 'DOCUMENTS'
    if documents_dir.exists() and documents_dir.is_dir():
        deprecated_patterns.append({
            'type': 'directory',
            'old': 'DOCUMENTS/',
            'new': 'docs/',
            'path': str(documents_dir),
            'message': 'Rename DOCUMENTS/ to docs/ (lowercase, no caps)'
        })

    return {
        'branch': branch,
        'results': results,
        'scores': scores,
        'average': avg_score,
        'cli_violations': cli_violations,
        'modules_violations': modules_violations,
        'encapsulation_violations': encapsulation_violations,
        'error_handling_violations': error_handling_violations,
        'trigger_violations': trigger_violations,
        'log_level_violations': log_level_violations,
        'log_handler_violations': log_handler_violations,
        'log_visibility_violations': log_visibility_violations,
        'permission_flags_violations': permission_flags_violations,
        'cli_flags_violations': [],
        'json_structure_violations': json_structure_violations,
        'deprecated_patterns': deprecated_patterns,
        'files_checked': len(all_file_results),
        'type_errors': type_errors,
        'type_error_files': type_error_files
    }
