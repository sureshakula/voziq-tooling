# =================== AIPass ====================
# Name: branch_loader.py
# Version: 1.0.0
# Description: Loads branch-specific prompt + private integrations (UserPromptSubmit)
# Branch: hooks
# Layer: apps/handlers/prompt
# Created: 2026-05-22
# Modified: 2026-05-22
# =============================================

"""Loads .aipass/aipass_local_prompt.md and private integration prompts for injection."""

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
        logger.info("[HOOKS] branch_loader: speak error: %s", exc)


def _find_branch_root(cwd: str) -> Path | None:
    """Walk up from CWD looking for .trinity/ or apps/ — stop at repo root."""
    search = Path(cwd).resolve()
    while search.parent != search:
        if (search / ".trinity").is_dir() or (search / "apps").is_dir():
            return search
        if (search / "pyproject.toml").exists() or (search / ".git").is_dir():
            return None
        search = search.parent
    return None


def handle(hook_data: dict) -> dict:
    """Load branch prompt and private integration prompts."""
    _speak("branch prompt")

    try:
        cwd = hook_data.get("cwd", "") or str(Path.cwd())
        branch_root = _find_branch_root(cwd)
        if not branch_root:
            return {"stdout": "", "exit_code": 0}

        parts: list[str] = []

        prompt_file = branch_root / ".aipass" / "aipass_local_prompt.md"
        if prompt_file.exists():
            content = prompt_file.read_text(encoding="utf-8").strip()
            branch_name = branch_root.name.upper()
            parts.append(f"# Branch Context: {branch_name}\n<!-- Source: {prompt_file} -->\n{content}")

        integrations_dir = branch_root / "apps" / "integrations"
        if integrations_dir.is_dir():
            for prompt in sorted(integrations_dir.glob("*/private_prompt.md")):
                parts.append(prompt.read_text(encoding="utf-8").strip())

        if not parts:
            return {"stdout": "", "exit_code": 0}

        return {"stdout": "\n".join(parts), "exit_code": 0}

    except Exception as exc:
        logger.info("[HOOKS] branch_loader: unexpected error: %s", exc)
        return {"stdout": "", "exit_code": 0}
