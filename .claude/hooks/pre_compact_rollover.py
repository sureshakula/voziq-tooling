#!/usr/bin/env python3
"""
Pre-Compact Rollover Hook — check branch memory files and run rollover if overdue.

Runs alongside pre_compact.py on PreCompact events. Scans all branches'
.trinity files for over-limit conditions and executes rollover via drone
if any are found. Stdout stays clean (pre_compact.py owns stdout for
context injection). All logging goes to stderr.

Version: 1.0.0
"""

import json
import subprocess
import sys
from pathlib import Path


def _find_repo_root():
    """Find the AIPass repo root (contains AIPASS_REGISTRY.json)."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "AIPASS_REGISTRY.json").exists():
            return parent
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "AIPASS_REGISTRY.json").exists():
            return parent
    return None


def _read_registry(repo_root):
    """Read branch list from AIPASS_REGISTRY.json."""
    registry_path = repo_root / "AIPASS_REGISTRY.json"
    if not registry_path.exists():
        return []
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        branches = data.get("branches", [])
        for branch in branches:
            raw_path = branch.get("path", "")
            resolved = Path(raw_path)
            if not resolved.is_absolute():
                resolved = repo_root / raw_path
            branch["_resolved_path"] = resolved
        return branches
    except Exception:
        return []


def _check_file(file_path):
    """Check if a .trinity memory file is overdue for rollover.

    Returns (overdue: bool, description: str) or (False, "") if not overdue.
    """
    if not file_path.is_file():
        return False, ""

    try:
        raw = file_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception:
        return False, ""

    metadata = data.get("document_metadata", {})
    schema_version = metadata.get("schema_version", "1.0.0")
    limits = metadata.get("limits", {})

    if schema_version.startswith("2"):
        reasons = []
        max_sessions = limits.get("max_sessions")
        if max_sessions is not None:
            sessions = data.get("sessions", [])
            if isinstance(sessions, list) and len(sessions) >= max_sessions:
                reasons.append(f"{len(sessions)}/{max_sessions} sessions")

        max_key_learnings = limits.get("max_key_learnings")
        if max_key_learnings is not None:
            key_learnings = data.get("key_learnings", {})
            if isinstance(key_learnings, dict) and len(key_learnings) >= max_key_learnings:
                reasons.append(f"{len(key_learnings)}/{max_key_learnings} learnings")

        max_observations = limits.get("max_observations")
        if max_observations is not None:
            observations = data.get("observations", [])
            if isinstance(observations, list) and len(observations) >= max_observations:
                reasons.append(f"{len(observations)}/{max_observations} observations")

        if reasons:
            return True, ", ".join(reasons)
        return False, ""

    # v1: line-count based
    max_lines = limits.get("max_lines", 600)
    current_lines = raw.count("\n") + 1
    if current_lines >= max_lines:
        return True, f"{current_lines}/{max_lines} lines"
    return False, ""


def _find_overdue(repo_root):
    """Scan all branches for overdue memory files. Returns list of (branch, type, reason)."""
    branches = _read_registry(repo_root)
    overdue = []

    for branch in branches:
        name = branch.get("name", "unknown")
        branch_path = branch.get("_resolved_path")
        if not branch_path or not branch_path.is_dir():
            continue

        for memory_type in ["local", "observations"]:
            file_path = branch_path / ".trinity" / f"{memory_type}.json"
            is_overdue, reason = _check_file(file_path)
            if is_overdue:
                overdue.append((name, memory_type, reason))

    return overdue


def _run_rollover(repo_root):
    """Execute rollover via drone subprocess. Returns (success, output)."""
    try:
        result = subprocess.run(
            ["drone", "@memory", "rollover", "run"],
            capture_output=True,
            text=True,
            timeout=110,
            cwd=str(repo_root),
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Rollover timed out (110s)"
    except Exception as e:
        return False, str(e)


def main():
    """Main hook entry point."""
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    try:
        repo_root = _find_repo_root()
        if not repo_root:
            sys.exit(0)

        overdue = _find_overdue(repo_root)
        if not overdue:
            sys.exit(0)

        summary = "; ".join(f"{name}.{mtype} ({reason})" for name, mtype, reason in overdue)
        print(f"Pre-compact rollover: {len(overdue)} overdue — {summary}", file=sys.stderr)

        success, output = _run_rollover(repo_root)
        if success:
            print(f"Pre-compact rollover: complete ({len(overdue)} files processed)", file=sys.stderr)
        else:
            print(f"Pre-compact rollover: failed — {output[:200]}", file=sys.stderr)

    except Exception as e:
        print(f"Pre-compact rollover error: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from hook_log import run_and_log

    run_and_log("PreCompact", "provider", __file__, main)
