# =================== AIPass ====================
# Name: handoff_platform/__init__.py
# Description: OS-dispatched CLI session launch — tmux, wt.exe, fallback
# Version: 1.0.0
# Created: 2026-04-20
# Modified: 2026-04-20
# =============================================

"""
handoff_platform — OS-dispatched CLI session launch.

Consumers: modules/handoff.py, modules/init_flow.py (stage 11).

Linux/Mac: tmux new-session -d -s aipass-handoff -c <cwd>; send-keys '<cli> "<prompt>"'
Windows:   wt.exe -w 0 nt -d <cwd> <cli> "<prompt>"  (Windows Terminal)
Fallback:  caller receives command string for manual display — no silent fail.

All public functions return data; presentation is handled by the module layer.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Optional

from aipass.prax import logger

# Platform constants — consistent with setup.sh naming
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

_TMUX_SESSION = "aipass-handoff"


def build_cli_cmd(cli: str, flag_variant: str) -> str:
    """Build the CLI invocation string from cli name and flag variant."""
    parts = [cli]
    if cli == "claude" and flag_variant == "skip-permissions":
        parts.append("--dangerously-skip-permissions")  # noqa: S603
    return " ".join(parts)


def build_manual_command(cli: str, prompt: str, cwd: str, flag_variant: str = "default") -> str:
    """Return the equivalent manual shell command for user display."""
    cli_cmd = build_cli_cmd(cli, flag_variant)
    safe_prompt = prompt.replace('"', '\\"')
    return f'cd {cwd} && {cli_cmd} "{safe_prompt}"'


def launch_tmux(cli: str, prompt: str, cwd: str, flag_variant: str = "default") -> bool:
    """Launch CLI in a new tmux session. Returns True on success."""
    if not shutil.which("tmux"):
        logger.warning("[handoff_platform] tmux not found on PATH")
        return False

    cli_cmd = build_cli_cmd(cli, flag_variant)
    safe_prompt = prompt.replace('"', '\\"')

    try:
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", _TMUX_SESSION, "-c", cwd],
            check=True,
            timeout=10,
        )
        subprocess.run(
            ["tmux", "send-keys", "-t", _TMUX_SESSION, f'{cli_cmd} "{safe_prompt}"', "Enter"],
            check=True,
            timeout=10,
        )
        logger.info("[handoff_platform] tmux session '%s' started in %s", _TMUX_SESSION, cwd)
        return True
    except subprocess.CalledProcessError as exc:
        logger.warning("[handoff_platform] tmux launch failed: %s", exc)
        return False
    except subprocess.TimeoutExpired as exc:
        logger.warning("[handoff_platform] tmux command timed out: %s", exc)
        return False


def launch_wt(cli: str, prompt: str, cwd: str, flag_variant: str = "default") -> bool:
    """Launch CLI in Windows Terminal (wt.exe). Returns True on success."""
    if not shutil.which("wt"):
        logger.warning("[handoff_platform] wt.exe not found on PATH")
        return False

    cli_cmd = build_cli_cmd(cli, flag_variant)
    safe_prompt = prompt.replace('"', '\\"')

    try:
        subprocess.run(
            ["wt", "-w", "0", "nt", "-d", cwd, cli_cmd, f'"{safe_prompt}"'],
            check=True,
            timeout=15,
        )
        logger.info("[handoff_platform] wt.exe session started in %s", cwd)
        return True
    except subprocess.CalledProcessError as exc:
        logger.warning("[handoff_platform] wt.exe launch failed: %s", exc)
        return False
    except subprocess.TimeoutExpired as exc:
        logger.warning("[handoff_platform] wt.exe command timed out: %s", exc)
        return False


def launch_handoff(
    cli: str,
    prompt: str,
    cwd: str,
    flag_variant: str = "default",
    platform_override: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Dispatch CLI launch to the appropriate platform handler.

    Returns (launched, manual_command):
      launched=True  — tmux/wt session was started successfully
      launched=False — auto-launch unavailable; caller displays manual_command
      manual_command — always populated; equivalent command for manual run

    Order: tmux (Linux/Mac) → wt.exe (Windows) → fallback (caller handles display).
    """
    manual_cmd = build_manual_command(cli, prompt, cwd, flag_variant)
    target = platform_override or ("windows" if IS_WINDOWS else "unix")

    if target == "windows":
        if launch_wt(cli, prompt, cwd, flag_variant):
            return True, manual_cmd
    else:
        if launch_tmux(cli, prompt, cwd, flag_variant):
            return True, manual_cmd

    logger.info("[handoff_platform] auto-launch unavailable — fallback command ready")
    return False, manual_cmd
