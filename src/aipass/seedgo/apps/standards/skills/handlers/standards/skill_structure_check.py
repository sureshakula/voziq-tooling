"""
Skill Structure Standards Checker Handler

Validates skill directory structure compliance for AIPass skills.
Checks tier detection, required files, handler contract, 3-layer subdirs, stray files.
"""

# =================== META ====================
# Name: skill_structure_check.py
# Description: Skill Structure Standards Checker Handler
# Version: 1.0.0
# Created: 2026-03-07
# Modified: 2026-03-07
# =============================================


import ast
from pathlib import Path
from typing import Dict, List


# Valid items allowed in a skill root directory
VALID_ROOT_ITEMS = {
    "SKILL.md",
    "handler.py",
    "__init__.py",
    "apps",
    "tests",
    "docs",
    "requirements.txt",
    ".gitignore",
    "__pycache__",
}


def _handler_has_run(handler_path: Path) -> bool:
    """Check if handler.py has a run() function using AST parsing.

    Args:
        handler_path: Path to handler.py

    Returns:
        bool: True if run() function found at module level
    """
    try:
        source = handler_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(handler_path))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return False

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run":
            return True

    return False


def check_skill_structure(skill_path: str) -> Dict:
    """
    Check if skill follows valid directory structure

    Args:
        skill_path: Path to skill directory

    Returns:
        dict: {
            'passed': bool,
            'checks': list,
            'score': float,
            'standard': str
        }
    """
    checks: List[Dict] = []
    path = Path(skill_path)

    # Check 1: Skill directory exists and is a directory
    if not path.exists():
        return {
            "passed": False,
            "checks": [
                {
                    "name": "Skill directory exists",
                    "passed": False,
                    "message": f"Directory not found: {skill_path}",
                }
            ],
            "score": 0.0,
            "standard": "SKILL_STRUCTURE",
        }

    if not path.is_dir():
        return {
            "passed": False,
            "checks": [
                {
                    "name": "Skill directory exists",
                    "passed": False,
                    "message": f"Path is not a directory: {skill_path}",
                }
            ],
            "score": 0.0,
            "standard": "SKILL_STRUCTURE",
        }

    checks.append(
        {
            "name": "Skill directory exists",
            "passed": True,
            "message": f"Directory found: {path.name}/",
        }
    )

    # Check 2: SKILL.md exists (required for all tiers)
    skill_md = path / "SKILL.md"
    if skill_md.exists():
        checks.append(
            {
                "name": "SKILL.md exists",
                "passed": True,
                "message": "SKILL.md found (required for all tiers)",
            }
        )
    else:
        checks.append(
            {
                "name": "SKILL.md exists",
                "passed": False,
                "message": "SKILL.md missing (required for all tiers)",
            }
        )

    # Detect tier
    has_handler = (path / "handler.py").exists()
    has_apps = (path / "apps").exists()

    # Check 3: If handler.py exists, it must have a run() function
    if has_handler:
        handler_path = path / "handler.py"
        if _handler_has_run(handler_path):
            checks.append(
                {
                    "name": "handler.py has run()",
                    "passed": True,
                    "message": "handler.py contains run() function",
                }
            )
        else:
            checks.append(
                {
                    "name": "handler.py has run()",
                    "passed": False,
                    "message": "handler.py missing run() function (required for Tier 2+)",
                }
            )

    # Check 4: If apps/ exists, it must have modules/ and handlers/ subdirs
    if has_apps:
        apps_path = path / "apps"
        has_modules = (apps_path / "modules").exists()
        has_handlers = (apps_path / "handlers").exists()

        if has_modules and has_handlers:
            checks.append(
                {
                    "name": "apps/ 3-layer structure",
                    "passed": True,
                    "message": "apps/ has both modules/ and handlers/ (Tier 3)",
                }
            )
        else:
            missing = []
            if not has_modules:
                missing.append("modules/")
            if not has_handlers:
                missing.append("handlers/")
            checks.append(
                {
                    "name": "apps/ 3-layer structure",
                    "passed": False,
                    "message": f"apps/ missing: {', '.join(missing)} (required for Tier 3)",
                }
            )

    # Check 5: No stray files outside the structure
    stray_items = []
    try:
        for item in path.iterdir():
            if item.name not in VALID_ROOT_ITEMS:
                stray_items.append(item.name)
    except OSError:
        pass

    if stray_items:
        checks.append(
            {
                "name": "No stray files",
                "passed": False,
                "message": f"Unexpected items in skill root: {', '.join(sorted(stray_items))}",
            }
        )
    else:
        checks.append(
            {
                "name": "No stray files",
                "passed": True,
                "message": "All items match valid skill structure",
            }
        )

    # Determine detected tier for reporting
    if has_apps:
        tier = "Tier 3 (3-layer)"
    elif has_handler:
        tier = "Tier 2 (executable)"
    else:
        tier = "Tier 1 (minimal)"

    checks.append(
        {
            "name": "Tier detection",
            "passed": True,
            "message": f"Detected: {tier}",
        }
    )

    # Calculate score
    passed_count = sum(1 for c in checks if c["passed"])
    total = len(checks)
    score = (passed_count / total * 100) if total > 0 else 0.0

    return {
        "passed": score >= 75,
        "checks": checks,
        "score": score,
        "standard": "SKILL_STRUCTURE",
    }
