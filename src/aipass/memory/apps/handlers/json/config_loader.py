# =================== AIPass ====================
# Name: config_loader.py
# Description: Unified config loader for memory.config.json
# Version: 1.0.0
# Created: 2026-06-13
# Modified: 2026-06-13
# =============================================

"""
Unified Config Loader

Single entry point for reading memory.config.json.  Replaces the 9
ad-hoc readers that previously loaded the file independently, each
with subtly different defaults and error handling.

Provides a canonical DEFAULT_CONFIG, a non-mutating deep_merge, and a
self-healing load() that guarantees callers always receive a usable dict.

Usage:
    from aipass.memory.apps.handlers.json.config_loader import load, section

    cfg = load()
    rollover = section("rollover")
"""

import copy
import json
from pathlib import Path
from typing import Any

from aipass.memory.apps.handlers.json import json_handler
from aipass.prax import logger

_MEMORY_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_PATH = _MEMORY_ROOT / "memory_json" / "custom_config" / "memory.config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "_meta": {
        "memory_pool": {
            "consumers": ["intake/pool_processor.py", "intake/auto_process.py", "monitor/memory_watcher.py"],
            "purpose": "Vectorize files dropped in memory_pool/, archive beyond keep_recent",
        },
        "rollover": {
            "consumers": [
                "monitor/detector.py",
                "monitor/memory_watcher.py",
                "rollover/extractor.py",
                "templates/pusher.py",
            ],
            "purpose": "Line/entry thresholds that trigger .trinity rollover",
        },
        "plans": {
            "consumers": ["intake/plans_processor.py", "monitor/memory_watcher.py"],
            "purpose": "Vectorize closed plan .md files into ChromaDB",
        },
        "entry_limits": {
            "consumers": ["json/entry_limits.py", "modules/lint.py"],
            "purpose": "Per-entry char caps on .trinity writes (warn-first baseline)",
        },
    },
    "memory_pool": {
        "enabled": True,
        "process_on_startup": False,
        "keep_recent": 0,
        "supported_extensions": [".md", ".txt"],
        "collection_name": "memory_pool_docs",
        "chunk_size": 1000,
        "chunk_overlap": 100,
        "archive_path": "memory_pool_archive",
    },
    "rollover": {
        "defaults": {
            "max_lines": 500,
            "archive_oldest": 100,
        },
        "per_branch": {},
    },
    "plans": {
        "enabled": True,
        "path": ".backup/processed_plans",
        "collection_name": "plans",
        "supported_extensions": [".md"],
    },
    "entry_limits": {
        "enabled": True,
        "enforce": False,
        "entry_types": {
            "key_learnings": {
                "file": "local.json",
                "container": "key_learnings",
                "kind": "dict",
                "field": "value",
                "max_chars": 200,
            },
            "sessions": {
                "file": "local.json",
                "container": "sessions",
                "kind": "list",
                "field": "summary",
                "max_chars": 300,
            },
            "todos": {
                "file": "local.json",
                "container": "todos",
                "kind": "list",
                "field": "task",
                "max_chars": 200,
            },
            "observations": {
                "file": "observations.json",
                "container": "observations",
                "kind": "list",
                "field": "note",
                "max_chars": 600,
            },
        },
        "per_branch": {},
    },
}


def deep_merge(base: dict, overrides: dict) -> dict:
    """Recursively merge *overrides* into *base* without mutating either."""
    result = copy.deepcopy(base)
    for key, val in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = copy.deepcopy(val)
    return result


def load(self_heal: bool = True) -> dict[str, Any]:
    """Load memory.config.json, deep-merged over DEFAULT_CONFIG.

    Args:
        self_heal: If True and the file is missing, create it from defaults.

    Returns:
        The effective config dict (always safe to use).
    """
    if not _CONFIG_PATH.exists():
        if self_heal:
            _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
            logger.info(f"[config_loader] Created default config at {_CONFIG_PATH}")
            json_handler.log_operation(
                "config_load_self_heal",
                {"path": str(_CONFIG_PATH), "action": "created_default"},
                module_name="config_loader",
            )
            return copy.deepcopy(DEFAULT_CONFIG)

        logger.warning(f"[config_loader] Config not found at {_CONFIG_PATH}, using defaults")
        json_handler.log_operation(
            "config_load_missing",
            {"path": str(_CONFIG_PATH)},
            module_name="config_loader",
        )
        return copy.deepcopy(DEFAULT_CONFIG)

    raw = _CONFIG_PATH.read_text(encoding="utf-8")
    try:
        file_config = json.loads(raw)
    except json.JSONDecodeError as exc:
        # Malformed JSON is a red flag — log as error, don't overwrite
        logger.error(f"[config_loader] Malformed JSON in {_CONFIG_PATH}: {exc}")
        json_handler.log_operation(
            "config_load_malformed",
            {"path": str(_CONFIG_PATH), "error": str(exc)},
            module_name="config_loader",
        )
        return copy.deepcopy(DEFAULT_CONFIG)

    merged = deep_merge(DEFAULT_CONFIG, file_config)
    json_handler.log_operation(
        "config_load",
        {"path": str(_CONFIG_PATH)},
        module_name="config_loader",
    )
    return merged


def section(name: str) -> dict[str, Any]:
    """Return a single top-level section from the config, or empty dict."""
    return load().get(name, {})
