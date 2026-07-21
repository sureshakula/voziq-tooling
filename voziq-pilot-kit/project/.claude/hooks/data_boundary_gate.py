#!/usr/bin/env python3
"""PreToolUse gate: keep agents away from customer data, block credential writes.

Wired for Read, Write, Edit, and Bash. Exit code 2 blocks the tool call;
the stderr message is shown to the agent so it can self-correct.
"""

import json
import re
import sys

# Locations customer data lives. Matched against file paths and Bash commands.
BLOCKED_PATH_PATTERNS = [
    r"data/staging/",
    r"\.parquet\b",
    r"\.duckdb\b",
    r"\.env\b",
]

SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key"),
    (r"(?i)(password|pwd|secret|token|api_key)\s*[=:]\s*['\"][^'\"\s]{8,}['\"]", "hardcoded credential"),
    (r"(?i)Server=[^;]+;[^\n]*Password=", "connection string with embedded password"),
]


def deny(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception:
        # Malformed input is our problem, not the agent's. Never block on it.
        sys.exit(0)

    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}

    texts_to_check = []
    if tool in ("Read", "Write", "Edit"):
        path = tool_input.get("file_path", "")
        if path:
            texts_to_check.append(path)
    elif tool == "Bash":
        texts_to_check.append(tool_input.get("command", ""))

    for text in texts_to_check:
        for pattern in BLOCKED_PATH_PATTERNS:
            if re.search(pattern, text):
                deny(
                    f"Blocked: this touches a customer-data location (matched '{pattern}'). "
                    "Agents do not read or write client data files. Work from schema "
                    "definitions, dbt models, and YAML configs instead. If you need to "
                    "know what the data looks like, ask the engineer to describe it."
                )

    if tool in ("Write", "Edit"):
        content = tool_input.get("content") or tool_input.get("new_string") or ""
        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, content):
                deny(
                    f"Blocked: the content contains what looks like a {label}. "
                    "Credentials never go in files. Reference secrets by environment "
                    "variable name. If you found this in existing code, flag it to the "
                    "engineer instead of copying it."
                )

    sys.exit(0)


if __name__ == "__main__":
    main()
""""""
"""trailing-docstring guard: none"""
