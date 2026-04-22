# =================== AIPass ====================
# Name: json_handler.py
# Description: JSON file read/write and operation logging for spawn
# Version: 2.0.0
# Created: 2026-03-07
# Modified: 2026-04-22
# =============================================

"""JSON handler for spawn module.

Provides JSON I/O utilities, validation, and operation logging
for the three-JSON system (config, data, log).
"""

import inspect
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from aipass.prax import logger

_SPAWN_ROOT = Path(__file__).resolve().parents[3]
_JSON_DIR = _SPAWN_ROOT / "spawn_json"

_JSON_TYPES: tuple[str, ...] = ("config", "data", "log")
MAX_LOG_ENTRIES = 100


def _today() -> str:
    """Return today's date as ISO string."""
    return datetime.now().date().isoformat()


def read_json(file_path: Path) -> Optional[dict]:
    """Read and parse a JSON file."""
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.warning("Failed to read JSON from %s: %s", file_path, e)
        return None


def write_json(file_path: Path, data: Any, indent: int = 2) -> bool:
    """Write data to a JSON file."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(data, indent=indent) + "\n", encoding="utf-8")
        return True
    except OSError as e:
        logger.error("Failed to write JSON to %s: %s", file_path, e)
        return False


def _create_default(json_type: str, module_name: str) -> Any:
    """Return default content for a given JSON type.

    Args:
        json_type: One of "config", "data", "log".
        module_name: Logical module name.

    Returns:
        Default data structure.

    Raises:
        ValueError: For unknown json_type.
    """
    today = _today()
    if json_type == "config":
        return {
            "module_name": module_name,
            "version": "1.0.0",
            "config": {
                "max_log_entries": MAX_LOG_ENTRIES,
            },
            "created": today,
            "last_updated": today,
        }
    if json_type == "data":
        return {
            "created": today,
            "last_updated": today,
        }
    if json_type == "log":
        return []
    raise ValueError(f"Unknown json_type: {json_type!r}")


def validate_json_structure(data: Any, json_type: str) -> bool:
    """Validate that data matches the expected shape for json_type.

    Args:
        data: Parsed JSON data to validate.
        json_type: One of "config", "data", "log".

    Returns:
        True when the structure is valid, False otherwise.
    """
    if json_type == "config":
        if not isinstance(data, dict):
            return False
        return all(key in data for key in ("module_name", "version", "config"))
    if json_type == "data":
        if not isinstance(data, dict):
            return False
        return all(key in data for key in ("created", "last_updated"))
    if json_type == "log":
        return isinstance(data, list)
    return False


def get_json_path(module_name: str, json_type: str) -> Path:
    """Return the filesystem path for a module's JSON file.

    Args:
        module_name: Logical module name.
        json_type: One of "config", "data", "log".

    Returns:
        Absolute Path to the JSON file.
    """
    return _JSON_DIR / f"{module_name}_{json_type}.json"


def ensure_json_exists(module_name: str, json_type: str) -> bool:
    """Ensure a single JSON file exists; create with defaults if missing.

    If the file exists but fails validation it is regenerated.

    Args:
        module_name: Logical module name.
        json_type: One of "config", "data", "log".

    Returns:
        True after the file is confirmed present and valid.
    """
    _JSON_DIR.mkdir(parents=True, exist_ok=True)
    json_path = get_json_path(module_name, json_type)

    if json_path.exists():
        try:
            if json_path.stat().st_size == 0:
                logger.warning("ensure_json_exists: empty file at %s, regenerating", json_path)
            else:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                if validate_json_structure(data, json_type):
                    return True
        except Exception as exc:
            logger.warning("ensure_json_exists: failed to read %s, regenerating: %s", json_path, exc)

    default = _create_default(json_type, module_name)
    write_json(json_path, default)
    return True


def ensure_module_jsons(module_name: str) -> bool:
    """Ensure all three JSON files (config, data, log) exist for a module.

    Args:
        module_name: Logical module name.

    Returns:
        True when all files are present and valid.
    """
    for json_type in _JSON_TYPES:
        ensure_json_exists(module_name, json_type)
    return True


def load_json(module_name: str, json_type: str) -> Any | None:
    """Load a module's JSON file, auto-creating it if missing.

    Args:
        module_name: Logical module name.
        json_type: One of "config", "data", "log".

    Returns:
        Parsed JSON data, or None on failure.
    """
    if not ensure_json_exists(module_name, json_type):
        return None

    json_path = get_json_path(module_name, json_type)
    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("load_json: failed to read %s: %s", json_path, exc)
        return _create_default(json_type, module_name)


def save_json(module_name: str, json_type: str, data: Any) -> bool:
    """Write data to a module's JSON file after validation.

    For "data" type files the last_updated field is refreshed automatically.

    Args:
        module_name: Logical module name.
        json_type: One of "config", "data", "log".
        data: The data structure to persist.

    Returns:
        True on success.

    Raises:
        ValueError: When data fails structure validation.
    """
    if not validate_json_structure(data, json_type):
        raise ValueError(f"Invalid structure for {json_type} JSON")

    if json_type == "data" and isinstance(data, dict):
        data["last_updated"] = _today()

    json_path = get_json_path(module_name, json_type)
    return write_json(json_path, data)


def _get_caller_module_name() -> str:
    """Auto-detect calling module name from call stack."""
    stack = inspect.stack()
    if len(stack) > 2:
        caller_path = Path(stack[2].filename)
        module_name = caller_path.stem
        if module_name and not module_name.startswith("_"):
            return module_name
    return "unknown"


def log_operation(operation: str, data: Dict[str, Any] | None = None, module_name: str | None = None) -> bool:
    """Add entry to module operation log with automatic rotation.

    Auto-detects calling module if module_name not provided.

    Args:
        operation: Operation name to log.
        data: Optional data dict.
        module_name: Optional module name (auto-detected if not provided).

    Returns:
        True if successful, False otherwise.
    """
    if module_name is None:
        module_name = _get_caller_module_name()

    try:
        ensure_module_jsons(module_name)

        log = load_json(module_name, "log")
        if log is None:
            log = []

        entry: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
        }
        if data:
            entry["data"] = data

        log.append(entry)

        if len(log) > MAX_LOG_ENTRIES:
            log = log[-MAX_LOG_ENTRIES:]

        return save_json(module_name, "log", log)
    except Exception as exc:
        logger.warning("log_operation: failed for %s/%s: %s", module_name, operation, exc)
        return False
