# =================== AIPass ====================
# Name: list_templates.py
# Description: List Templates Handler
# Version: 1.1.0
# Created: 2025-11-07
# Modified: 2025-11-07
# =============================================

"""
List Templates Handler

Lists all available PLAN templates from template directories.

Features:
- Scans the package-relative templates/flow/ directory
- Returns sorted list of template names
- Multi-directory support
- Reusable across Flow modules

Usage:
    from aipass.flow.apps.handlers.template.list_templates import list_templates

    templates = list_templates()
    print(f"Available: {templates}")  # ['default', 'master', ...]
"""

from pathlib import Path

from aipass.flow.apps.handlers.json import json_handler

# INFRASTRUCTURE IMPORT PATTERN
_PKG_ROOT = Path(__file__).resolve().parents[4]

# =============================================
# CONFIGURATION
# =============================================

MODULE_NAME = "list_templates"
TEMPLATES_DIR = _PKG_ROOT / "templates" / "flow"

# =============================================
# HELPER FUNCTIONS
# =============================================

def _template_search_dirs() -> list[Path]:
    """Determine the ordered list of directories to search for templates"""
    return [TEMPLATES_DIR]

# =============================================
# HANDLER FUNCTION
# =============================================

def list_templates() -> list[str]:
    """
    List all available templates across the configured template directories.

    Returns:
        List of template names (without .md extension), sorted alphabetically

    Example:
        >>> list_templates()
        ['default', 'master', 'api', 'webapp']
    """
    try:
        template_names: set[str] = set()
        search_dirs = _template_search_dirs()

        for base_dir in search_dirs:
            if not base_dir.exists():
                continue

            for template_file in base_dir.glob("*.md"):
                template_names.add(template_file.stem)

        sorted_templates = sorted(template_names)

        json_handler.log_operation("templates_listed", {
            "count": len(sorted_templates),
            "templates": sorted_templates,
            "success": True,
        })

        return sorted_templates

    except Exception:
        return []
