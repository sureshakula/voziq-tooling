# =================== AIPass ====================
# Name: stop_sound.py
# Version: 1.1.0
# Description: Plays achievement bell + Piper voice on Stop events
# Branch: hooks
# Layer: apps/handlers/notification
# Created: 2026-05-20
# Modified: 2026-05-20
# =============================================

"""Plays achievement bell when the AI finishes responding (Stop event)."""

import os
from pathlib import Path

from aipass.hooks.apps.sound import speak

AIPASS_HOME = Path(os.environ.get("AIPASS_HOME", ""))
SOUNDS_DIR = AIPASS_HOME / ".claude" / "sounds"
SOUND_FILE = SOUNDS_DIR / "mixkit-achievement-bell-600.wav"


def handle(hook_data: dict) -> dict:
    """Play achievement bell and speak hook name on Stop event.

    Args:
        hook_data: Parsed hook event dict from engine.

    Returns:
        Result dict with stdout (empty) and exit_code.
    """
    if hook_data.get("stop_hook_active", False):
        return {"stdout": "", "exit_code": 0}

    speak("stop sound")
    return {"stdout": "", "exit_code": 0}
