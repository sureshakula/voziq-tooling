"""
Imports Standards Checker Handler

Validates module compliance with AIPass import standards.
Checks AIPASS_ROOT pattern, import order, Prax logger, sys.path setup.

Fixed bugs:
- Filters docstrings before checking imports (prevents false negatives from import examples)
- Only checks import section (not comments/docstrings)
- Detects handler-to-module import violations
- Makes Prax logger conditional (not required for small files)
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

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
    Check if module follows import standards

    Args:
        module_path: Path to Python module to check
        bypass_rules: Optional list of bypass rules to skip certain violations

    Returns:
        dict: {
            'passed': bool,           # Overall pass/fail
            'checks': [               # Individual check results
                {
                    'name': str,      # Check name
                    'passed': bool,   # Pass/fail
                    'message': str,   # Details (line number, etc.)
                }
            ],
            'score': int,             # 0-100 percentage
            'standard': str           # Standard name
        }
    """
    checks = []
    path = Path(module_path)

    # Check if entire standard is bypassed for this file
    if is_bypassed(module_path, 'imports', bypass_rules=bypass_rules):
        return {
            'passed': True,
            'checks': [{'name': 'Bypassed', 'passed': True, 'message': 'Standard bypassed via .seed/bypass.json'}],
            'score': 100,
            'standard': 'IMPORTS'
        }

    # Validate file exists
    if not path.exists():
        return {
            'passed': False,
            'checks': [{'name': 'File exists', 'passed': False, 'message': f'File not found: {module_path}'}],
            'score': 0,
            'standard': 'IMPORTS'
        }

    # Read file
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        return {
            'passed': False,
            'checks': [{'name': 'File readable', 'passed': False, 'message': f'Error reading file: {e}'}],
            'score': 0,
            'standard': 'IMPORTS'
        }

    # Filter out docstrings to prevent false positives from import examples
    filtered_lines = filter_docstrings(lines)

    # Find import section boundaries
    import_section_end = find_import_section_end(filtered_lines)
    import_lines = filtered_lines[:import_section_end]

    # Determine file type
    is_handler = '/handlers/' in module_path
    is_init_file = path.name == '__init__.py'
    is_small_file = len([l for l in lines if l.strip() and not l.strip().startswith('#')]) < 20

    # Check 1: AIPASS_ROOT pattern (required for modules, optional for handlers)
    if not is_init_file:
        aipass_root_check = check_aipass_root(import_lines, module_path, bypass_rules)
        checks.append(aipass_root_check)

    # Check 2: sys.path setup (required if AIPASS_ROOT exists)
    if not is_init_file:
        sys_path_check = check_sys_path(import_lines, module_path, bypass_rules)
        checks.append(sys_path_check)

    # Check 3: Prax logger import (conditional - not required for small files/__init__/handlers)
    # Handlers MUST NOT import Prax (error_handling standard) - skip this recommendation for them
    if not is_init_file and not is_small_file and not is_handler:
        prax_logger_check = check_prax_logger(import_lines, module_path, bypass_rules)
        # Make it informational for small files
        if prax_logger_check:
            checks.append(prax_logger_check)

    # Check 4: Handler independence (handlers must not import parent modules)
    if is_handler:
        handler_independence_check = check_handler_independence(import_lines, module_path, bypass_rules)
        if handler_independence_check:
            checks.append(handler_independence_check)

    # Check 5: Import order (only if file has imports)
    import_order_check = check_import_order(import_lines, module_path, bypass_rules)
    if import_order_check:
        checks.append(import_order_check)

    # Calculate score
    passed_checks = sum(1 for check in checks if check['passed'])
    total_checks = len(checks)
    score = int((passed_checks / total_checks * 100)) if total_checks > 0 else 0

    # Overall pass if score >= 75%
    overall_passed = score >= 75

    return {
        'passed': overall_passed,
        'checks': checks,
        'score': score,
        'standard': 'IMPORTS'
    }


def filter_docstrings(lines: List[str]) -> List[str]:
    """
    Filter out docstrings from lines to prevent false positives.

    This prevents import examples in module docstrings from being
    detected as actual imports.

    Returns:
        List of lines with docstrings removed
    """
    filtered_lines = []
    in_docstring = False
    docstring_marker = None

    for line in lines:
        stripped = line.strip()

        # Check for docstring start/end
        if '"""' in stripped or "'''" in stripped:
            # Determine which marker we're looking for
            if '"""' in stripped:
                marker = '"""'
            else:
                marker = "'''"

            # Count occurrences of the marker
            marker_count = stripped.count(marker)

            if not in_docstring:
                # Starting a docstring
                if marker_count == 2:
                    # Single-line docstring - skip this line entirely
                    continue
                elif marker_count == 1:
                    # Multi-line docstring starting
                    in_docstring = True
                    docstring_marker = marker
                    continue
            else:
                # Potentially ending a docstring
                if marker == docstring_marker and marker_count >= 1:
                    # Multi-line docstring ending
                    in_docstring = False
                    docstring_marker = None
                    continue

        # Skip lines inside docstrings
        if in_docstring:
            continue

        # Keep non-docstring lines
        filtered_lines.append(line)

    return filtered_lines


def find_import_section_end(lines: List[str]) -> int:
    """
    Find the line number where the import section ends (first def/class).

    This prevents false positives from matching patterns in docstrings,
    comments, or code examples.

    Returns:
        Line number where imports end (0-indexed)
    """
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Import section ends at first function or class definition
        if stripped.startswith('def ') or stripped.startswith('class ') or stripped.startswith('async def '):
            return i
    return len(lines)


def check_aipass_root(lines: List[str], file_path: str = "", bypass_rules: list | None = None) -> Dict:
    """
    Check for AIPASS_ROOT = Path.home() / "aipass_core" pattern

    Only checks actual code lines (not comments)
    """
    # Check if entire standard is bypassed
    if is_bypassed(file_path, 'imports', None, bypass_rules):
        return {
            'name': 'AIPASS_ROOT pattern',
            'passed': True,
            'message': 'Bypassed by bypass rules'
        }

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue

        # Look for AIPASS_ROOT assignment (actual code, not in string)
        if 'AIPASS_ROOT' in line and '=' in line and 'Path.home()' in line:
            # Verify it's not in a comment at end of line
            if '#' in line:
                code_part = line.split('#')[0]
                if 'AIPASS_ROOT' in code_part and 'Path.home()' in code_part:
                    return {
                        'name': 'AIPASS_ROOT pattern',
                        'passed': True,
                        'message': f'Found on line {i}'
                    }
            else:
                return {
                    'name': 'AIPASS_ROOT pattern',
                    'passed': True,
                    'message': f'Found on line {i}'
                }

    return {
        'name': 'AIPASS_ROOT pattern',
        'passed': False,
        'message': 'AIPASS_ROOT = Path.home() / "aipass_core" not found in import section'
    }


def check_sys_path(lines: List[str], file_path: str = "", bypass_rules: list | None = None) -> Dict:
    """
    Check for sys.path.insert(0, str(AIPASS_ROOT)) pattern

    Only checks actual code lines (not comments)
    """
    # Check if entire standard is bypassed
    if is_bypassed(file_path, 'imports', None, bypass_rules):
        return {
            'name': 'sys.path setup',
            'passed': True,
            'message': 'Bypassed by bypass rules'
        }

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue

        # Look for sys.path.insert with AIPASS_ROOT
        if 'sys.path.insert' in line and 'AIPASS_ROOT' in line:
            # Verify it's not in a comment
            if '#' in line:
                code_part = line.split('#')[0]
                if 'sys.path.insert' in code_part and 'AIPASS_ROOT' in code_part:
                    return {
                        'name': 'sys.path setup',
                        'passed': True,
                        'message': f'Found on line {i}'
                    }
            else:
                return {
                    'name': 'sys.path setup',
                    'passed': True,
                    'message': f'Found on line {i}'
                }

    return {
        'name': 'sys.path setup',
        'passed': False,
        'message': 'sys.path.insert(0, str(AIPASS_ROOT)) not found in import section'
    }


def check_prax_logger(lines: List[str], file_path: str = "", bypass_rules: list | None = None) -> Optional[Dict]:
    """
    Check for Prax logger import

    Note: "Nearly always" not "always" - conditional check
    """
    # Check if entire standard is bypassed
    if is_bypassed(file_path, 'imports', None, bypass_rules):
        return {
            'name': 'Prax logger import',
            'passed': True,
            'message': 'Bypassed by bypass rules'
        }

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue

        # Look for prax logger import
        if 'from prax.apps.modules.logger import' in line and 'system_logger' in line:
            return {
                'name': 'Prax logger import',
                'passed': True,
                'message': f'Found on line {i}'
            }

    # Return informational failure (not critical)
    return {
        'name': 'Prax logger import (recommended)',
        'passed': False,
        'message': 'Prax logger import not found (recommended: from prax.apps.modules.logger import system_logger)'
    }


def check_handler_independence(lines: List[str], module_path: str = "", bypass_rules: list | None = None) -> Optional[Dict]:
    """
    Check that handlers don't import from parent branch modules.

    Handlers must be independent and transportable.
    Forbidden: from <parent_branch>.apps.modules import ...
    Allowed: from prax.apps.modules.logger import ... (service imports)
    Allowed: from cli.apps.modules import ... (service imports)

    Args:
        lines: Lines to check
        module_path: Full path to module (to detect parent branch)
        bypass_rules: Optional list of bypass rules to skip certain violations

    Returns check result or None if not applicable
    """
    # Check if entire standard is bypassed
    if is_bypassed(module_path, 'imports', None, bypass_rules):
        return {
            'name': 'Handler independence',
            'passed': True,
            'message': 'Bypassed by bypass rules'
        }

    # Detect parent branch from module path
    # e.g., /home/aipass/seed/apps/handlers/... -> parent is 'seed'
    # e.g., /home/aipass/aipass_core/api/apps/handlers/... -> parent is 'api'
    parent_branch = None
    if module_path:
        path_parts = Path(module_path).parts
        # Find 'apps' in path and get the directory before it
        for i, part in enumerate(path_parts):
            if part == 'apps' and i > 0:
                parent_branch = path_parts[i-1]
                break

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue

        # Check for forbidden module imports
        if '.apps.modules' in line and ('from ' in line or 'import ' in line):
            # Extract the import statement
            if '#' in line:
                code_part = line.split('#')[0]
            else:
                code_part = line

            if '.apps.modules' in code_part:
                # Allowed service imports (prax, cli are infrastructure)
                if 'prax.apps.modules' in code_part or 'cli.apps.modules' in code_part:
                    continue

                # If we detected parent branch, check if importing from it
                if parent_branch and f'{parent_branch}.apps.modules' in code_part:
                    return {
                        'name': 'Handler independence',
                        'passed': False,
                        'message': f'Handler importing from parent module on line {i} (violates independence rule)'
                    }

                # Generic check if no parent branch detected
                if not parent_branch:
                    return {
                        'name': 'Handler independence',
                        'passed': False,
                        'message': f'Handler importing from branch module on line {i} (violates independence rule)'
                    }

    return {
        'name': 'Handler independence',
        'passed': True,
        'message': 'No forbidden module imports detected'
    }


def check_import_order(lines: List[str], file_path: str = "", bypass_rules: list | None = None) -> Optional[Dict]:
    """
    Check import order: infrastructure → Prax → services → internal

    Returns check result or None if no imports found
    """
    # Check if entire standard is bypassed
    if is_bypassed(file_path, 'imports', None, bypass_rules):
        return {
            'name': 'Import order',
            'passed': True,
            'message': 'Bypassed by bypass rules'
        }

    # Find all import lines with their line numbers
    imports = []
    prax_line = None

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue

        # Check for import statements
        if stripped.startswith('import ') or stripped.startswith('from '):
            # Track Prax logger specifically
            if 'prax.apps.modules.logger' in stripped:
                prax_line = i

            # Track other imports (not infrastructure setup)
            if 'import sys' not in stripped and 'from pathlib' not in stripped:
                imports.append((i, stripped))

    # If no imports found, skip this check
    if not imports:
        return None

    # Simple check: if Prax is imported, it should be early (before internal imports)
    if prax_line:
        # Find first internal import (seed.apps, cli.apps, etc.)
        first_internal_line = None
        for line_num, import_stmt in imports:
            # Check for any .apps. pattern (internal imports)
            if '.apps.' in import_stmt:
                # Skip if it's the Prax logger itself
                if 'prax.apps.modules.logger' not in import_stmt:
                    first_internal_line = line_num
                    break

        # If we have internal imports, Prax should come before them
        if first_internal_line and prax_line < first_internal_line:
            return {
                'name': 'Import order',
                'passed': True,
                'message': f'Prax logger before internal imports (line {prax_line} < {first_internal_line})'
            }
        elif first_internal_line:
            return {
                'name': 'Import order',
                'passed': False,
                'message': f'Prax logger should be before internal imports (line {prax_line} > {first_internal_line})'
            }
        else:
            # No internal imports, Prax is fine
            return {
                'name': 'Import order',
                'passed': True,
                'message': 'Prax logger imported (no internal imports to check)'
            }

    # If no Prax logger, we already failed that check, so import order is N/A
    return {
        'name': 'Import order',
        'passed': True,
        'message': 'No specific order issues detected'
    }
