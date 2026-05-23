# =================== AIPass ====================
# Name: hook_sounds_plugin.py
# Description: Toggle hook notification sounds on/off
# Version: 1.0.0
# Created: 2026-04-09
# Modified: 2026-04-09
# =============================================

"""Toggle hook notification sounds on/off.

Creates or removes a flag file that hook sound scripts check before
playing audio.  When muted, hooks still run their essential logic
(prompt injection, logging) but skip audio playback.
"""

from __future__ import annotations

from pathlib import Path

from aipass.prax import logger
from aipass.cli.apps.modules import console
from aipass.drone.apps.handlers.json import json_handler

MUTE_FLAG = Path("/tmp/aipass-hooks-muted")


def mute() -> bool:
    """Create the mute flag file — silences hook sounds."""
    MUTE_FLAG.touch()
    logger.info("Hook sounds muted (flag: %s)", MUTE_FLAG)
    return True


def unmute() -> bool:
    """Remove the mute flag file — re-enables hook sounds."""
    MUTE_FLAG.unlink(missing_ok=True)
    logger.info("Hook sounds unmuted (flag removed: %s)", MUTE_FLAG)
    return True


def is_muted() -> bool:
    """Check if hook sounds are currently muted."""
    return MUTE_FLAG.exists()


def handle_command(command: str | None = None, args: list[str] | None = None) -> bool:
    """Route hook-sounds commands.

    Args:
        command: "on", "off", or None (show status).
        args: Not used.

    Returns:
        True on success.
    """
    json_handler.log_operation("handle_command", {"plugin": "hook_sounds", "command": command})

    if command == "off":
        mute()
        console.print("Hook sounds: MUTED")
        return True

    if command == "on":
        unmute()
        console.print("Hook sounds: ACTIVE")
        return True

    # No command = show status
    if is_muted():
        console.print("Hook sounds: MUTED (off)")
        console.print(f"  Flag: {MUTE_FLAG}")
    else:
        console.print("Hook sounds: ACTIVE (on)")

    return True
