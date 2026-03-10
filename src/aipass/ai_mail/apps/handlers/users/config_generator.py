# =================== AIPass ====================
# Name: config_generator.py
# Description: Local Config Auto-Generation Handler
# Version: 1.0.0
# Created: 2025-11-18
# Modified: 2025-11-18
# =============================================

"""
Local Config Auto-Generation Handler

Auto-generates user_config.json files for branches that use AI_MAIL.
Creates ai_mail_config/ directory and populates with branch-specific config.
"""

# =============================================
# IMPORTS
# =============================================
import json
from pathlib import Path
from typing import Dict

# =============================================
# CONFIG GENERATION FUNCTIONS
# =============================================

def generate_local_config(branch_info: Dict) -> Dict:
    """
    Generate local user_config.json content for a branch.

    Args:
        branch_info: Branch info dict from registry with keys:
            - name: Branch name (e.g., "SEED")
            - path: Branch path
            - email: Branch email address (e.g., "@seed")
            - description: Branch description

    Returns:
        Dict with user_config.json structure
    """
    branch_name = branch_info.get("name", "").lower()
    branch_email = branch_info.get("email", f"@{branch_name}")
    branch_path = Path(branch_info.get("path", ""))

    # Generate display name from branch info
    display_name = generate_display_name(branch_info)

    # Generate mailbox path (.ai_mail.local/ in branch directory)
    mailbox_path = str(branch_path / ".ai_mail.local")

    config = {
        "version": "1.0.0",
        "current_user": branch_name,
        "users": {
            branch_name: {
                "name": branch_info.get("name", "").title(),
                "email_address": branch_email,
                "display_name": display_name,
                "mailbox_path": mailbox_path
            }
        },
        "settings": {
            "timestamp_format": "%Y-%m-%d %H:%M:%S",
            "max_inbox_display": 20,
            "max_sent_display": 20
        }
    }

    return config


def generate_display_name(branch_info: Dict) -> str:
    """
    Generate user-friendly display name for branch.

    Args:
        branch_info: Branch info dict from registry

    Returns:
        Display name string (e.g., "Seed (Standards Branch)")
    """
    name = branch_info.get("name", "Unknown").title()
    description = branch_info.get("description", "")

    # If description is meaningful (not default), use it
    if description and description != "New branch - purpose TBD":
        return f"{name} ({description})"
    else:
        # Use profile as context if available
        profile = branch_info.get("profile", "")
        if profile and profile != "AIPass Workshop":
            return f"{name} ({profile})"
        else:
            # Just branch name
            return name


def create_local_config_file(branch_info: Dict, force: bool = False) -> Path | None:
    """
    Create local user_config.json file for a branch.

    Saves to branch's [branch_name]_json/ directory (e.g., seed_json/user_config.json).
    Follows the pattern: all JSON files for a branch go in their [branch]_json/ folder.

    Args:
        branch_info: Branch info dict from registry
        force: If True, overwrite existing config file

    Returns:
        Path to created config file, or None if failed
    """
    try:
        branch_path = Path(branch_info.get("path", ""))
        if not branch_path.exists():
            return None

        # Get branch name for directory pattern
        branch_name = branch_info.get("name", "").lower()

        # Config directory: [branch_name]_json/
        config_dir = branch_path / f"{branch_name}_json"

        # Create directory if it doesn't exist
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)

        # Config file path
        config_file = config_dir / "user_config.json"

        # Check if already exists
        if config_file.exists() and not force:
            return config_file

        # Generate config content
        config = generate_local_config(branch_info)

        # Write config file
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        return config_file

    except Exception:
        return None


def create_mailbox_directory(branch_path: Path) -> Path | None:
    """
    Create .ai_mail.local/ mailbox directory for a branch.

    Creates subdirectories: inbox/, sent/, deleted/

    Args:
        branch_path: Path to branch directory

    Returns:
        Path to mailbox directory, or None if failed
    """
    try:
        mailbox_dir = branch_path / ".ai_mail.local"
        mailbox_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (mailbox_dir / "sent").mkdir(exist_ok=True)

        # Create empty inbox.json if doesn't exist
        inbox_file = mailbox_dir / "inbox.json"
        if not inbox_file.exists():
            inbox_data = {
                "mailbox": "inbox",
                "total_messages": 0,
                "unread_count": 0,
                "messages": []
            }
            with open(inbox_file, 'w', encoding='utf-8') as f:
                json.dump(inbox_data, f, indent=2)

        # Create empty sent.json if doesn't exist
        sent_file = mailbox_dir / "sent.json"
        if not sent_file.exists():
            sent_data = {
                "mailbox": "sent",
                "total_messages": 0,
                "messages": []
            }
            with open(sent_file, 'w', encoding='utf-8') as f:
                json.dump(sent_data, f, indent=2)

        return mailbox_dir

    except Exception:
        return None


def setup_branch_for_aimail(branch_info: Dict, force: bool = False) -> bool:
    """
    Complete AI_MAIL setup for a branch.

    Creates:
    - ai_mail_config/user_config.json
    - .ai_mail.local/ mailbox directory
    - .ai_mail.local/inbox.json
    - .ai_mail.local/sent.json

    Args:
        branch_info: Branch info dict from registry
        force: If True, overwrite existing files

    Returns:
        True if setup successful, False otherwise
    """
    try:
        # Create config file
        config_file = create_local_config_file(branch_info, force=force)
        if not config_file:
            return False

        # Create mailbox directory
        branch_path = Path(branch_info.get("path", ""))
        mailbox_dir = create_mailbox_directory(branch_path)
        if not mailbox_dir:
            return False

        return True

    except Exception:
        return False


if __name__ == "__main__":
    from aipass.cli.apps.modules import console

    console.print("\n" + "="*70)
    console.print("LOCAL CONFIG AUTO-GENERATION HANDLER")
    console.print("="*70)
    console.print("\nPURPOSE:")
    console.print("  Auto-generates user_config.json files for branches using AI_MAIL")
    console.print("  Creates ai_mail_config/ directory and mailbox structure")
    console.print()
    console.print("FUNCTIONS PROVIDED:")
    console.print("  - generate_local_config(branch_info) -> Dict")
    console.print("  - generate_display_name(branch_info) -> str")
    console.print("  - create_local_config_file(branch_info, force) -> Path | None")
    console.print("  - create_mailbox_directory(branch_path) -> Path | None")
    console.print("  - setup_branch_for_aimail(branch_info, force) -> bool")
    console.print()
    console.print("HANDLER CHARACTERISTICS:")
    console.print("  ✓ Independent - no module dependencies")
    console.print("  ✓ Can import Prax (service provider)")
    console.print("  ✓ Pure business logic")
    console.print("  ✗ CANNOT import parent modules")
    console.print()
    console.print("SETUP WORKFLOW:")
    console.print("  1. Generate config from branch registry info")
    console.print("  2. Create ai_mail_config/ directory")
    console.print("  3. Write user_config.json with branch-specific settings")
    console.print("  4. Create .ai_mail.local/ mailbox directory")
    console.print("  5. Initialize inbox.json and sent.json")
    console.print()
    console.print("="*70 + "\n")
