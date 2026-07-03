# =================== AIPass ====================
# Name: update_ops.py
# Description: Update handler — path-based template sync engine (P1 rewrite, TDPLAN-0006)
# Version: 2.0.0
# Created: 2026-03-07
# Modified: 2026-06-06
# =============================================

"""Update handler — path-based template sync engine.

P1 rewrite (TDPLAN-0006, issue #636): replaces the broken ID-based
change-detection engine with explicit template walking. No renames,
no pruning, never touches identity/memory files.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from aipass.prax.apps.modules.logger import system_logger as logger

from aipass.spawn.apps.handlers.meta_ops import (
    generate_branch_meta,
    get_template_dir,
    load_template_registry,
    save_branch_meta,
)
from aipass.spawn.apps.handlers.json_ops import backup_json, deep_merge
from aipass.spawn.apps.handlers.placeholders import build_replacements_dict, replace_placeholders
from aipass.spawn.apps.handlers.registry import find_registry, load_registry, branches_as_list
from aipass.spawn.apps.handlers.json import json_handler

_NEVER_UPDATE_PREFIXES = (".trinity/",)
_NEVER_UPDATE_FILES = frozenset(
    {
        "DASHBOARD.local.json",
        "artifacts/birth_certificate.json",
        ".seedgo/bypass.json",
    }
)
_SKIP_TRACKING = frozenset(
    {
        ".spawn/.template_registry.json",
        ".spawn/.branch_meta.json",
    }
)


def _is_never_update(resolved_path: str) -> bool:
    """Check if a resolved path is in the create-only set."""
    if resolved_path in _NEVER_UPDATE_FILES:
        return True
    for prefix in _NEVER_UPDATE_PREFIXES:
        if resolved_path.startswith(prefix):
            return True
    return False


# =============================================================================
# PUBLIC API
# =============================================================================


def update_branch(branch_name: str, dry_run: bool = False, trace: bool = False) -> dict:
    """Update a single branch from its class template.

    Path-based engine: walks the template directory, resolves placeholder
    paths, and for each file decides add/merge/skip. No renames, no pruning.
    Identity files (.trinity/*, DASHBOARD, birth_certificate, bypass.json)
    are never touched — create-only.
    """
    errors: list[str] = []
    counts = {"additions": 0, "renames": 0, "updates": 0, "pruned": 0, "skipped_py": 0}
    additions_detail: list[dict] = []
    updates_detail: list[dict] = []

    branch_dir = _resolve_branch_path(branch_name)
    if branch_dir is None:
        return _result(branch_name, False, counts, [f"Branch '{branch_name}' not found in registry"], dry_run)
    if not branch_dir.is_dir():
        return _result(branch_name, False, counts, [f"Branch directory does not exist: {branch_dir}"], dry_run)

    if trace:
        logger.info("[update] Resolved %s -> %s", branch_name, branch_dir)

    citizen_class = _read_citizen_class(branch_dir)
    template_dir = get_template_dir(citizen_class)

    if not template_dir.is_dir():
        return _result(branch_name, False, counts, [f"Template directory not found: {template_dir}"], dry_run)

    if trace:
        logger.info("[update] Citizen class: %s, template: %s", citizen_class, template_dir)

    replacements = build_replacements_dict(branch_dir, branch_name)

    # Walk template directories — create missing ones in branch
    for template_subdir in sorted(template_dir.rglob("*")):
        if not template_subdir.is_dir():
            continue
        if "__pycache__" in template_subdir.parts:
            continue
        rel_dir = template_subdir.relative_to(template_dir).as_posix()
        resolved_dir = replace_placeholders(rel_dir, replacements)
        if _is_never_update(resolved_dir + "/"):
            continue
        if resolved_dir in _SKIP_TRACKING:
            continue
        dest_dir = branch_dir / resolved_dir
        if not dest_dir.exists():
            if not dry_run:
                dest_dir.mkdir(parents=True, exist_ok=True)
            additions_detail.append({"template_path": resolved_dir, "type": "directory"})
            counts["additions"] += 1
            if trace:
                logger.info("[update] Added directory: %s", resolved_dir)

    # Walk template files — add/merge/skip per type
    for template_file in sorted(template_dir.rglob("*")):
        if not template_file.is_file():
            continue
        if "__pycache__" in template_file.parts:
            continue

        rel_path = template_file.relative_to(template_dir).as_posix()

        if rel_path in _SKIP_TRACKING:
            continue

        resolved_path = replace_placeholders(rel_path, replacements)

        if _is_never_update(resolved_path):
            if trace:
                logger.info("[update] SKIP (create-only): %s", resolved_path)
            continue

        dest = branch_dir / resolved_path

        if not dest.exists():
            # ADDITION — missing file from template
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    content = template_file.read_text(encoding="utf-8")
                    content = replace_placeholders(content, replacements)
                    dest.write_text(content, encoding="utf-8")
                except (UnicodeDecodeError, UnicodeEncodeError) as enc_err:
                    logger.warning("[update] Binary file, copying directly: %s (%s)", resolved_path, enc_err)
                    shutil.copy2(template_file, dest)
            additions_detail.append({"template_path": resolved_path, "type": "file"})
            counts["additions"] += 1
            if trace:
                logger.info("[update] Added: %s", resolved_path)

        elif dest.suffix == ".py":
            counts["skipped_py"] += 1
            updates_detail.append({"template_path": rel_path, "branch_path": resolved_path})
            if trace:
                logger.info("[update] SKIP .py: %s", resolved_path)

        elif dest.suffix == ".json":
            result = _merge_json(template_file, dest, replacements, dry_run, trace, branch_dir / ".spawn" / ".recovery")
            if result == "updated":
                counts["updates"] += 1
                updates_detail.append({"template_path": rel_path, "branch_path": resolved_path})
            elif result == "error":
                errors.append(f"JSON merge failed for {resolved_path}")

    # Refresh branch metadata (informational tracking)
    if not dry_run:
        template_registry = load_template_registry(template_dir)
        if template_registry:
            updated_meta = generate_branch_meta(branch_dir, template_registry)
            updated_meta["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
            save_branch_meta(branch_dir, updated_meta)

    success = len(errors) == 0
    if success and not dry_run:
        json_handler.log_operation("update_executed", data={"branch": branch_name})

    return _result(
        branch_name,
        success,
        counts,
        errors,
        dry_run,
        _additions_detail=additions_detail,
        _updates_detail=updates_detail,
        _renames_detail=[],
        _pruned_detail=[],
    )


def update_all(dry_run: bool = False, trace: bool = False, citizen_class: str | None = None) -> list[dict]:
    """Update all branches from AIPASS_REGISTRY.json.

    Iterates through all registered branches, calls update_branch() for each.
    Skips spawn itself (can't update yourself).
    When citizen_class is specified, only updates branches of that class.
    Returns list of result dicts.
    """
    registry_path = find_registry()
    registry = load_registry(registry_path)
    branches = branches_as_list(registry.get("branches", []))

    if not branches:
        return []

    results: list[dict] = []

    for branch_entry in branches:
        name = branch_entry.get("name", "")
        lower_name = name.lower()

        if lower_name == "spawn":
            if trace:
                logger.info("[update] Skipping spawn (self)")
            continue

        if citizen_class:
            branch_dir = _resolve_branch_path(lower_name)
            if branch_dir and branch_dir.is_dir():
                actual_class = _read_citizen_class(branch_dir)
                if actual_class != citizen_class:
                    if trace:
                        logger.info("[update] Skipping %s (class=%s, filter=%s)", name, actual_class, citizen_class)
                    continue

        if trace:
            logger.info("[update] Processing branch: %s", name)

        try:
            result = update_branch(lower_name, dry_run=dry_run, trace=trace)
            results.append(result)
        except Exception as exc:
            logger.error("[update] Error updating %s: %s", name, exc)
            results.append(
                {
                    "branch": lower_name,
                    "success": False,
                    "additions": 0,
                    "renames": 0,
                    "updates": 0,
                    "pruned": 0,
                    "skipped_py": 0,
                    "errors": [str(exc)],
                    "dry_run": dry_run,
                }
            )

    return results


# =============================================================================
# INTERNAL HELPERS
# =============================================================================


def _read_citizen_class(branch_dir: Path) -> str:
    """Read citizen_class from a branch's passport.json."""
    from aipass.spawn.apps.handlers.class_registry import validate_class

    passport_path = branch_dir / ".trinity" / "passport.json"
    if not passport_path.exists():
        return "aipass_framework"
    try:
        data = json.loads(passport_path.read_text(encoding="utf-8"))
        citizen_class = data.get("identity", {}).get("citizen_class", "aipass_framework")
        if not validate_class(citizen_class):
            logger.warning(
                "[update] Unknown citizen_class '%s' in %s, falling back to 'aipass_framework'",
                citizen_class,
                passport_path,
            )
            return "aipass_framework"
        return citizen_class
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("[update] Failed to read citizen_class from passport %s: %s", passport_path, e)
        return "aipass_framework"


def _resolve_branch_path(branch_name: str) -> Path | None:
    """Resolve a branch name to its absolute directory path via the registry."""
    registry_path = find_registry()
    project_root = registry_path.parent
    registry = load_registry(registry_path)

    for branch in branches_as_list(registry.get("branches", [])):
        reg_name = branch.get("name", "")
        if reg_name.lower() == branch_name.lower():
            rel_path = branch.get("path", "")
            if rel_path:
                return (project_root / rel_path).resolve()

    return None


def _merge_json(
    template_file: Path,
    dest: Path,
    replacements: dict,
    dry_run: bool,
    trace: bool,
    backup_dest: Path | None = None,
) -> str:
    """Deep-merge a template JSON file into the branch copy.

    Returns "updated", "unchanged", or "error".
    """
    try:
        template_content = template_file.read_text(encoding="utf-8")
        template_content = replace_placeholders(template_content, replacements)
        template_data = json.loads(template_content)

        existing_text = dest.read_text(encoding="utf-8")
        existing_data = json.loads(existing_text)

        merged = deep_merge(template_data, existing_data)
        merged_text = json.dumps(merged, indent=2, ensure_ascii=False) + "\n"

        if merged_text == existing_text:
            if trace:
                logger.info("[update] JSON unchanged: %s", dest.name)
            return "unchanged"

        if not dry_run:
            backup_json(dest, backup_dir=backup_dest)
            dest.write_text(merged_text, encoding="utf-8")

        if trace:
            logger.info("[update] JSON merged: %s", dest.name)
        return "updated"

    except (json.JSONDecodeError, IOError) as exc:
        logger.error("[update] JSON merge failed for %s: %s", dest.name, exc)
        return "error"


# =============================================================================
# RESULT HELPERS
# =============================================================================


def _result(
    branch_name: str,
    success: bool,
    counts: dict,
    errors: list[str],
    dry_run: bool,
    **extra: Any,
) -> dict:
    """Build a standardized result dict."""
    result = {
        "branch": branch_name,
        "success": success,
        "additions": counts.get("additions", 0),
        "renames": counts.get("renames", 0),
        "updates": counts.get("updates", 0),
        "pruned": counts.get("pruned", 0),
        "skipped_py": counts.get("skipped_py", 0),
        "errors": errors,
        "dry_run": dry_run,
    }
    result.update(extra)
    return result
