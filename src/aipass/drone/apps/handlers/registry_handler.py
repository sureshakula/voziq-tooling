# =================== AIPass ====================
# Name: registry_handler.py
# Description: Handler for registry file operations
# Version: 1.0.0
# Created: 2026-03-09
# Modified: 2026-03-09
# =============================================

"""
Handler for registry file operations.

Handles loading, parsing, and normalizing AIPASS_REGISTRY.json.
All file I/O and data transformation for the registry lives here.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from aipass.prax import logger
from .exceptions import (
    RegistryCorruptError,
    RegistryNotFoundError,
    RegistryPermissionError,
)


# ---------------------------------------------------------------------------
# Registry path resolution
# ---------------------------------------------------------------------------

_registry_path: Optional[Path] = None


def find_registry() -> Path:
    """Find AIPASS_REGISTRY.json by walking up from this file's location.

    Search order:
    1. Explicitly set path via set_registry_path()
    2. AIPASS_REGISTRY environment variable
    3. Walk up from drone package location
    4. Walk up from cwd
    5. Default: package-relative path
    """
    # Walk up from this file (works for pip editable installs)
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        candidate = parent / "AIPASS_REGISTRY.json"
        if candidate.exists():
            return candidate

    # Walk up from cwd (works for regular installs)
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        candidate = parent / "AIPASS_REGISTRY.json"
        if candidate.exists():
            return candidate

    # Fallback — use package-relative path (no filesystem assumptions)
    return Path(__file__).resolve().parents[4] / "AIPASS_REGISTRY.json"


def get_registry_path() -> Path:
    """Get the current registry path.

    Priority:
    1. Explicitly set path via set_registry_path()
    2. AIPASS_REGISTRY environment variable
    3. Walk-up finder from package location
    """
    global _registry_path

    if _registry_path is not None:
        return _registry_path

    env_path = os.environ.get("AIPASS_REGISTRY")
    if env_path:
        return Path(env_path)

    return find_registry()


def set_registry_path(path: str | Path) -> None:
    """Set a custom registry path."""
    global _registry_path
    _registry_path = Path(path)


def reset_registry_path() -> None:
    """Reset registry path to default (useful for testing)."""
    global _registry_path
    _registry_path = None


# ---------------------------------------------------------------------------
# Registry loading and querying
# ---------------------------------------------------------------------------

def load_registry() -> Dict[str, Any]:
    """Load the branch registry from disk.

    Returns:
        Registry dictionary with branches (normalized to dict format)

    Raises:
        RegistryNotFoundError: If registry file doesn't exist
        RegistryCorruptError: If registry file is invalid JSON
        RegistryPermissionError: If registry file cannot be read
    """
    registry_path = get_registry_path()

    if not registry_path.exists():
        raise RegistryNotFoundError(
            f"Registry not found at {registry_path}. "
            "Create an AIPASS_REGISTRY.json in your project root."
        )

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except PermissionError as e:
        raise RegistryPermissionError(f"Permission denied reading registry: {e}")
    except json.JSONDecodeError as e:
        raise RegistryCorruptError(f"Registry file is corrupted: {e}")
    except Exception as e:
        raise RegistryCorruptError(f"Failed to read registry: {e}")

    if not isinstance(data, dict):
        raise RegistryCorruptError("Registry must be a JSON object")

    if "branches" not in data:
        raise RegistryCorruptError("Registry missing 'branches' field")

    # Normalize: AIPASS_REGISTRY uses list format, convert to dict keyed by name
    branches_raw = data["branches"]
    if isinstance(branches_raw, list):
        branches_dict = {}
        registry_dir = registry_path.parent
        for branch in branches_raw:
            name = branch.get("name", "").lower()
            if not name:
                continue
            # Resolve relative paths against registry location
            raw_path = branch.get("path", "")
            branch_path = Path(raw_path)
            if not branch_path.is_absolute():
                branch_path = (registry_dir / branch_path).resolve()
            entry = dict(branch)
            entry["name"] = name
            entry["path"] = str(branch_path)
            branches_dict[name] = entry
        data["branches"] = branches_dict
    elif not isinstance(branches_raw, dict):
        raise RegistryCorruptError("Registry 'branches' must be a list or dict")

    return data


def get_all_branches(
    branch_type: Optional[str] = None,
    status: str = "active",
) -> List[Dict[str, Any]]:
    """Get all branches from the registry, optionally filtered."""
    try:
        registry = load_registry()
    except RegistryNotFoundError:
        return []

    branches = registry.get("branches", {}).values()

    filtered = []
    for branch in branches:
        if status and branch.get("status") != status:
            continue
        if branch_type and branch.get("type") != branch_type:
            continue
        filtered.append(branch)

    return filtered


def get_branch_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get a single branch by name (case-insensitive)."""
    try:
        registry = load_registry()
    except RegistryNotFoundError:
        return None

    return registry.get("branches", {}).get(name.lower())
