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
import re


def _extract_target(command: str) -> str:
    """Extract the @target branch name from a dispatch command."""
    match = re.search(r"dispatch\s+@(\S+)", command)
    return f"@{match.group(1)}" if match else "@<target>"


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

    target = _extract_target(command)

    result = {
        "additionalContext": (
            f"[AUTO-WATCHDOG] Dispatch detected — arm watchdog NOW.\n"
            f"Use the Monitor tool (NOT Bash run_in_background) to run:\n"
            f"  drone @devpulse watchdog agent {target}\n"
            f"The Monitor tool's return is what wakes your session when "
            f"the dispatched agent finishes. run_in_background cannot wake you."
        )
    }
    return {"stdout": json.dumps(result), "exit_code": 0, "sound": "auto watchdog"}
