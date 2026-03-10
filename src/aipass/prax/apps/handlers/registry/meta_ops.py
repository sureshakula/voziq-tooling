# =================== AIPass ====================
# Name: meta_ops.py
# Description: Metadata Operations Handler
# Version: 1.0.0
# Created: 2025-11-04
# Modified: 2026-03-09
# =============================================

"""
Metadata Operations Handler

Functions for branch and template metadata:
- Load template registry
- Load branch metadata
- Generate metadata for existing branches
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from aipass.prax import logger


# =============================================================================
# CONSTANTS
# =============================================================================

def _find_repo_root() -> Path:
    """Walk up from this file to find repo root (contains AIPASS_REGISTRY.json)."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "AIPASS_REGISTRY.json").exists():
            return parent
    return Path.cwd()

def _get_template_dir() -> Path:
    """Lazily resolve template directory (package-relative)."""
    return _find_repo_root() / "src" / "aipass" / "cortex" / "templates" / "branch_template"

# Files that get renamed during branch creation
FILE_RENAMES = {
    "PROJECT.json": "{BRANCHNAME}.json",
    "LOCAL..json": "{BRANCHNAME}.local.json",
    "OBSERVATIONS.json": "{BRANCHNAME}.observations.json",
    "AI_MAIL.json": "{BRANCHNAME}.ai_mail.json",
    "BRANCH.ID.json": "{BRANCHNAME}.id.json",
    "BRANCH.py": "{branchname}.py",
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate SHA-256 hash of file content

    Args:
        file_path: Path to file

    Returns:
        Hex string of file hash (first 12 characters for readability)
    """
    if not file_path.is_file():
        return ""

    try:
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            # Read in chunks for large files
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        # Return first 12 chars of hash (enough for uniqueness)
        return sha256.hexdigest()[:12]
    except Exception:
        return ""


# =============================================================================
# TEMPLATE REGISTRY OPERATIONS
# =============================================================================

def load_template_registry() -> Optional[Dict]:
    """
    Load template_registry.json from template directory

    Returns:
        Template registry dict or None if not found/error
    """
    registry_path = _get_template_dir() / "template_registry.json"

    if not registry_path.exists():
        return None

    try:
        with open(registry_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


# =============================================================================
# BRANCH METADATA OPERATIONS
# =============================================================================

def load_branch_meta(branch_dir: Path) -> Optional[Dict]:
    """
    Load .branch_meta.json from branch directory

    Args:
        branch_dir: Path to branch directory

    Returns:
        Branch metadata dict or None if not found/error
    """
    meta_path = branch_dir / ".branch_meta.json"

    if not meta_path.exists():
        # This is normal for old branches that predate ID tracking
        return None

    try:
        with open(meta_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Loading .branch_meta.json: {e}")
        return None


def heal_branch_meta(
    branch_dir: Path,
    branch_meta: Optional[Dict],
    template_registry: Dict,
    template_version: str
) -> Optional[Dict]:
    """
    Auto-heal branch metadata if format is outdated or missing

    Handles:
    - Missing .branch_meta.json (returns None - caller should regenerate)
    - Old format: name→id mapping (auto-converts to new id→file_info format)
    - Corrupted/invalid data (regenerates from scratch)

    Args:
        branch_dir: Path to branch directory
        branch_meta: Loaded metadata (or None if missing)
        template_registry: Template registry for regeneration
        template_version: Current template version

    Returns:
        Healed metadata dict, or None if should regenerate from scratch
    """
    # If no metadata exists, signal caller to regenerate
    if branch_meta is None:
        logger.info("No branch_meta - treating all template files as potential additions")
        return None

    # Check if file_tracking exists and needs healing
    if "file_tracking" not in branch_meta:
        logger.info("Missing file_tracking - regenerating metadata")
        return None

    file_tracking = branch_meta.get("file_tracking", {})
    if not file_tracking:
        # Empty tracking is fine
        return branch_meta

    # Detect old format: first value is string (name→id) vs dict (id→file_info)
    first_value = next(iter(file_tracking.values()))

    if isinstance(first_value, str):
        # OLD FORMAT DETECTED - Auto-heal to new format AND remap IDs
        logger.info("Old branch_meta format detected - auto-healing...")

        # Build hash→template_id lookup for ID remapping
        hash_to_template_id = {}
        for file_id, file_info in template_registry.get("files", {}).items():
            if file_info.get("content_hash"):
                hash_to_template_id[file_info["content_hash"]] = file_id

        # Old format: {"filename.py": "f001"}
        # New format: {"f001": {"current_name": "filename.py", "content_hash": "abc123"}}

        # Invert the mapping: name→id becomes id→file_info
        healed_tracking = {}
        id_remapping = {}  # Track old_id → new_id for reporting

        for filename, old_file_id in file_tracking.items():
            # Calculate content hash if file exists
            file_path = branch_dir / filename
            content_hash = None
            if file_path.exists() and file_path.is_file():
                content_hash = calculate_file_hash(file_path)

            # Try to remap ID using content hash
            new_file_id = old_file_id  # Default to old ID

            # Skip remapping for empty files (hash: e3b0c44298fc = empty file)
            # Multiple empty files share same hash, causing false matches
            if content_hash and content_hash != "e3b0c44298fc" and content_hash in hash_to_template_id:
                new_file_id = hash_to_template_id[content_hash]
                if new_file_id != old_file_id:
                    id_remapping[old_file_id] = new_file_id

            healed_tracking[new_file_id] = {
                "current_name": filename,
                "content_hash": content_hash
            }

        # Update metadata with healed format
        branch_meta["file_tracking"] = healed_tracking

        # Save healed version
        save_branch_meta(branch_dir, branch_meta)

        if id_remapping:
            logger.info(f"Branch metadata auto-healed and saved ({len(id_remapping)} IDs remapped)")
        else:
            logger.info("Branch metadata auto-healed and saved")

        return branch_meta

    # Format is already correct - but check if IDs need remapping
    logger.info("Checking for ID reassignments...")

    # Build hash→template_id lookup
    hash_to_template_id = {}
    for file_id, file_info in template_registry.get("files", {}).items():
        if file_info.get("content_hash"):
            hash_to_template_id[file_info["content_hash"]] = file_id

    # Check each tracked file for ID reassignment
    remapped_tracking = {}
    id_remapping = {}

    for current_id, file_info in file_tracking.items():
        content_hash = file_info.get("content_hash")

        # Try to remap ID using content hash
        new_id = current_id  # Default to current ID

        # Skip remapping for empty files (hash: e3b0c44298fc = empty file)
        # Multiple empty files share same hash, causing false matches
        if content_hash and content_hash != "e3b0c44298fc" and content_hash in hash_to_template_id:
            new_id = hash_to_template_id[content_hash]
            if new_id != current_id:
                id_remapping[current_id] = new_id

        remapped_tracking[new_id] = file_info

    # If IDs were remapped, save updated metadata
    if id_remapping:
        logger.warning(f"Detected ID reassignments - remapping {len(id_remapping)} files...")
        branch_meta["file_tracking"] = remapped_tracking
        branch_meta["last_updated"] = datetime.now().isoformat()
        save_branch_meta(branch_dir, branch_meta)
        logger.info("Branch metadata updated with current template IDs")
    else:
        logger.info("All IDs current - no remapping needed")

    # Format is already correct
    return branch_meta


def save_branch_meta(branch_dir: Path, metadata: Dict) -> bool:
    """
    Save .branch_meta.json to branch directory

    Args:
        branch_dir: Path to branch directory
        metadata: Metadata dict to save

    Returns:
        True if successful, False otherwise
    """
    meta_path = branch_dir / ".branch_meta.json"

    try:
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Saving .branch_meta.json: {e}")
        return False


def generate_branch_meta_for_existing_branch(
    target_path: Path,
    branch_name: str,
    template_registry: Dict
) -> Optional[Dict]:
    """
    Generate .branch_meta.json for existing branch that predates ID tracking

    Scans the branch directory and maps existing files to template IDs with content hashes.

    Args:
        target_path: Path to existing branch
        branch_name: Branch name for placeholder substitution
        template_registry: Loaded template registry

    Returns:
        Dict with metadata structure, or None if failed
    """
    # Build reverse lookup: template_filename -> (template_id, file_info)
    template_name_to_info = {}

    # Map files
    for file_id, file_info in template_registry.get("files", {}).items():
        template_name_to_info[file_info["current_name"]] = (file_id, file_info)

    # Map directories
    for dir_id, dir_info in template_registry.get("directories", {}).items():
        template_name_to_info[dir_info["current_name"]] = (dir_id, dir_info)

    # Build file tracking with new structure: file_id -> {current_name, path, content_hash}
    file_tracking = {}
    branch_upper = branch_name.upper().replace("-", "_")

    # Map files (handle projects placeholder substitution)
    for template_name, (template_id, template_info) in template_name_to_info.items():
        # Handle placeholder patterns
        if "projects" in template_name:
            actual_name = template_name.replace("projects", branch_upper)
        else:
            # Check if this file gets renamed by FILE_RENAMES pattern
            if template_name in FILE_RENAMES:
                actual_name = FILE_RENAMES[template_name].replace("{BRANCHNAME}", branch_upper)
            else:
                actual_name = template_name

        # Check if file/directory exists in branch
        file_path = target_path / actual_name
        if file_path.exists():
            # Calculate content hash for files (not directories)
            content_hash = ""
            if file_path.is_file():
                content_hash = calculate_file_hash(file_path)

            # Use new structure matching template_registry.json
            file_tracking[template_id] = {
                "current_name": actual_name,
                "path": actual_name,  # Relative path from branch root
                "content_hash": content_hash,
                "has_branch_placeholder": "projects" in template_name or "PROJECTS" in template_name
            }

    # Create metadata structure
    meta_data = {
        "template_version": template_registry.get("metadata", {}).get("version", "1.0.0"),
        "branch_created": "unknown",  # Can't determine for existing branches
        "last_updated": datetime.now().isoformat(),
        "file_tracking": file_tracking
    }

    return meta_data
