"""
AIPass Routing & Discovery Module.

Provides symbolic addressing for multi-agent systems. Resolves @branch names
to absolute paths at runtime.

Core API:
    resolve_branch(name) -> str          # @branch → absolute path
    register_branch(name, path, type)    # Add branch to registry
    list_branches(type, status)          # List all branches
    branch_exists(name) -> bool          # Check if branch exists
    get_branch_info(name) -> dict        # Get branch metadata

Command Routing (Phase 2):
    route_command(target, command, args, timeout) -> CommandResult
    discover_modules(target) -> list     # Available commands for a branch
    get_help(target, command) -> HelpResult  # Structured help for a branch

@all Operations (Phase 3):
    route_all(command, args, timeout) -> dict[str, CommandResult]
    get_system_help() -> dict[str, HelpResult]  # Help across all branches

Registry Management:
    initialize_registry()                # Create empty registry
    set_registry_path(path)             # Set custom registry location
    get_registry_path() -> Path         # Get current registry path

Example:
    >>> from aipass.routing import resolve_branch, register_branch
    >>> register_branch("my_agent", "/path/to/agent", "agent")
    >>> path = resolve_branch("@my_agent")
    >>> print(path)
    /path/to/agent

    >>> from aipass.routing import route_command
    >>> result = route_command("@my_agent", "status")
    >>> print(result.stdout)

    >>> from aipass.routing import route_all
    >>> results = route_all("status")
    >>> for branch, r in results.items():
    ...     print(f"{branch}: exit={r.exit_code}")
"""

from .config import get_registry_path, reset_registry_path, set_registry_path
from .discovery import HelpResult, discover_modules, get_help, get_system_help
from .exceptions import (
    BranchAlreadyExistsError,
    BranchNotFoundError,
    CommandExecutionError,
    InvalidPathError,
    RegistryCorruptError,
    RegistryError,
    RegistryNotFoundError,
    RegistryPermissionError,
    RoutingError,
)
from .executor import CommandResult
from .registry import add_branch as register_branch
from .registry import initialize_registry
from .resolver import branch_exists, get_branch_info, list_branches, resolve_branch
from .router import route_all, route_command

__version__ = "1.0.0"

__all__ = [
    # Core API
    "resolve_branch",
    "register_branch",
    "list_branches",
    "branch_exists",
    "get_branch_info",
    # Command routing (Phase 2)
    "route_command",
    "discover_modules",
    "get_help",
    "CommandResult",
    # Help & discovery (Phase 3)
    "HelpResult",
    "get_system_help",
    "route_all",
    # Registry management
    "initialize_registry",
    "set_registry_path",
    "get_registry_path",
    "reset_registry_path",
    # Exceptions
    "RoutingError",
    "BranchNotFoundError",
    "BranchAlreadyExistsError",
    "InvalidPathError",
    "RegistryError",
    "RegistryNotFoundError",
    "RegistryCorruptError",
    "RegistryPermissionError",
    "CommandExecutionError",
]
