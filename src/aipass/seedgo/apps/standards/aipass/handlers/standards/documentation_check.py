#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: documentation_check.py - Documentation Standards Checker Handler
# Date: 2025-11-15
# Version: 0.1.0
# Category: seed/standards/checkers
#
# CHANGELOG (Max 5 entries):
#   - v0.1.0 (2025-11-15): Initial implementation - documentation standards checking
#
# CODE STANDARDS:
#   - Handler implements checking logic, module orchestrates
# =============================================

"""
Documentation Standards Checker Handler

Validates documentation compliance with AIPass documentation standards.
Checks shebang, META block, module docstring, function docstrings.
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Optional

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
    Check if module follows documentation standards

    Args:
        module_path: Path to Python module to check

    Returns:
        dict: {
            'passed': bool,           # Overall pass/fail
            'checks': [               # Individual check results
                {
                    'name': str,      # Check name
                    'passed': bool,   # Pass/fail
                    'message': str,   # Details
                }
            ],
            'score': int,             # 0-100 percentage
            'standard': str           # Standard name
        }
    """
    checks = []
    path = Path(module_path)

    # Check if entire standard is bypassed for this file
    if is_bypassed(module_path, 'documentation', bypass_rules=bypass_rules):
        return {
            'passed': True,
            'checks': [{'name': 'Bypassed', 'passed': True, 'message': 'Standard bypassed via .seed/bypass.json'}],
            'score': 100,
            'standard': 'DOCUMENTATION'
        }

    # Validate file exists
    if not path.exists():
        return {
            'passed': False,
            'checks': [{'name': 'File exists', 'passed': False, 'message': f'File not found: {module_path}'}],
            'score': 0,
            'standard': 'DOCUMENTATION'
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
            'standard': 'DOCUMENTATION'
        }

    # Skip __init__.py files (different documentation standards)
    if path.name == '__init__.py':
        return {
            'passed': True,
            'checks': [{'name': 'Documentation check', 'passed': True, 'message': '__init__.py file (skipped)'}],
            'score': 100,
            'standard': 'DOCUMENTATION'
        }

    # Check 1: Shebang line
    shebang_check = check_shebang(lines, module_path)
    checks.append(shebang_check)

    # Check 2: META block
    meta_check = check_meta_block(content, lines)
    checks.append(meta_check)

    # Check 3: Module-level docstring
    docstring_check = check_module_docstring(lines)
    checks.append(docstring_check)

    # Check 4: Function docstrings (for public functions)
    function_docs_check = check_function_docstrings(content, lines)
    if function_docs_check:
        checks.append(function_docs_check)

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
        'standard': 'DOCUMENTATION'
    }


def check_shebang(lines: List[str], module_path: str = "") -> Dict:
    """
    Check for correct shebang line

    Should be: #!/home/aipass/.venv/bin/python3
    EXCEPTION: MEMORY_BANK uses #!/home/aipass/MEMORY_BANK/.venv/bin/python3
    """
    if not lines:
        return {
            'name': 'Shebang line',
            'passed': False,
            'message': 'File is empty'
        }

    first_line = lines[0].strip()

    # Determine if this is a MEMORY_BANK file
    is_memory_bank = '/MEMORY_BANK/' in module_path

    # Define valid shebangs
    standard_shebang = '#!/home/aipass/.venv/bin/python3'
    memory_bank_shebang = '#!/home/aipass/MEMORY_BANK/.venv/bin/python3'

    # Check for correct shebang based on location
    if is_memory_bank:
        if first_line == memory_bank_shebang:
            return {
                'name': 'Shebang line',
                'passed': True,
                'message': f'Correct MEMORY_BANK shebang ({memory_bank_shebang})'
            }
        elif first_line == standard_shebang:
            return {
                'name': 'Shebang line',
                'passed': False,
                'message': f'Wrong shebang for MEMORY_BANK: {first_line} (should be {memory_bank_shebang})'
            }
    else:
        if first_line == standard_shebang:
            return {
                'name': 'Shebang line',
                'passed': True,
                'message': f'Correct shebang ({standard_shebang})'
            }
        elif first_line == memory_bank_shebang:
            return {
                'name': 'Shebang line',
                'passed': False,
                'message': f'Wrong shebang: {first_line} (should be {standard_shebang} for non-MEMORY_BANK files)'
            }

    # Handle other shebangs
    if first_line.startswith('#!'):
        expected = memory_bank_shebang if is_memory_bank else standard_shebang
        return {
            'name': 'Shebang line',
            'passed': False,
            'message': f'Wrong shebang: {first_line} (should be {expected})'
        }

    expected = memory_bank_shebang if is_memory_bank else standard_shebang
    return {
        'name': 'Shebang line',
        'passed': False,
        'message': f'Missing shebang line (should be {expected})'
    }


def check_meta_block(content: str, lines: List[str]) -> Dict:
    """
    Check for complete META block

    Required fields:
    - Name: filename - Description
    - Date: YYYY-MM-DD
    - Version: X.Y.Z
    - Category: branch or branch/handlers
    - CHANGELOG: At least one entry
    - CODE STANDARDS: Reference
    """
    # Check for META header markers
    if '# ===================AIPASS====================' not in content:
        return {
            'name': 'META block',
            'passed': False,
            'message': 'Missing META block (no AIPASS header found)'
        }

    if '# META DATA HEADER' not in content:
        return {
            'name': 'META block',
            'passed': False,
            'message': 'Missing "# META DATA HEADER" line'
        }

    # Check required fields
    missing_fields = []

    if not re.search(r'# Name:\s+[\w\-]+\.py\s+-\s+', content):
        missing_fields.append('Name')

    if not re.search(r'# Date:\s+\d{4}-\d{2}-\d{2}', content):
        missing_fields.append('Date')

    if not re.search(r'# Version:\s+\d+\.\d+\.\d+', content):
        missing_fields.append('Version')

    if not re.search(r'# Category:\s+\w+', content):
        missing_fields.append('Category')

    if '# CHANGELOG' not in content:
        missing_fields.append('CHANGELOG')

    if '# CODE STANDARDS:' not in content:
        missing_fields.append('CODE STANDARDS')

    if missing_fields:
        return {
            'name': 'META block',
            'passed': False,
            'message': f'Incomplete META block - missing: {", ".join(missing_fields)}'
        }

    return {
        'name': 'META block',
        'passed': True,
        'message': 'Complete META block with all required fields'
    }


def check_module_docstring(lines: List[str]) -> Dict:
    """
    Check for module-level docstring after META block

    Should be triple-quoted string explaining module purpose
    """
    # Find the end of META block
    meta_end = -1
    for i, line in enumerate(lines):
        if '# =============================================' in line and i > 0:
            meta_end = i
            break

    if meta_end == -1:
        return {
            'name': 'Module docstring',
            'passed': False,
            'message': 'Cannot find end of META block'
        }

    # Look for docstring within next 10 lines after META block
    for i in range(meta_end + 1, min(meta_end + 11, len(lines))):
        stripped = lines[i].strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            return {
                'name': 'Module docstring',
                'passed': True,
                'message': 'Module-level docstring present'
            }

    return {
        'name': 'Module docstring',
        'passed': False,
        'message': 'Missing module-level docstring after META block'
    }


def check_function_docstrings(content: str, lines: List[str]) -> Optional[Dict]:
    """
    Check that public functions have docstrings

    Public functions (not starting with _) should have docstrings
    """
    # Find all public function definitions
    public_functions = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('def ') and not stripped.startswith('def _'):
            # Extract function name
            match = re.match(r'def\s+(\w+)\s*\(', stripped)
            if match:
                func_name = match.group(1)
                public_functions.append((func_name, i))

    if not public_functions:
        # No public functions, check passes
        return None

    # Check each function for docstring
    undocumented = []
    for func_name, line_num in public_functions:
        # Look for docstring in next few lines
        has_docstring = False
        for check_line in range(line_num, min(line_num + 5, len(lines) + 1)):
            if check_line - 1 < len(lines):
                check_stripped = lines[check_line - 1].strip()
                if check_stripped.startswith('"""') or check_stripped.startswith("'''"):
                    has_docstring = True
                    break

        if not has_docstring:
            undocumented.append(f'{func_name} (line {line_num})')

    if undocumented:
        return {
            'name': 'Function docstrings',
            'passed': False,
            'message': f'{len(undocumented)} public functions missing docstrings: {undocumented[0]}'
        }

    return {
        'name': 'Function docstrings',
        'passed': True,
        'message': f'All {len(public_functions)} public functions have docstrings'
    }
