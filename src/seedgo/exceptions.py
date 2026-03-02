"""
Seed Go Exception Hierarchy

Defines all custom exceptions for the seedgo package.
All exceptions inherit from SeedGoError for easy catch-all handling.
"""


class SeedGoError(Exception):
    """Base exception for all seedgo errors.

    Catch this to handle any seedgo-specific failure without caring
    about the specific cause.
    """


class ConfigError(SeedGoError):
    """Raised when config loading or parsing fails.

    Covers missing required fields, invalid JSON, schema violations,
    and unresolvable profile references.
    """


class PluginError(SeedGoError):
    """Raised when a plugin fails to load or execute.

    Covers import failures, missing required attributes (PLUGIN_NAME,
    check function), and runtime errors during check execution.
    """


class DiscoveryError(SeedGoError):
    """Raised when plugin discovery encounters an unrecoverable error.

    Note: Individual broken plugins are silently skipped during discovery.
    This exception is only raised when the discovery process itself fails
    (e.g., the plugins directory is unreadable).
    """
