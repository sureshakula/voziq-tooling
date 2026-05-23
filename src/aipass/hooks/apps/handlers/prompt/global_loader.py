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


def handle(hook_data: dict) -> dict:
    """Load AIPass global prompt from AIPASS_HOME."""
    speak("global prompt")

    try:
        aipass_home = os.environ.get("AIPASS_HOME", "")
        if not aipass_home:
            return {"stdout": "", "exit_code": 0}

        prompt_file = Path(aipass_home) / ".aipass" / "aipass_global_prompt.md"
        if not prompt_file.exists():
            return {"stdout": "", "exit_code": 0}

        content = prompt_file.read_text(encoding="utf-8")
        return {"stdout": content, "exit_code": 0}

    except Exception as exc:
        logger.info("[HOOKS] global_loader: unexpected error: %s", exc)
        return {"stdout": "", "exit_code": 0}
