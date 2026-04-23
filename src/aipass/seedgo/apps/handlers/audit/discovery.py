# =================== AIPass ====================
# Name: discovery.py
# Description: Branch Discovery Handler
# Version: 1.0.0
# Created: 2026-03-05
# Modified: 2026-03-05
# =============================================

"""
Branch Discovery Handler

Discovers all AIPass branches from AIPASS_REGISTRY.json
"""

from pathlib import Path
from typing import List, Dict

# =============================================================================
# INFRASTRUCTURE SETUP
# =============================================================================

# IMPORTS
# =============================================================================

import json

from aipass.prax import logger
from aipass.seedgo.apps.handlers.json import json_handler

# =============================================================================
# PRIVATE BRANCH DETECTION
# =============================================================================


def _is_branch_private(branch_name: str) -> bool:
    """Check if branch is in the private registry."""
    registry_path = _find_registry()
    priv_path = registry_path.parent / "PRIVATE_BRANCH_REGISTRY.json" if registry_path.exists() else None
    if not priv_path or not priv_path.exists():
        return False
    try:
        with open(priv_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        for branch in registry.get("branches", []):
            if branch.get("name", "").upper() == branch_name.upper():
                return True
    except (json.JSONDecodeError, IOError):
        logger.info("Cannot read private registry for branch %s", branch_name)
    return False


# =============================================================================
# PUBLIC API
# =============================================================================


def _find_registry() -> Path:
    """
    Find *_REGISTRY.json by walking up from CWD first, then from __file__.
    CWD-first matches drone's registry_handler search order and supports
    external projects with their own registries.
    """
    # Walk up from CWD first — this is where the user is working
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        matches = sorted(parent.glob("*_REGISTRY.json"))
        if matches:
            return matches[0]
    # Fallback: walk up from this file (pip editable installs)
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        matches = sorted(parent.glob("*_REGISTRY.json"))
        if matches:
            return matches[0]
    return Path.cwd() / "AIPASS_REGISTRY.json"


def _find_caller_registries() -> List[Path]:
    """Find registries from the caller's project via AIPASS_CALLER_CWD."""
    import os

    caller_cwd = os.environ.get("AIPASS_CALLER_CWD", "")
    if not caller_cwd:
        return []
    caller_path = Path(caller_cwd)
    for parent in [caller_path] + list(caller_path.parents):
        matches = sorted(parent.glob("*_REGISTRY.json"))
        if matches:
            return matches
    return []


def _branches_from_registry(registry_path: Path) -> List[Dict[str, str]]:
    """Extract branch dicts from a single registry file."""
    branches = []
    if not registry_path.exists():
        return branches
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry_data = json.load(f)
        registry_dir = registry_path.parent
        raw_branches = registry_data.get("branches", [])
        if isinstance(raw_branches, dict):
            raw_branches = list(raw_branches.values())
        for branch in raw_branches:
            branch_name = branch.get("name", "")
            raw_path = branch.get("path", "")
            branch_path = Path(raw_path)
            if not branch_path.is_absolute():
                branch_path = (registry_dir / branch_path).resolve()
            if not branch_path.exists():
                continue
            entry_file = None
            standard_entry = branch_path / "apps" / f"{branch_name.lower()}.py"
            branch_entry = branch_path / "apps" / "branch.py"
            if standard_entry.exists():
                entry_file = standard_entry
            elif branch_entry.exists():
                entry_file = branch_entry
            if entry_file:
                branches.append({"name": branch_name, "path": str(branch_path), "entry_file": str(entry_file)})
    except (json.JSONDecodeError, IOError):
        logger.info("Cannot read registry %s", registry_path)
    return branches


def discover_branches(include_private: bool = False) -> List[Dict[str, str]]:
    """
    Discover all branches from AIPASS_REGISTRY.json and caller's project registry.

    Args:
        include_private: If False (default), excludes branches listed in
                         PRIVATE_BRANCH_REGISTRY.json. Set True to include them.

    Returns:
        List of dicts with 'name', 'path', 'entry_file' keys
    """
    primary_path = _find_registry()
    branches = _branches_from_registry(primary_path)

    seen_names = {b["name"].upper() for b in branches}
    for caller_reg in _find_caller_registries():
        if caller_reg.resolve() == primary_path.resolve():
            continue
        for b in _branches_from_registry(caller_reg):
            if b["name"].upper() not in seen_names:
                branches.append(b)
                seen_names.add(b["name"].upper())

    if not include_private:
        branches = [b for b in branches if not _is_branch_private(b["name"])]

    json_handler.log_operation("branches_discovered", {"count": len(branches)})
    return sorted(branches, key=lambda x: x["name"])


def check_internal_access(branch_name: str) -> bool:
    """
    Check if the current working directory is inside a private branch.

    Used to enforce isolation per DPLAN-035: private branches can only be
    audited from inside their own directory.

    Args:
        branch_name: Name of the branch to check

    Returns:
        True if CWD is inside the branch (access allowed), False otherwise
    """
    _branch_path = None
    _priv_branches = discover_branches(include_private=True)
    for _b in _priv_branches:
        if _b["name"].upper() == branch_name.upper():
            _branch_path = Path(_b["path"])
            break

    if _branch_path is None:
        return True  # Branch not found in registry, allow access

    cwd = Path.cwd()
    return cwd == _branch_path or cwd.is_relative_to(_branch_path)
