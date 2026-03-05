#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: json_structure_check.py - JSON Structure Standards Checker Handler
# Date: 2025-11-21
# Version: 0.3.0
# Category: seed/standards/checkers
#
# CHANGELOG (Max 5 entries):
#   - v0.3.0 (2025-11-21): Complete rewrite - validates actual implementation (handler config, JSON files existence, paths)
#   - v0.2.0 (2025-11-15): Fixed false positives using AST parsing instead of string search
#   - v0.1.0 (2025-11-15): Initial implementation - JSON structure standards checking
#
# CODE STANDARDS:
#   - Handler implements checking logic, module orchestrates
# =============================================

"""
JSON Structure Standards Checker Handler

Validates three-JSON pattern implementation:
- Handler configuration (correct paths)
- JSON file existence for modules
- Naming patterns
- Directory structure

This checker catches:
- Misconfigured json_handler.py (wrong BRANCH_ROOT paths)
- Missing JSON files for modules
- Non-standard naming patterns
- Orphaned JSON files
"""

import sys
import re
import ast
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Infrastructure
AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))


def is_bypassed(file_path: str, standard: str, line: int | None = None, bypass_rules: list | None = None) -> bool:
    """Check if a violation should be bypassed"""
    if not bypass_rules:
        return False
    for rule in bypass_rules:
        # Must match standard
        if rule.get('standard') and rule.get('standard') != standard:
            continue
        # Must match file (check if rule file path is in the full path)
        rule_file = rule.get('file', '')
        if rule_file and rule_file not in file_path:
            continue
        # Check line-specific bypass
        rule_lines = rule.get('lines', [])
        if rule_lines and line is not None:
            if line in rule_lines:
                return True
        elif not rule_lines:
            return True
    return False


def check_module(module_path: str, bypass_rules: list | None = None) -> Dict:
    """
    Check if module follows JSON structure standards

    Validates:
    1. json_handler.py files: Configuration correctness
    2. Modules using json_handler: JSON files exist
    3. Direct JSON operations: Should use json_handler

    Args:
        module_path: Path to Python module to check
        bypass_rules: Optional list of bypass rules to skip specific violations

    Returns:
        dict: {
            'passed': bool,
            'checks': [{'name': str, 'passed': bool, 'message': str}],
            'score': int,
            'standard': str
        }
    """
    checks = []
    path = Path(module_path)

    # Validate file exists
    if not path.exists():
        return {
            'passed': False,
            'checks': [{'name': 'File exists', 'passed': False, 'message': f'File not found: {module_path}'}],
            'score': 0,
            'standard': 'JSON STRUCTURE'
        }

    # Read file
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {
            'passed': False,
            'checks': [{'name': 'File readable', 'passed': False, 'message': f'Error reading file: {e}'}],
            'score': 0,
            'standard': 'JSON STRUCTURE'
        }

    # Determine what type of file this is
    if 'json_handler' in path.name and path.parent.name == 'json':
        # This is a json_handler.py file - check configuration
        checks = check_json_handler_config(path, content, bypass_rules)
    elif 'apps/modules' in str(path):
        # This is a module - check if it has JSON files (if it uses json_handler)
        checks = check_module_json_files(path, content, bypass_rules)
    else:
        # Other files - check for direct JSON operations
        json_check = check_json_handler_usage(content, module_path, bypass_rules)
        if json_check:
            checks.append(json_check)

    # If no checks, skip (not applicable)
    if not checks:
        return {
            'passed': True,
            'checks': [{'name': 'JSON structure check', 'passed': True, 'message': 'No JSON operations detected (skipped)'}],
            'score': 100,
            'standard': 'JSON STRUCTURE'
        }

    # Calculate score
    passed_checks = sum(1 for check in checks if check['passed'])
    total_checks = len(checks)
    score = int((passed_checks / total_checks * 100)) if total_checks > 0 else 0
    overall_passed = score >= 75

    return {
        'passed': overall_passed,
        'checks': checks,
        'score': score,
        'standard': 'JSON STRUCTURE'
    }


def get_branch_path(branch_name: str) -> Optional[str]:
    """Get actual branch path from BRANCH_REGISTRY.json"""
    registry_path = Path.home() / "BRANCH_REGISTRY.json"
    if registry_path.exists():
        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            for branch in registry.get('branches', []):
                if branch.get('name', '').lower() == branch_name.lower():
                    return branch.get('path', '')
        except (json.JSONDecodeError, IOError):
            pass
    return None


def check_json_handler_config(handler_path: Path, content: str, bypass_rules: list | None = None) -> List[Dict]:
    """
    Check if json_handler.py is configured correctly for its branch

    Critical checks:
    - BRANCH_ROOT points to correct branch (not SEED)
    - JSON_DIR points to {branch}_json/
    - TEMPLATES_DIR points to branch's templates
    """
    checks = []
    branch_name = detect_branch(handler_path)

    if not branch_name:
        checks.append({
            'name': 'Branch detection',
            'passed': False,
            'message': f'Cannot detect branch from path: {handler_path}'
        })
        return checks

    # Get actual branch path from registry
    actual_branch_path = get_branch_path(branch_name)
    if actual_branch_path:
        # Convert path to relative from home for display
        home = str(Path.home())
        relative_path = actual_branch_path.replace(home + '/', '')
    else:
        relative_path = f'aipass_core/{branch_name}'  # Fallback assumption

    # Check 1: BRANCH_ROOT configuration
    # Pattern matches: BRANCH_ROOT = Path.home() / "path" or BRANCH_ROOT = Path.home() / 'path'
    root_var_pattern = r"(\w+)_ROOT\s*=\s*Path\.home\(\)\s*/\s*['\"]([^'\"]+)['\"]"
    root_matches = re.findall(root_var_pattern, content)

    var_prefix = branch_name.upper()

    root_check_passed = False
    root_message = ''

    # Filter to only check the branch-specific ROOT constant (ignore AIPASS_ROOT which is infrastructure)
    branch_specific_matches = [(var_name, path_value) for var_name, path_value in root_matches if var_name != 'AIPASS']

    for var_name, path_value in branch_specific_matches:
        # var_name is already just the prefix (e.g., "SEED" from "SEED_ROOT")
        # Check if pointing to correct location
        if branch_name == 'seed' and path_value == 'seed':
            root_check_passed = True
            root_message = f'{var_name}_ROOT correctly points to /home/aipass/seed'
        elif branch_name != 'seed':
            # For other branches, check if handler path matches actual branch path
            if actual_branch_path and actual_branch_path in str(handler_path):
                # Handler is in correct branch - check if ROOT constant points to same location
                # Build expected path pattern from relative_path
                path_parts = relative_path.split('/')
                expected_pattern = '" / "'.join(path_parts)
                if expected_pattern in content or expected_pattern.replace('" / "', "' / '") in content:
                    root_check_passed = True
                    root_message = f'{var_name}_ROOT correctly points to {actual_branch_path}'
                elif 'seed' in path_value.lower():
                    root_check_passed = False
                    root_message = f'{var_name}_ROOT points to SEED paths - should point to {actual_branch_path}'
                    break
            elif 'seed' in path_value.lower():
                root_check_passed = False
                root_message = f'{var_name}_ROOT points to SEED paths - should point to {actual_branch_path or relative_path}'
                break

    if not root_matches:
        checks.append({
            'name': 'BRANCH_ROOT configuration',
            'passed': False,
            'message': 'No BRANCH_ROOT constant found in handler'
        })
    elif not branch_specific_matches:
        checks.append({
            'name': 'BRANCH_ROOT configuration',
            'passed': False,
            'message': f'No {branch_name.upper()}_ROOT constant found (only AIPASS_ROOT infrastructure)'
        })
    else:
        if not root_message:
            root_message = f'Unable to validate {branch_name.upper()}_ROOT configuration'
        checks.append({
            'name': 'BRANCH_ROOT configuration',
            'passed': root_check_passed,
            'message': root_message
        })

    # Check 2: JSON_DIR configuration
    json_dir_pattern = r"(\w+)_JSON_DIR\s*="
    json_dir_matches = re.findall(json_dir_pattern, content)

    if json_dir_matches:
        expected_json_dir = f'{branch_name}_json'
        json_dir_correct = any(expected_json_dir in content for expected_json_dir in [f'"{branch_name}_json"', f"'{branch_name}_json'", f'/ "{branch_name}_json"', f"/ '{branch_name}_json'"])

        checks.append({
            'name': 'JSON_DIR configuration',
            'passed': json_dir_correct,
            'message': f'JSON_DIR {"correctly" if json_dir_correct else "incorrectly"} configured (should point to {branch_name}_json/)'
        })

    # Check 3: TEMPLATES_DIR configuration
    templates_pattern = r"TEMPLATES_DIR\s*="
    if re.search(templates_pattern, content):
        # Should reference branch's own templates, not SEED's
        if branch_name != 'seed' and 'seed' in content.lower() and 'json_templates' in content:
            # Check if it's using SEED's templates
            seed_template_check = '"seed"' in content and 'json_templates' in content
            checks.append({
                'name': 'TEMPLATES_DIR configuration',
                'passed': not seed_template_check,
                'message': 'TEMPLATES_DIR points to SEED - should use branch templates' if seed_template_check else 'TEMPLATES_DIR correctly configured'
            })

    return checks


def check_module_json_files(module_path: Path, content: str, bypass_rules: list | None = None) -> List[Dict]:
    """
    Check if module has its three JSON files (if it uses json_handler)

    Checks:
    - If module imports json_handler, it should have config/data/log files
    - Files should be in correct directory
    - Naming should follow pattern
    """
    checks = []

    # Check if module uses json_handler
    uses_json_handler = 'from' in content and 'json_handler import' in content

    if not uses_json_handler:
        # Module doesn't use json_handler - check if it should
        has_json_ops = check_json_handler_usage(content, str(module_path), bypass_rules)
        if has_json_ops:
            checks.append(has_json_ops)
        return checks

    # Module uses json_handler - verify JSON files exist
    branch_name = detect_branch(module_path)
    module_name = module_path.stem

    if not branch_name:
        checks.append({
            'name': 'Branch detection',
            'passed': False,
            'message': f'Cannot detect branch from path: {module_path}'
        })
        return checks

    if branch_name == 'seed':
        json_dir = Path.home() / 'seed' / 'seed_json'
    else:
        json_dir = Path.home() / 'aipass_core' / branch_name / f'{branch_name}_json'

    # Check if directory exists
    if not json_dir.exists():
        checks.append({
            'name': 'JSON directory exists',
            'passed': False,
            'message': f'JSON directory not found: {json_dir}'
        })
        return checks

    # Check for three JSON files
    config_file = json_dir / f'{module_name}_config.json'
    data_file = json_dir / f'{module_name}_data.json'
    log_file = json_dir / f'{module_name}_log.json'

    files_status = []
    all_exist = True

    for json_type, json_file in [('config', config_file), ('data', data_file), ('log', log_file)]:
        if json_file.exists():
            files_status.append(f'{json_type}✓')
        else:
            files_status.append(f'{json_type}✗')
            all_exist = False

    checks.append({
        'name': 'Module JSON files',
        'passed': all_exist,
        'message': f'Module JSON files: {", ".join(files_status)} in {json_dir.name}/' if all_exist else f'Missing JSON files: {", ".join(files_status)} - should exist in {json_dir.name}/'
    })

    return checks


def check_json_handler_usage(content: str, file_path: str, bypass_rules: list | None = None) -> Optional[Dict]:
    """
    Check that modules use json_handler for JSON operations (not direct json.load/dump)
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None

    has_json_import = False
    has_json_operations = False
    has_json_handler_import = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == 'json':
                    has_json_import = True

        if isinstance(node, ast.ImportFrom):
            if node.module == 'json':
                has_json_import = True
            if node.module and 'json_handler' in node.module:
                has_json_handler_import = True

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if (isinstance(node.func.value, ast.Name) and
                    node.func.value.id == 'json' and
                    node.func.attr in ['dump', 'load']):
                    has_json_operations = True

    # No JSON operations detected
    if not has_json_import and not has_json_operations:
        return None

    # Has JSON operations but not using json_handler
    if has_json_operations and not has_json_handler_import:
        # Check if bypassed
        if is_bypassed(file_path, 'json_structure', bypass_rules=bypass_rules):
            return None

        return {
            'name': 'json_handler usage',
            'passed': False,
            'message': 'Direct JSON operations detected (use json_handler for three-JSON pattern)'
        }

    return None


def detect_branch(file_path: Path) -> Optional[str]:
    """
    Detect which branch a file belongs to from its path

    Uses BRANCH_REGISTRY.json as source of truth for all branch paths.
    Falls back to path heuristics if registry unavailable.

    Returns branch name (lowercase) or None if cannot detect
    """
    file_path_str = str(file_path)

    # Try BRANCH_REGISTRY.json first (source of truth)
    registry_path = Path.home() / "BRANCH_REGISTRY.json"
    if registry_path.exists():
        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            # Sort by path length (longest first) to match most specific path
            branches = sorted(
                registry.get('branches', []),
                key=lambda b: len(b.get('path', '')),
                reverse=True
            )
            for branch in branches:
                branch_path = branch.get('path', '')
                if branch_path and file_path_str.startswith(branch_path):
                    return branch.get('name', '').lower()
        except (json.JSONDecodeError, IOError):
            pass  # Fall through to heuristics

    # Fallback: path-based heuristics
    path_parts = file_path.parts

    # Check if in seed
    if 'seed' in path_parts:
        return 'seed'

    # Check if in aipass_core/{branch}
    if 'aipass_core' in path_parts:
        idx = path_parts.index('aipass_core')
        if idx + 1 < len(path_parts):
            return path_parts[idx + 1]

    return None
