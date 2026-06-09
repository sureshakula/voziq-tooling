# =================== AIPass ====================
# Name: global_loader.py
# Version: 1.0.0
# Description: Loads AIPass global prompt for injection (UserPromptSubmit)
# Branch: hooks
# Layer: apps/handlers/prompt
# Created: 2026-05-22
# Modified: 2026-05-22
# =============================================

"""Loads .aipass/aipass_global_prompt.md from AIPASS_HOME for prompt injection."""

import os
from pathlib import Path

from aipass.hooks.apps.sound import speak
from aipass.prax.apps.modules.logger import system_logger as logger


def _find_project_prompt() -> Path | None:
    """Walk up from CWD to find the nearest .aipass/aipass_global_prompt.md."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / ".aipass" / "aipass_global_prompt.md"
        if candidate.is_file():
            return candidate
        if parent == parent.parent:
            break
    return None


def handle(hook_data: dict) -> dict:
    """Load global prompt — project-local if outside AIPass, AIPass-internal if inside."""
    speak("global prompt")

    try:
        import importlib

        cadence = importlib.import_module("aipass.hooks.apps.modules.cadence")
        if not cadence.should_fire("global"):
            return {"stdout": "", "exit_code": 0}
    except Exception as exc:
        logger.info("[HOOKS] global_loader: cadence check failed, firing anyway: %s", exc)

    try:
        aipass_home = os.environ.get("AIPASS_HOME", "")
        cwd = str(Path.cwd())

        if aipass_home and cwd.startswith(aipass_home):
            prompt_file = Path(aipass_home) / ".aipass" / "aipass_global_prompt.md"
        else:
            prompt_file = _find_project_prompt()

        if not prompt_file or not prompt_file.exists():
            return {"stdout": "", "exit_code": 0}

        content = prompt_file.read_text(encoding="utf-8")
        return {"stdout": content, "exit_code": 0}

    except Exception as exc:
        logger.info("[HOOKS] global_loader: unexpected error: %s", exc)
        return {"stdout": "", "exit_code": 0}
