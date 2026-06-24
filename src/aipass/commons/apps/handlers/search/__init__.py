# ===================AIPASS====================
# META DATA HEADER
# Name: __init__.py - Search handler package
# Date: 2026-06-12
# Version: 1.0.0
# Category: commons/apps/handlers/search
# =============================================

"""
The Commons - Search Handler

FTS5 full-text search operations and index management.
"""

from .search_queries import backfill_fts_index

__all__ = ["backfill_fts_index"]
