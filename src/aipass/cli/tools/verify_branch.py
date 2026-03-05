#!/home/aipass/.venv/bin/python3
# -*- coding: utf-8 -*-

# ===================AIPASS====================
# META DATA HEADER
# Name: verify_branch.py - Branch Template Verification
# Date: 2025-11-08
# Version: 1.0.0
# Category: cortex/modules
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2025-11-08): Initial implementation - Compare template vs branch
#
# CODE STANDARDS:
#   - Error handling: Use error handler system (apps/handlers/error/)
# =============================================

"""
Branch Template Verification Tool

Compares template directory with created branch to identify:
- Files in template but missing in branch
- Files in branch but not in template
- Renamed files
"""

import sys
import json
from pathlib import Path
from typing import Set, List, Tuple
from fnmatch import fnmatch

# INFRASTRUCTURE IMPORT PATTERN
AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))

# Get template directory
TEMPLATE_DIR = AIPASS_ROOT / "cortex" / "templates" / "branch_template"


def load_ignore_patterns() -> Tuple[List[str], List[str]]:
    """Load ignore patterns from .registry_ignore.json"""
    ignore_file = TEMPLATE_DIR / ".registry_ignore.json"

    if not ignore_file.exists():
        return [], []

    try:
        with open(ignore_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            ignore_files = data.get("ignore_files", [])
            ignore_patterns = data.get("ignore_patterns", [])
            return ignore_files, ignore_patterns
    except Exception as e:
        print(f"Warning: Could not load .registry_ignore.json: {e}")
        return [], []


def should_exclude(path: Path, base_dir: Path, ignore_files: List[str], ignore_patterns: List[str]) -> bool:
    """Check if path should be excluded based on ignore patterns"""
    rel_path = path.relative_to(base_dir)
    filename = path.name
    path_str = str(rel_path)

    # Check exact filename matches
    if filename in ignore_files:
        return True

    # Check glob patterns
    for pattern in ignore_patterns:
        if fnmatch(filename, pattern):
            return True
        # Check if any parent directory matches
        for part in rel_path.parts:
            if fnmatch(part, pattern):
                return True

    return False


def get_file_set(directory: Path, ignore_files: List[str], ignore_patterns: List[str]) -> Set[str]:
    """Get set of all file paths in directory (relative)"""
    files = set()

    for item in directory.rglob("*"):
        if item.is_file() and not should_exclude(item, directory, ignore_files, ignore_patterns):
            rel_path = str(item.relative_to(directory))
            files.add(rel_path)

    return files


def verify_branch(branch_dir: Path) -> Tuple[List[str], List[str], List[str]]:
    """
    Compare template with branch

    Returns:
        Tuple of (in_template_only, in_branch_only, in_both)
    """
    # Load ignore patterns from .registry_ignore.json
    ignore_files, ignore_patterns = load_ignore_patterns()

    template_files = get_file_set(TEMPLATE_DIR, ignore_files, ignore_patterns)
    branch_files = get_file_set(branch_dir, ignore_files, ignore_patterns)

    in_template_only = sorted(template_files - branch_files)
    in_branch_only = sorted(branch_files - template_files)
    in_both = sorted(template_files & branch_files)

    return in_template_only, in_branch_only, in_both


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 verify_branch.py <branch_directory>")
        print("Example: python3 verify_branch.py test_branch002")
        sys.exit(1)

    branch_path = Path(sys.argv[1])
    if not branch_path.is_absolute():
        # Assume it's relative to cortex directory
        branch_path = Path.cwd() / branch_path

    if not branch_path.exists():
        print(f"❌ ERROR: Branch directory not found: {branch_path}")
        sys.exit(1)

    print(f"\n=== Branch Verification ===")
    print(f"Template: {TEMPLATE_DIR}")
    print(f"Branch: {branch_path}")
    print()

    in_template_only, in_branch_only, in_both = verify_branch(branch_path)

    print(f"Files in both: {len(in_both)}")
    print(f"Files in template only: {len(in_template_only)}")
    print(f"Files in branch only: {len(in_branch_only)}")
    print()

    if in_template_only:
        print("❌ Missing from branch (expected from template):")
        for file in in_template_only:
            print(f"  - {file}")
        print()

    if in_branch_only:
        print("✅ Additional files in branch (renamed or new):")
        for file in in_branch_only:
            print(f"  + {file}")
        print()

    if not in_template_only and not in_branch_only:
        print("✅ Branch matches template perfectly")

    print("="*70)


if __name__ == "__main__":
    main()
