# =================== AIPass ====================
# Name: bridge_handler.py
# Description: Hook bridge — settings.json I/O for hook installation
# Version: 1.0.0
# Created: 2026-04-22
# Modified: 2026-04-22
# =============================================

"""Hook bridge handler — reads/writes Claude Code settings.json for hook management.

Provides AIPASS_HOME resolution, hook manifest, install/uninstall logic.
The module layer (hook_bridge.py) handles command routing and display.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from aipass.prax import logger
from aipass.seedgo.apps.handlers.json import json_handler


# ---------------------------------------------------------------------------
# AIPASS_HOME resolution
# ---------------------------------------------------------------------------


def resolve_aipass_home() -> Path | None:
    """Resolve AIPASS_HOME from env var or importlib fallback."""
    env_home = os.environ.get("AIPASS_HOME")
    if env_home:
        p = Path(env_home)
        if p.is_dir():
            return p
    try:
        import importlib.util

        spec = importlib.util.find_spec("aipass")
        if spec and spec.submodule_search_locations:
            pkg_dir = Path(list(spec.submodule_search_locations)[0])
            project_root = pkg_dir.parents[1]
            if (project_root / ".aipass").exists():
                return project_root
    except Exception as exc:
        logger.info("bridge_handler: importlib fallback failed: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Settings I/O
# ---------------------------------------------------------------------------


def read_settings(path: Path) -> dict:
    """Read and parse settings.json. Returns {} on failure."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("bridge_handler: could not read %s: %s", path, exc)
        return {}


def write_settings(path: Path, data: dict) -> bool:
    """Write settings.json with backup and pretty formatting."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            shutil.copy2(path, path.with_suffix(".json.bak"))
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return True
    except Exception as exc:
        logger.warning("bridge_handler: could not write %s: %s", path, exc)
        return False


# ---------------------------------------------------------------------------
# Hook detection
# ---------------------------------------------------------------------------

_AIPASS_COMMAND_MARKERS = (
    "AIPass/.claude/hooks/",
    "$AIPASS_HOME",
    "aipass_global_prompt",
    "aipass/hooks/apps/handlers/bridges/claude.py",
)


def is_aipass_hook_entry(entry: dict) -> bool:
    """Check if a hook entry is an AIPass hook (marked or pattern-matched)."""
    if entry.get("_aipass"):
        return True
    for hook in entry.get("hooks", []):
        cmd = hook.get("command", "")
        if any(marker in cmd for marker in _AIPASS_COMMAND_MARKERS):
            return True
    return False


def count_aipass_hooks(settings: dict) -> int:
    """Count AIPass hook entries across all events."""
    count = 0
    for entries in settings.get("hooks", {}).values():
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and is_aipass_hook_entry(entry):
                    count += 1
    return count


# ---------------------------------------------------------------------------
# Hook manifest — the canonical set of AIPass hooks
# ---------------------------------------------------------------------------

_BRIDGE = "$AIPASS_HOME/.venv/bin/python3 $AIPASS_HOME/src/aipass/hooks/apps/handlers/bridges/claude.py"

AIPASS_HOOK_MANIFEST: dict[str, list[dict]] = {
    "UserPromptSubmit": [
        {
            "_aipass": True,
            "hooks": [{"type": "command", "command": f"{_BRIDGE} UserPromptSubmit:global_prompt"}],
        },
        {
            "_aipass": True,
            "hooks": [{"type": "command", "command": f"{_BRIDGE} UserPromptSubmit:branch_prompt"}],
        },
        {
            "_aipass": True,
            "hooks": [{"type": "command", "command": f"{_BRIDGE} UserPromptSubmit:identity_injector"}],
        },
        {
            "_aipass": True,
            "hooks": [{"type": "command", "command": f"{_BRIDGE} UserPromptSubmit:email_notification"}],
        },
    ],
    "PreToolUse": [
        {
            "_aipass": True,
            "matcher": "Bash|Edit|MultiEdit|Write|Read|Grep|Glob|WebSearch|WebFetch|Task",
            "hooks": [{"type": "command", "command": f"{_BRIDGE} PreToolUse"}],
        },
    ],
    "PostToolUse": [
        {
            "_aipass": True,
            "matcher": "Bash|Edit|MultiEdit|Write|NotebookEdit",
            "hooks": [{"type": "command", "command": f"{_BRIDGE} PostToolUse"}],
        },
    ],
    "SubagentStop": [
        {
            "_aipass": True,
            "hooks": [{"type": "command", "command": f"{_BRIDGE} SubagentStop"}],
        },
    ],
    "Stop": [
        {
            "_aipass": True,
            "hooks": [{"type": "command", "command": f"{_BRIDGE} Stop"}],
        },
    ],
    "Notification": [
        {
            "_aipass": True,
            "hooks": [{"type": "command", "command": f"{_BRIDGE} Notification"}],
        },
    ],
    "PreCompact": [
        {
            "_aipass": True,
            "matcher": "manual",
            "hooks": [{"type": "command", "command": f"{_BRIDGE} PreCompact:pre_compact", "timeout": 60}],
        },
        {
            "_aipass": True,
            "matcher": "auto",
            "hooks": [{"type": "command", "command": f"{_BRIDGE} PreCompact:pre_compact", "timeout": 60}],
        },
        {
            "_aipass": True,
            "matcher": "manual",
            "hooks": [{"type": "command", "command": f"{_BRIDGE} PreCompact:pre_compact_rollover", "timeout": 120}],
        },
        {
            "_aipass": True,
            "matcher": "auto",
            "hooks": [{"type": "command", "command": f"{_BRIDGE} PreCompact:pre_compact_rollover", "timeout": 120}],
        },
    ],
}


# ---------------------------------------------------------------------------
# Install / uninstall
# ---------------------------------------------------------------------------


def ensure_aipass_env(settings: dict, aipass_home: str) -> bool:
    """Ensure AIPASS_HOME is in the env section. Returns True if added."""
    env = settings.setdefault("env", {})
    if "AIPASS_HOME" in env:
        return False
    env["AIPASS_HOME"] = aipass_home
    return True


def install_hooks(settings: dict) -> tuple[dict, int]:
    """Add AIPass hooks to settings. Skips events that already have AIPass entries."""
    hooks = settings.setdefault("hooks", {})
    added = 0
    for event_name, manifest_entries in AIPASS_HOOK_MANIFEST.items():
        existing = hooks.get(event_name, [])
        if not isinstance(existing, list):
            existing = []
        has_aipass = any(is_aipass_hook_entry(e) for e in existing if isinstance(e, dict))
        if has_aipass:
            continue
        existing.extend(manifest_entries)
        hooks[event_name] = existing
        added += len(manifest_entries)
    json_handler.log_operation("bridge_install_hooks", {"added": added})
    return settings, added


def uninstall_hooks(settings: dict) -> tuple[dict, int]:
    """Remove AIPass hook entries only. Preserves all non-AIPass entries."""
    hooks = settings.get("hooks", {})
    removed = 0
    for event_name in list(hooks.keys()):
        entries = hooks[event_name]
        if not isinstance(entries, list):
            continue
        filtered = []
        for entry in entries:
            if isinstance(entry, dict) and is_aipass_hook_entry(entry):
                removed += 1
            else:
                filtered.append(entry)
        if filtered:
            hooks[event_name] = filtered
        else:
            del hooks[event_name]
    json_handler.log_operation("bridge_uninstall_hooks", {"removed": removed})
    return settings, removed
