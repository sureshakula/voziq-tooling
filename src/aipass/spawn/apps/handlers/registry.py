# =================== AIPass ====================
# Name: registry.py
# Description: *_REGISTRY.json discovery and CRUD operations
# Version: 1.0.0
# Created: 2026-03-05
# Modified: 2026-06-10
# =============================================

"""*_REGISTRY.json discovery and CRUD operations."""

import sys
from datetime import datetime
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger
from aipass.spawn.apps.handlers.json import json_handler


def branches_as_list(branches):
    """Normalize branches to a list regardless of storage format.

    The registry may store branches as:
    - A list of dicts (legacy format)
    - A dict keyed by name (dict format from setup.sh)

    Returns:
        list of branch entry dicts
    """
    if isinstance(branches, dict):
        return list(branches.values())
    if isinstance(branches, list):
        return branches
    return []


def find_registry(start_path=None):
    """Find *_REGISTRY.json — walks up from start_path only.

    Does NOT pass package_root — prevents silent registration in
    AIPass's own registry when creating agents in external projects.

    Args:
        start_path: Directory to start searching from.

    Returns:
        Path to *_REGISTRY.json.
    """
    from aipass.aipass.shared.registry_discovery import find_registry as _common_find

    return _common_find(start_path=start_path)


def load_registry(registry_path):
    """
    Load registry from JSON file. Returns empty schema if missing.

    Args:
        registry_path: Path to AIPASS_REGISTRY.json

    Returns:
        Dict with metadata and branches list
    """
    registry_path = Path(registry_path)
    if not registry_path.exists():
        return {
            "metadata": {
                "version": "1.0.0",
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "total_branches": 0,
            },
            "branches": [],
        }

    data = json_handler.read_json(registry_path)
    if data is not None:
        return data
    return {
        "metadata": {
            "version": "1.0.0",
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "total_branches": 0,
        },
        "branches": [],
    }


def save_registry(registry_path, data):
    """
    Save registry to JSON file. Auto-updates timestamp and sorts branches.

    Args:
        registry_path: Path to AIPASS_REGISTRY.json
        data: Registry dict to save

    Returns:
        True on success, False on error
    """
    registry_path = Path(registry_path)
    data["metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    if "branches" in data:
        branches = data["branches"]
        if isinstance(branches, dict):
            branch_list = list(branches.values())
        else:
            branch_list = branches
        data["branches"] = sorted(branch_list, key=lambda b: b.get("name", ""))

    return json_handler.write_json(registry_path, data)


def get_next_citizen_number(registry_path):
    """Get next citizen number from registry (count of existing branches + 1).

    Args:
        registry_path: Path to AIPASS_REGISTRY.json

    Returns:
        int: Next citizen number
    """
    data = load_registry(registry_path)
    branches = data.get("branches", [])
    return len(branches_as_list(branches)) + 1


def _validate_path_containment(branch_path, registry_path):
    """Reject paths that escape the project root (directory containing the registry)."""
    registry_root = Path(registry_path).resolve().parent
    bp = Path(branch_path)
    resolved = (registry_root / bp).resolve() if not bp.is_absolute() else bp.resolve()
    try:
        resolved.relative_to(registry_root)
        return True
    except ValueError:
        logger.warning("[registry] Path %s is outside project root %s", resolved, registry_root)
        return False


def add_to_registry(registry_path, branch_name, branch_path, profile, email, purpose="", registry_id=""):
    """
    Add a new branch entry to the registry.

    Uses file locking around the entire read-modify-write cycle to prevent
    corruption from concurrent spawns. Skips locking on Windows.

    Args:
        registry_path: Path to AIPASS_REGISTRY.json
        branch_name: Uppercase branch name (e.g. "MY_AGENT")
        branch_path: Absolute path to branch directory
        profile: Profile string (e.g. "AIPass Workshop")
        email: Branch email (e.g. "@my_agent")
        purpose: Optional purpose description

    Returns:
        True if added, False if already exists or error
    """
    registry_path = Path(registry_path)

    if not _validate_path_containment(branch_path, registry_path):
        logger.error("[registry] Path containment violation: %s escapes project root", branch_path)
        return False

    lock_path = registry_path.parent / f".{registry_path.stem}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        lock_fd = None
    else:
        import fcntl

        lock_fd = open(lock_path, "w", encoding="utf-8")  # noqa: SIM115
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

    try:
        registry = load_registry(registry_path)
        branches = registry.get("branches", [])

        if isinstance(branches, dict):
            if branch_name in branches:
                return False
        else:
            for branch in branches:
                if branch.get("name") == branch_name:
                    return False

        today = datetime.now().strftime("%Y-%m-%d")
        entry = {
            "name": branch_name,
            "path": Path(branch_path).as_posix(),
            "profile": profile,
            "description": purpose or "New agent - purpose TBD",
            "email": email,
            "status": "active",
            "created": today,
            "last_active": today,
        }
        if registry_id:
            entry["registry_id"] = registry_id

        if isinstance(branches, dict):
            branches[branch_name] = entry
        else:
            branches.append(entry)
        registry["branches"] = branches
        registry["metadata"]["total_branches"] = len(branches_as_list(branches))

        json_handler.log_operation("registry_updated", data={"branch": branch_name})

        return save_registry(registry_path, registry)
    finally:
        if lock_fd is not None and sys.platform != "win32":
            import fcntl

            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()


def fix_passport_registry_id(branch_dir: Path, registry_path: Path) -> bool:
    """Update passport.json registry_id if it doesn't match the current registry.

    Call when adopting an existing agent or during sync-registry --fix to repair
    registry_id mismatches caused by registry recreation.

    Args:
        branch_dir: Path to the branch directory (containing .trinity/passport.json)
        registry_path: Path to the project registry (*_REGISTRY.json)

    Returns:
        True if passport was updated, False if already correct or failed.
    """
    passport_path = branch_dir / ".trinity" / "passport.json"
    if not passport_path.exists():
        return False
    if not registry_path.exists():
        return False

    try:
        registry_data = json_handler.read_json(registry_path)
        if registry_data is None:
            return False
        current_id = registry_data.get("metadata", {}).get("id", "")
    except Exception as e:
        logger.warning("[registry] Cannot read registry_id from %s: %s", registry_path.name, e)
        return False

    if not current_id:
        return False

    try:
        passport = json_handler.read_json(passport_path)
        if passport is None:
            return False
        old_id = passport.get("citizenship", {}).get("registry_id", "")
        if old_id == current_id:
            return False  # Already correct, no update needed

        passport.setdefault("citizenship", {})["registry_id"] = current_id
        success = json_handler.write_json(passport_path, passport)
        if success:
            logger.info(
                "[registry] Fixed registry_id for %s: %s → %s",
                branch_dir.name,
                old_id[:8] if old_id else "empty",
                current_id[:8],
            )
        return success
    except Exception as e:
        logger.warning("[registry] Failed to fix registry_id for %s: %s", branch_dir.name, e)
        return False


def ensure_project_has_owner(registry_path):
    """Ensure exactly one branch entry in the registry has owner:true.

    Owner is determined by citizen_class=manager (read from passport).
    Falls back to citizen_number==1 if no manager found.
    Writes to the REGISTRY ENTRY (sealed authority), not the passport.
    """
    registry_path = Path(registry_path)
    reg_data = load_registry(registry_path)
    branches = branches_as_list(reg_data.get("branches", []))
    if not branches:
        return False

    for branch in branches:
        if branch.get("owner") is True:
            return False

    registry_root = registry_path.parent
    owner_branch = None

    for branch in branches:
        branch_path = registry_root / branch.get("path", "")
        passport_path = branch_path / ".trinity" / "passport.json"
        if passport_path.exists():
            passport = json_handler.read_json(passport_path)
            if passport and passport.get("identity", {}).get("citizen_class") == "manager":
                owner_branch = branch
                break

    if owner_branch is None:
        for branch in branches:
            branch_path = registry_root / branch.get("path", "")
            passport_path = branch_path / ".trinity" / "passport.json"
            if passport_path.exists():
                passport = json_handler.read_json(passport_path)
                if passport and passport.get("citizenship", {}).get("owner") is True:
                    owner_branch = branch
                    break

    if owner_branch is None:
        return False

    owner_branch["owner"] = True
    save_registry(registry_path, reg_data)
    logger.info("[registry] Set owner=true on %s (registry entry)", owner_branch.get("name", "?"))
    return True


def backfill_owner_and_registry_id(registry_path):
    """Backfill owner and registry_id fields into all registry branch entries.

    - Sets registry_id from each branch's passport citizenship.registry_id
    - Sets owner:true on the manager branch (devpulse in AIPass)
    """
    registry_path = Path(registry_path)
    reg_data = load_registry(registry_path)
    branches = branches_as_list(reg_data.get("branches", []))
    if not branches:
        return False

    registry_root = registry_path.parent
    changed = False

    for branch in branches:
        branch_path = registry_root / branch.get("path", "")
        passport_path = branch_path / ".trinity" / "passport.json"
        if not passport_path.exists():
            continue
        passport = json_handler.read_json(passport_path)
        if not passport:
            continue

        rid = passport.get("citizenship", {}).get("registry_id", "")
        if rid and "registry_id" not in branch:
            branch["registry_id"] = rid
            changed = True

        citizen_class = passport.get("identity", {}).get("citizen_class", "")
        if citizen_class == "manager" and not branch.get("owner"):
            branch["owner"] = True
            changed = True

    if changed:
        save_registry(registry_path, reg_data)
        logger.info("[registry] Backfilled owner + registry_id into registry entries")
    return changed


def get_owner(start_path=None):
    """Return the branch entry dict whose owner==true, or None.

    Walks up from start_path (default CWD) to find *_REGISTRY.json.
    """
    registry_path = find_registry(start_path=start_path)
    if not registry_path.exists():
        return None
    reg_data = load_registry(registry_path)
    for branch in branches_as_list(reg_data.get("branches", [])):
        if branch.get("owner") is True:
            return branch
    return None


def is_owner(email, start_path=None):
    """True iff email matches the owner entry's email.

    Normalizes email — tolerates with/without leading '@'.
    """
    if not email:
        return False
    normalized = email if email.startswith("@") else f"@{email}"
    owner = get_owner(start_path=start_path)
    if owner is None:
        return False
    owner_email = owner.get("email", "")
    owner_normalized = owner_email if owner_email.startswith("@") else f"@{owner_email}"
    return normalized == owner_normalized
