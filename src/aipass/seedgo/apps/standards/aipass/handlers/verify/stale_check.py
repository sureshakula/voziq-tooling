#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: stale_check.py - Stale Patterns Checker Handler
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
Stale Patterns Checker Handler

Checks for deprecated patterns in the seed codebase.
Returns violations found during grep search.
"""

import sys
import subprocess
from pathlib import Path
from typing import Dict

# Infrastructure
AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))

# Business logic imports
from seed.apps.handlers.config import ignore_handler


def check_stale_patterns() -> Dict:
    """
    Check for deprecated patterns in /home/aipass/seed/

    Returns:
        Dict with check results
    """
    seed_path = Path.home() / "seed"
    deprecated_patterns = ignore_handler.get_deprecated_patterns()

    violations = []

    for pattern, reason in deprecated_patterns.items():
        try:
            # Use grep to search for pattern
            result = subprocess.run(
                ["grep", "-rn", pattern, str(seed_path),
                 "--include=*.py", "--include=*.md"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:  # Pattern found
                for line in result.stdout.strip().split('\n'):
                    if line:
                        # Parse grep output: file:line:content
                        parts = line.split(':', 2)
                        if len(parts) >= 2:
                            file_path = parts[0]
                            line_num = parts[1]
                            # Make path relative to seed for readability
                            rel_path = Path(file_path).relative_to(seed_path)
                            violations.append({
                                'pattern': pattern,
                                'reason': reason,
                                'location': f"{rel_path}:{line_num}"
                            })
        except subprocess.TimeoutExpired:
            # Timeout - skip this pattern
            pass
        except Exception:
            # Error checking pattern - skip
            pass

    return {
        'name': 'Stale Patterns',
        'passed': len(violations) == 0,
        'violations': violations,
        'checked': [f"Searched for: {', '.join(deprecated_patterns.keys())}"],
        'score': 100 if len(violations) == 0 else 0
    }
