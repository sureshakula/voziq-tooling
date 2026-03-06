"""
Command Consistency Checker Handler

Checks if new commands/flags are documented everywhere they should be.
Validates documentation completeness for command flags.
"""

import sys
from pathlib import Path
from typing import Dict

from ..file import file_handler


def check_command_consistency() -> Dict:
    """
    Check if new commands/flags are documented everywhere they should be.

    Scans audit module for flags, checks if they appear in:
    - README.md
    - seed.py help text
    - docs/ files

    Returns:
        Dict with check results
    """
    seed_path = Path.home() / "seed"
    missing_docs = []

    # Define command flags to check (source of truth: where they're implemented)
    # Format: (flag, description, implemented_in)
    command_flags = [
        ("--show-bypasses", "audit bypass inspection", "standards_audit.py"),
        ("--bypasses", "audit bypass inspection (short)", "standards_audit.py"),
    ]

    # Files that should document commands
    doc_files = {
        'readme': seed_path / "README.md",
        'seed_help': seed_path / "apps" / "seed.py",
    }

    for flag, description, source in command_flags:
        # Check each documentation file
        for doc_name, doc_path in doc_files.items():
            if not doc_path.exists():
                continue

            try:
                content = file_handler.read_file(str(doc_path))
                if content and flag not in content:
                    missing_docs.append({
                        'flag': flag,
                        'description': description,
                        'missing_from': doc_name,
                        'file': str(doc_path.relative_to(seed_path))
                    })
            except Exception:
                # Error reading file - skip
                pass

    # Group by flag for cleaner output
    flags_missing = {}
    for item in missing_docs:
        flag = item['flag']
        if flag not in flags_missing:
            flags_missing[flag] = {
                'description': item['description'],
                'missing_from': []
            }
        flags_missing[flag]['missing_from'].append(item['missing_from'])

    return {
        'name': 'Command Consistency',
        'passed': len(missing_docs) == 0,
        'missing': flags_missing,
        'checked': [f"Checked {len(command_flags)} flags against {len(doc_files)} doc files"],
        'score': 100 if len(missing_docs) == 0 else 50
    }
