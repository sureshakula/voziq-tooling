# =================== AIPass ====================
# Name: __init__.py
# Description: Scanning handler package for module command discovery
# Version: 1.0.0
# Created: 2026-03-17
# Modified: 2026-03-17
# =============================================

"""Scanning handler package -- discovers available commands in branches."""

from aipass.drone.apps.handlers.scanning.scanner import (
    scan_branch,
    scan_help_output,
    scan_module_files,
)
from aipass.drone.apps.handlers.scanning.formatters import (
    format_no_commands,
    format_scan_results,
)

__all__ = [
    "format_no_commands",
    "format_scan_results",
    "scan_branch",
    "scan_help_output",
    "scan_module_files",
]
