# =================== AIPass ====================
# Name: subagent_gate.py
# Version: 1.0.0
# Description: Checks modified Python files against seedgo standards on SubagentStop
# Branch: hooks
# Layer: apps/handlers/security
# Created: 2026-05-22
# Modified: 2026-05-22
# =============================================

"""Checks modified Python files against seedgo standards and blocks on violations."""

import json
import os
import subprocess
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger

_ALLOW = {"stdout": "", "exit_code": 0}


def _block(reason: str) -> dict:
    return {"stdout": json.dumps({"decision": "block", "reason": reason}), "exit_code": 2, "sound": "subagent gate"}


def _get_package_from_cwd(cwd: str) -> str:
    """Derive package name from CWD path (e.g., 'aipass' from src/aipass/hooks)."""
    parts = Path(cwd).parts
    for i, part in enumerate(parts):
        if part == "src" and i + 2 < len(parts):
            return parts[i + 1]
    return ""


def _find_repo_root(cwd: str) -> Path | None:
    """Walk up from AIPASS_HOME or CWD to find the git repo root."""
    for start in (os.environ.get("AIPASS_HOME", ""), cwd):
        if not start:
            continue
        p = Path(start)
        while p != p.parent:
            if (p / ".git").exists():
                return p
            p = p.parent
    return None


def _get_cwd_branch(cwd: str, repo_root: Path) -> str | None:
    """Detect which branch directory (src/<package>/<name>) the CWD is in."""
    package = _get_package_from_cwd(cwd)
    if not package:
        logger.info("[HOOKS] subagent_gate: CWD %s not inside src/<package>", cwd)
        return None
    src = repo_root / "src" / package
    try:
        rel = Path(cwd).resolve().relative_to(src)
        return rel.parts[0] if rel.parts else None
    except ValueError:
        logger.info("[HOOKS] subagent_gate: CWD %s not inside %s", cwd, src)
        return None


def _get_modified_py_files(cwd: str, repo_root: Path) -> list[str]:
    """Get modified .py files scoped to the CWD branch via drone."""
    cwd_branch = _get_cwd_branch(cwd, repo_root)
    package = _get_package_from_cwd(cwd)
    branch_dir = repo_root / "src" / package / cwd_branch if (cwd_branch and package) else None
    if not branch_dir or not branch_dir.exists():
        return []
    result = subprocess.run(
        ["drone", "@git", "status"],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(branch_dir),
    )
    files: list[str] = []
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
        full = repo_root / filepath
        if full.exists():
            files.append(str(full))
    return files


def _run_seedgo_checklist(file_path: str, repo_root: Path) -> list[str]:
    """Run seedgo checklist on a single file, return violation strings."""
    if "/.claude/" in file_path:
        return []
    result = subprocess.run(
        ["drone", "@seedgo", "checklist", file_path],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(repo_root),
    )
    if result.returncode != 0:
        return []
    violations: list[str] = []
    for line in result.stdout.split("\n"):
        line = line.strip()
        if line.startswith("✗"):
            v = line[1:].strip()
            if v:
                violations.append(v)
    return violations[:5]


def _check_hook_readme_accountability(cwd: str, repo_root: Path) -> str | None:
    """Return advisory if hook files changed without README update."""
    cwd_branch = _get_cwd_branch(cwd, repo_root)
    package = _get_package_from_cwd(cwd)
    branch_dir = repo_root / "src" / package / cwd_branch if (cwd_branch and package) else None
    if not branch_dir or not branch_dir.exists():
        return None
    result = subprocess.run(
        ["drone", "@git", "status", "--all"],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(branch_dir),
    )
    changed: list[str] = []
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
    return None


def handle(hook_data: dict) -> dict:
    """Check modified files against seedgo standards on subagent stop."""
    try:
        cwd = hook_data.get("cwd", "") or os.getcwd()
        repo_root = _find_repo_root(cwd)
        if repo_root is None:
            return _ALLOW

        modified = _get_modified_py_files(cwd, repo_root)
        if not modified:
            return _ALLOW

        readme_reminder = _check_hook_readme_accountability(cwd, repo_root)

        all_violations: dict[str, list[str]] = {}
        for f in modified:
            vs = _run_seedgo_checklist(f, repo_root)
            if vs:
                name = Path(f).name
                all_violations[name] = vs

        if all_violations:
            lines = ["Standards violations found in files you modified:\n"]
            for fname, vs in all_violations.items():
                lines.append(f"  {fname}:")
                for v in vs:
                    lines.append(f"    - {v}")
            lines.append("\nFix these violations before finishing.")
            if readme_reminder:
                lines.append(f"\n{readme_reminder}")
            return _block("\n".join(lines))

        if readme_reminder:
            result_data = {"decision": "allow", "reason": readme_reminder}
            return {"stdout": json.dumps(result_data), "exit_code": 0}

        return _ALLOW

    except Exception as exc:
        logger.info("[HOOKS] subagent_gate: unexpected error (allowing): %s", exc)
        return _ALLOW
