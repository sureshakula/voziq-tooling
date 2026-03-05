#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: __init__.py - Diagnostics Handlers Package
# Date: 2025-11-29
# Version: 0.1.0
# Category: seed/handlers/diagnostics
#
# CHANGELOG (Max 5 entries):
#   - v0.1.0 (2025-11-29): Initial implementation - exports discovery and runner
#
# CODE STANDARDS:
#   - Handlers implement, modules orchestrate
# =============================================

"""
Diagnostics Handlers Package

Exports:
    - discover_branches: Discover all branches from registry
    - run_branch_diagnostics: Run diagnostics on a single branch
"""

from seed.apps.handlers.diagnostics.discovery import discover_branches
from seed.apps.handlers.diagnostics.runner import run_branch_diagnostics

__all__ = [
    'discover_branches',
    'run_branch_diagnostics',
]
