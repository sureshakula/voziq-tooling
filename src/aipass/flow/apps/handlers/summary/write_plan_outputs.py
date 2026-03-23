# =================== AIPass ====================
# Name: write_plan_outputs.py
# Description: Write Plan Outputs Handler
# Version: 1.1.0
# Created: 2025-11-07
# Modified: 2025-11-07
# =============================================

"""
Write Plan Outputs Handler

Writes plan summaries to both global and branch-local files.

Features:
- Writes CLAUDE.json (global system-wide file)
- Writes CLAUDE.local.md (per-branch files)
- Handles active and closed plans
- Generates clickable links with file_uri and vscode_uri
- Filters empty plans based on config
- Reusable across Flow modules

Global vs Local Pattern:
- **Global:** {repo_root}/CLAUDE.json (all plans, all branches)
- **Local:** {repo_root}/src/aipass/[branch]/CLAUDE.local.md (branch-specific)

Usage:
    from aipass.flow.apps.handlers.summary.write_plan_outputs import write_plan_outputs

    summaries = {
        "0001": {"summary": "...", "status": "open", "file_path": "...", ...},
        "0002": {"summary": "...", "status": "closed", "file_path": "...", ...}
    }
    write_plan_outputs(summaries)
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from aipass.flow.apps.handlers.json import json_handler
from aipass.prax.apps.modules.logger import system_logger as logger

# INFRASTRUCTURE IMPORT PATTERN
_PKG_ROOT = Path(__file__).resolve().parents[4]
FLOW_ROOT = _PKG_ROOT / "flow"

# =============================================
# CONFIGURATION
# =============================================

MODULE_NAME = "write_plan_outputs"


def _find_repo_root() -> Path:
    """Walk up from this file to find the repo root (contains AIPASS_REGISTRY.json)."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "AIPASS_REGISTRY.json").exists():
            return parent
    return Path.cwd()


_REPO_ROOT = _find_repo_root()
CLAUDE_JSON_FILE = _REPO_ROOT / "CLAUDE.json"

# =============================================
# HELPER FUNCTIONS
# =============================================

def _normalize_plan_entry(plan_num: str, info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalize plan metadata for downstream outputs.

    Args:
        plan_num: Plan number (e.g., "0001")
        info: Raw plan info from registry/summaries

    Returns:
        Normalized plan entry dict or None if invalid
    """
    plan_id = f"FPLAN-{plan_num}"
    file_path = info.get("file_path", "")
    path_obj: Optional[Path] = None

    if file_path:
        path_obj = Path(file_path)
        if not path_obj.is_absolute():
            path_obj = _PKG_ROOT / file_path

    branch_dir: Optional[Path] = None
    branch_relative_path = ""

    if path_obj is not None:
        if path_obj.is_file():
            branch_dir = path_obj.parent
        elif path_obj.exists():
            branch_dir = path_obj

        try:
            branch_relative_path = str(path_obj.relative_to(_PKG_ROOT))
        except Exception as exc:
            logger.warning("[write_plan_outputs] Could not resolve relative path for plan %s: %s", plan_num, exc)
            branch_relative_path = str(path_obj)
    else:
        branch_relative_path = file_path

    branch_name = (info.get("location") or "").split("/", 1)[0]

    if not branch_name and branch_relative_path:
        branch_name = branch_relative_path.split("/", 1)[0]

    if branch_dir is not None and not branch_name:
        try:
            branch_name = branch_dir.relative_to(_PKG_ROOT).parts[0]
        except Exception as exc:
            logger.warning("[write_plan_outputs] Could not determine branch name from dir for plan %s: %s", plan_num, exc)
            branch_name = branch_dir.name if branch_dir.name else "unknown"

    entry = {
        "plan": plan_id,
        "status": info.get("status", "unknown"),
        "summary": info.get("summary", ""),
        "subject": info.get("subject", ""),
        "branch": branch_name or "unknown",
        "location": info.get("location", "unknown"),
        "file_path": file_path,
        "relative_path": branch_relative_path,
        "generated_at": info.get("generated_at"),
        "is_empty": info.get("is_empty", False),
        "branch_path": None,
        "branch_relative_path": ""
    }

    if path_obj is not None and branch_dir is not None:
        try:
            entry["branch_relative_path"] = str(path_obj.relative_to(branch_dir))
        except Exception as exc:
            logger.warning("[write_plan_outputs] Could not compute branch-relative path for plan %s: %s", plan_num, exc)
            entry["branch_relative_path"] = entry["relative_path"]

    if path_obj is not None:
        entry["absolute_path"] = str(path_obj)
        try:
            entry["file_uri"] = path_obj.as_uri()
        except ValueError as exc:
            logger.warning("[write_plan_outputs] Could not generate file URI for plan %s: %s", plan_num, exc)
            entry["file_uri"] = None

        entry["vscode_uri"] = f"vscode://file{entry['absolute_path']}" if entry.get("absolute_path") else None

    if branch_dir is not None:
        try:
            branch_dir.relative_to(_PKG_ROOT)
            entry["branch_path"] = branch_dir
        except Exception as exc:
            logger.warning("[write_plan_outputs] Branch dir outside package root for plan %s: %s", plan_num, exc)
            entry["branch_path"] = None

    return entry


def _build_plan_output_sets(summaries: Dict[str, Any]):
    """
    Partition plan entries into central and branch-specific collections.

    Args:
        summaries: Dict of plan_number -> plan_info

    Returns:
        Tuple of (active_entries, closed_entries, branch_map)
    """
    active_entries = []
    closed_entries = []
    branch_map: Dict[Path, Dict[str, Any]] = {}

    for plan_num in sorted(summaries.keys()):
        entry = _normalize_plan_entry(plan_num, summaries[plan_num])
        if entry is None:
            continue

        json_entry = {k: v for k, v in entry.items() if k not in {"branch_path"} and v is not None}

        if entry["status"] == "closed":
            closed_entries.append(json_entry)
        else:
            active_entries.append(json_entry)

        branch_path = entry.get("branch_path")
        if branch_path:
            branch_bucket = branch_map.setdefault(
                branch_path,
                {"branch_name": entry["branch"], "active": [], "closed": []}
            )
            branch_entry = {k: v for k, v in entry.items() if k != "branch_path" and v is not None}
            if entry["status"] == "closed":
                branch_bucket["closed"].append(branch_entry)
            else:
                branch_bucket["active"].append(branch_entry)

    return active_entries, closed_entries, branch_map


def _write_central_summary_json(active_entries: list, closed_entries: list) -> bool:
    """
    Persist aggregated plan data to CLAUDE.json (global file).

    Args:
        active_entries: List of active plan entries
        closed_entries: List of closed plan entries

    Returns:
        True if successful, False otherwise
    """
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active_plans": active_entries,
        "recently_closed": closed_entries[-5:],
        "statistics": {
            "active_count": len(active_entries),
            "total_closed": len(closed_entries),
            "recently_closed_included": min(len(closed_entries), 5)
        }
    }

    try:
        with open(CLAUDE_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return True
    except Exception as exc:
        logger.error("[write_plan_outputs] Failed to write central summary JSON: %s", exc)
        return False


def _format_plan_lines(entries: list, default_message: str) -> list:
    """
    Format plan entries as markdown bullet lines.

    Args:
        entries: List of plan entry dicts
        default_message: Message to show if list is empty

    Returns:
        List of markdown-formatted lines
    """
    if not entries:
        return [default_message]

    lines = []
    for entry in entries:
        plan_id = entry["plan"]
        icon = "✅" if entry["status"] == "closed" else ("⚪" if entry.get("is_empty") else "🟢")

        # Construct proper link with filename (not just directory)
        relative_path = entry.get("branch_relative_path") or entry.get("relative_path")
        if relative_path:
            # Use relative path + plan_id.md for clean links
            link_target = f"{relative_path}/{plan_id}.md"
        else:
            link_target = entry.get("file_path")

        if link_target:
            plan_link = f"[{plan_id}]({link_target})"
        else:
            plan_link = plan_id

        lines.append(f"- {plan_link} ({entry.get('branch', 'unknown')}) {icon}")
        lines.append(f"  {entry.get('summary', '')}")
    return lines


def _write_branch_local_files(branch_map: Dict[Path, Dict[str, Any]]) -> bool:
    """
    Write CLAUDE.local.md files for each branch (local files).

    Args:
        branch_map: Dict of branch_path -> {branch_name, active, closed}

    Returns:
        True if all writes successful, False if any failed
    """
    all_success = True

    for branch_path, data in branch_map.items():
        branch_name = data.get("branch_name") or branch_path.name
        file_path = branch_path / "CLAUDE.local.md"

        lines = [
            "⚠️ WARNING: This file is automatically updated by the flow system. Manual edits will be overwritten.",
            "",
            f"## Plan Summaries — {branch_name}",
            ""
        ]

        lines.append("Active Plans:")
        lines.extend(_format_plan_lines(data.get("active", []), "- None"))
        lines.append("")

        lines.append("Recently Closed:")
        recent_closed = data.get("closed", [])[-5:]
        lines.extend(_format_plan_lines(recent_closed, "- None"))
        lines.append("")

        content = "\n".join(lines).rstrip() + "\n"

        try:
            branch_path.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as exc:
            logger.error("[write_plan_outputs] Failed to write branch-local file for '%s': %s", branch_name, exc)
            all_success = False

    return all_success

# =============================================
# HANDLER FUNCTION
# =============================================

def write_plan_outputs(summaries: Dict[str, Any], hide_empty: bool = True) -> bool:
    """
    Write centralized JSON and branch-local markdown outputs.

    This is the main function that orchestrates writing to both:
    - CLAUDE.json (global system-wide file)
    - CLAUDE.local.md (per-branch files)

    Args:
        summaries: Dict of plan_number -> plan_info
        hide_empty: Whether to hide empty plans from output (default True)

    Returns:
        True if all writes successful, False if any failed

    Example:
        >>> summaries = {
        ...     "0001": {
        ...         "summary": "Task description",
        ...         "status": "open",
        ...         "file_path": "flow/plans/FPLAN-0001.md",
        ...         "subject": "Flow restructuring",
        ...         "location": "flow",
        ...         "is_empty": False
        ...     }
        ... }
        >>> write_plan_outputs(summaries)
        True
    """
    # Filter empty plans if configured
    filtered_summaries = {}
    for plan_num, info in summaries.items():
        if hide_empty and info.get("is_empty") and info.get("status") != "closed":
            continue
        filtered_summaries[plan_num] = info

    # Build output sets
    active_entries, closed_entries, branch_map = _build_plan_output_sets(filtered_summaries)

    # Write global and local files
    global_success = _write_central_summary_json(active_entries, closed_entries)
    local_success = _write_branch_local_files(branch_map)

    if global_success and local_success:
        json_handler.log_operation("plan_outputs_written", {
            "active_plans": len(active_entries),
            "closed_plans": len(closed_entries),
            "branches_written": len(branch_map),
            "success": True,
        })

    return global_success and local_success
