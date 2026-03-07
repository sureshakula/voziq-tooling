"""
Skill Format Standards Checker Handler

Validates SKILL.md format compliance for AIPass skills.
Checks frontmatter parsing, required fields, version format, handler consistency.
"""

# =================== META ====================
# Name: skill_format_check.py
# Description: Skill Format Standards Checker Handler
# Version: 1.0.0
# Created: 2026-03-07
# Modified: 2026-03-07
# =============================================


import re
from pathlib import Path
from typing import Dict, List


def _parse_frontmatter(content: str) -> Dict:
    """Parse YAML frontmatter from SKILL.md content.

    Handles simple key: value pairs without requiring PyYAML.
    Supports strings, booleans, and lists.

    Args:
        content: Full file content of SKILL.md

    Returns:
        dict with parsed frontmatter, or empty dict if invalid
    """
    lines = content.split("\n")

    # Find frontmatter delimiters
    if not lines or lines[0].strip() != "---":
        return {}

    end_index = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_index = i
            break

    if end_index is None:
        return {}

    # Parse simple YAML key: value pairs
    frontmatter = {}
    current_key = None
    for line in lines[1:end_index]:
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        # List item (continuation of previous key)
        if stripped.startswith("- ") and current_key is not None:
            if not isinstance(frontmatter[current_key], list):
                frontmatter[current_key] = []
            frontmatter[current_key].append(stripped[2:].strip())
            continue

        # Key: value pair
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            current_key = key

            # Parse booleans
            if value.lower() in ("true", "yes"):
                frontmatter[key] = True
            elif value.lower() in ("false", "no"):
                frontmatter[key] = False
            elif value == "":
                # Could be a list starting on next line
                frontmatter[key] = ""
            else:
                frontmatter[key] = value

    return frontmatter


def _is_valid_semver(version: str) -> bool:
    """Check if version string follows semver format.

    Args:
        version: Version string to validate

    Returns:
        bool: True if valid semver
    """
    pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$"
    return bool(re.match(pattern, version))


def check_skill_format(skill_path: str) -> Dict:
    """
    Check if skill has valid SKILL.md format

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

    # Validate skill directory exists
    if not path.exists() or not path.is_dir():
        return {
            "passed": False,
            "checks": [
                {
                    "name": "Skill directory",
                    "passed": False,
                    "message": f"Skill directory not found: {skill_path}",
                }
            ],
            "score": 0.0,
            "standard": "SKILL_FORMAT",
        }

    # Check 1: SKILL.md exists
    skill_md = path / "SKILL.md"
    if not skill_md.exists():
        checks.append(
            {
                "name": "SKILL.md exists",
                "passed": False,
                "message": "SKILL.md not found in skill directory",
            }
        )
        # Cannot continue without SKILL.md
        return {
            "passed": False,
            "checks": checks,
            "score": 0.0,
            "standard": "SKILL_FORMAT",
        }

    checks.append(
        {
            "name": "SKILL.md exists",
            "passed": True,
            "message": "SKILL.md found",
        }
    )

    # Read SKILL.md
    try:
        content = skill_md.read_text(encoding="utf-8")
    except Exception as e:
        checks.append(
            {
                "name": "SKILL.md readable",
                "passed": False,
                "message": f"Error reading SKILL.md: {e}",
            }
        )
        return {
            "passed": False,
            "checks": checks,
            "score": 0.0,
            "standard": "SKILL_FORMAT",
        }

    # Check 2: YAML frontmatter is parseable
    frontmatter = _parse_frontmatter(content)
    if not frontmatter:
        checks.append(
            {
                "name": "YAML frontmatter",
                "passed": False,
                "message": "No valid YAML frontmatter found (must start with --- and end with ---)",
            }
        )
        # Cannot check fields without frontmatter
        passed_count = sum(1 for c in checks if c["passed"])
        total = len(checks)
        score = (passed_count / total * 100) if total > 0 else 0.0
        return {
            "passed": score >= 75,
            "checks": checks,
            "score": score,
            "standard": "SKILL_FORMAT",
        }

    checks.append(
        {
            "name": "YAML frontmatter",
            "passed": True,
            "message": "Frontmatter parsed successfully",
        }
    )

    # Check 3: name field present and non-empty
    name_val = frontmatter.get("name", "")
    if name_val and isinstance(name_val, str) and name_val.strip():
        checks.append(
            {
                "name": "name field",
                "passed": True,
                "message": f"name: {name_val}",
            }
        )
    else:
        checks.append(
            {
                "name": "name field",
                "passed": False,
                "message": "name field missing or empty in frontmatter",
            }
        )

    # Check 4: description field present and non-empty
    desc_val = frontmatter.get("description", "")
    if desc_val and isinstance(desc_val, str) and desc_val.strip():
        checks.append(
            {
                "name": "description field",
                "passed": True,
                "message": f"description: {desc_val[:60]}",
            }
        )
    else:
        checks.append(
            {
                "name": "description field",
                "passed": False,
                "message": "description field missing or empty in frontmatter",
            }
        )

    # Check 5: has_handler consistency
    has_handler = frontmatter.get("has_handler")
    if has_handler is True:
        handler_py = path / "handler.py"
        if handler_py.exists():
            checks.append(
                {
                    "name": "has_handler consistency",
                    "passed": True,
                    "message": "has_handler: true and handler.py exists",
                }
            )
        else:
            checks.append(
                {
                    "name": "has_handler consistency",
                    "passed": False,
                    "message": "has_handler: true but handler.py not found",
                }
            )
    elif has_handler is not None:
        checks.append(
            {
                "name": "has_handler consistency",
                "passed": True,
                "message": "has_handler: false (no handler expected)",
            }
        )

    # Check 6: version format (semver) if present
    version_val = frontmatter.get("version", "")
    if version_val and isinstance(version_val, str):
        if _is_valid_semver(version_val):
            checks.append(
                {
                    "name": "version format",
                    "passed": True,
                    "message": f"version: {version_val} (valid semver)",
                }
            )
        else:
            checks.append(
                {
                    "name": "version format",
                    "passed": False,
                    "message": f"version: {version_val} (invalid semver - expected X.Y.Z)",
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
        "standard": "SKILL_FORMAT",
    }
