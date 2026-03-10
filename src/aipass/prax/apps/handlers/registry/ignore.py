# =================== AIPass ====================
# Name: ignore.py
# Description: Registry Ignore Pattern Handler
# Version: 1.0.0
# Created: 2025-11-06
# Modified: 2026-03-09
# =============================================

"""
Registry Ignore Handler

Manages patterns for excluding files from:
- Branch creation (don't copy template-internal files)
- Registry regeneration (don't track template-internal files)

Loads patterns from registry_ignore.json in template directory.
"""

import json
from pathlib import Path
from typing import List, Set
from fnmatch import fnmatch


def load_ignore_patterns(template_dir: Path) -> dict:
    """
    Load ignore patterns from registry_ignore.json

    Args:
        template_dir: Path to template directory

    Returns:
        Dict with ignore_files and ignore_patterns lists
        Returns empty lists if file not found
    """
    ignore_file = template_dir / "registry_ignore.json"

    if not ignore_file.exists():
        # Return empty patterns if file doesn't exist
        return {
            "ignore_files": [],
            "ignore_patterns": []
        }

    try:
        with open(ignore_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {
                "ignore_files": data.get("ignore_files", []),
                "ignore_patterns": data.get("ignore_patterns", [])
            }
    except Exception:
        return {
            "ignore_files": [],
            "ignore_patterns": []
        }


def should_ignore(
    file_path: Path,
    template_dir: Path,
    ignore_files: List[str],
    ignore_patterns: List[str]
) -> bool:
    """
    Check if a file should be ignored based on patterns

    Args:
        file_path: Path to file to check
        template_dir: Template directory (for relative path calculation)
        ignore_files: List of exact filenames to ignore
        ignore_patterns: List of glob patterns to ignore

    Returns:
        True if file should be ignored, False otherwise
    """
    filename = file_path.name

    # Check exact filename matches
    if filename in ignore_files:
        return True

    # Check glob patterns
    for pattern in ignore_patterns:
        if fnmatch(filename, pattern):
            return True

    # Check if any parent directory matches patterns
    try:
        relative_path = file_path.relative_to(template_dir)
        for part in relative_path.parts:
            for pattern in ignore_patterns:
                if fnmatch(part, pattern):
                    return True
    except ValueError:
        # file_path not relative to template_dir
        pass

    return False


def get_ignored_files(template_dir: Path) -> Set[str]:
    """
    Get set of all ignored filenames for quick lookup

    Args:
        template_dir: Path to template directory

    Returns:
        Set of filenames to ignore
    """
    patterns = load_ignore_patterns(template_dir)
    return set(patterns.get("ignore_files", []))


def get_ignore_patterns(template_dir: Path) -> List[str]:
    """
    Get list of ignore glob patterns

    Args:
        template_dir: Path to template directory

    Returns:
        List of glob patterns to ignore
    """
    patterns = load_ignore_patterns(template_dir)
    return patterns.get("ignore_patterns", [])
