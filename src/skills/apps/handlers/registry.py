# ===================AIPASS====================
# META DATA HEADER
# Name: registry.py - Skill registry management
# Date: 2026-03-07
# Version: 1.0.0
# Category: skills/apps/handlers
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2026-03-07): Initial implementation
#
# CODE STANDARDS:
#   - Handler layer: returns dicts, NEVER prints
#   - Manages discovered skills cache
# =============================================

from pathlib import Path


def build_registry(search_paths, discover_fn):
    """Discover and cache all skills from search paths.

    Args:
        search_paths: List of (path, source_label) tuples to scan.
        discover_fn: Callable that takes a path and source label,
                     returns list of skill dicts.

    Returns:
        list[dict]: All discovered skills across all search paths.
            Each dict has: name, description, path, has_handler, source, tags.
    """
    registry = []
    seen_names = set()

    for search_path, source_label in search_paths:
        path = Path(search_path)
        if not path.exists():
            continue

        skills = discover_fn(path, source_label)
        for skill in skills:
            # First match wins for same name
            if skill["name"] not in seen_names:
                seen_names.add(skill["name"])
                registry.append(skill)

    return registry


def get_skill(name, registry):
    """Look up a skill by name in the registry.

    Args:
        name: Skill name to find.
        registry: List of skill dicts from build_registry.

    Returns:
        dict or None: The matching skill dict, or None if not found.
    """
    for skill in registry:
        if skill["name"] == name:
            return skill
    return None


def get_skill_names(registry):
    """Get all skill names from the registry.

    Args:
        registry: List of skill dicts from build_registry.

    Returns:
        list[str]: Sorted list of skill names.
    """
    return sorted(skill["name"] for skill in registry)
