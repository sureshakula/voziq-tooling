# =================== AIPass ====================
# Name: loader.py
# Version: 1.0.0
# Description: Hook config loader — finds and parses .aipass/hooks.json
# Branch: hooks
# Layer: apps/handlers/config
# Created: 2026-05-19
# Modified: 2026-05-19
# =============================================

"""Loads per-project hook configuration from .aipass/hooks.json."""

import json
import os
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger

AIPASS_HOME = os.environ.get("AIPASS_HOME", "")


def find_project_config() -> dict | None:
    """Walk up from CWD looking for .aipass/hooks.json."""
    search = Path.cwd()
    home = Path.home()
    while search != home and search.parent != search:
        config = search / ".aipass" / "hooks.json"
        if config.exists():
            try:
                raw = config.read_text(encoding="utf-8")
                if AIPASS_HOME:
                    raw = raw.replace("$AIPASS_HOME", AIPASS_HOME)
                return json.loads(raw)
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("[HOOKS] bad config %s: %s", config, exc)
                return None
        search = search.parent
    return None
