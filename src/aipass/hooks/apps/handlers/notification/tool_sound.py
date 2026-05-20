# =================== AIPass ====================
# Name: tool_sound.py
# Version: 1.1.0
# Description: Announces hook name via Piper TTS on tool use
# Branch: hooks
# Layer: apps/handlers/notification
# Created: 2026-05-19
# Modified: 2026-05-19
# =============================================

"""Announces hook name via Piper TTS when the AI uses tools (PreToolUse event)."""

import subprocess
import tempfile
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger

PIPER_BIN = Path.home() / ".local" / "share" / "piper" / "piper"
PIPER_VOICE = Path.home() / ".local" / "share" / "piper-voices" / "en_US-amy-medium.onnx"


def _speak(text: str) -> None:
    """Generate speech via Piper TTS and play it (fire-and-forget)."""
    if not PIPER_BIN.exists() or not PIPER_VOICE.exists():
        logger.info("[HOOKS] tool_sound: piper not available")
        return

    try:
        wav_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav_path = wav_file.name
        wav_file.close()

        piper_result = subprocess.run(
            [str(PIPER_BIN), "-m", str(PIPER_VOICE), "-f", wav_path],
            input=text,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if piper_result.returncode == 0 and Path(wav_path).exists():
            subprocess.Popen(
                ["aplay", "-q", wav_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except subprocess.TimeoutExpired:
        logger.info("[HOOKS] tool_sound: piper timed out")
    except OSError as exc:
        logger.info("[HOOKS] tool_sound: playback error: %s", exc)


def handle(hook_data: dict) -> dict:
    """Announce hook name for matching tool use events.

    Args:
        hook_data: Parsed hook event dict from engine (tool_name, etc.)

    Returns:
        Result dict with stdout (empty) and exit_code.
    """
    tool_name = hook_data.get("tool_name", "")
    if not tool_name:
        return {"stdout": "", "exit_code": 0}

    _speak(f"tool sound: {tool_name}")
    return {"stdout": "", "exit_code": 0}
