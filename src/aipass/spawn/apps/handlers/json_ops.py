# =================== AIPass ====================
# Name: json_ops.py
# Description: JSON operations — re-exports from aipass.aipass.shared
# Version: 2.0.0
# Created: 2026-03-07
# Modified: 2026-06-10
# =============================================

"""JSON operations — thin re-export from aipass.aipass.shared.json_ops."""

from aipass.aipass.shared.json_ops import backup_json, deep_merge

__all__ = ["deep_merge", "backup_json"]
