"""
Seed Go — Portable, Plugin-Based Code Standards Checker

A standalone framework for defining and enforcing code quality standards
via a plugin system. Zero AIPass dependencies — works with just:

    pip install seed-go

Public API:
    CheckResult   — return type for all plugin check() functions
    CheckItem     — one individual check within a plugin result
    Severity      — ERROR / WARNING / INFO severity levels
    discover_plugins() — find plugins from all sources
    load_config()      — load and resolve .seedgo/config.json

Plugin contract (minimal plugin in ~20 lines):

    PLUGIN_NAME = "my-plugin"
    PLUGIN_DESCRIPTION = "What this plugin checks"
    FILE_TYPES = ["*.py"]

    def check(file_path: str, config: dict | None = None) -> CheckResult:
        ...

Example:

    from seedgo import discover_plugins, load_config, CheckResult

    plugins = discover_plugins(project_root="/path/to/project")
    config = load_config("/path/to/project")
"""

__version__ = "1.0.0"
__author__ = "AIPass"

from .models import CheckResult, CheckItem, Severity
from .discovery import discover_plugins
from .config import load_config
from .runner import run_checks

__all__ = [
    "CheckResult",
    "CheckItem",
    "Severity",
    "discover_plugins",
    "load_config",
    "run_checks",
    "__version__",
]
