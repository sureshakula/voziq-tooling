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
        logger.info("[HOOKS] global_loader: speak error: %s", exc)


def handle(hook_data: dict) -> dict:
    """Load AIPass global prompt from AIPASS_HOME."""
    _speak("global prompt")

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
