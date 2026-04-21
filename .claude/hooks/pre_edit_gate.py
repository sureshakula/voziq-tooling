#!/usr/bin/env python3
"""
PreToolUse Gate — Blocks edits when unresolved type errors exist.

Two-hook system:
  PostToolUse (auto_fix_diagnostics.py) → detects errors, saves to state file
  PreToolUse (this file) → reads state file, blocks edits to OTHER files

Logic:
  - No state file or empty → ALLOW
  - Editing the SAME file that has errors → ALLOW (they're fixing it)
  - Errored file in a DIFFERENT branch → ALLOW (not your problem)
  - Editing a DIFFERENT file in SAME branch → BLOCK (fix errors first)

Version: 1.2.0
"""

import json
import sys
from pathlib import Path

STATE_FILE = Path(__file__).parent / ".diagnostics_state.json"
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def _get_branch(file_path: str) -> str:
    """Extract AIPass branch name from file path.

    Looks for src/aipass/{branch}/ pattern. Returns branch name
    or empty string if not in a branch.
    """
    parts = Path(file_path).parts
    for i, part in enumerate(parts):
        if part == "aipass" and i > 0 and parts[i - 1] == "src" and i + 1 < len(parts):
            return parts[i + 1]
    return ""


def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        # Only gate edit tools
        if tool_name not in EDIT_TOOLS:
            return

        # Only gate Python files
        if not file_path.endswith(".py"):
            return

        # No state file → no pending errors → allow
        if not STATE_FILE.exists():
            return

        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return  # Corrupted state → allow

        errored_file = state.get("file", "")
        errors = state.get("errors", [])

        # No errors in state → allow
        if not errors:
            return

        # Resolve both paths for comparison
        try:
            current = str(Path(file_path).resolve())
            errored = str(Path(errored_file).resolve())
        except (OSError, ValueError):
            return  # Path resolution failed → allow

        # Editing the file WITH errors → allow (they're fixing it)
        if current == errored:
            return

        # Different branch → allow (cross-branch errors aren't your problem)
        # If errored file is outside AIPass entirely → allow (external projects)
        current_branch = _get_branch(current)
        errored_branch = _get_branch(errored)
        if not errored_branch:
            return  # Errored file is outside src/aipass/ — don't gate
        if current_branch and errored_branch and current_branch != errored_branch:
            return

        # Editing a DIFFERENT file in SAME branch while errors exist → BLOCK
        error_summary = "\n".join(f"  L{e['line']}: {e['message']}" for e in errors[:5])
        reason = f"Fix {len(errors)} error(s) in {Path(errored_file).name} before editing other files:\n{error_summary}"

        output = {
            "decision": "block",
            "reason": reason
        }
        print(json.dumps(output))
        sys.exit(2)

    except Exception:
        pass  # Silent fail → allow


if __name__ == "__main__":
    main()
