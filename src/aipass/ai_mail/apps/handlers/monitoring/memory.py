# =================== AIPass ====================
# Name: memory.py
# Description: Memory Health Handler
# Version: 1.0.0
# Created: 2025-11-15
# Modified: 2025-11-15
# =============================================

"""
Memory Health Handler

Independent handler for memory file monitoring logic.
Provides functions for counting file lines and determining health status.

Architecture:
- No cross-domain imports (independent handler)
- Provides: line counting, status determination
- Used by: monitoring modules
"""

# =============================================
# IMPORTS
# =============================================
from pathlib import Path

from aipass.ai_mail.apps.handlers.json import json_handler


# =============================================
# CONSTANTS
# =============================================

# Health status thresholds
THRESHOLD_GREEN_MAX = 400
THRESHOLD_YELLOW_MIN = 401
THRESHOLD_YELLOW_MAX = 550
THRESHOLD_RED_MIN = 551
THRESHOLD_EMAIL_TRIGGER = 600

# Status indicators
STATUS_GREEN = "🟢 Healthy"
STATUS_YELLOW = "🟡 Approaching"
STATUS_RED = "🔴 Compress Now"

# =============================================
# CORE FUNCTIONS
# =============================================

def count_file_lines(file_path: Path | str) -> int:
    """
    Count lines in a file

    Args:
        file_path: Path to file to count

    Returns:
        Number of lines in file, or 0 if file doesn't exist or error
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except Exception as e:
        return 0


def get_status_from_count(line_count: int) -> str:
    """
    Determine health status from line count

    Args:
        line_count: Number of lines in file

    Returns:
        Status string with emoji indicator
    """
    if line_count <= THRESHOLD_GREEN_MAX:
        return STATUS_GREEN
    elif THRESHOLD_YELLOW_MIN <= line_count <= THRESHOLD_YELLOW_MAX:
        return STATUS_YELLOW
    else:
        return STATUS_RED


def should_send_email(line_count: int) -> bool:
    """
    Determine if email notification should be sent

    Args:
        line_count: Number of lines in file

    Returns:
        True if line count exceeds email trigger threshold
    """
    return line_count >= THRESHOLD_EMAIL_TRIGGER


def get_health_info(file_path: Path | str) -> dict:
    """
    Get complete health information for a file

    Args:
        file_path: Path to file to analyze

    Returns:
        Dict with line_count, status, needs_email
    """
    json_handler.log_operation("get_health_info", {"file_path": str(file_path)})

    line_count = count_file_lines(file_path)

    return {
        "line_count": line_count,
        "status": get_status_from_count(line_count),
        "needs_email": should_send_email(line_count),
        "file_path": str(file_path)
    }


def format_compression_prompt(file_type: str, line_count: int) -> str:
    """
    Generate compression agent prompt

    Args:
        file_type: Type of file (e.g., "local.md", "observations.md")
        line_count: Current line count

    Returns:
        Formatted compression prompt
    """
    return f"""Compress my {file_type} file from {line_count} lines to 400 lines following the compression rules:

- Top 25% (most recent): Keep mostly intact
- Next 25%: Reduce slightly (combine details)
- Next 25%: Reduce more (summary format)
- Last 25% (oldest): Delete if needed for space

Preserve:
- All session headers and dates
- Key achievements and milestones
- Critical errors and resolutions
- Important patterns and learnings

Remove:
- Routine status updates
- Redundant information
- Low-value details
- Completed temporary tasks

Maintain chronological order (newest first)."""


# =============================================
# VALIDATION
# =============================================

def validate_thresholds(green_max: int, yellow_min: int, yellow_max: int, red_min: int) -> bool:
    """
    Validate threshold configuration

    Args:
        green_max: Maximum for green status
        yellow_min: Minimum for yellow status
        yellow_max: Maximum for yellow status
        red_min: Minimum for red status

    Returns:
        True if thresholds are valid, False otherwise
    """
    if yellow_min != green_max + 1:
        return False

    if yellow_max < yellow_min:
        return False

    if red_min != yellow_max + 1:
        return False

    return True


if __name__ == "__main__":
    from aipass.cli.apps.modules import console
    console.print("\n" + "="*70)
    console.print("MEMORY HEALTH HANDLER")
    console.print("="*70)
    console.print("\nFunctions provided:")
    console.print("  - count_file_lines(file_path) -> int")
    console.print("  - get_status_from_count(line_count) -> str")
    console.print("  - should_send_email(line_count) -> bool")
    console.print("  - get_health_info(file_path) -> dict")
    console.print("  - format_compression_prompt(file_type, line_count) -> str")
    console.print("  - validate_thresholds(...) -> bool")
    console.print("\nThresholds:")
    console.print(f"  Green: 0-{THRESHOLD_GREEN_MAX} lines")
    console.print(f"  Yellow: {THRESHOLD_YELLOW_MIN}-{THRESHOLD_YELLOW_MAX} lines")
    console.print(f"  Red: {THRESHOLD_RED_MIN}+ lines")
    console.print(f"  Email trigger: {THRESHOLD_EMAIL_TRIGGER}+ lines")
    console.print("\n" + "="*70 + "\n")
