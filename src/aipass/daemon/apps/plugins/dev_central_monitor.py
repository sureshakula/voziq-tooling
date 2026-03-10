# =================== AIPass ====================
# Name: dev_central_monitor.py
# Description: Hourly System Monitor Plugin
# Version: 1.0.0
# Created: 2026-02-23
# Modified: 2026-02-23
# =============================================

"""
Hourly System Monitor Plugin

Wakes DEV_CENTRAL every 60 minutes to:
1. Check system health (daemon, branches, errors)
2. Monitor VERA's autonomous performance (metrics, decisions, output)
3. Identify and attempt to resolve blockers
4. Record findings in VERA_AUTONOMOUS_TRACKER.md
5. Learn patterns for teaching autonomous operation

Patrick's directive (Session 124): DEV_CENTRAL should be the best
at overcoming blockers. Learn, then teach VERA.
"""

from aipass.prax import logger
# logger imported from aipass.prax

PLUGIN_CONFIG = {
    "name": "dev_central_monitor",
    "schedule": "interval",
    "time": None,
    "interval_minutes": 60,
    "enabled": False,  # Disabled 2026-02-26: too noisy, spawns full agent every hour
    "branch": "@dev_central",
    "fresh": True,
    "max_turns": 15,
    "prompt": (
        "HOURLY SYSTEM CHECK -- You are DEV_CENTRAL's autonomous monitor.\n\n"

        "STEP 1: Check inbox (ai_mail inbox). Process any mail -- close FYIs, act on tasks.\n"
        "STEP 2: Check daemon health:\n"
        "  - ps aux | grep daemon.py (is it running?)\n"
        "  - tail -10 daemon log for errors\n"
        "  - If daemon is dead, restart it\n"
        "STEP 3: Monitor VERA:\n"
        "  - Read head -40 of VERA's NOTEPAD.md (what did she do since last check?)\n"
        "  - Check: gh pr list --repo AIOSAI/AIPass --state open (new PRs?)\n"
        "  - Is she idling? If 3+ consecutive clean heartbeats, investigate why\n"
        "  - If blocked: attempt to unblock (research, dispatch help, pivot suggestion)\n"
        "STEP 4: Check for system errors:\n"
        "  - Any error emails in inbox?\n"
        "  - Any stale locks? ls /tmp/claude_dispatch_*.lock\n"
        "STEP 5: Record findings:\n"
        "  - Update VERA_AUTONOMOUS_TRACKER.md with observations\n"
        "  - Note any blockers found and how they were resolved\n"
        "  - Update your own DEV_CENTRAL.local.json with session summary\n\n"

        "LEARNING GOAL: You are building expertise in autonomous agent management. "
        "Every hour, you learn something about how VERA operates, what blocks her, "
        "and how to unblock her. Record patterns. Build playbooks. "
        "You teach VERA by sending her targeted guidance when you spot issues.\n\n"

        "Keep it focused. 15 turns max. Check, record, unblock, move on."
    ),
}


def run() -> dict:
    """
    Optional custom logic before/after spawn.
    Currently returns config only - scheduler handles the actual wake.
    """
    return {
        "status": "ready",
        "plugin": PLUGIN_CONFIG["name"],
        "branch": PLUGIN_CONFIG["branch"],
    }
