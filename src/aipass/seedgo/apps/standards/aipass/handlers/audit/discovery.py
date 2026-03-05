#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: discovery.py - Branch Discovery Handler
# Date: 2025-11-29
# Version: 1.0.0
# Category: seed/handlers/audit
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2025-11-29): Extracted from standards_audit.py module
#
# CODE STANDARDS:
#   - Implementation handler for branch discovery
#   - Reads BRANCH_REGISTRY.json to find all branches
# =============================================

"""
Branch Discovery Handler

Discovers all AIPass branches from BRANCH_REGISTRY.json
"""

import sys
from pathlib import Path
from typing import List, Dict

# =============================================================================
# INFRASTRUCTURE SETUP
# =============================================================================

AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))

# =============================================================================
# IMPORTS
# =============================================================================

import json

# =============================================================================
# PRIVATE BRANCH DETECTION
# =============================================================================

def _is_branch_private(branch_name: str) -> bool:
    """Check if branch is in the private registry."""
    registry_path = Path.home() / "PRIVATE_BRANCH_REGISTRY.json"
    if not registry_path.exists():
        return False
    try:
        with open(registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        for branch in registry.get("branches", []):
            if branch.get("name", "").upper() == branch_name.upper():
                return True
    except (json.JSONDecodeError, IOError):
        pass
    return False


# =============================================================================
# PUBLIC API
# =============================================================================

def discover_branches(include_private: bool = False) -> List[Dict[str, str]]:
    """
    Discover all AIPass branches from BRANCH_REGISTRY.json

    Args:
        include_private: If False (default), excludes branches listed in
                         PRIVATE_BRANCH_REGISTRY.json. Set True to include them.

    Returns:
        List of dicts with 'name', 'path', 'entry_file' keys
    """
    branches = []
    registry_path = Path.home() / "BRANCH_REGISTRY.json"

    # Try to read from BRANCH_REGISTRY.json (source of truth)
    if registry_path.exists():
        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                registry_data = json.load(f)

            for branch in registry_data.get('branches', []):
                branch_name = branch.get('name', '')
                branch_path = Path(branch.get('path', ''))

                if not branch_path.exists():
                    continue

                # Determine entry point based on branch name
                entry_file = None

                # Most branches: apps/{branch_name}.py (lowercase)
                standard_entry = branch_path / "apps" / f"{branch_name.lower()}.py"
                if standard_entry.exists():
                    entry_file = standard_entry

                # SEED: apps/seed.py
                elif branch_name == 'SEED':
                    seed_entry = branch_path / "apps" / "seed.py"
                    if seed_entry.exists():
                        entry_file = seed_entry

                # MEMORY_BANK: apps/modules/rollover.py
                elif branch_name == 'MEMORY_BANK':
                    rollover_entry = branch_path / "apps" / "modules" / "rollover.py"
                    if rollover_entry.exists():
                        entry_file = rollover_entry

                # .VSCODE: apps/vscode.py (no dot prefix)
                elif branch_name == '.VSCODE':
                    vscode_entry = branch_path / "apps" / "vscode.py"
                    if vscode_entry.exists():
                        entry_file = vscode_entry

                # Add branch if we found an entry point
                if entry_file:
                    branches.append({
                        'name': branch_name,
                        'path': str(branch_path),
                        'entry_file': str(entry_file)
                    })

            if not include_private:
                branches = [b for b in branches if not _is_branch_private(b['name'])]

            return sorted(branches, key=lambda x: x['name'])

        except Exception:
            # Fall through to manual discovery
            pass

    # Fallback: manual directory scanning (if registry doesn't exist)

    # Check aipass_core branches
    aipass_core = Path.home() / "aipass_core"
    if aipass_core.exists():
        for branch_dir in aipass_core.iterdir():
            if not branch_dir.is_dir() or branch_dir.name.startswith('.'):
                continue

            apps_dir = branch_dir / "apps"
            if apps_dir.exists():
                entry_file = apps_dir / f"{branch_dir.name}.py"
                if entry_file.exists():
                    branches.append({
                        'name': branch_dir.name.upper(),
                        'path': str(branch_dir),
                        'entry_file': str(entry_file)
                    })

    # Check SEED branch
    seed_dir = Path.home() / "seed"
    seed_entry = seed_dir / "apps" / "seed.py"
    if seed_entry.exists():
        branches.append({
            'name': 'SEED',
            'path': str(seed_dir),
            'entry_file': str(seed_entry)
        })

    # Check MEMORY_BANK
    memory_bank_dir = Path.home() / "MEMORY_BANK"
    if memory_bank_dir.exists():
        rollover_file = memory_bank_dir / "apps" / "modules" / "rollover.py"
        if rollover_file.exists():
            branches.append({
                'name': 'MEMORY_BANK',
                'path': str(memory_bank_dir),
                'entry_file': str(rollover_file)
            })

    if not include_private:
        branches = [b for b in branches if not _is_branch_private(b['name'])]

    return sorted(branches, key=lambda x: x['name'])
