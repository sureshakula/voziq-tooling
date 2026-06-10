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

    result = {
        "additionalContext": (
            "[AUTO-WATCHDOG] Dispatch detected — arm watchdog NOW. "
            "Run the watchdog one-liner from your local prompt with "
            "run_in_background: true and timeout: 600000."
        )
    }
    return {"stdout": json.dumps(result), "exit_code": 0, "sound": "auto watchdog"}
