# =================== AIPass ====================
# Name: json_handler.py
# Description: JSON auto-creating handler for hooks data files
# Version: 1.0.0
# Created: 2026-07-15
# Modified: 2026-07-15
# =============================================

"""JSON auto-creating handler for hooks data files."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
import inspect

from aipass.prax.apps.modules.logger import system_logger as logger

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    for _stream in (sys.stdout, sys.stderr):
        _reconfigure = getattr(_stream, "reconfigure", None)
        if _reconfigure is not None:
            _reconfigure(encoding="utf-8", errors="replace")

_BRANCH_ROOT = Path(__file__).resolve().parents[3]
_BRANCH_NAME = _BRANCH_ROOT.name
JSON_DIR = _BRANCH_ROOT / f"{_BRANCH_NAME}_json"


def _get_caller_module_name() -> str:
    """Auto-detect calling module name from call stack."""
    stack = inspect.stack()
    if len(stack) > 2:
        caller_frame = stack[2]
        caller_path = Path(caller_frame.filename)
        module_name = caller_path.stem
        if module_name and not module_name.startswith("_"):
            return module_name
    return "unknown"


def _create_default(json_type: str, module_name: str) -> Any:
    """Create default JSON structure from inline code defaults."""
    today = datetime.now().date().isoformat()
    if json_type == "config":
        return {
            "module_name": module_name,
            "version": "1.0.0",
            "config": {"max_log_entries": 100},
            "created": today,
        }
    elif json_type == "data":
        return {
            "module_name": module_name,
            "created": today,
            "last_updated": today,
        }
    elif json_type == "log":
        return []
    raise ValueError(f"Unknown json_type: {json_type}")


def validate_json_structure(data: Any, json_type: str) -> bool:
    """Validate JSON structure matches expected type."""
    if json_type == "config":
        return isinstance(data, dict) and all(k in data for k in ["module_name", "version", "config"])
    elif json_type == "data":
        return isinstance(data, dict) and all(k in data for k in ["created", "last_updated"])
    elif json_type == "log":
        return isinstance(data, list)
    return False


def get_json_path(module_name: str, json_type: str) -> Path:
    """Get path for module JSON file."""
    return JSON_DIR / f"{module_name}_{json_type}.json"


def ensure_json_exists(module_name: str, json_type: str) -> bool:
    """Ensure JSON file exists, create from template if missing."""
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    json_path = get_json_path(module_name, json_type)
    if json_path.exists():
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if validate_json_structure(data, json_type):
                return True
        except Exception as exc:
            logger.warning("[HOOKS] json_handler: ensure_json_exists failed for %s_%s: %s", module_name, json_type, exc)
    template = _create_default(json_type, module_name)
    json_path.write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def load_json(module_name: str, json_type: str) -> Any | None:
    """Load JSON file, auto-create if missing."""
    if not ensure_json_exists(module_name, json_type):
        return None
    json_path = get_json_path(module_name, json_type)
    return json.loads(json_path.read_text(encoding="utf-8"))


def save_json(module_name: str, json_type: str, data: Any) -> bool:
    """Save JSON file."""
    json_path = get_json_path(module_name, json_type)
    if not validate_json_structure(data, json_type):
        raise ValueError(f"Invalid structure for {json_type} JSON")
    if json_type == "data" and isinstance(data, dict):
        data["last_updated"] = datetime.now().date().isoformat()
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def ensure_module_jsons(module_name: str) -> bool:
    """Ensure all 3 JSON files exist for a module."""
    ensure_json_exists(module_name, "config")
    ensure_json_exists(module_name, "data")
    ensure_json_exists(module_name, "log")
    return True


def log_operation(
    operation: str,
    data: dict[str, Any] | None = None,
    module_name: str | None = None,
) -> bool:
    """Add entry to module log with automatic rotation.

    Auto-detects calling module if module_name not provided.
    """
    if module_name is None:
        module_name = _get_caller_module_name()
    ensure_module_jsons(module_name)

    config = load_json(module_name, "config")
    max_entries = 100
    if config and "config" in config:
        max_entries = config["config"].get("max_log_entries", 100)

    log = load_json(module_name, "log")
    if log is None:
        log = []

    entry: dict[str, Any] = {"timestamp": datetime.now().isoformat(), "operation": operation}
    if data:
        entry["data"] = data

    log.append(entry)
    if len(log) > max_entries:
        log = log[-max_entries:]

    return save_json(module_name, "log", log)


def read_json_file(path: Path) -> Any:
    """Read and parse a JSON file at an arbitrary path."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_file(path: Path, data: Any) -> None:
    """Write data as JSON to an arbitrary path."""
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
