# ===================AIPASS====================
# META DATA HEADER
# Name: __init__.py - Database handler package
# Date: 2026-03-07
# Version: 1.0.0
# Category: commons/apps/handlers/database
# =============================================

"""
The Commons - Database Handler

SQLite connection management, schema initialization, and retry logic.
"""

from .db import get_db, close_db, init_db, retry_on_locked

__all__ = ["get_db", "close_db", "init_db", "retry_on_locked"]
