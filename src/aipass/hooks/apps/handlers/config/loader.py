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
    """Walk up from CWD looking for .aipass/hooks.json, with trust verification."""
    from aipass.hooks.apps.handlers.config.trust_registry import (
        REGISTRY_PATH,
        bootstrap,
        is_trusted,
    )

    search = Path.cwd()
    home = Path.home()
    while search != home and search.parent != search:
        config_file = search / ".aipass" / "hooks.json"
        if config_file.exists():
            project_dir = str(search)

            if not REGISTRY_PATH.exists():
                bootstrap()

            if not is_trusted(project_dir):
                logger.warning(
                    "[HOOKS] project not enrolled in trust registry: %s (run: aipass init update)",
                    project_dir,
                )
                return None

            try:
                raw = config_file.read_text(encoding="utf-8")
                if AIPASS_HOME:
                    raw = raw.replace("$AIPASS_HOME", AIPASS_HOME)
                parsed = json.loads(raw)
                parsed["_source"] = "project"
                return parsed
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("[HOOKS] bad config %s: %s", config_file, exc)
                return None
        search = search.parent
    return None
