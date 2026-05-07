#!/usr/bin/env python3
"""
Global Prompt Loader — replaces hardcoded `cat` of aipass_global_prompt.md.

Uses $AIPASS_HOME for path portability. Exits silently when CWD is inside
a project that has its own UserPromptSubmit hooks (avoids injecting the
22KB AIPass source-tree prompt into standalone projects).

Version: 1.0.0
"""

import json
import os
from pathlib import Path


def _project_has_own_hooks() -> bool:
    """Check if CWD is inside a project with its own UserPromptSubmit hooks."""
    search = Path.cwd()
    home = Path.home()
    while search != home and search.parent != search:
        settings = search / ".claude" / "settings.json"
        if settings.exists():
            try:
                data = json.loads(settings.read_text(encoding="utf-8"))
                ups = data.get("hooks", {}).get("UserPromptSubmit", [])
                if ups:
                    return True
            except (json.JSONDecodeError, OSError):
                pass
        search = search.parent
    return False


def main():
    if _project_has_own_hooks():
        return

    aipass_home = os.environ.get("AIPASS_HOME", "")
    if not aipass_home:
        return

    prompt_file = Path(aipass_home) / ".aipass" / "aipass_global_prompt.md"
    if prompt_file.exists():
        print(prompt_file.read_text(encoding="utf-8"), end="")


if __name__ == "__main__":
    main()
