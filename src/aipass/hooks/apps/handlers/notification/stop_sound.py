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
import subprocess
import tempfile
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger

AIPASS_HOME = Path(os.environ.get("AIPASS_HOME", ""))
SOUNDS_DIR = AIPASS_HOME / ".claude" / "sounds"
SOUND_FILE = SOUNDS_DIR / "mixkit-achievement-bell-600.wav"

PIPER_BIN = Path.home() / ".local" / "share" / "piper" / "piper"
PIPER_VOICE = Path.home() / ".local" / "share" / "piper-voices" / "en_US-amy-medium.onnx"


def _play(sound_path: Path) -> None:
    """Play a WAV file via aplay (fire-and-forget)."""
    if not sound_path.exists():
        logger.info("[HOOKS] stop_sound: file not found: %s", sound_path)
        return
    try:
        subprocess.Popen(
            ["aplay", "-q", str(sound_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        logger.info("[HOOKS] stop_sound: playback error: %s", exc)


def _speak(text: str) -> None:
    """Generate speech via Piper TTS and play it (fire-and-forget)."""
    if not PIPER_BIN.exists() or not PIPER_VOICE.exists():
        logger.info("[HOOKS] stop_sound: piper not available")
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
        logger.info("[HOOKS] stop_sound: piper timed out")
    except OSError as exc:
        logger.info("[HOOKS] stop_sound: speak error: %s", exc)


def handle(hook_data: dict) -> dict:
    """Play achievement bell and speak hook name on Stop event.

    Args:
        hook_data: Parsed hook event dict from engine.

    Returns:
        Result dict with stdout (empty) and exit_code.
    """
    if hook_data.get("stop_hook_active", False):
        return {"stdout": "", "exit_code": 0}

    _speak("stop sound")
    return {"stdout": "", "exit_code": 0}
