# =================== AIPass ====================
# Name: errors.py
# Description: Error Detection Handler
# Version: 1.0.0
# Created: 2025-11-15
# Modified: 2025-11-15
# =============================================

"""
Error Detection Handler

Independent handler for error log parsing and deduplication.
Provides functions for parsing error logs and generating unique error signatures.

Architecture:
- No cross-domain imports (independent handler)
- Provides: error parsing, hash generation, branch detection
- Used by: monitoring modules
"""

# =============================================
# IMPORTS
# =============================================
import hashlib
import re
from pathlib import Path
from typing import Optional, Dict, Tuple

from aipass.ai_mail.apps.handlers.json import json_handler


def _find_repo_root() -> Path:
    """Walk up from this file to find AIPASS_REGISTRY.json (repo root)."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "AIPASS_REGISTRY.json").exists():
            return parent
    return Path.cwd()


_REPO_ROOT = _find_repo_root()

# =============================================
# CONSTANTS
# =============================================

# Log line pattern - matches both prax format and Python default
# Format: 2025-10-25 15:26:37 - logger_name - ERROR - message
LOG_PATTERN = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})[,.]?\d* - (.+?) - (ERROR|WARNING|INFO) - (.+)$'

# =============================================
# CORE FUNCTIONS
# =============================================

def parse_error_log_line(log_line: str) -> Optional[Dict]:
    """
    Parse error log line to extract components

    Format: 2025-10-25 15:26:37 - captured_flow_plan_summarizer - ERROR - Failed to write...

    Args:
        log_line: Log line to parse

    Returns:
        Dict with timestamp, logger_name, module_name, level, message
        None if not an ERROR line or parsing fails
    """
    json_handler.log_operation("parse_error_log_line", {"log_line_length": len(log_line)})

    match = re.match(LOG_PATTERN, log_line.strip())

    if not match:
        return None

    timestamp, logger_name, level, message = match.groups()

    # Only process ERROR level
    if level != "ERROR":
        return None

    # Extract module name (remove 'captured_' prefix if present)
    module_name = logger_name.replace('captured_', '')

    return {
        "timestamp": timestamp,
        "logger_name": logger_name,
        "module_name": module_name,
        "level": level,
        "message": message.strip()
    }


def generate_error_hash(module_name: str, error_message: str) -> str:
    """
    Generate unique hash for error deduplication

    Combines module name and error message to create a unique identifier
    for tracking error occurrences.

    Args:
        module_name: Logger/module name (e.g., 'flow_plan_summarizer')
        error_message: Error message text

    Returns:
        SHA256 hash (first 12 chars)
    """
    combined = f"{module_name}::{error_message}"
    return hashlib.sha256(combined.encode()).hexdigest()[:12]


def get_branch_from_log_path(log_file_path: str) -> Tuple[str, Path]:
    """
    Extract branch name and root path from log file path

    Args:
        log_file_path: Full path to log file (e.g., .../api/logs/openrouter.log)

    Returns:
        Tuple of (branch_name, branch_root_path)
        Example: ("API", Path(".../api"))

    Special case: root directory returns ("AIPASS.admin", Path("/"))
    """
    log_path = Path(log_file_path)

    # Navigate up from log file to branch root
    # .../api/logs/openrouter.log -> .../api
    branch_root = log_path.parent.parent

    # Special case: root directory
    if branch_root == Path("/"):
        return "AIPASS.admin", branch_root

    # Extract branch name from directory name
    # .../api -> "API"
    # .../backup-system -> "BACKUP_SYSTEM"
    branch_folder = branch_root.name.replace("-", "_")
    branch_name = branch_folder.upper()

    return branch_name, branch_root


def get_ai_mail_file_for_branch(branch_name: str, branch_root: Path) -> Optional[Path]:
    """
    Build path to branch's .ai_mail.md file

    Args:
        branch_name: Branch name in UPPERCASE (e.g., "API", "FLOW")
        branch_root: Path to branch root directory

    Returns:
        Path to .ai_mail.md file, or None if doesn't exist

    Pattern: {branch_root}/{BRANCHNAME}.ai_mail.md
    Special case: root -> /AIPASS.admin.ai_mail.md
    """
    if branch_root == Path("/"):
        ai_mail_file = Path("/AIPASS.admin.ai_mail.md")
    else:
        ai_mail_file = branch_root / f"{branch_name}.ai_mail.md"

    if not ai_mail_file.exists():
        return None

    return ai_mail_file


def should_exclude_error(module_name: str) -> bool:
    """
    Determine if error should be excluded from monitoring

    Args:
        module_name: Module name from error

    Returns:
        True if error should be excluded (to prevent infinite loops)
    """
    # Self-exclusion: Don't monitor error_monitor's own errors
    return "error_monitor" in module_name.lower()


def format_error_email(error_hash: str, error_info: Dict, branch_name: str) -> str:
    """
    Format error email notification

    Args:
        error_hash: Unique error identifier
        error_info: Error details (module, message, timestamps)
        branch_name: Branch name

    Returns:
        Formatted email message
    """
    branch_root = _REPO_ROOT / "src" / "aipass" / branch_name.lower()
    logs_dir = branch_root / "logs"

    message = f"""Error detected in {branch_name} logs

Error ID: {error_hash}
Module: {error_info['module_name']}
First seen: {error_info['first_seen']}
Last seen: {error_info['last_seen']}
Notification count: {error_info.get('count', 1)}

Error message:
{error_info['error_text']}

Check logs: {logs_dir}/{error_info['module_name']}.log
"""
    return message


def extract_module_from_log_filename(log_file_path: str) -> str:
    """
    Extract module name from log file name

    Args:
        log_file_path: Path to log file

    Returns:
        Module name (filename without .log extension)
    """
    return Path(log_file_path).stem


# =============================================
# VALIDATION
# =============================================

def validate_error_data_entry(error_info: Dict) -> bool:
    """
    Validate error tracking data entry structure

    Args:
        error_info: Error data entry to validate

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(error_info, dict):
        return False

    required_fields = ["first_seen", "last_seen", "count", "error_text", "module_name"]
    return all(field in error_info for field in required_fields)


if __name__ == "__main__":
    from aipass.cli.apps.modules import console
    console.print("\n" + "="*70)
    console.print("ERROR DETECTION HANDLER")
    console.print("="*70)
    console.print("\nFunctions provided:")
    console.print("  - parse_error_log_line(log_line) -> dict | None")
    console.print("  - generate_error_hash(module_name, error_message) -> str")
    console.print("  - get_branch_from_log_path(log_file_path) -> (str, Path)")
    console.print("  - get_ai_mail_file_for_branch(branch_name, branch_root) -> Path | None")
    console.print("  - should_exclude_error(module_name) -> bool")
    console.print("  - format_error_email(error_hash, error_info, branch_name) -> str")
    console.print("  - extract_module_from_log_filename(log_file_path) -> str")
    console.print("  - validate_error_data_entry(error_info) -> bool")
    console.print("\nLog pattern:")
    console.print("  2025-10-25 15:26:37 - module_name - ERROR - message")
    console.print("\nError hash:")
    console.print("  SHA256(module_name::error_message)[:12]")
    console.print("\n" + "="*70 + "\n")
