"""
AIPass Drone — Command routing & discovery module.

Provides symbolic addressing for multi-agent systems. Resolves @branch names
to absolute paths at runtime via AIPASS_REGISTRY.json.

Core API:
    resolve_branch(name) -> str          # @branch -> absolute path
    list_branches(type, status)          # List all branches
    branch_exists(name) -> bool          # Check if branch exists
    get_branch_info(name) -> dict        # Get branch metadata

Command Routing:
    route_command(target, command, args, timeout) -> CommandResult
    discover_modules(target) -> list     # Available commands for a branch
    get_help(target, command) -> HelpResult

@all Operations:
    route_all(command, args, timeout) -> dict[str, CommandResult]
    get_system_help() -> dict[str, HelpResult]

Registry Management:
    set_registry_path(path)             # Set custom registry location
    get_registry_path() -> Path         # Get current registry path
"""

from aipass.drone.apps.modules.config import get_registry_path, reset_registry_path, set_registry_path
from aipass.drone.apps.modules.discovery import HelpResult, discover_modules, get_help, get_system_help
from aipass.drone.apps.modules import (
    BranchAlreadyExistsError,
    BranchNotFoundError,
    CommandExecutionError,
    CommandResult,
    InvalidPathError,
    RegistryCorruptError,
    RegistryError,
    RegistryNotFoundError,
    RegistryPermissionError,
    RoutingError,
)
from aipass.drone.apps.modules.resolver import branch_exists, get_branch_info, list_branches, resolve_branch
from aipass.drone.apps.modules.router import route_all, route_command

__version__ = "1.0.0"

__all__ = [
    # Core API
    "resolve_branch",
    "list_branches",
    "branch_exists",
    "get_branch_info",
    # Command routing
    "route_command",
    "discover_modules",
    "get_help",
    "CommandResult",
    # Help & discovery
    "HelpResult",
    "get_system_help",
    "route_all",
    # Registry management
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
