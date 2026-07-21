#!/usr/bin/env python3
"""PostToolUse: run ruff on edited Python files, feed violations back.

Exit code 2 returns the violations to the agent so problems get fixed in
the same session instead of surfacing in CI. Skips silently when ruff is
not installed or anything goes wrong; a lint hook must never break edits.
"""

import json
import shutil
import subprocess
import sys


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    path = (event.get("tool_input") or {}).get("file_path", "")
    if not path.endswith(".py"):
        sys.exit(0)
    if shutil.which("ruff") is None:
        sys.exit(0)

    try:
        result = subprocess.run(
            ["ruff", "check", "--no-cache", path],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception:
        sys.exit(0)

    if result.returncode != 0 and result.stdout.strip():
        print(
            "Ruff found problems in the file you just edited. Fix them now:\n"
            + result.stdout,
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
