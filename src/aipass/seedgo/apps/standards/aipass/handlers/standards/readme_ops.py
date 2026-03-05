#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: readme_ops.py - README Update Operations Handler
# Date: 2026-02-21
# Version: 1.0.0
# Category: seed/standards/handlers
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2026-02-21): Initial build - extracted from readme_update module (DPLAN-026 Phase 4)
#
# CODE STANDARDS:
#   - Handler: implementation details for readme_update module
#   - Uses importlib for cross-branch generator loading
#   - Reads BRANCH_REGISTRY.json for branch resolution
#   - No CLI output, no logger - returns data to module
# =============================================

"""
README Update Operations Handler

Implementation details for the readme_update module. Handles branch resolution,
generator loading, and target resolution. Returns data structures for the
module to display.
"""

import sys
import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional

# =============================================================================
# INFRASTRUCTURE SETUP
# =============================================================================

AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))

# =============================================================================
# CONSTANTS
# =============================================================================

REGISTRY_PATH = Path.home() / "BRANCH_REGISTRY.json"
GENERATOR_PATH = Path.home() / "seed" / "apps" / "handlers" / "standards" / "readme_generator.py"

# Section display names for output
SECTION_NAMES = {
    'tree': 'TREE',
    'modules': 'MODULES',
    'commands': 'COMMANDS',
    'header': 'HEADER',
    'last_updated': 'LAST_UPDATED',
}


# =============================================================================
# BRANCH RESOLUTION
# =============================================================================

def resolve_branch(branch_arg: str) -> Optional[Dict]:
    """
    Resolve @branch argument to branch info from registry.

    Args:
        branch_arg: Branch name, optionally prefixed with @

    Returns:
        Branch dict from registry, or None if not found
    """
    if not REGISTRY_PATH.exists():
        return None

    try:
        content = REGISTRY_PATH.read_text(encoding='utf-8')
        registry = json.loads(content)
    except (json.JSONDecodeError, OSError):
        return None

    # Strip @ prefix and normalize
    name = branch_arg.lstrip('@').upper()

    for branch in registry.get('branches', []):
        if branch.get('name', '').upper() == name:
            return branch
        # Also check aliases
        aliases = branch.get('aliases', [])
        for alias in aliases:
            if alias.lstrip('@').upper() == name:
                return branch

    return None


def get_all_branches() -> List[Dict]:
    """
    Get all branches from the registry.

    Returns:
        List of branch dicts, or empty list on failure
    """
    if not REGISTRY_PATH.exists():
        return []

    try:
        content = REGISTRY_PATH.read_text(encoding='utf-8')
        registry = json.loads(content)
        return registry.get('branches', [])
    except (json.JSONDecodeError, OSError):
        return []


# =============================================================================
# GENERATOR LOADER
# =============================================================================

def load_generator():
    """
    Load readme_generator module via importlib to avoid cross-branch import issues.

    Returns:
        The readme_generator module, or None on failure
    """
    if not GENERATOR_PATH.exists():
        return None

    try:
        spec = importlib.util.spec_from_file_location(
            "readme_generator",
            str(GENERATOR_PATH)
        )
        if spec is None or spec.loader is None:
            return None
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        return generator
    except Exception:
        return None


# =============================================================================
# TARGET RESOLUTION
# =============================================================================

def resolve_targets(args: List[str]) -> tuple:
    """
    Resolve command arguments to a list of branch targets.

    Handles @all, @branch, and bare branch names.

    Args:
        args: List of branch arguments

    Returns:
        Tuple of (branches_list, error_message).
        On success: (list_of_dicts, None)
        On failure: ([], error_string)
    """
    if not args:
        return [], "no_args"

    target = args[0]

    # Handle @all
    if target.lstrip('@').lower() == 'all':
        branches = get_all_branches()
        if not branches:
            return [], "no_branches"
        return branches, None

    # Handle specific branch
    branch = resolve_branch(target)
    if not branch:
        return [], f"not_found:{target}"

    return [branch], None
