#!/usr/bin/env python3
"""Gemini BeforeModel hook: inject per-turn AIPass context."""
import json
import sys
from datetime import datetime
from pathlib import Path


def find_repo_root():
    p = Path.cwd()
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    return None


def get_branch_from_cwd(repo_root):
    cwd = Path.cwd()
    try:
        rel = cwd.relative_to(repo_root / "src" / "aipass")
        return str(rel).split("/")[0]
    except ValueError:
        try:
            rel = cwd.relative_to(repo_root / "src")
            return str(rel).split("/")[0]
        except ValueError:
            return None


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception:
        input_data = {}

    repo_root = find_repo_root()
    if not repo_root:
        print(json.dumps({}))
        return

    context_parts = []

    now = datetime.now().strftime("%A, %B %-d %Y — %-I:%M %p")
    context_parts.append(f"# Current Time: {now}")

    branch = get_branch_from_cwd(repo_root)
    if branch:
        branch_dir = repo_root / "src" / "aipass" / branch
        if not branch_dir.exists():
            branch_dir = repo_root / "src" / branch

        passport = branch_dir / ".trinity" / "passport.json"
        if passport.exists():
            try:
                data = json.loads(passport.read_text(encoding="utf-8"))
                identity = data.get("identity", {})
                traits = data.get("traits", [])
                context_parts.append(
                    f"# {branch.upper()} Identity\n"
                    f"Path: {data.get('branch_info', {}).get('path', 'unknown')}\n"
                    f"Role: {identity.get('role', 'unknown')}\n"
                    f"Traits: {' | '.join(traits)}\n"
                    f"Purpose: {identity.get('purpose', 'unknown')}"
                )
            except Exception:
                pass

        inbox = branch_dir / ".ai_mail.local" / "inbox.json"
        if inbox.exists():
            try:
                mail = json.loads(inbox.read_text(encoding="utf-8"))
                unread = mail.get("unread_count", 0)
                if unread > 0:
                    context_parts.append(
                        f"You have {unread} new emails - check with: "
                        f"drone @ai_mail inbox"
                    )
            except Exception:
                pass

    if context_parts:
        context = "\n\n".join(context_parts)
        output = {
            "hookSpecificOutput": {
                "hookEventName": "BeforeModel",
                "additionalContext": context
            }
        }
    else:
        output = {}

    print(json.dumps(output))


if __name__ == "__main__":
    main()
