"""
Routing module custom exceptions.

Defines the exception hierarchy for routing and branch resolution errors.
"""


class RoutingError(Exception):
    """Base exception for all routing-related errors."""
    pass


class BranchNotFoundError(RoutingError):
    """Raised when a branch cannot be found in the registry."""
    pass


class BranchAlreadyExistsError(RoutingError):
    """Raised when attempting to register a branch that already exists."""
    pass


class InvalidPathError(RoutingError):
    """Raised when a path is invalid or doesn't exist."""
    pass


class RegistryError(RoutingError):
    """Base exception for registry-related errors."""
    pass


class RegistryNotFoundError(RegistryError):
    """Raised when the registry file doesn't exist."""
    pass


class RegistryCorruptError(RegistryError):
    """Raised when the registry file is corrupted or invalid JSON."""
    pass


class RegistryPermissionError(RegistryError):
    """Raised when there are permission issues accessing the registry."""
    pass


class CommandExecutionError(RoutingError):
    """Raised when command execution fails (Phase 2 feature)."""
    pass
