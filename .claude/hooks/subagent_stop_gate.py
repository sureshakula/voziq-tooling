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

    Only returns files inside the current branch's directory (or repo-root files).
    This prevents dispatched agents' changes from triggering violations on the
    orchestrator or other agents sharing the worktree.
    """
    if AIPASS_ROOT is None:
        return []
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"], capture_output=True, text=True, timeout=5, cwd=str(AIPASS_ROOT)
        )
        cwd_branch = _get_cwd_branch()
        files = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line.endswith(".py") and not line.startswith(".claude/"):
                if cwd_branch and line.startswith("src/aipass/"):
                    file_branch = line.split("/")[2] if len(line.split("/")) > 2 else None
                    if file_branch and file_branch != cwd_branch:
                        continue
                full = AIPASS_ROOT / line
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


def main():
    try:
        input_data = json.load(sys.stdin)

        modified = get_modified_py_files()
        if not modified:
            return  # Nothing to check

        all_violations = {}
        for f in modified:
            vs = run_seedgo_checklist(f)
            if vs:
                name = Path(f).name
                all_violations[name] = vs

        if not all_violations:
            return  # All clear

        # Build the block reason
        lines = ["Standards violations found in files you modified:\n"]
        for fname, vs in all_violations.items():
            lines.append(f"  {fname}:")
            for v in vs:
                lines.append(f"    - {v}")
        lines.append("\nFix these violations before finishing.")

        output = {"decision": "block", "reason": "\n".join(lines)}
        print(json.dumps(output))

    except Exception:
        pass  # Silent fail — don't block on errors


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from hook_log import run_and_log

    run_and_log("SubagentStop", "provider", __file__, main)
