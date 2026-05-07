#!/usr/bin/env python3
"""
Identity Injector - Injects branch identity on every prompt.

Reads from [BRANCH].id.json and outputs core identity fields.
Finds the branch root by walking up from CWD looking for apps/ or *.id.json.

When CWD is inside a project that has its own UserPromptSubmit hooks,
this provider-level hook exits silently to avoid double-firing.

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


def find_repo_root() -> Path | None:
    """Find the repo root (contains pyproject.toml or .git)."""
    search = Path.cwd()
    while search.parent != search:
        if (search / "pyproject.toml").exists() or (search / ".git").is_dir():
            return search
        search = search.parent
    return None


def find_branch_root() -> Path | None:
    """Find the branch root directory by walking up from CWD."""
    cwd = Path.cwd()
    repo_root = find_repo_root()
    if not repo_root:
        return None

    search_path = cwd
    while search_path >= repo_root:
        has_trinity = (search_path / ".trinity").is_dir()
        has_id = list(search_path.glob("*.id.json"))

        if has_trinity or has_id:
            return search_path

        if search_path == repo_root:
            break
        search_path = search_path.parent

    return None


def find_id_file(branch_root: Path) -> Path | None:
    """Find the identity file for a branch (.trinity/passport.json or *.id.json)."""
    # AIPass pattern: .trinity/passport.json
    passport = branch_root / ".trinity" / "passport.json"
    if passport.exists():
        return passport
    # Dev-Pass fallback: *.id.json
    id_files = list(branch_root.glob("*.id.json"))
    if id_files:
        return id_files[0]
    return None


def format_identity(data: dict) -> str:
    """Format branch_info + identity for injection."""
    lines = []

    # Try branch_info first (enriched passports), fall back to identity block (setup.sh passports)
    branch = data.get("branch_info", {})
    identity = data.get("identity", {})
    name = branch.get("branch_name") or identity.get("name", "UNKNOWN")
    lines.append(f"# {name} Identity")
    lines.append(f"Path: {branch.get('path', 'unknown')}")
    lines.append(f"Email: {branch.get('email', 'unknown')}")

    identity = data.get("identity", {})
    if identity.get("role"):
        lines.append(f"Role: {identity['role']}")
    traits = identity.get("traits") or data.get("traits")
    if traits:
        if isinstance(traits, list):
            lines.append("Traits: " + " | ".join(traits))
        else:
            lines.append(f"Traits: {traits}")
    if identity.get("purpose"):
        lines.append(f"Purpose: {identity['purpose']}")

    what_i_do = identity.get("what_i_do", [])
    if what_i_do:
        lines.append("Do: " + " | ".join(what_i_do[:4]))

    what_i_dont_do = identity.get("what_i_dont_do", [])
    if what_i_dont_do:
        lines.append("Don't: " + " | ".join(what_i_dont_do[:3]))

    principles = data.get("principles", [])
    if principles:
        lines.append("Principles: " + " * ".join(principles))

    return "\n".join(lines)


def main():
    if _project_has_own_hooks():
        return

    branch_root = find_branch_root()
    if not branch_root:
        return

    id_file = find_id_file(branch_root)
    if not id_file or not id_file.exists():
        return

    try:
        data = json.loads(id_file.read_text(encoding="utf-8"))
        output = format_identity(data)
        if output:
            print(f"\n{output}")
    except (json.JSONDecodeError, KeyError):
        pass


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from hook_log import run_and_log

    run_and_log("UserPromptSubmit", "provider", __file__, main)
