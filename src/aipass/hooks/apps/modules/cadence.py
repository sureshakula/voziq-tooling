# =================== AIPass ====================
# Name: cadence.py
# Version: 1.0.0
# Description: Per-session turn counter for prompt injection cadence (DPLAN-0200)
# Branch: hooks
# Layer: apps/modules
# Created: 2026-06-08
# Modified: 2026-06-08
# =============================================

"""Turn counter for prompt injection cadence — fires loaders every Nth turn."""

import json
import os
from pathlib import Path

from aipass.cli.apps.modules import err_console
from aipass.prax.apps.modules.logger import system_logger as logger

CONSOLE = err_console

_GUARD_DIR = Path("/tmp")
_BRANCH_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_PATH = _BRANCH_ROOT / "hooks_json" / "custom_config" / "cadence_config.json"

HELP_COMMANDS = [
    ("cadence", "Show prompt injection cadence config and state"),
]

DEFAULTS = {
    "enabled": True,
    "period": 5,
    "loaders": {
        "global": {"offset": 0},
        "branch": {"offset": 0},
    },
}

_turn: int | None = None
_config: dict | None = None


def _deep_merge(base: dict, updates: dict) -> dict:
    """Deep merge updates into base (modifies base in-place)."""
    for key, value in updates.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _load_config() -> dict:
    global _config
    if _config is not None:
        return _config

    import copy

    result = copy.deepcopy(DEFAULTS)

    if _CONFIG_PATH.is_file():
        try:
            overrides = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            _deep_merge(result, overrides)
        except (json.JSONDecodeError, OSError) as exc:
            logger.info("[HOOKS] cadence: config load failed, using defaults: %s", exc)

    _config = result
    return result


def _state_path() -> Path | None:
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    if not session_id:
        return None
    return _GUARD_DIR / f"aipass-cadence-{session_id}.json"


def _load_and_increment() -> int:
    """Load turn counter from /tmp, increment, write back. Cached per-process."""
    global _turn
    if _turn is not None:
        return _turn

    path = _state_path()
    if path is None:
        _turn = 0
        return 0

    count = 0
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            count = data.get("turn", 0) + 1
        except (json.JSONDecodeError, OSError) as exc:
            logger.info("[HOOKS] cadence: state read failed, resetting: %s", exc)
            count = 0

    try:
        path.write_text(json.dumps({"turn": count}), encoding="utf-8")
    except OSError as exc:
        logger.info("[HOOKS] cadence: state write failed: %s", exc)

    _turn = count
    return count


def should_fire(loader_name: str) -> bool:
    """Check if a loader should fire this turn. Always True on turn 0 or if cadence disabled."""
    config = _load_config()

    if not config.get("enabled", True):
        return True

    period = config.get("period", 5)
    if period <= 0:
        return True

    loader_config = config.get("loaders", {}).get(loader_name, {})
    offset = loader_config.get("offset", 0)

    turn = _load_and_increment()

    if turn == 0:
        return True

    return (turn % period) == offset


def reset_counter() -> None:
    """Reset counter to -1 so next turn reads 0 (all loaders fire). Called from PreCompact."""
    path = _state_path()
    if path is None:
        return
    try:
        path.write_text(json.dumps({"turn": -1}), encoding="utf-8")
        logger.info("[HOOKS] cadence: counter reset for post-compact re-injection")
    except OSError as exc:
        logger.info("[HOOKS] cadence: reset write failed: %s", exc)


# =============================================================================
# MODULE INTERFACE (drone @hooks routing)
# =============================================================================


def print_introspection() -> None:
    """Print cadence config and current state."""
    config = _load_config()
    CONSOLE.print("[bold cyan]cadence[/bold cyan] Module")
    CONSOLE.print(f"  Enabled: {config.get('enabled', True)}")
    CONSOLE.print(f"  Period: {config.get('period', 5)} turns")
    loaders = config.get("loaders", {})
    for name, lcfg in loaders.items():
        CONSOLE.print(f"  Loader '{name}': offset={lcfg.get('offset', 0)}")
    path = _state_path()
    if path and path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            CONSOLE.print(f"  Current turn: {data.get('turn', '?')}")
        except (json.JSONDecodeError, OSError) as exc:
            logger.info("[HOOKS] cadence: state read for introspection failed: %s", exc)
            CONSOLE.print("  Current turn: (unreadable)")
    else:
        CONSOLE.print("  Current turn: (no state file)")
    CONSOLE.print(f"  Config file: {_CONFIG_PATH}")


def handle_command(command: str, args: list) -> bool:
    """Route cadence commands from drone @hooks."""
    if command in ("--help", "-h", "help"):
        CONSOLE.print("[bold cyan]cadence[/bold cyan] — Prompt injection cadence control")
        CONSOLE.print()
        CONSOLE.print("  drone @hooks cadence    Show cadence config and current turn state")
        return True

    if command == "cadence":
        if not args:
            print_introspection()
            return True
    return False
