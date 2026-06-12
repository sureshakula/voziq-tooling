# ===================AIPASS====================
# META DATA HEADER
# Name: parser.py - Parses drone command output
# Date: 2026-03-07
# Version: 1.0.0
# Category: skills/catalog/drone_commands/apps/handlers
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2026-03-07): Initial implementation
#
# CODE STANDARDS:
#   - Handlers layer: returns dicts, NEVER prints
#   - stdlib only (no external deps)
#   - Pure functions, no side effects
# =============================================

"""
Parser handler for drone command output.

Cleans up and structures raw drone output into usable data.
Never prints -- always returns structured results.
"""

import re


def parse_output(raw_output):
    """Clean up raw drone command output.

    Strips ANSI escape codes, trims whitespace, and normalizes line endings.

    Args:
        raw_output: Raw string output from a drone command.

    Returns:
        str: Cleaned output string.
    """
    if not raw_output:
        return ""

    # Strip ANSI escape sequences (color codes, cursor movements, etc.)
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
    cleaned = ansi_pattern.sub("", raw_output)

    # Normalize line endings
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    # Strip trailing whitespace from each line, remove excess blank lines
    lines = cleaned.split("\n")
    lines = [line.rstrip() for line in lines]

    # Collapse multiple consecutive blank lines into one
    result_lines = []
    prev_blank = False
    for line in lines:
        is_blank = len(line.strip()) == 0
        if is_blank and prev_blank:
            continue
        result_lines.append(line)
        prev_blank = is_blank

    # Strip leading/trailing blank lines from result
    result = "\n".join(result_lines).strip()

    return result


def extract_modules(systems_output):
    """Parse `drone systems` output into a list of module names.

    Expects output where each line contains a module name, possibly with
    status indicators or descriptions. Extracts the module name from each
    non-empty, non-header line.

    Args:
        systems_output: Raw output from `drone systems` command.

    Returns:
        list[str]: List of module name strings.
    """
    if not systems_output:
        return []

    cleaned = parse_output(systems_output)
    lines = cleaned.split("\n")

    modules = []
    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip header/separator lines (dashes, equals, common headers)
        if line.startswith("---") or line.startswith("==="):
            continue
        if line.lower().startswith("registered") or line.lower().startswith("available"):
            continue

        # Extract module name -- could be first word, or prefixed with indicators
        # Common formats:
        #   module_name          - plain name
        #   [OK] module_name     - with status
        #   * module_name        - with bullet
        #   @module_name         - with @ prefix

        # Remove common prefixes
        cleaned_line = line
        cleaned_line = re.sub(r"^\[.*?\]\s*", "", cleaned_line)  # [OK], [ERR], etc.
        cleaned_line = re.sub(r"^[*\-+]\s*", "", cleaned_line)  # bullet points
        cleaned_line = cleaned_line.lstrip("@")  # @ prefix

        # Take first word as module name
        parts = cleaned_line.split()
        if parts:
            module_name = parts[0].strip()
            # Validate it looks like a module name (alphanumeric + underscores)
            if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", module_name):
                modules.append(module_name)

    return modules
