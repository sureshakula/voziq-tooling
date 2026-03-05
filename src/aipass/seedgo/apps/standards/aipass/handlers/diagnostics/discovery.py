#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: discovery.py - Branch Discovery Handler
# Date: 2025-11-29
# Version: 0.1.0
# Category: seed/handlers/diagnostics
#
# CHANGELOG (Max 5 entries):
#   - v0.1.0 (2025-11-29): Initial implementation - branch discovery
#
# CODE STANDARDS:
#   - Handlers implement, modules orchestrate
# =============================================

"""
Branch Discovery Handler

Discovers all branches from the registry for diagnostics scanning.
"""

from typing import Dict, List


def discover_branches() -> List[Dict]:
    """
    Discover all branches from registry

    Returns:
        List of dicts with 'name' and 'path' keys
    """
    import sys
    from pathlib import Path

    # Infrastructure
    AIPASS_ROOT = Path.home() / "aipass_core"
    sys.path.insert(0, str(AIPASS_ROOT))
    sys.path.insert(0, str(Path.home()))

    # Import at function level to avoid orchestration at module level
    from drone.apps.modules import get_all_branches

    try:
        branches = get_all_branches()
        return branches
    except Exception as e:
        print(f"Error discovering branches: {e}")
        return []
