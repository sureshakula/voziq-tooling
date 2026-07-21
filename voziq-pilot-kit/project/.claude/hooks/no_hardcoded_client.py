#!/usr/bin/env python3
"""PreToolUse gate: client-specific values go in YAML, never in code.

Rejects .py and .sql writes containing a client short code from
client_codes.txt (one code per line, # for comments). Config folders,
fixtures, and test data are exempt. Exit code 2 blocks the write.
"""

import json
import pathlib
import re
import sys

CODE_EXTENSIONS = (".py", ".sql")
EXEMPT_PATH_HINTS = ("config", "fixtures", "tests/data")


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = event.get("tool_input") or {}
    path = tool_input.get("file_path", "")
    if not path.endswith(CODE_EXTENSIONS):
        sys.exit(0)
    if any(hint in path.lower() for hint in EXEMPT_PATH_HINTS):
        sys.exit(0)

    codes_file = pathlib.Path(__file__).parent / "client_codes.txt"
    if not codes_file.exists():
        sys.exit(0)
    codes = [
        line.strip()
        for line in codes_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    content = tool_input.get("content") or tool_input.get("new_string") or ""
    for code in codes:
        if re.search(rf"\b{re.escape(code)}\b", content, re.IGNORECASE):
            print(
                f"Blocked: '{code}' is a client identifier and this is a code file. "
                "Client-specific values live in YAML configuration (common base plus "
                "client overrides), never in .py or .sql. Parameterize this and put "
                "the value in the client's config.",
                file=sys.stderr,
            )
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
