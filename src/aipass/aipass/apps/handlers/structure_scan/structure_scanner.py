# =================== AIPass ====================
# Name: structure_scanner.py
# Description: Project structure validation for aipass doctor
# Version: 1.0.0
# Created: 2026-05-14
# Modified: 2026-05-14
# =============================================

"""
Structure Scanner — detect misplaced agents, init pollution, registry mismatches.

Pure scanning logic. Returns plain dicts/lists — no Rich markup.
Display concerns belong to the doctor module.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

from aipass.aipass.apps.handlers.json import json_handler
from aipass.prax import logger


class AgentInfo(NamedTuple):
    """An agent discovered on disk via .trinity/passport.json."""

    name: str
    path: Path
    registry_id: str
    passport_data: Dict[str, Any]


class PlacementIssue(NamedTuple):
    """Agent placement problem."""

    agent_name: str
    actual_path: str
    expected_pattern: str
    severity: str  # "warn" or "fail"


class PollutionHit(NamedTuple):
    """Same registry_id found at multiple locations."""

    registry_id: str
    agent_name: str
    locations: List[str]


class RegistryIssue(NamedTuple):
    """Registry path mismatch."""

    branch_name: str
    registered_path: str
    problem: str  # "missing" or "mismatch"


# =============================================================================
# PROJECT ROOT DETECTION
# =============================================================================


def find_project_root(start: Path) -> Optional[Path]:
    """Walk up from *start* looking for a registry file or pyproject.toml with src/.

    Returns:
        Project root Path, or None if not found.
    """
    p = start.resolve()
    for parent in (p, *p.parents):
        if list(parent.glob("*_REGISTRY.json")):
            return parent
        if (parent / "pyproject.toml").exists() and (parent / "src").is_dir():
            return parent
        if parent == parent.parent:
            break
    return None


# =============================================================================
# AGENT DETECTION
# =============================================================================


def scan_agents(project_root: Path) -> List[AgentInfo]:
    """Find all agents by scanning for .trinity/passport.json under project_root.

    Returns:
        List of AgentInfo for each valid passport found.
    """
    agents: List[AgentInfo] = []
    for passport_path in sorted(project_root.rglob(".trinity/passport.json")):
        try:
            data = json.loads(passport_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("[structure_scan] unreadable passport: %s — %s", passport_path, exc)
            continue

        branch_info = data.get("branch_info", {})
        citizenship = data.get("citizenship", {})
        name = branch_info.get("branch_name", passport_path.parent.parent.name)
        registry_id = citizenship.get("registry_id", "")
        agent_dir = passport_path.parent.parent

        agents.append(
            AgentInfo(
                name=name,
                path=agent_dir,
                registry_id=registry_id,
                passport_data=data,
            )
        )

    logger.info("[structure_scan] found %d agents under %s", len(agents), project_root)
    json_handler.log_operation("scan_agents", {"count": len(agents), "root": str(project_root)})
    return agents


# =============================================================================
# PLACEMENT VALIDATION
# =============================================================================


def check_placement(agents: List[AgentInfo], project_root: Path) -> List[PlacementIssue]:
    """Check whether each agent is in src/<package>/<agent>/ or src/<agent>/.

    Returns:
        List of PlacementIssue for agents in unexpected locations.
    """
    src_dir = project_root / "src"
    issues: List[PlacementIssue] = []

    for agent in agents:
        rel = None
        try:
            rel = agent.path.relative_to(src_dir)
        except ValueError:
            logger.warning("[structure_scan] agent %s outside src/: %s", agent.name, agent.path)
            issues.append(
                PlacementIssue(
                    agent_name=agent.name,
                    actual_path=str(agent.path),
                    expected_pattern="src/<package>/<agent>/ or src/<agent>/",
                    severity="warn",
                )
            )
            continue

        parts = rel.parts
        if len(parts) == 1:
            # src/<agent>/ — valid single-agent layout
            continue
        elif len(parts) == 2:
            # src/<package>/<agent>/ — valid multi-agent package layout
            continue
        else:
            issues.append(
                PlacementIssue(
                    agent_name=agent.name,
                    actual_path=str(agent.path),
                    expected_pattern="src/<package>/<agent>/ (too deeply nested)",
                    severity="warn",
                )
            )

    return issues


# =============================================================================
# POLLUTION DETECTION
# =============================================================================


def detect_pollution(agents: List[AgentInfo]) -> List[PollutionHit]:
    """Find duplicate registry_ids — same agent found at multiple locations.

    Returns:
        List of PollutionHit for each duplicated registry_id.
    """
    id_to_locations: Dict[str, List[AgentInfo]] = {}
    for agent in agents:
        if not agent.registry_id:
            continue
        id_to_locations.setdefault(agent.registry_id, []).append(agent)

    hits: List[PollutionHit] = []
    for rid, group in id_to_locations.items():
        if len(group) > 1:
            hits.append(
                PollutionHit(
                    registry_id=rid,
                    agent_name=group[0].name,
                    locations=[str(a.path) for a in group],
                )
            )
    return hits


# =============================================================================
# REGISTRY CONSISTENCY
# =============================================================================


def find_registry(project_root: Path) -> Optional[Path]:
    """Find *_REGISTRY.json under project_root."""
    candidates = list(project_root.glob("*_REGISTRY.json"))
    return candidates[0] if candidates else None


def check_registry_consistency(
    registry_path: Path,
    agents: List[AgentInfo],
) -> List[RegistryIssue]:
    """Validate that registry branches[].path entries match actual filesystem.

    Returns:
        List of RegistryIssue for each problem found.
    """
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("[structure_scan] registry unreadable: %s", exc)
        return [RegistryIssue("(registry)", str(registry_path), "unreadable")]

    branches = data.get("branches", [])
    agent_paths = {str(a.path.resolve()) for a in agents}
    issues: List[RegistryIssue] = []

    for branch in branches:
        name = branch.get("name", "unknown")
        path_str = branch.get("path", "")
        if not path_str:
            issues.append(RegistryIssue(name, "", "missing"))
            continue

        reg_path = Path(path_str).resolve()
        if not reg_path.exists():
            issues.append(RegistryIssue(name, path_str, "missing"))
        elif str(reg_path) not in agent_paths:
            trinity = reg_path / ".trinity" / "passport.json"
            if not trinity.exists():
                issues.append(RegistryIssue(name, path_str, "no_passport"))

    return issues


# =============================================================================
# PYPROJECT CHECK
# =============================================================================


def check_pyproject(project_root: Path) -> Dict[str, Any]:
    """Check for pyproject.toml presence at project root.

    Returns:
        Dict with 'found' bool and optional 'path' string.
    """
    pyproject = project_root / "pyproject.toml"
    return {
        "found": pyproject.exists(),
        "path": str(pyproject) if pyproject.exists() else "",
    }
