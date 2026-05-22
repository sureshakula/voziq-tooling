# =================== AIPass ====================
# Name: auto_watchdog.py
# Version: 1.0.0
# Description: Reminds agent to arm watchdog after dispatch (PostToolUse)
# Branch: hooks
# Layer: apps/handlers/lifecycle
# Created: 2026-05-21
# Modified: 2026-05-21
# =============================================

"""Checks for dispatch commands and reminds the agent to arm the watchdog."""

import json
import subprocess
import tempfile
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger

PIPER_BIN = Path.home() / ".local" / "share" / "piper" / "piper"
PIPER_VOICE = Path.home() / ".local" / "share" / "piper-voices" / "en_US-amy-medium.onnx"


def _speak(text: str) -> None:
    if not PIPER_BIN.exists() or not PIPER_VOICE.exists():
        return
    try:
        wav_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav_path = wav_file.name
        wav_file.close()
        result = subprocess.run(
            [str(PIPER_BIN), "-m", str(PIPER_VOICE), "-f", wav_path],
            input=text,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and Path(wav_path).exists():
            subprocess.Popen(["aplay", "-q", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.info("[HOOKS] auto_watchdog: speak error: %s", exc)


def handle(hook_data: dict) -> dict:
    """Return additionalContext reminder if dispatch detected without watchdog.

    Args:
        hook_data: Parsed hook event dict from engine.

    Returns:
        Result dict with stdout (JSON additionalContext or empty) and exit_code.
    """
    tool_name = hook_data.get("tool_name", "")
    if tool_name != "Bash":
        return {"stdout": "", "exit_code": 0}

    command = hook_data.get("tool_input", {}).get("command", "")

    if "drone @ai_mail dispatch" not in command:
        return {"stdout": "", "exit_code": 0}

    if "unread_count" in command and "while [" in command:
        return {"stdout": "", "exit_code": 0}

    if "dispatch wake" in command and "dispatch @" not in command:
        return {"stdout": "", "exit_code": 0}

    _speak("auto watchdog")

    result = {
        "additionalContext": (
            "[AUTO-WATCHDOG] Dispatch detected — arm watchdog NOW. "
            "Run the watchdog one-liner from your local prompt with "
            "run_in_background: true and timeout: 600000."
        )
    }
    return {"stdout": json.dumps(result), "exit_code": 0}
