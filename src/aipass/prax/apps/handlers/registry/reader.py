# =================== AIPass ====================
# Name: reader.py
# Description: Branch Registry Reader Handler
# Version: 0.1.0
# Created: 2025-11-15
# Modified: 2026-03-09
# =============================================

"""
Branch Registry Reader Handler

Reads BRANCH_REGISTRY.json and returns branch information.
Used by branch watcher to discover which branches to monitor.
"""

import json
from pathlib import Path
from typing import List, Dict, Any


# =============================================================================
# CONSTANTS
# =============================================================================

def _find_repo_root() -> Path:
    """Walk up from this file to find the repo root (contains AIPASS_REGISTRY.json)."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "AIPASS_REGISTRY.json").exists():
            return parent
    return Path.cwd()

_branch_registry_path_cache: Path | None = None

def _get_branch_registry_path() -> Path:
    """Lazily resolve AIPASS_REGISTRY.json path."""
    global _branch_registry_path_cache
    if _branch_registry_path_cache is None:
        _branch_registry_path_cache = _find_repo_root() / "AIPASS_REGISTRY.json"
    return _branch_registry_path_cache

# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def read_registry() -> List[Dict[str, Any]] | None:
    """
    Read BRANCH_REGISTRY.json and return list of branches

    Returns:
        List of branch dictionaries, or None on error
    """
    try:
        if not _get_branch_registry_path().exists():
            return None

        with open(_get_branch_registry_path(), 'r', encoding='utf-8') as f:
            data = json.load(f)

        branches = data.get('branches', [])
        return branches

    except json.JSONDecodeError:
        return None
    except Exception:
        return None


def get_branch_paths(branch_names: List[str] | None = None) -> List[Path] | None:
    """
    Get paths for specified branches (or all branches if None)

    Args:
        branch_names: List of branch names to get paths for, or None for all

    Returns:
        List of Path objects, or None on error
    """
    branches = read_registry()
    if branches is None:
        return None

    paths = []
    for branch in branches:
        # Filter by branch names if specified
        if branch_names:
            if branch.get('name') not in branch_names:
                continue

        branch_path = branch.get('path')
        if branch_path:
            paths.append(Path(branch_path))

    return paths


def get_branch_info(branch_name: str) -> Dict[str, Any] | None:
    """
    Get detailed information for a specific branch

    Args:
        branch_name: Name of the branch

    Returns:
        Branch dictionary, or None if not found
    """
    branches = read_registry()
    if branches is None:
        return None

    for branch in branches:
        if branch.get('name') == branch_name:
            return branch

    return None
