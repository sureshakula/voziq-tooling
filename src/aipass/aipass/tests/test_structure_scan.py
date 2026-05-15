# =================== AIPass ====================
# Name: test_structure_scan.py
# Description: Tests for doctor structure scanner (DPLAN-0177)
# Version: 1.0.0
# Created: 2026-05-14
# Modified: 2026-05-14
# =============================================

"""Tests for structure scanner handler — agent detection, placement, pollution, registry."""

import json
from pathlib import Path
from unittest.mock import patch

from aipass.aipass.apps.handlers.structure_scan.structure_scanner import (
    check_placement,
    check_pyproject,
    check_registry_consistency,
    detect_pollution,
    find_project_root,
    find_registry,
    scan_agents,
)
from aipass.aipass.apps.handlers.ui.progress import GLYPH_FAIL, GLYPH_WARN
from aipass.aipass.apps.modules.doctor import _check_structure


# =============================================================================
# Helpers
# =============================================================================


def _make_agent(tmp_path: Path, name: str, registry_id: str = "uuid-1", subdir: str = "") -> Path:
    """Create a minimal agent directory with passport."""
    if subdir:
        agent_dir = tmp_path / "src" / subdir / name
    else:
        agent_dir = tmp_path / "src" / name
    trinity = agent_dir / ".trinity"
    trinity.mkdir(parents=True, exist_ok=True)
    passport = {
        "branch_info": {"branch_name": name},
        "citizenship": {"registry_id": registry_id},
    }
    (trinity / "passport.json").write_text(json.dumps(passport), encoding="utf-8")
    return agent_dir


def _make_registry(tmp_path: Path, branches: list) -> Path:
    """Create a registry file."""
    reg = tmp_path / "TEST_REGISTRY.json"
    reg.write_text(json.dumps({"branches": branches}), encoding="utf-8")
    return reg


# =============================================================================
# TestFindProjectRoot
# =============================================================================


class TestFindProjectRoot:
    def test_finds_by_registry(self, tmp_path: Path) -> None:
        """Finds project root via *_REGISTRY.json."""
        (tmp_path / "AIPASS_REGISTRY.json").write_text("{}", encoding="utf-8")
        deep = tmp_path / "src" / "pkg" / "agent"
        deep.mkdir(parents=True)
        result = find_project_root(deep)
        assert result == tmp_path

    def test_finds_by_pyproject_with_src(self, tmp_path: Path) -> None:
        """Finds project root via pyproject.toml + src/ dir."""
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        (tmp_path / "src").mkdir()
        result = find_project_root(tmp_path / "src")
        assert result == tmp_path

    def test_returns_none_when_nothing(self, tmp_path: Path) -> None:
        """Returns None when no markers found."""
        result = find_project_root(tmp_path)
        assert result is None


# =============================================================================
# TestScanAgents
# =============================================================================


class TestScanAgents:
    def test_finds_agents(self, tmp_path: Path) -> None:
        """Discovers agents by scanning for .trinity/passport.json."""
        _make_agent(tmp_path, "alpha", "uuid-a")
        _make_agent(tmp_path, "beta", "uuid-b")
        agents = scan_agents(tmp_path)
        assert len(agents) == 2
        names = {a.name for a in agents}
        assert names == {"alpha", "beta"}

    def test_skips_corrupt_passport(self, tmp_path: Path) -> None:
        """Skips passports that aren't valid JSON."""
        _make_agent(tmp_path, "good", "uuid-g")
        bad_dir = tmp_path / "src" / "bad" / ".trinity"
        bad_dir.mkdir(parents=True)
        (bad_dir / "passport.json").write_text("not json{{{", encoding="utf-8")
        agents = scan_agents(tmp_path)
        assert len(agents) == 1
        assert agents[0].name == "good"

    def test_empty_project(self, tmp_path: Path) -> None:
        """Returns empty list when no passports found."""
        agents = scan_agents(tmp_path)
        assert agents == []

    def test_extracts_registry_id(self, tmp_path: Path) -> None:
        """Extracts registry_id from passport citizenship section."""
        _make_agent(tmp_path, "agent1", "my-uuid-123")
        agents = scan_agents(tmp_path)
        assert agents[0].registry_id == "my-uuid-123"


# =============================================================================
# TestCheckPlacement
# =============================================================================


class TestCheckPlacement:
    def test_valid_single_agent(self, tmp_path: Path) -> None:
        """src/<agent>/ is valid placement."""
        _make_agent(tmp_path, "myagent")
        agents = scan_agents(tmp_path)
        issues = check_placement(agents, tmp_path)
        assert issues == []

    def test_valid_package_agent(self, tmp_path: Path) -> None:
        """src/<package>/<agent>/ is valid placement."""
        _make_agent(tmp_path, "myagent", subdir="mypkg")
        agents = scan_agents(tmp_path)
        issues = check_placement(agents, tmp_path)
        assert issues == []

    def test_deeply_nested_flagged(self, tmp_path: Path) -> None:
        """src/<a>/<b>/<c>/ is too deeply nested."""
        agent_dir = tmp_path / "src" / "a" / "b" / "c"
        trinity = agent_dir / ".trinity"
        trinity.mkdir(parents=True)
        passport = {"branch_info": {"branch_name": "deep"}, "citizenship": {"registry_id": "uuid-d"}}
        (trinity / "passport.json").write_text(json.dumps(passport), encoding="utf-8")
        agents = scan_agents(tmp_path)
        issues = check_placement(agents, tmp_path)
        assert len(issues) == 1
        assert "too deeply nested" in issues[0].expected_pattern

    def test_outside_src_flagged(self, tmp_path: Path) -> None:
        """Agent outside src/ directory is flagged."""
        agent_dir = tmp_path / "other" / "agent"
        trinity = agent_dir / ".trinity"
        trinity.mkdir(parents=True)
        passport = {"branch_info": {"branch_name": "stray"}, "citizenship": {"registry_id": "uuid-s"}}
        (trinity / "passport.json").write_text(json.dumps(passport), encoding="utf-8")
        agents = scan_agents(tmp_path)
        issues = check_placement(agents, tmp_path)
        assert len(issues) == 1
        assert issues[0].agent_name == "stray"


# =============================================================================
# TestDetectPollution
# =============================================================================


class TestDetectPollution:
    def test_no_duplicates(self, tmp_path: Path) -> None:
        """Unique registry_ids produce no pollution hits."""
        _make_agent(tmp_path, "a", "uuid-1")
        _make_agent(tmp_path, "b", "uuid-2", subdir="pkg")
        agents = scan_agents(tmp_path)
        hits = detect_pollution(agents)
        assert hits == []

    def test_duplicate_detected(self, tmp_path: Path) -> None:
        """Same registry_id at two locations is flagged."""
        _make_agent(tmp_path, "original", "uuid-dup")
        _make_agent(tmp_path, "copy", "uuid-dup", subdir="pkg")
        agents = scan_agents(tmp_path)
        hits = detect_pollution(agents)
        assert len(hits) == 1
        assert len(hits[0].locations) == 2
        assert hits[0].registry_id == "uuid-dup"

    def test_empty_registry_id_ignored(self, tmp_path: Path) -> None:
        """Agents without registry_id are skipped."""
        _make_agent(tmp_path, "noid", "")
        agents = scan_agents(tmp_path)
        hits = detect_pollution(agents)
        assert hits == []


# =============================================================================
# TestRegistryConsistency
# =============================================================================


class TestRegistryConsistency:
    def test_all_paths_valid(self, tmp_path: Path) -> None:
        """All registry paths exist and have passports."""
        agent_dir = _make_agent(tmp_path, "alpha", "uuid-a")
        reg = _make_registry(tmp_path, [{"name": "alpha", "path": str(agent_dir)}])
        agents = scan_agents(tmp_path)
        issues = check_registry_consistency(reg, agents)
        assert issues == []

    def test_missing_path_detected(self, tmp_path: Path) -> None:
        """Registry path that doesn't exist is flagged."""
        reg = _make_registry(tmp_path, [{"name": "ghost", "path": str(tmp_path / "src" / "ghost")}])
        issues = check_registry_consistency(reg, [])
        assert len(issues) == 1
        assert issues[0].branch_name == "ghost"
        assert issues[0].problem == "missing"

    def test_no_passport_detected(self, tmp_path: Path) -> None:
        """Registry path exists but has no passport."""
        no_passport_dir = tmp_path / "src" / "bare"
        no_passport_dir.mkdir(parents=True)
        reg = _make_registry(tmp_path, [{"name": "bare", "path": str(no_passport_dir)}])
        issues = check_registry_consistency(reg, [])
        assert len(issues) == 1
        assert issues[0].problem == "no_passport"

    def test_corrupt_registry(self, tmp_path: Path) -> None:
        """Corrupt registry JSON returns unreadable issue."""
        reg = tmp_path / "BAD_REGISTRY.json"
        reg.write_text("not json", encoding="utf-8")
        issues = check_registry_consistency(reg, [])
        assert len(issues) == 1
        assert issues[0].problem == "unreadable"

    def test_empty_path_flagged(self, tmp_path: Path) -> None:
        """Empty path string in registry is flagged as missing."""
        reg = _make_registry(tmp_path, [{"name": "empty", "path": ""}])
        issues = check_registry_consistency(reg, [])
        assert len(issues) == 1
        assert issues[0].problem == "missing"


# =============================================================================
# TestFindRegistry
# =============================================================================


class TestFindRegistry:
    def test_finds_registry(self, tmp_path: Path) -> None:
        """Finds *_REGISTRY.json in project root."""
        (tmp_path / "AIPASS_REGISTRY.json").write_text("{}", encoding="utf-8")
        result = find_registry(tmp_path)
        assert result is not None
        assert result.name == "AIPASS_REGISTRY.json"

    def test_returns_none(self, tmp_path: Path) -> None:
        """Returns None when no registry file."""
        result = find_registry(tmp_path)
        assert result is None


# =============================================================================
# TestCheckPyproject
# =============================================================================


class TestCheckPyproject:
    def test_pyproject_present(self, tmp_path: Path) -> None:
        """Found when pyproject.toml exists."""
        (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
        result = check_pyproject(tmp_path)
        assert result["found"] is True
        assert result["path"] != ""

    def test_pyproject_missing(self, tmp_path: Path) -> None:
        """Not found when pyproject.toml absent."""
        result = check_pyproject(tmp_path)
        assert result["found"] is False
        assert result["path"] == ""


# =============================================================================
# TestCheckStructureIntegration
# =============================================================================


class TestCheckStructureIntegration:
    def test_no_project_root(self, tmp_path: Path, monkeypatch) -> None:
        """Returns warning when no project root detected."""
        monkeypatch.chdir(tmp_path)
        with patch(
            "aipass.aipass.apps.modules.doctor.find_project_root",
            return_value=None,
        ):
            results = _check_structure()
        assert len(results) == 1
        assert results[0].glyph == GLYPH_WARN
        assert "project root" in results[0].label

    def test_clean_project(self, tmp_path: Path) -> None:
        """Clean project with agents, registry, pyproject gets all PASS."""
        _make_agent(tmp_path, "agent1", "uuid-1")
        _make_registry(tmp_path, [{"name": "agent1", "path": str(tmp_path / "src" / "agent1")}])
        (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
        with patch("aipass.aipass.apps.modules.doctor.find_project_root", return_value=tmp_path):
            results = _check_structure()
        glyphs = {r.glyph for r in results}
        assert GLYPH_FAIL not in glyphs
        assert GLYPH_WARN not in glyphs

    def test_pollution_reported(self, tmp_path: Path) -> None:
        """Duplicate registry_id shows up as FAIL in structure check."""
        _make_agent(tmp_path, "orig", "uuid-dup")
        _make_agent(tmp_path, "copy", "uuid-dup", subdir="pkg")
        _make_registry(tmp_path, [])
        (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
        with patch("aipass.aipass.apps.modules.doctor.find_project_root", return_value=tmp_path):
            results = _check_structure()
        pollution_results = [r for r in results if "pollution" in r.label]
        assert len(pollution_results) == 1
        assert pollution_results[0].glyph == GLYPH_FAIL
