# =================== AIPass ====================
# Name: navmap.py
# Version: 1.0.0
# Description: Tier 1 navigation map — periodic prompt injection (UserPromptSubmit)
# Branch: hooks
# Layer: apps/handlers/prompt
# Created: 2026-06-18
# Modified: 2026-06-18
# =============================================

"""Loads .aipass/tier1_navmap.md — richer navigation map injected periodically."""

import os
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger


def _find_project_file(filename: str) -> Path | None:
    """Walk up from CWD to find the nearest .aipass/<filename>."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / ".aipass" / filename
        if candidate.is_file():
            return candidate
        if parent == parent.parent:
            break
    return None


def handle(hook_data: dict) -> dict:
    """Load tier1 navmap — periodic (cadence period 5) + turn 0 + post-compaction."""
    try:
        import importlib

        cadence = importlib.import_module("aipass.hooks.apps.modules.cadence")
        if not cadence.should_fire("navmap", hook_data):
            return {"stdout": "", "exit_code": 0}
    except Exception as exc:
        logger.info("[HOOKS] navmap: cadence check failed, firing anyway: %s", exc)

    try:
        aipass_home = os.environ.get("AIPASS_HOME", "")
        cwd = str(Path.cwd())

        if aipass_home and cwd.startswith(aipass_home):
            prompt_file = Path(aipass_home) / ".aipass" / "tier1_navmap.md"
        else:
            prompt_file = _find_project_file("tier1_navmap.md")

        if not prompt_file or not prompt_file.exists():
            return {"stdout": "", "exit_code": 0}

        content = prompt_file.read_text(encoding="utf-8")
        return {"stdout": content, "exit_code": 0, "sound": "navmap"}

    except Exception as exc:
        logger.info("[HOOKS] navmap: unexpected error: %s", exc)
        return {"stdout": "", "exit_code": 0}
