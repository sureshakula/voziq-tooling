"""Tests for handler_import_check."""

# =================== META ====================
# Name: test_handler_import.py
# Description: Unit tests for handler_import_check checker handler
# Version: 1.0.0
# Created: 2026-04-26
# Modified: 2026-04-26
# =============================================

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_file(path: Path, content: str) -> None:
    """Write content to a file, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_infrastructure(monkeypatch):
    """Mock heavy infrastructure imports for the handler_import checker."""
    mock_logger = MagicMock()
    mock_json_handler = MagicMock()
    mock_json_handler.log_operation = MagicMock(return_value=True)

    # -- prax ---------------------------------------------------------------
    prax_mod = MagicMock()
    prax_mod.logger = mock_logger
    monkeypatch.setitem(sys.modules, "aipass.prax", prax_mod)

    # -- seedgo json handler ------------------------------------------------
    json_pkg = MagicMock()
    json_pkg.json_handler = mock_json_handler
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.json", json_pkg)
    json_mod = MagicMock()
    json_mod.log_operation = mock_json_handler.log_operation
    monkeypatch.setitem(
        sys.modules,
        "aipass.seedgo.apps.handlers.json.json_handler",
        json_mod,
    )

    # -- bypass handler -----------------------------------------------------
    bypass_pkg = MagicMock()
    bypass_ignore = MagicMock()
    bypass_ignore.get_template_ignore_patterns = MagicMock(return_value=[])
    bypass_pkg.ignore_handler = bypass_ignore
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.bypass", bypass_pkg)
    monkeypatch.setitem(
        sys.modules,
        "aipass.seedgo.apps.handlers.bypass.ignore_handler",
        bypass_ignore,
    )

    # Force re-import so checker picks up fresh mocks
    monkeypatch.delitem(
        sys.modules,
        "aipass.seedgo.apps.handlers.aipass_standards.handler_import_check",
        raising=False,
    )
    monkeypatch.delitem(
        sys.modules,
        "aipass.seedgo.apps.handlers.aipass_standards.handler_import_content",
        raising=False,
    )


# ===========================================================================
# handler_import_check tests
# ===========================================================================


class TestHandlerImportCheck:
    """Tests for the handler_import_check checker."""

    def test_branch_with_handler_import_passes(self, tmp_path: Path) -> None:
        """apps/__init__.py containing 'from . import handlers' scores 100."""
        _write_file(
            tmp_path / "apps" / "__init__.py",
            "from . import handlers\n",
        )
        from aipass.seedgo.apps.handlers.aipass_standards.handler_import_check import (
            check_branch,
        )

        result = check_branch(str(tmp_path))
        assert result["passed"] is True
        assert result["score"] == 100
        assert result["standard"] == "HANDLER_IMPORT"

    def test_branch_missing_handler_import_fails(self, tmp_path: Path) -> None:
        """apps/__init__.py without the handler import scores 0."""
        _write_file(
            tmp_path / "apps" / "__init__.py",
            "from . import modules\n",
        )
        from aipass.seedgo.apps.handlers.aipass_standards.handler_import_check import (
            check_branch,
        )

        result = check_branch(str(tmp_path))
        assert result["passed"] is False
        assert result["score"] == 0
        assert result["standard"] == "HANDLER_IMPORT"
        failed = [c for c in result["checks"] if not c["passed"]]
        assert len(failed) == 1
        assert "missing" in failed[0]["message"]

    def test_branch_no_apps_init_fails(self, tmp_path: Path) -> None:
        """Branch with no apps/__init__.py at all scores 0."""
        # Create apps/ directory but no __init__.py
        (tmp_path / "apps").mkdir(parents=True)
        from aipass.seedgo.apps.handlers.aipass_standards.handler_import_check import (
            check_branch,
        )

        result = check_branch(str(tmp_path))
        assert result["passed"] is False
        assert result["score"] == 0
        assert "not found" in result["checks"][0]["message"]

    def test_branch_bypassed(self, tmp_path: Path) -> None:
        """Bypass rule matches produce score 100."""
        # No apps/ at all -- bypass should still pass
        from aipass.seedgo.apps.handlers.aipass_standards.handler_import_check import (
            check_branch,
        )

        bypass = [{"standard": "handler_import"}]
        result = check_branch(str(tmp_path), bypass_rules=bypass)
        assert result["passed"] is True
        assert result["score"] == 100

    def test_branch_no_apps_dir(self, tmp_path: Path) -> None:
        """Branch with no apps/ directory at all scores 0."""
        from aipass.seedgo.apps.handlers.aipass_standards.handler_import_check import (
            check_branch,
        )

        result = check_branch(str(tmp_path))
        assert result["passed"] is False
        assert result["score"] == 0
        assert "not found" in result["checks"][0]["message"]

    def test_content_returns_string(self) -> None:
        """handler_import_content.get_handler_import_standards() returns non-empty string."""
        from aipass.seedgo.apps.handlers.aipass_standards.handler_import_content import (
            get_handler_import_standards,
        )

        content = get_handler_import_standards()
        assert isinstance(content, str)
        assert len(content) > 0
        assert "HANDLER IMPORT" in content
