#!/usr/bin/env python3
"""
PreToolUse Gate — Blocks unsafe edits at the hook layer.

Rules (checked in order):
  1. Inbox lock  — any write targeting *.ai_mail.local/inbox.json is BLOCKED.
                   Use `drone @ai_mail email` instead.
  2. Cross-branch — writes to src/aipass/X/** from a CWD inside src/aipass/Y/**
                    are BLOCKED unless the calling branch is in TRUSTED_CROSS_WRITERS.
  3. State-file  — edits to OTHER .py files while the current branch has unresolved
                   type errors are BLOCKED. (original v1.2.0 logic)

Track E additions: rules 1 + 2 (DPLAN-0139).
Version: 1.3.0
"""

import json
import os
import sys
from pathlib import Path

STATE_FILE = Path(__file__).parent / ".diagnostics_state.json"
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

# Single source of truth lives in permissions.py — inline here as fallback
# so the hook works even when aipass package is not on sys.path.
TRUSTED_CROSS_WRITERS: tuple[str, ...] = ("devpulse", "seedgo", "spawn")


def _get_branch(file_path: str) -> str:
    """Extract AIPass branch name from a file path (src/aipass/{branch}/ pattern)."""
    parts = Path(file_path).parts
    for i, part in enumerate(parts):
        if part == "aipass" and i > 0 and parts[i - 1] == "src" and i + 1 < len(parts):
            return parts[i + 1]
    return ""


def _block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(2)


def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        if tool_name not in EDIT_TOOLS:
            return

        if not file_path:
            return

        # ------------------------------------------------------------------
        # Rule 1: Inbox lock — block all writes to *.ai_mail.local/inbox.json
        # ------------------------------------------------------------------
        fp = Path(file_path)
        if fp.name == "inbox.json" and ".ai_mail.local" in fp.parts:
            _block(
                "Direct writes to inbox.json are blocked.\n"
                "Use: drone @ai_mail email @<branch> \"Subject\" \"Body\""
            )

        # ------------------------------------------------------------------
        # Rule 2: Cross-branch write enforcement
        # ------------------------------------------------------------------
        cwd = input_data.get("cwd", "") or os.getcwd()
        cwd_branch = _get_branch(cwd)
        target_branch = _get_branch(str(fp.resolve()) if not fp.is_absolute() else str(fp))

        if cwd_branch and target_branch and cwd_branch != target_branch:
            if cwd_branch not in TRUSTED_CROSS_WRITERS:
                _block(
                    f"Cross-branch write blocked: '{cwd_branch}' cannot write to '{target_branch}'.\n"
                    f"Trusted cross-writers: {', '.join(TRUSTED_CROSS_WRITERS)}"
                )

        # ------------------------------------------------------------------
        # Rule 3: State-file (original v1.2.0) — .py files only
        # ------------------------------------------------------------------
        if not file_path.endswith(".py"):
            return

        if not STATE_FILE.exists():
            return

        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return

        errored_file = state.get("file", "")
        errors = state.get("errors", [])

        if not errors:
            return

        try:
            current = str(Path(file_path).resolve())
            errored = str(Path(errored_file).resolve())
        except (OSError, ValueError):
            return

        if current == errored:
            return

        current_branch = _get_branch(current)
        errored_branch = _get_branch(errored)
        if not errored_branch:
            return
        if current_branch and errored_branch and current_branch != errored_branch:
            return

        error_summary = "\n".join(f"  L{e['line']}: {e['message']}" for e in errors[:5])
        _block(
            f"Fix {len(errors)} error(s) in {Path(errored_file).name} before editing other files:\n"
            f"{error_summary}"
        )

    except Exception:
        pass  # Silent fail → allow


if __name__ == "__main__":
    main()
