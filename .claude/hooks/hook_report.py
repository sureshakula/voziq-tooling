#!/usr/bin/env python3
"""
Hook Execution Report — reads /tmp/aipass_hook_log.jsonl and shows what fired.

Usage:
    python3 hook_report.py                  # Last session (or last 5 min)
    python3 hook_report.py --all            # All entries in log
    python3 hook_report.py --session ID     # Specific session
    python3 hook_report.py --cwd /path      # Filter by CWD
    python3 hook_report.py --clear          # Wipe log and start fresh
    python3 hook_report.py --json           # Output raw JSON instead of table

Version: 1.0.0
"""

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_LOG_FILE = Path("/tmp/aipass_hook_log.jsonl")

_EVENT_ORDER = [
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "SubagentStop",
    "PreCompact",
    "Stop",
    "Notification",
]


def _load_entries(
    session: str = "",
    cwd: str = "",
    since_minutes: int = 0,
    all_entries: bool = False,
) -> list[dict]:
    if not _LOG_FILE.exists():
        return []

    entries = []
    now = datetime.now(timezone.utc)

    for line in _LOG_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if session and entry.get("session", "") != session:
            continue
        if cwd and not entry.get("cwd", "").startswith(cwd):
            continue

        if not all_entries and since_minutes > 0:
            try:
                ts = datetime.fromisoformat(entry["ts"].replace("Z", "+00:00"))
                age = (now - ts).total_seconds() / 60
                if age > since_minutes:
                    continue
            except (KeyError, ValueError):
                continue

        entries.append(entry)

    return entries


def _format_bytes(n: int) -> str:
    if n == 0:
        return "silent"
    if n < 1024:
        return f"{n}B"
    return f"{n / 1024:.1f}KB"


def _format_table(entries: list[dict]) -> str:
    if not entries:
        return "No hook activity found."

    lines = []

    sessions = set(e.get("session", "")[:8] for e in entries)
    cwds = set(e.get("cwd", "") for e in entries)
    ts_range = ""
    if entries:
        first_ts = entries[0].get("ts", "")[:19]
        last_ts = entries[-1].get("ts", "")[:19]
        ts_range = f"{first_ts} -> {last_ts}" if first_ts != last_ts else first_ts

    lines.append("Hook Execution Report")
    lines.append("=" * 70)
    if len(sessions) == 1:
        lines.append(f"Session: {list(sessions)[0]}...")
    else:
        lines.append(f"Sessions: {len(sessions)}")
    if len(cwds) == 1:
        lines.append(f"CWD: {list(cwds)[0]}")
    else:
        lines.append(f"CWDs: {', '.join(sorted(cwds))}")
    lines.append(f"Time: {ts_range}")
    lines.append(f"Total fires: {len(entries)}")
    lines.append("")

    hdr = f"{'#':>3} | {'Event':<22} | {'Source':<8} | {'Script':<28} | {'ms':>6} | {'Output':>8} | {'Exit':>4}"
    lines.append(hdr)
    lines.append("-" * len(hdr))

    for i, e in enumerate(entries, 1):
        event = e.get("event", "?")
        source = e.get("source", "?")
        script = e.get("script", "?")
        ms = e.get("elapsed_ms", 0)
        out = _format_bytes(e.get("output_bytes", 0))
        exit_code = e.get("exit_code", 0)
        exit_str = str(exit_code) if exit_code != 0 else ""

        lines.append(f"{i:>3} | {event:<22} | {source:<8} | {script:<28} | {ms:>6.1f} | {out:>8} | {exit_str:>4}")

    lines.append("")

    event_counts = Counter(e.get("event", "") for e in entries)
    source_counts = Counter((e.get("event", ""), e.get("source", "")) for e in entries)

    warnings = []
    for event, count in event_counts.items():
        sources = [s for (ev, s), c in source_counts.items() if ev == event]
        unique_sources = set(sources)
        if count > 1 and len(unique_sources) > 1:
            warnings.append(f"DOUBLE-FIRE: {event} fired {count}x from {', '.join(sorted(unique_sources))}")
        elif count > 4:
            warnings.append(f"HIGH FREQUENCY: {event} fired {count}x")

    suppressed = [e for e in entries if e.get("output_bytes", 0) == 0 and e.get("event") == "UserPromptSubmit"]
    if suppressed:
        scripts = [e.get("script", "?") for e in suppressed]
        warnings.append(
            f"CWD-GUARDED (likely): {len(suppressed)} UserPromptSubmit hook(s) produced no output: {', '.join(scripts)}"
        )

    if warnings:
        lines.append("Warnings:")
        for w in warnings:
            lines.append(f"  ! {w}")
    else:
        lines.append("No warnings.")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hook execution report")
    parser.add_argument("--all", action="store_true", help="Show all entries")
    parser.add_argument("--session", default="", help="Filter by session ID (prefix match)")
    parser.add_argument("--cwd", default="", help="Filter by CWD prefix")
    parser.add_argument("--minutes", type=int, default=5, help="Show last N minutes (default: 5)")
    parser.add_argument("--clear", action="store_true", help="Clear log file")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    if args.clear:
        if _LOG_FILE.exists():
            _LOG_FILE.unlink()
            print("Log cleared.")
        else:
            print("No log file to clear.")
        return

    entries = _load_entries(
        session=args.session,
        cwd=args.cwd,
        since_minutes=args.minutes,
        all_entries=args.all,
    )

    if args.json:
        print(json.dumps(entries, indent=2))
    else:
        print(_format_table(entries))


if __name__ == "__main__":
    main()
