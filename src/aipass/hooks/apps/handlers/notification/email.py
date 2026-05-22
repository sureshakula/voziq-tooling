# =================== AIPass ====================
# Name: email.py
# Version: 1.1.0
# Description: Checks inbox for unread emails on UserPromptSubmit
# Branch: hooks
# Layer: apps/handlers/notification
# Created: 2026-05-21
# Modified: 2026-05-21
# =============================================

"""Checks branch inbox for unread emails and returns notification text."""

import json
import subprocess
import tempfile
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger

PIPER_BIN = Path.home() / ".local" / "share" / "piper" / "piper"
PIPER_VOICE = Path.home() / ".local" / "share" / "piper-voices" / "en_US-amy-medium.onnx"


def _speak(text: str) -> None:
    """Generate speech via Piper TTS and play it (fire-and-forget)."""
    if not PIPER_BIN.exists() or not PIPER_VOICE.exists():
        logger.info("[HOOKS] email: piper not available")
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
        logger.info("[HOOKS] email: piper timed out")
    except OSError as exc:
        logger.info("[HOOKS] email: speak error: %s", exc)


def _find_branch_root() -> Path | None:
    """Find the branch root by walking up from CWD looking for branch markers."""
    cwd = Path.cwd()
    repo_root = _find_repo_root()
    if not repo_root:
        return None

    search = cwd
    for _ in range(10):
        has_trinity = (search / ".trinity").is_dir()
        has_apps = (search / "apps").is_dir()
        has_mail = (search / ".ai_mail.local").is_dir() or (search / "ai_mail.local").is_dir()

        if (has_trinity or has_apps or has_mail) and search != repo_root:
            return search

        if search == repo_root:
            break

        parent = search.parent
        if parent == search:
            break
        search = parent

    return None


def _find_repo_root() -> Path | None:
    """Find the repo root (contains pyproject.toml or .git)."""
    search = Path.cwd()
    while search.parent != search:
        if (search / "pyproject.toml").exists() or (search / ".git").is_dir():
            return search
        search = search.parent
    return None


def _count_new_emails(branch_root: Path) -> int:
    """Count unread emails in the branch's inbox."""
    inbox_path = branch_root / ".ai_mail.local" / "inbox.json"
    if not inbox_path.exists():
        inbox_path = branch_root / "ai_mail.local" / "inbox.json"

    if not inbox_path.exists():
        return 0

    try:
        data = json.loads(inbox_path.read_text(encoding="utf-8"))
        messages = data if isinstance(data, list) else data.get("messages", [])
        count = 0
        for msg in messages:
            if msg.get("status") == "new":
                count += 1
            elif msg.get("status") is None and not msg.get("read", False):
                count += 1
        return count
    except (json.JSONDecodeError, OSError) as exc:
        logger.info("[HOOKS] email: inbox read error: %s", exc)
        return 0


def handle(hook_data: dict) -> dict:
    """Check inbox and return email notification if unread messages exist.

    Args:
        hook_data: Parsed hook event dict from engine.

    Returns:
        Result dict with stdout (notification text or empty) and exit_code.
    """
    branch_root = _find_branch_root()
    if not branch_root:
        logger.info("[HOOKS] email: no branch root found")
        return {"stdout": "", "exit_code": 0}

    new_count = _count_new_emails(branch_root)
    if new_count == 0:
        return {"stdout": "", "exit_code": 0}

    plural = "s" if new_count != 1 else ""
    _speak(f"email notification: {new_count} new email{plural}")
    msg = f"You have {new_count} new email{plural} - check with: drone @ai_mail inbox | then: drone @ai_mail view <id> | close with: drone @ai_mail close <id>"
    logger.info("[HOOKS] email: %d new email%s", new_count, plural)
    return {"stdout": msg, "exit_code": 0}
