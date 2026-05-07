#!/usr/bin/env python3
"""
Branch Prompt Loader — AIPass Public Repo

Injects branch-specific prompts based on CWD. When working in a branch
directory, loads .aipass/aipass_local_prompt.md and outputs it so the
AI sees branch-specific context.

When CWD is inside a project that has its own UserPromptSubmit hooks
(e.g. a standalone aipass-init project), this provider-level hook exits
silently to avoid double-firing.

Version: 1.1.0
"""

import json
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


def find_branch_root() -> Path | None:
    """
    Find the branch root directory.
    Looks for .trinity/ or .aipass/ as branch indicators.
    Stops at the repo root (has pyproject.toml or .git).
    """
    cwd = Path.cwd()
    search_path = cwd

    while search_path.parent != search_path:
        # Branch indicators: has .trinity/ (memory files) or apps/ (code)
        has_trinity = (search_path / ".trinity").is_dir()
        has_apps = (search_path / "apps").is_dir()

        if has_trinity or has_apps:
            return search_path

        # Stop at repo root
        if (search_path / "pyproject.toml").exists() or (search_path / ".git").is_dir():
            return None

        search_path = search_path.parent

    return None


def main():
    if _project_has_own_hooks():
        return

    branch_root = find_branch_root()

    if branch_root:
        prompt_file = branch_root / ".aipass" / "aipass_local_prompt.md"
        if prompt_file.exists():
            content = prompt_file.read_text().strip()
            branch_name = branch_root.name.upper()
            print(f"\n# Branch Context: {branch_name}\n<!-- Source: {prompt_file} -->\n{content}")


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from hook_log import run_and_log

    run_and_log("UserPromptSubmit", "provider", __file__, main)
