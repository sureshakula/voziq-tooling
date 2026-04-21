#!/usr/bin/env python3
"""
Hook probe: PreToolUse

Fires on the Claude Code [PreToolUse] hook event.
Records a structured entry to last_ping.jsonl. Never blocks. Silent-fail on any exception.

To enable — add this snippet to AIPass/.claude/settings.json (inside "hooks"):

    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/AIPass/.claude/hooks/probes/probe_pre_tool_use.py"
          }
        ]
      }
    ]

Replace /path/to/AIPass with the actual AIPass repo root path.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Log file lives next to this script
_LOG_FILE = Path(__file__).parent / "last_ping.jsonl"
_EVENT = "PreToolUse"


def main() -> None:
    start = time.monotonic()

    # --- Read stdin (tolerant of parse failures) ---
    payload: dict = {}
    try:
        raw = sys.stdin.read()
        if raw.strip():
            payload = json.loads(raw)
    except Exception:
        pass

    # --- Extract fields ---
    tool = (
        payload.get("tool_name")
        or payload.get("hook_event_name")
        or ""
    )
    cwd = payload.get("cwd") or os.getcwd()

    agent_id = (
        os.environ.get("CLAUDE_CODE_SESSION_ID")
        or os.environ.get("CLAUDE_SESSION_ID")
        or "unknown"
    )
    cli_version = os.environ.get("CLAUDE_CODE_VERSION", "unknown")
    env_has_claude_project_dir = bool(os.environ.get("CLAUDE_PROJECT_DIR"))
    env_has_aipass_home = bool(os.environ.get("AIPASS_HOME"))

    elapsed_ms = (time.monotonic() - start) * 1000.0
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    entry = {
        "event": _EVENT,
        "tool": tool,
        "cwd": cwd,
        "agent_id": agent_id,
        "timestamp": timestamp,
        "script_elapsed_ms": round(elapsed_ms, 3),
        "cli_version": cli_version,
        "env_has_claude_project_dir": env_has_claude_project_dir,
        "env_has_aipass_home": env_has_aipass_home,
    }

    # --- Append to log (never block) ---
    try:
        _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
