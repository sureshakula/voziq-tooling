#!/usr/bin/env python3
"""
Email Notification Hook - Notifies of new emails on prompt submit.

Checks the current branch's inbox for unread emails and displays
a notification if any exist.

Version: 1.0.0
"""
import json
from pathlib import Path


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
    for _ in range(10):
        has_trinity = (search_path / ".trinity").is_dir()
        has_id = list(search_path.glob("*.id.json"))
        has_apps = (search_path / "apps").is_dir()
        has_mail = (search_path / ".ai_mail.local").is_dir() or (search_path / "ai_mail.local").is_dir()

        if (has_trinity or has_id or has_apps or has_mail) and search_path != repo_root:
            return search_path

        if search_path == repo_root:
            break

        parent = search_path.parent
        if parent == search_path:
            break
        search_path = parent

    return None


def count_new_emails(branch_root: Path) -> int:
    """Count new (unread) emails in the branch's inbox."""
    # Check both patterns: .ai_mail.local (canonical) and ai_mail.local (legacy)
    inbox_path = branch_root / ".ai_mail.local" / "inbox.json"
    if not inbox_path.exists():
        inbox_path = branch_root / "ai_mail.local" / "inbox.json"

    if not inbox_path.exists():
        return 0

    try:
        with open(inbox_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle both formats: {"messages": [...]} and bare [...]
        messages = data if isinstance(data, list) else data.get("messages", [])
        count = 0
        for msg in messages:
            if msg.get("status") == "new":
                count += 1
            elif msg.get("status") is None and not msg.get("read", False):
                count += 1

        return count

    except (json.JSONDecodeError, OSError):
        return 0


def main():
    branch_root = find_branch_root()
    if not branch_root:
        return

    new_count = count_new_emails(branch_root)
    if new_count > 0:
        plural = "s" if new_count != 1 else ""
        print(f"You have {new_count} new email{plural} - check with: drone @ai_mail inbox | then: drone @ai_mail view <id> | close with: drone @ai_mail close <id>")


if __name__ == "__main__":
    main()
