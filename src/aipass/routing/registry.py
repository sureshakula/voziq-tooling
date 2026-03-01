"""
Registry operations for branch management.

Handles loading, saving, and managing the BRANCH_REGISTRY.json file.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import get_registry_path
from .exceptions import (
    BranchAlreadyExistsError,
    InvalidPathError,
    RegistryCorruptError,
    RegistryNotFoundError,
    RegistryPermissionError,
)


def load_registry() -> Dict[str, Any]:
    """
    Load the branch registry from disk.

    Returns:
        Registry dictionary with version, branches, and metadata

    Raises:
        RegistryNotFoundError: If registry file doesn't exist
        RegistryCorruptError: If registry file is invalid JSON
        RegistryPermissionError: If registry file cannot be read
    """
    registry_path = get_registry_path()

    if not registry_path.exists():
        raise RegistryNotFoundError(
            f"Registry not found at {registry_path}. "
            "Run initialize_registry() to create one."
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

    # Validate structure
    if not isinstance(data, dict):
        raise RegistryCorruptError("Registry must be a JSON object")

    if "branches" not in data:
        raise RegistryCorruptError("Registry missing 'branches' field")

    return data


def save_registry(registry: Dict[str, Any]) -> None:
    """
    Save the branch registry to disk.

    Args:
        registry: Registry dictionary to save

    Raises:
        RegistryPermissionError: If registry file cannot be written
    """
    registry_path = get_registry_path()

    # Ensure directory exists
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    # Update metadata timestamp
    if "metadata" not in registry:
        registry["metadata"] = {}

    registry["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
    registry["metadata"]["managed_by"] = "aipass.routing"

    try:
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
    except PermissionError as e:
        raise RegistryPermissionError(f"Permission denied writing registry: {e}")
    except Exception as e:
        raise RegistryPermissionError(f"Failed to write registry: {e}")


def initialize_registry() -> None:
    """
    Create a new empty registry file.

    Creates the registry directory and file if they don't exist.
    If registry already exists, does nothing.
    """
    registry_path = get_registry_path()

    if registry_path.exists():
        return

    registry = {
        "version": "1.0",
        "branches": {},
        "metadata": {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "managed_by": "aipass.routing",
        },
    }

    save_registry(registry)


def add_branch(
    name: str,
    path: str | Path,
    branch_type: str = "agent",
    status: str = "active",
) -> None:
    """
    Add a branch to the registry.

    Args:
        name: Branch name (without @ prefix)
        path: Absolute path to branch directory
        branch_type: Type of branch (agent, service, module, etc.)
        status: Branch status (active, inactive, archived)

    Raises:
        BranchAlreadyExistsError: If branch name already exists
        InvalidPathError: If path doesn't exist or isn't a directory
        RegistryNotFoundError: If registry doesn't exist
    """
    # Validate path
    path_obj = Path(path).resolve()
    if not path_obj.exists():
        raise InvalidPathError(f"Path does not exist: {path}")
    if not path_obj.is_dir():
        raise InvalidPathError(f"Path is not a directory: {path}")

    # Load registry
    try:
        registry = load_registry()
    except RegistryNotFoundError:
        # Auto-initialize if registry doesn't exist
        initialize_registry()
        registry = load_registry()

    # Check if branch already exists
    if name in registry["branches"]:
        raise BranchAlreadyExistsError(
            f"Branch '{name}' already exists in registry"
        )

    # Add branch entry
    registry["branches"][name] = {
        "name": name,
        "path": str(path_obj),
        "type": branch_type,
        "status": status,
        "created": datetime.now(timezone.utc).isoformat(),
    }

    save_registry(registry)


def remove_branch(name: str) -> None:
    """
    Remove a branch from the registry.

    Args:
        name: Branch name (without @ prefix)

    Raises:
        RegistryNotFoundError: If registry doesn't exist
    """
    registry = load_registry()

    if name in registry["branches"]:
        del registry["branches"][name]
        save_registry(registry)


def update_branch_status(name: str, status: str) -> None:
    """
    Update the status of a branch.

    Args:
        name: Branch name (without @ prefix)
        status: New status (active, inactive, archived)

    Raises:
        RegistryNotFoundError: If registry doesn't exist
    """
    registry = load_registry()

    if name in registry["branches"]:
        registry["branches"][name]["status"] = status
        registry["branches"][name]["last_seen"] = datetime.now(timezone.utc).isoformat()
        save_registry(registry)


def get_all_branches(
    branch_type: Optional[str] = None,
    status: str = "active",
) -> List[Dict[str, Any]]:
    """
    Get all branches from the registry, optionally filtered.

    Args:
        branch_type: Filter by branch type (optional)
        status: Filter by status (default: "active")

    Returns:
        List of branch dictionaries

    Raises:
        RegistryNotFoundError: If registry doesn't exist
    """
    try:
        registry = load_registry()
    except RegistryNotFoundError:
        return []

    branches = registry.get("branches", {}).values()

    # Apply filters
    filtered = []
    for branch in branches:
        if status and branch.get("status") != status:
            continue
        if branch_type and branch.get("type") != branch_type:
            continue
        filtered.append(branch)

    return filtered


def get_branch_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Get a single branch by name.

    Args:
        name: Branch name (without @ prefix)

    Returns:
        Branch dictionary or None if not found

    Raises:
        RegistryNotFoundError: If registry doesn't exist
    """
    try:
        registry = load_registry()
    except RegistryNotFoundError:
        return None

    return registry.get("branches", {}).get(name)
