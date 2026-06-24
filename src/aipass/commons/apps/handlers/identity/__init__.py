# ===================AIPASS====================
# META DATA HEADER
# Name: __init__.py - Identity handler package
# Date: 2026-03-07
# Version: 1.0.0
# Category: commons/apps/handlers/identity
# =============================================

"""
The Commons - Identity Handler

Branch detection from CWD, registry lookup, mention extraction.
"""

from .identity_ops import (
    find_branch_root,
    get_branch_info_from_registry,
    get_caller_branch,
    extract_mentions,
    resolve_display_name,
)

__all__ = [
    "find_branch_root",
    "get_branch_info_from_registry",
    "get_caller_branch",
    "extract_mentions",
    "resolve_display_name",
]
