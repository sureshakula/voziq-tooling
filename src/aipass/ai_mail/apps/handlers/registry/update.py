# =================== AIPass ====================
# Name: update.py
# Description: Registry Update Handler
# Version: 1.0.0
# Created: 2025-11-15
# Modified: 2025-11-15
# =============================================

"""
Registry Update Handler

Handles updating branch registry with ping data including:
- Updating registry with branch status
- Recording ping timestamps
- Maintaining statistics (green/yellow/red counts)

Handler Independence:
- No module imports from ai_mail
- Only uses Prax logger and standard library
- Fully transportable and self-contained
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple


# Constants
MODULE_NAME = "registry.update"
_AI_MAIL_ROOT = Path(__file__).resolve().parents[3]  # ai_mail/
AI_MAIL_JSON = _AI_MAIL_ROOT / ".ai_mail.local"
REGISTRY_PATH = AI_MAIL_JSON / "local_memory_monitor_registry.json"
THRESHOLDS = {
    "green": (0, 400),
    "yellow": (401, 550),
    "red": (551, float('inf'))
}


def ping_registry(
    branch_name: str,
    branch_path: Path,
    local_status: Dict,
    obs_status: Dict
) -> bool:
    """
    Update registry with branch status.

    Args:
        branch_name: Name of branch (e.g., "FLOW", "AIPASS.admin")
        branch_path: Full path to branch directory
        local_status: Dict with {"line_count": int, "status": str}
        obs_status: Dict with {"line_count": int, "status": str}

    Returns:
        True if registry updated successfully, False otherwise
    """
    try:
        # Ensure registry directory exists
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Load or create registry
        if REGISTRY_PATH.exists():
            with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                registry = json.load(f)
        else:
            registry = _create_empty_registry()

        # Update branch entry
        registry["active_branches"][str(branch_path)] = {
            "branch_name": branch_name,
            "last_ping": datetime.now().isoformat(),
            "local_md": local_status,
            "observations_md": obs_status
        }

        # Update statistics
        registry["last_updated"] = datetime.now().isoformat()
        registry["statistics"] = _calculate_statistics(registry)

        # Save registry
        with open(REGISTRY_PATH, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2)

        return True

    except Exception as e:
        return False


def _create_empty_registry() -> Dict:
    """
    Create empty registry structure.

    Returns:
        Empty registry dict
    """
    return {
        "last_updated": "",
        "active_branches": {},
        "statistics": {
            "total_branches": 0,
            "green_status": 0,
            "yellow_status": 0,
            "red_status": 0
        }
    }


def _calculate_statistics(registry: Dict) -> Dict:
    """
    Calculate statistics from registry data.

    Args:
        registry: Full registry dict

    Returns:
        Statistics dict with counts
    """
    green, yellow, red = 0, 0, 0

    for branch_data in registry["active_branches"].values():
        for file_type in ["local_md", "observations_md"]:
            status = branch_data.get(file_type, {}).get("status", "")
            if status == "green":
                green += 1
            elif status == "yellow":
                yellow += 1
            elif status == "red":
                red += 1

    return {
        "total_branches": len(registry["active_branches"]),
        "green_status": green,
        "yellow_status": yellow,
        "red_status": red
    }


def get_status_from_count(line_count: int) -> str:
    """
    Determine status based on line count.

    Args:
        line_count: Number of lines in file

    Returns:
        Status code: "green", "yellow", or "red"
    """
    if THRESHOLDS["green"][0] <= line_count <= THRESHOLDS["green"][1]:
        return "green"
    elif THRESHOLDS["yellow"][0] <= line_count <= THRESHOLDS["yellow"][1]:
        return "yellow"
    else:  # red threshold
        return "red"


def count_file_lines(file_path: Path) -> int:
    """
    Count total lines in file.

    Args:
        file_path: Path to file to count

    Returns:
        Number of lines in file, 0 if file doesn't exist
    """
    if not file_path.exists():
        return 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except Exception as e:
        return 0


def update_json_memory_health(
    file_path: Path,
    line_count: int,
    status_code: str
) -> bool:
    """
    Update memory_health in JSON file metadata.

    Args:
        file_path: Path to JSON file
        line_count: Current line count
        status_code: Status ("green", "yellow", "red")

    Returns:
        True if updated successfully, False otherwise
    """
    if not file_path.exists():
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Update memory health in metadata
        if "metadata" in data and "memory_health" in data["metadata"]:
            data["metadata"]["memory_health"]["current_lines"] = line_count
            data["metadata"]["memory_health"]["status"] = status_code

            # Save updated file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True
        else:
            return False

    except Exception as e:
        return False


def get_branch_context() -> Tuple[str, Path]:
    """
    Determine current branch name and directory.

    Returns:
        Tuple of (branch_name, branch_path)
    """
    cwd = Path.cwd()

    # Special case: root directory
    if cwd == Path("/"):
        return "AIPASS.admin", cwd

    # Extract branch name from last directory in path
    branch_folder = cwd.name.replace("-", "_")
    branch_name = branch_folder.upper()

    return branch_name, cwd


if __name__ == "__main__":
    from aipass.cli.apps.modules import console
    console.print("\n" + "="*70)
    console.print("AI_MAIL HANDLER: registry/update.py")
    console.print("="*70)
    console.print("\nRegistry Update Handler")
    console.print()
    console.print("FUNCTIONS PROVIDED:")
    console.print("  - ping_registry(branch_name, branch_path, local_status, obs_status) -> bool")
    console.print("  - get_status_from_count(line_count) -> str")
    console.print("  - count_file_lines(file_path) -> int")
    console.print("  - update_json_memory_health(file_path, line_count, status_code) -> bool")
    console.print("  - get_branch_context() -> Tuple[str, Path]")
    console.print()
    console.print("THRESHOLDS:")
    console.print(f"  Green:  {THRESHOLDS['green'][0]} - {THRESHOLDS['green'][1]} lines")
    console.print(f"  Yellow: {THRESHOLDS['yellow'][0]} - {THRESHOLDS['yellow'][1]} lines")
    console.print(f"  Red:    {THRESHOLDS['red'][0]}+ lines")
    console.print()
    console.print("TESTING:")

    branch_name, branch_path = get_branch_context()
    console.print(f"\nCurrent branch: {branch_name}")
    console.print(f"Current path: {branch_path}")

    console.print("\n" + "="*70 + "\n")
