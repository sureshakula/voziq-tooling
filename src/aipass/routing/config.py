"""
Registry configuration management.

Handles registry path configuration with environment variable support.
"""

import os
from pathlib import Path
from typing import Optional


_registry_path: Optional[Path] = None


def get_registry_path() -> Path:
    """
    Get the current registry path.

    Priority:
    1. Explicitly set path via set_registry_path()
    2. AIPASS_REGISTRY_PATH environment variable
    3. Default: ~/.aipass/BRANCH_REGISTRY.json

    Returns:
        Path to the registry file
    """
    global _registry_path

    if _registry_path is not None:
        return _registry_path

    env_path = os.environ.get("AIPASS_REGISTRY_PATH")
    if env_path:
        return Path(env_path)

    return Path.home() / ".aipass" / "BRANCH_REGISTRY.json"


def set_registry_path(path: str | Path) -> None:
    """
    Set a custom registry path.

    Args:
        path: Path to the registry file
    """
    global _registry_path
    _registry_path = Path(path)


def reset_registry_path() -> None:
    """
    Reset registry path to default (useful for testing).
    """
    global _registry_path
    _registry_path = None
