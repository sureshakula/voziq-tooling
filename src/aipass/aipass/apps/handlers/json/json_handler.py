# =================== AIPass ====================
# Name: json_handler.py
# Description: Branch-local shim — delegates to aipass.aipass.shared.json_handler
# Version: 2.0.0
# Created: 2026-04-16
# Modified: 2026-06-06
# =============================================

"""Branch-local JSON handler — thin shim over the shared ``aipass.aipass.shared`` library.

All logic lives in ``aipass.aipass.shared.json_handler.JsonHandler``.
This module binds a ``JsonHandler`` instance to the aipass branch's
``aipass_json/`` directory and re-exports the public API as module-level
functions so existing callers (``json_handler.log_operation(...)``) keep working.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, Dict, Optional

from aipass.aipass.shared.json_handler import JsonHandler


def _get_caller_module_name() -> str:
    """Auto-detect calling module name from call stack."""
    stack = inspect.stack()
    if len(stack) > 2:
        caller_path = Path(stack[2].filename)
        module_name = caller_path.stem
        if module_name and not module_name.startswith("_"):
            return module_name
    return "unknown"


_PKG_ROOT = Path(__file__).resolve().parents[4]

AIPASS_BRANCH_ROOT = _PKG_ROOT / "aipass"
AIPASS_JSON_DIR = AIPASS_BRANCH_ROOT / "aipass_json"


def _handler() -> JsonHandler:
    """Create a handler bound to the current AIPASS_JSON_DIR."""
    return JsonHandler(AIPASS_JSON_DIR)


def load_path(file_path: Path) -> Optional[dict]:
    """Load JSON from an arbitrary file path."""
    return JsonHandler.read_json(file_path)


def save_path(file_path: Path, data: Any, indent: int = 2) -> bool:
    """Write JSON data to an arbitrary file path atomically."""
    return JsonHandler.write_json(file_path, data, indent)


def validate_json_structure(data: Any, json_type: str) -> bool:
    """Validate that data matches the expected shape for json_type."""
    return JsonHandler.validate_json_structure(data, json_type)


def get_json_path(module_name: str, json_type: str) -> Path:
    """Return the filesystem path for a module's JSON file."""
    return _handler().get_json_path(module_name, json_type)


def ensure_json_exists(module_name: str, json_type: str) -> bool:
    """Ensure a single JSON file exists; create with defaults if missing."""
    return _handler().ensure_json_exists(module_name, json_type)


def ensure_module_jsons(module_name: str) -> bool:
    """Ensure all three JSON files (config, data, log) exist for a module."""
    return _handler().ensure_module_jsons(module_name)


def load_json(module_name: str, json_type: str) -> Optional[Any]:
    """Load a module's JSON file, auto-creating it if missing."""
    return _handler().load_json(module_name, json_type)


def save_json(module_name: str, json_type: str, data: Any) -> bool:
    """Save JSON file. Raises ValueError on invalid structure."""
    return _handler().save_json(module_name, json_type, data)


def log_operation(
    operation: str,
    data: Dict[str, Any] | None = None,
    module_name: str | None = None,
) -> bool:
    """Add entry to module operation log with automatic rotation."""
    if module_name is None:
        module_name = _get_caller_module_name()
    return _handler().log_operation(operation, data, module_name)
