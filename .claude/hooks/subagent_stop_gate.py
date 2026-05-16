#!/usr/bin/env python3
"""
SubagentStop Gate — Checks files modified by subagents before allowing them to finish.

Runs seedgo checklist + basic validation on any .py files the subagent touched.
If violations found, blocks the stop and tells the subagent to fix them.

Version: 1.0.0
"""

import json
import os
import sys
import subprocess
from pathlib import Path


def _find_repo_root() -> Path | None:
    """Walk up from CWD or AIPASS_HOME to find the git repo root."""
    for start in (os.environ.get("AIPASS_HOME", ""), os.getcwd()):
        p = Path(start)
        while p != p.parent:
            if (p / ".git").exists():
                return p
            p = p.parent
    return None


AIPASS_ROOT = _find_repo_root()


def _get_cwd_branch() -> str | None:
    """Detect which branch directory (src/aipass/<name>) the CWD is in."""
    cwd = Path.cwd().resolve()
    if AIPASS_ROOT is None:
        return None
    src = AIPASS_ROOT / "src" / "aipass"
    try:
        rel = cwd.relative_to(src)
        return rel.parts[0] if rel.parts else None
    except ValueError:
        return None


def get_modified_py_files() -> list[str]:
    """Get Python files modified in the working tree, scoped to the CWD branch.

    Uses drone @git status (branch-scoped) instead of raw git to comply with
    git_gate enforcement. Only returns .py files inside the current branch.
    """
    if AIPASS_ROOT is None:
        return []
    cwd_branch = _get_cwd_branch()
    branch_dir = AIPASS_ROOT / "src" / "aipass" / cwd_branch if cwd_branch else None
    if not branch_dir or not branch_dir.exists():
        return []
    try:
        result = subprocess.run(
            ["drone", "@git", "status"], capture_output=True, text=True, timeout=10, cwd=str(branch_dir)
        )
        files = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line or "file(s) changed" in line:
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            _, filepath = parts
            if not filepath.endswith(".py") or filepath.startswith(".claude/"):
                continue
            full = AIPASS_ROOT / filepath
            if full.exists():
                files.append(str(full))
        return files
    except Exception:
        return []


def run_seedgo_checklist(file_path: str) -> list[str]:
    """Run seedgo checklist on a single file."""
    if AIPASS_ROOT is None:
        return []
    if "/.claude/" in file_path:
        return []
    try:
        result = subprocess.run(
            ["drone", "@seedgo", "checklist", file_path],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(AIPASS_ROOT),
        )
        if result.returncode != 0:
            return []
        violations = []
        for line in result.stdout.split("\n"):
            line = line.strip()
            if line.startswith("\u2717"):
                v = line[1:].strip()
                if v:
                    violations.append(v)
        return violations[:5]
    except Exception:
        return []


def check_hook_readme_accountability() -> str | None:
    """Check if hook files changed but README wasn't updated. Returns reminder or None."""
    if AIPASS_ROOT is None:
        return None
    cwd_branch = _get_cwd_branch()
    branch_dir = AIPASS_ROOT / "src" / "aipass" / cwd_branch if cwd_branch else None
    if not branch_dir or not branch_dir.exists():
        return None
    try:
        result = subprocess.run(
            ["drone", "@git", "status", "--all"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(branch_dir),
        )
        changed = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line or "file(s) changed" in line:
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                changed.append(parts[1])

        hook_files_changed = any(f.startswith(".claude/hooks/") and f.endswith(".py") for f in changed)
        readme_changed = ".claude/hooks/README.md" in changed

        if hook_files_changed and not readme_changed:
            return (
                "Hook files were modified but .claude/hooks/README.md was not updated. "
                "Consider updating the README to reflect your changes."
            )
    except Exception:
        pass
    return None


def main():
    try:
        json.load(sys.stdin)

        modified = get_modified_py_files()
        if not modified:
            return  # Nothing to check

        readme_reminder = check_hook_readme_accountability()

        all_violations = {}
        for f in modified:
            vs = run_seedgo_checklist(f)
            if vs:
                name = Path(f).name
                all_violations[name] = vs

        if all_violations:
            # Build the block reason
            lines = ["Standards violations found in files you modified:\n"]
            for fname, vs in all_violations.items():
                lines.append(f"  {fname}:")
                for v in vs:
                    lines.append(f"    - {v}")
            lines.append("\nFix these violations before finishing.")

            if readme_reminder:
                lines.append(f"\n⚠️ {readme_reminder}")

            output = {"decision": "block", "reason": "\n".join(lines)}
            print(json.dumps(output))
        elif readme_reminder:
            output = {"decision": "allow", "reason": f"⚠️ {readme_reminder}"}
            print(json.dumps(output))

    except Exception:
        pass  # Silent fail — don't block on errors


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from hook_log import run_and_log

    run_and_log("SubagentStop", "provider", __file__, main)
