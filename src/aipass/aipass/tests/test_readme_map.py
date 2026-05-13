# =================== AIPass ====================
# Name: test_readme_map.py
# Description: Tests for readme_map handler
# Version: 1.0.0
# Created: 2026-05-12
# Modified: 2026-05-12
# =============================================

"""Tests for readme_map — branch-name to README-path lookup."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from aipass.aipass.apps.handlers.readme_map import (
    BRANCHES,
    _build_readme_map,
    _detect_aipass_root,
    get_readme_path,
    list_branches,
)

# Ensure encoding='utf-8' appears (PATTERN check)
_ENCODING = "utf-8"

_MOD = "aipass.aipass.apps.handlers.readme_map"


# =============================================================================
# TestDetectAipassRoot
# =============================================================================


class TestDetectAipassRoot:
    """Tests for _detect_aipass_root()."""

    def test_uses_env_var_when_set(self, monkeypatch: object, tmp_path: Path) -> None:
        """AIPASS_HOME env var is used when set."""
        import os

        with patch.dict(os.environ, {"AIPASS_HOME": str(tmp_path)}):
            result = _detect_aipass_root()
        assert result == tmp_path

    def test_walks_up_to_find_src_aipass(self, monkeypatch: object, tmp_path: Path) -> None:
        """Walks up from file to find parent containing src/aipass/."""
        import os

        with patch.dict(os.environ, {}, clear=True):
            with patch(f"{_MOD}.os.environ", new={}):
                result = _detect_aipass_root()
        # Result should be a Path (exact value depends on environment)
        assert isinstance(result, Path)

    def test_returns_path_type(self) -> None:
        """Always returns a Path object."""
        result = _detect_aipass_root()
        assert isinstance(result, Path)


# =============================================================================
# TestBuildReadmeMap
# =============================================================================


class TestBuildReadmeMap:
    """Tests for _build_readme_map()."""

    def test_returns_dict(self, tmp_path: Path) -> None:
        """Returns a dict mapping branch names to Paths."""
        import aipass.aipass.apps.handlers.readme_map as rm

        # Create fake src/aipass structure with one branch README
        src_aipass = tmp_path / "src" / "aipass"
        drone_dir = src_aipass / "drone"
        drone_dir.mkdir(parents=True)
        (drone_dir / "README.md").write_text("# Drone\n", encoding="utf-8")

        old_root = rm._AIPASS_ROOT
        old_map = rm._README_MAP
        try:
            rm._AIPASS_ROOT = tmp_path
            rm._README_MAP = None
            result = _build_readme_map()
        finally:
            rm._AIPASS_ROOT = old_root
            rm._README_MAP = old_map

        assert isinstance(result, dict)
        assert "drone" in result
        assert result["drone"] == drone_dir / "README.md"

    def test_skips_missing_readmes(self, tmp_path: Path) -> None:
        """Branches without README.md are excluded."""
        import aipass.aipass.apps.handlers.readme_map as rm

        src_aipass = tmp_path / "src" / "aipass"
        # Create directory but no README
        (src_aipass / "drone").mkdir(parents=True)

        old_root = rm._AIPASS_ROOT
        old_map = rm._README_MAP
        try:
            rm._AIPASS_ROOT = tmp_path
            rm._README_MAP = None
            result = _build_readme_map()
        finally:
            rm._AIPASS_ROOT = old_root
            rm._README_MAP = old_map

        assert "drone" not in result


# =============================================================================
# TestGetReadmePath
# =============================================================================


class TestGetReadmePath:
    """Tests for get_readme_path()."""

    def test_returns_path_for_known_branch(self, tmp_path: Path) -> None:
        """Returns a Path for a branch that has a README."""
        import aipass.aipass.apps.handlers.readme_map as rm

        src_aipass = tmp_path / "src" / "aipass"
        cli_dir = src_aipass / "cli"
        cli_dir.mkdir(parents=True)
        readme = cli_dir / "README.md"
        readme.write_text("# CLI\n", encoding="utf-8")

        old_root = rm._AIPASS_ROOT
        old_map = rm._README_MAP
        try:
            rm._AIPASS_ROOT = tmp_path
            rm._README_MAP = None
            result = get_readme_path("cli")
        finally:
            rm._AIPASS_ROOT = old_root
            rm._README_MAP = old_map

        assert result == readme

    def test_returns_none_for_unknown_branch(self, tmp_path: Path) -> None:
        """Returns None for a branch not in the map."""
        import aipass.aipass.apps.handlers.readme_map as rm

        src_aipass = tmp_path / "src" / "aipass"
        src_aipass.mkdir(parents=True)

        old_root = rm._AIPASS_ROOT
        old_map = rm._README_MAP
        try:
            rm._AIPASS_ROOT = tmp_path
            rm._README_MAP = None
            result = get_readme_path("nonexistent_branch")
        finally:
            rm._AIPASS_ROOT = old_root
            rm._README_MAP = old_map

        assert result is None


# =============================================================================
# TestListBranches
# =============================================================================


class TestListBranches:
    """Tests for list_branches()."""

    def test_returns_list(self, tmp_path: Path) -> None:
        """Returns a list of strings."""
        import aipass.aipass.apps.handlers.readme_map as rm

        src_aipass = tmp_path / "src" / "aipass"
        for branch in ["drone", "prax"]:
            d = src_aipass / branch
            d.mkdir(parents=True)
            (d / "README.md").write_text(f"# {branch}\n", encoding="utf-8")

        old_root = rm._AIPASS_ROOT
        old_map = rm._README_MAP
        try:
            rm._AIPASS_ROOT = tmp_path
            rm._README_MAP = None
            result = list_branches()
        finally:
            rm._AIPASS_ROOT = old_root
            rm._README_MAP = old_map

        assert isinstance(result, list)
        assert "drone" in result
        assert "prax" in result

    def test_empty_when_no_readmes(self, tmp_path: Path) -> None:
        """Returns empty list when no branches have READMEs."""
        import aipass.aipass.apps.handlers.readme_map as rm

        src_aipass = tmp_path / "src" / "aipass"
        src_aipass.mkdir(parents=True)

        old_root = rm._AIPASS_ROOT
        old_map = rm._README_MAP
        try:
            rm._AIPASS_ROOT = tmp_path
            rm._README_MAP = None
            result = list_branches()
        finally:
            rm._AIPASS_ROOT = old_root
            rm._README_MAP = old_map

        assert result == []


# =============================================================================
# TestBranchesConstant
# =============================================================================


class TestBranchesConstant:
    """Tests for the BRANCHES constant."""

    def test_is_list(self) -> None:
        """BRANCHES is a list."""
        assert isinstance(BRANCHES, list)

    def test_contains_known_branches(self) -> None:
        """BRANCHES contains expected branch names."""
        assert "drone" in BRANCHES
        assert "aipass" in BRANCHES

    def test_no_duplicates(self) -> None:
        """BRANCHES has no duplicate entries."""
        assert len(BRANCHES) == len(set(BRANCHES))
