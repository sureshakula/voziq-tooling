"""
Branch resolution logic.

Resolves symbolic @branch names to absolute paths and metadata.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .exceptions import BranchNotFoundError, RegistryNotFoundError
from .registry import get_all_branches, get_branch_by_name, load_registry


def normalize_branch_name(symbolic_name: str) -> str:
    """
    Normalize a symbolic branch name.

    Strips @ prefix if present and returns clean branch name.

    Args:
        symbolic_name: Branch name with or without @ prefix

    Returns:
        Clean branch name without @ prefix
    """
    if symbolic_name.startswith("@"):
        return symbolic_name[1:]
    return symbolic_name


def resolve_branch(symbolic_name: str) -> str:
    """
    Resolve a symbolic branch name to its absolute path.

    Args:
        symbolic_name: Branch name with or without @ prefix (e.g., "@my_agent" or "my_agent")

    Returns:
        Absolute path to branch directory as string

    Raises:
        BranchNotFoundError: If branch not in registry
        RegistryNotFoundError: If registry file missing or corrupt
    """
    # Let RegistryNotFoundError propagate from load_registry
    registry = load_registry()

    name = normalize_branch_name(symbolic_name)
    branch = registry.get("branches", {}).get(name)

    if branch is None:
        raise BranchNotFoundError(
            f"Branch '{symbolic_name}' not found in registry"
        )

    return branch["path"]


def branch_exists(symbolic_name: str) -> bool:
    """
    Check if a branch exists in the registry.

    Args:
        symbolic_name: Branch name with or without @ prefix

    Returns:
        True if branch exists, False otherwise
    """
    name = normalize_branch_name(symbolic_name)
    branch = get_branch_by_name(name)
    return branch is not None


def get_branch_info(symbolic_name: str) -> Dict[str, Any]:
    """
    Get full metadata for a branch.

    Args:
        symbolic_name: Branch name with or without @ prefix

    Returns:
        Dictionary with branch metadata (name, path, type, status, timestamps)

    Raises:
        BranchNotFoundError: If branch not in registry
        RegistryNotFoundError: If registry file missing or corrupt
    """
    # Let RegistryNotFoundError propagate from load_registry
    registry = load_registry()

    name = normalize_branch_name(symbolic_name)
    branch = registry.get("branches", {}).get(name)

    if branch is None:
        raise BranchNotFoundError(
            f"Branch '{symbolic_name}' not found in registry"
        )

    return branch


def list_branches(
    branch_type: Optional[str] = None,
    status: str = "active",
) -> List[str]:
    """
    List all registered branches, optionally filtered by type and status.

    Args:
        branch_type: Filter by branch type (optional)
        status: Filter by status (default: "active")

    Returns:
        List of branch names with @ prefix
    """
    branches = get_all_branches(branch_type=branch_type, status=status)
    return [f"@{branch['name']}" for branch in branches]
