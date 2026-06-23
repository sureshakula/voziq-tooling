#!/usr/bin/env python3
"""Codex SessionStart hook: inject AIPass identity context.

Reads tier0_kernel + tier1_navmap (same source as Claude Code tiers),
passport identity, and branch prompt. Outputs Codex-format JSON with
additionalContext. Codex fires once at SessionStart — no per-turn cadence.
"""

import json
import sys
from pathlib import Path


def find_repo_root():
    """Walk up to find .git directory."""
    p = Path.cwd()
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    return None


def get_branch_from_cwd(repo_root):
    """Determine branch name from CWD relative to repo."""
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
        json.loads(sys.stdin.read())
    except Exception:
        pass

    repo_root = find_repo_root()
    if not repo_root:
        print(json.dumps({}))
        return

    context_parts = []

    # 1. Tiered prompts (same source as Claude Code tiers)
    tier0 = repo_root / ".aipass" / "tier0_kernel.md"
    if tier0.exists():
        context_parts.append(tier0.read_text(encoding="utf-8")[:2500])
    tier1 = repo_root / ".aipass" / "tier1_navmap.md"
    if tier1.exists():
        context_parts.append(tier1.read_text(encoding="utf-8")[:8000])

    # 2. Branch identity
    branch = get_branch_from_cwd(repo_root)
    if branch:
        branch_dir = repo_root / "src" / "aipass" / branch
        if not branch_dir.exists():
            branch_dir = repo_root / "src" / branch

        # Passport
        passport = branch_dir / ".trinity" / "passport.json"
        if passport.exists():
            try:
                data = json.loads(passport.read_text(encoding="utf-8"))
                identity = data.get("identity", {})
                context_parts.append(
                    f"# Branch Identity: {branch.upper()}\n"
                    f"Role: {identity.get('role', 'unknown')}\n"
                    f"Purpose: {identity.get('purpose', 'unknown')}\n"
                    f"Class: {identity.get('citizen_class', 'unknown')}"
                )
            except Exception:
                pass

        # Branch prompt
        branch_prompt = branch_dir / ".aipass" / "aipass_local_prompt.md"
        if branch_prompt.exists():
            context_parts.append(branch_prompt.read_text(encoding="utf-8")[:4000])

    if context_parts:
        context = "\n\n---\n\n".join(context_parts)
        output = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}
    else:
        output = {}

    print(json.dumps(output))


if __name__ == "__main__":
    main()
