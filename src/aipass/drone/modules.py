"""Internal module registry for drone.

Routes @module commands to Python packages installed alongside drone,
as opposed to external branches in BRANCH_REGISTRY.json.

Modules register by providing a drone_adapter module with:
- DRONE_MODULE dict (name, version, description)
- handle_command(command, args) -> dict with stdout/stderr/exit_code
- get_help(command=None) -> str
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass

# Maps module name -> import path for its drone_adapter
_MODULE_REGISTRY: dict[str, str] = {
    "seedgo": "seedgo.drone_adapter",
    # Future modules register here:
    # "prax": "aipass.prax.drone_adapter",
    # "cortex": "aipass.cortex.drone_adapter",
}


@dataclass
class ModuleInfo:
    """Metadata about a registered module."""

    name: str
    version: str
    description: str
    adapter_path: str


def list_modules() -> list[str]:
    """Return sorted list of registered module names."""
    return sorted(_MODULE_REGISTRY.keys())


def get_module_info(name: str) -> ModuleInfo | None:
    """Get module metadata without executing anything.

    Returns None if the module is not registered or not importable.
    """
    adapter_path = _MODULE_REGISTRY.get(name)
    if adapter_path is None:
        return None
    try:
        mod = importlib.import_module(adapter_path)
        meta = getattr(mod, "DRONE_MODULE", {})
        return ModuleInfo(
            name=meta.get("name", name),
            version=meta.get("version", "unknown"),
            description=meta.get("description", ""),
            adapter_path=adapter_path,
        )
    except ImportError:
        return None


def is_module(name: str) -> bool:
    """Check if name is a registered module (doesn't verify importability)."""
    return name in _MODULE_REGISTRY


def route_module_command(name: str, command: str, args: list[str] | None = None) -> dict:
    """Route a command to a module's drone adapter.

    Returns dict with keys: stdout, stderr, exit_code.
    Raises: KeyError if module not registered, ImportError if adapter missing,
            AttributeError if adapter lacks handle_command.
    """
    adapter_path = _MODULE_REGISTRY[name]
    mod = importlib.import_module(adapter_path)
    handler = getattr(mod, "handle_command")
    return handler(command, args)


def get_module_help(name: str, command: str | None = None) -> str:
    """Get help text from a module's drone adapter.

    Returns help string, or empty string if unavailable.
    """
    adapter_path = _MODULE_REGISTRY.get(name)
    if adapter_path is None:
        return ""
    try:
        mod = importlib.import_module(adapter_path)
        help_fn = getattr(mod, "get_help", None)
        if help_fn is None:
            return ""
        return help_fn(command)
    except (ImportError, AttributeError):
        return ""


def register_module(name: str, adapter_path: str) -> None:
    """Register a new module. Used for dynamic registration (e.g., plugins)."""
    _MODULE_REGISTRY[name] = adapter_path
