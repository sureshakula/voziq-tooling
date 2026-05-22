# =================== AIPass ====================
# Name: git_gate.py
# Version: 1.0.0
# Description: Blocks raw git/gh commands and protected file edits (PreToolUse)
# Branch: hooks
# Layer: apps/handlers/security
# Created: 2026-05-21
# Modified: 2026-05-21
# =============================================

"""Blocks raw git/gh commands and edits to settings/hooks files."""

import json
import os
import re
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
        logger.info("[HOOKS] git_gate: speak error: %s", exc)


RAW_GIT_RE = re.compile(r"(?<![@\w/.])git\s")
RAW_GH_RE = re.compile(r"(?<![@\w/.])gh\s")

GH_ALLOWED_SUBCOMMANDS = ("api",)

BLOCKED_EDIT_PATTERNS = [
    re.compile(r"/\.claude/settings(\.local)?\.json$"),
    re.compile(r"/\.claude/hooks/"),
    re.compile(r"/\.git/hooks/"),
]

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

TRUSTED_HOOK_EDITORS = ("devpulse", "seedgo")

GIT_GH_REDIRECT = (
    "All git/gh commands are blocked. Use drone instead:\n"
    "  drone @git status        # working tree status\n"
    "  drone @git diff           # see changes\n"
    "  drone @git log            # commit history\n"
    "  drone @git smart-sync     # fetch + rebase\n"
    "  drone @git sync           # checkout main + pull\n"
    "  drone @git issue list     # GitHub issues\n"
    "  drone @git run list       # CI runs\n"
    "  drone @git workflow run   # trigger workflows"
)

EDIT_REDIRECT = (
    "{path} is protected — settings.json, .claude/hooks/, and .git/hooks/ "
    "govern the enforcement layer itself.\n"
    "If a real change is needed, ask devpulse to make it directly."
)

_BLOCK_ALLOW = {"stdout": "", "exit_code": 0}


def _cwd_branch(cwd: str) -> str:
    parts = Path(cwd).parts
    for i, part in enumerate(parts):
        if part == "aipass" and i > 0 and parts[i - 1] == "src" and i + 1 < len(parts):
            return parts[i + 1]
    return ""


def _is_allowed_gh(cmd: str) -> bool:
    match = re.search(r"(?<![@\w/.])gh\s+(\w+)", cmd)
    if match:
        return match.group(1) in GH_ALLOWED_SUBCOMMANDS
    return False


def _block(reason: str) -> dict:
    return {"stdout": json.dumps({"decision": "block", "reason": reason}), "exit_code": 2}


def _check_bash(tool_input: dict) -> dict:
    cmd = tool_input.get("command", "")
    if not cmd:
        return _BLOCK_ALLOW
    scan = re.sub(r'"(?:[^"\\]|\\.)*"', '""', cmd)
    scan = re.sub(r"'(?:[^'\\]|\\.)*'", "''", scan)
    if RAW_GIT_RE.search(scan):
        return _block(GIT_GH_REDIRECT)
    if RAW_GH_RE.search(scan) and not _is_allowed_gh(cmd):
        return _block(GIT_GH_REDIRECT)
    return _BLOCK_ALLOW


def _check_edit(tool_input: dict, cwd: str) -> dict:
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not file_path:
        return _BLOCK_ALLOW
    for pat in BLOCKED_EDIT_PATTERNS:
        if pat.search(file_path):
            if _cwd_branch(cwd) in TRUSTED_HOOK_EDITORS:
                return _BLOCK_ALLOW
            return _block(EDIT_REDIRECT.format(path=file_path))
    return _BLOCK_ALLOW


def handle(hook_data: dict) -> dict:
    """Block raw git/gh commands and protected file edits.

    Args:
        hook_data: Parsed hook event dict from engine.

    Returns:
        Result dict with stdout (block JSON or empty) and exit_code.
    """
    _speak("git gate")

    try:
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})
        cwd = hook_data.get("cwd", "") or os.getcwd()
        if tool_name == "Bash":
            return _check_bash(tool_input)
        if tool_name in EDIT_TOOLS:
            return _check_edit(tool_input, cwd)
        return _BLOCK_ALLOW
    except Exception as exc:
        logger.info("[HOOKS] git_gate: unexpected error (allowing): %s", exc)
        return _BLOCK_ALLOW
