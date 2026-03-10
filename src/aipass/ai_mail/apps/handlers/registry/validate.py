# =================== AIPass ====================
# Name: validate.py
# Description: Registry Validation Handler
# Version: 1.0.0
# Created: 2025-11-15
# Modified: 2025-11-15
# =============================================

"""
Registry Validation Handler

Handles validation of branch registry data including:
- Checking for email address collisions
- Validating email derivation rules
- Detecting unreachable branches

Handler Independence:
- No module imports from ai_mail
- Only uses Prax logger and standard library
- Fully transportable and self-contained
"""

from pathlib import Path
from typing import List, Dict, Tuple


# Constants
MODULE_NAME = "registry.validate"


def check_email_collisions(branches: List[Dict]) -> Tuple[bool, List[Dict]]:
    """
    Check for email address collisions in branch list.

    Args:
        branches: List of branch dicts with keys: name, path, email

    Returns:
        Tuple of (has_collisions: bool, collisions: List[Dict])
        Collision dict format:
        {
            "email": "@email",
            "branch1": "First Branch Name",
            "branch2": "Second Branch Name"
        }
    """
    email_map = {}
    collisions = []

    for branch in branches:
        email = branch["email"]
        if email in email_map:
            # Collision detected
            collisions.append({
                "email": email,
                "branch1": email_map[email],
                "branch2": branch["name"]
            })
        else:
            email_map[email] = branch["name"]

    has_collisions = len(collisions) > 0

    return has_collisions, collisions


def get_collision_report(collisions: List[Dict]) -> str:
    """
    Generate human-readable collision report.

    Args:
        collisions: List of collision dicts from check_email_collisions()

    Returns:
        Formatted report string
    """
    if not collisions:
        return "No collisions detected."

    report_lines = [
        f"EMAIL ADDRESS COLLISIONS DETECTED: {len(collisions)}",
        "",
        "One or more branches are unreachable via AI_Mail!",
        "",
        "Collisions:"
    ]

    for collision in collisions:
        report_lines.extend([
            "",
            f"  {collision['email']}",
            f"    - {collision['branch1']}",
            f"    - {collision['branch2']}",
        ])

    report_lines.extend([
        "",
        "Fix: Rename branches in BRANCH_REGISTRY.json to ensure unique email derivation",
        "See email derivation rules in registry/read.py"
    ])

    return "\n".join(report_lines)


def validate_branch_data(branch: Dict) -> Tuple[bool, str]:
    """
    Validate a single branch entry.

    Args:
        branch: Branch dict with keys: name, path, email

    Returns:
        Tuple of (is_valid: bool, error_message: str)
        error_message is empty string if valid
    """
    # Check required fields
    required_fields = ["name", "path", "email"]
    for field in required_fields:
        if field not in branch:
            return False, f"Missing required field: {field}"
        if not branch[field]:
            return False, f"Empty value for field: {field}"

    # Validate email format
    if not branch["email"].startswith("@"):
        return False, f"Email must start with @: {branch['email']}"

    # Validate path format
    path = branch["path"]
    if not path.startswith("/"):
        return False, f"Path must be absolute: {path}"

    return True, ""


def validate_all_branches(branches: List[Dict]) -> Tuple[bool, List[str]]:
    """
    Validate all branch entries.

    Args:
        branches: List of branch dicts

    Returns:
        Tuple of (all_valid: bool, error_messages: List[str])
    """
    errors = []

    for i, branch in enumerate(branches):
        is_valid, error_msg = validate_branch_data(branch)
        if not is_valid:
            errors.append(f"Branch {i} ({branch.get('name', 'UNKNOWN')}): {error_msg}")

    all_valid = len(errors) == 0

    return all_valid, errors


def get_duplicate_names(branches: List[Dict]) -> List[str]:
    """
    Find duplicate branch names.

    Args:
        branches: List of branch dicts

    Returns:
        List of duplicate branch names
    """
    name_counts = {}
    duplicates = []

    for branch in branches:
        name = branch.get("name", "")
        if name:
            name_counts[name] = name_counts.get(name, 0) + 1

    for name, count in name_counts.items():
        if count > 1:
            duplicates.append(name)

    return duplicates


def get_duplicate_paths(branches: List[Dict]) -> List[str]:
    """
    Find duplicate branch paths.

    Args:
        branches: List of branch dicts

    Returns:
        List of duplicate branch paths
    """
    path_counts = {}
    duplicates = []

    for branch in branches:
        path = branch.get("path", "")
        if path:
            path_counts[path] = path_counts.get(path, 0) + 1

    for path, count in path_counts.items():
        if count > 1:
            duplicates.append(path)

    return duplicates


if __name__ == "__main__":
    from aipass.cli.apps.modules import console
    console.print("\n" + "="*70)
    console.print("AI_MAIL HANDLER: registry/validate.py")
    console.print("="*70)
    console.print("\nRegistry Validation Handler")
    console.print()
    console.print("FUNCTIONS PROVIDED:")
    console.print("  - check_email_collisions(branches) -> Tuple[bool, List[Dict]]")
    console.print("  - get_collision_report(collisions) -> str")
    console.print("  - validate_branch_data(branch) -> Tuple[bool, str]")
    console.print("  - validate_all_branches(branches) -> Tuple[bool, List[str]]")
    console.print("  - get_duplicate_names(branches) -> List[str]")
    console.print("  - get_duplicate_paths(branches) -> List[str]")
    console.print()
    console.print("TESTING:")

    # Sample test data
    test_branches = [
        {"name": "AIPASS.admin", "path": "/", "email": "@admin"},
        {"name": "FLOW", "path": "src/aipass/flow", "email": "@flow"},
        {"name": "DRONE", "path": "src/aipass/drone", "email": "@drone"},
    ]

    has_collisions, collisions = check_email_collisions(test_branches)
    console.print(f"\nCollisions detected: {has_collisions}")
    console.print(f"Number of collisions: {len(collisions)}")

    all_valid, errors = validate_all_branches(test_branches)
    console.print(f"\nAll branches valid: {all_valid}")
    console.print(f"Validation errors: {len(errors)}")

    console.print("\n" + "="*70 + "\n")
