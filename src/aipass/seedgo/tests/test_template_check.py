"""Tests for template_check — template/boilerplate detection checker."""

# =================== META ====================
# Name: test_template_check.py
# Description: Unit tests for template_check
# Version: 1.0.0
# Created: 2026-07-01
# Modified: 2026-07-01
# =============================================

import json

import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_infrastructure(monkeypatch):
    """Mock heavy infrastructure imports for standards checkers."""
    import sys

    mock_logger = MagicMock()
    mock_json_handler = MagicMock()
    mock_json_handler.log_operation = MagicMock(return_value=True)

    prax_mod = MagicMock()
    prax_mod.logger = mock_logger
    monkeypatch.setitem(sys.modules, "aipass.prax", prax_mod)

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

    from aipass.seedgo.apps.handlers.bypass.utils import (
        is_bypassed as real_is_bypassed,
    )

    bypass_pkg = MagicMock()
    bypass_utils = MagicMock()
    bypass_utils.is_bypassed = real_is_bypassed
    bypass_pkg.utils = bypass_utils
    bypass_ignore = MagicMock()
    bypass_ignore.get_template_ignore_patterns = MagicMock(return_value=[])
    bypass_pkg.ignore_handler = bypass_ignore
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.bypass", bypass_pkg)
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.bypass.utils", bypass_utils)
    monkeypatch.setitem(
        sys.modules,
        "aipass.seedgo.apps.handlers.bypass.ignore_handler",
        bypass_ignore,
    )

    for mod_name in [
        "aipass.seedgo.apps.handlers.aipass_standards.template_check",
    ]:
        monkeypatch.delitem(sys.modules, mod_name, raising=False)


# ===========================================================================
# 1. _find_markers — core detection logic
# ===========================================================================


class TestFindMarkers:
    """Tests for the _find_markers helper."""

    def test_needs_configuration_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            _find_markers,
        )

        markers = _find_markers("This file NEEDS CONFIGURATION.", False)
        assert any("NEEDS CONFIGURATION" in m for m in markers)

    def test_mustache_branchname_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            _find_markers,
        )

        markers = _find_markers("Welcome to {{BRANCHNAME}}.", False)
        assert any("{{BRANCHNAME}}" in m for m in markers)

    def test_mustache_branch_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            _find_markers,
        )

        markers = _find_markers("Branch: {{BRANCH}}", False)
        assert any("{{BRANCH}}" in m for m in markers)

    def test_instructions_marker_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            _find_markers,
        )

        markers = _find_markers("INSTRUCTIONS FOR FILLING OUT THIS TEMPLATE", False)
        assert len(markers) >= 1

    def test_when_youre_done_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            _find_markers,
        )

        markers = _find_markers("WHEN YOU'RE DONE, delete this section", False)
        assert any("WHEN YOU'RE DONE" in m for m in markers)

    def test_single_curly_detected_in_markdown(self):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            _find_markers,
        )

        markers = _find_markers(
            "Role: {one-line role description}\nDo: {Primary responsibility}",
            True,
        )
        assert any("single-curly" in m for m in markers)

    def test_single_curly_not_detected_in_json(self):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            _find_markers,
        )

        markers = _find_markers('{"key": "value", "nested": {"a": 1}}', False)
        assert not any("single-curly" in m for m in markers)

    def test_double_curly_not_double_counted_as_single(self):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            _find_markers,
        )

        content = "Hello {{BRANCH}}, welcome."
        markers = _find_markers(content, True)
        assert not any("single-curly" in m for m in markers)

    def test_clean_content_no_markers(self):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            _find_markers,
        )

        markers = _find_markers(
            "This is a well-configured branch prompt with real content.",
            True,
        )
        assert markers == []

    def test_case_insensitive_detection(self):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            _find_markers,
        )

        markers = _find_markers("needs configuration", False)
        assert any("NEEDS CONFIGURATION" in m for m in markers)


# ===========================================================================
# 2. check_branch — integration tests
# ===========================================================================


class TestCheckBranch:
    """Tests for the check_branch function."""

    def test_stub_prompt_flagged(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            check_branch,
        )

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        (aipass_dir / "aipass_local_prompt.md").write_text(
            "# {{BRANCHNAME}}\nNEEDS CONFIGURATION\n"
            "INSTRUCTIONS FOR FILLING OUT THIS TEMPLATE\n"
            "WHEN YOU'RE DONE, delete this block.\n"
            "Role: {one-line role description}\n"
        )
        (tmp_path / "README.md").write_text("# My Branch\nConfigured.")
        trinity = tmp_path / ".trinity"
        trinity.mkdir()
        (trinity / "passport.json").write_text('{"branch": "test"}')

        result = check_branch(str(tmp_path))
        assert result["passed"] is True
        assert result["advisory"] is True
        assert result["score"] < 100
        prompt_check = next(c for c in result["checks"] if "aipass_local_prompt" in c["name"])
        assert not prompt_check["passed"]
        assert "template markers" in prompt_check["message"]

    def test_configured_branch_clean(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            check_branch,
        )

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        (aipass_dir / "aipass_local_prompt.md").write_text("# My Branch\nThis is my real prompt with real content.")
        (tmp_path / "README.md").write_text("# My Branch\nReal documentation.")
        trinity = tmp_path / ".trinity"
        trinity.mkdir()
        (trinity / "passport.json").write_text(json.dumps({"branch": "test", "role": "builder"}))

        result = check_branch(str(tmp_path))
        assert result["passed"] is True
        assert result["score"] == 100
        assert all(c["passed"] for c in result["checks"])

    def test_bypass_suppresses_warning(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            check_branch,
        )

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        (aipass_dir / "aipass_local_prompt.md").write_text("NEEDS CONFIGURATION\n{{BRANCH}}\n")
        (tmp_path / "README.md").write_text("# Configured\nReal content.")

        bypass_rules = [
            {
                "file": "aipass_local_prompt",
                "standard": "template",
                "reason": "intentionally left as template",
            }
        ]
        result = check_branch(str(tmp_path), bypass_rules=bypass_rules)
        prompt_check = next(c for c in result["checks"] if "aipass_local_prompt" in c["name"])
        assert prompt_check["passed"]
        assert "bypassed" in prompt_check["message"]

    def test_trinity_json_no_false_positive(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            check_branch,
        )

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        (aipass_dir / "aipass_local_prompt.md").write_text("Real prompt.")
        (tmp_path / "README.md").write_text("# Branch\nReal docs.")
        trinity = tmp_path / ".trinity"
        trinity.mkdir()
        (trinity / "passport.json").write_text(
            json.dumps(
                {
                    "branch_info": {"branch_name": "test"},
                    "identity": {"role": "builder", "purpose": "testing"},
                    "nested": {"key": "value"},
                }
            )
        )
        (trinity / "local.json").write_text(
            json.dumps(
                {
                    "sessions": [{"date": "2026-01-01", "summary": "work"}],
                    "todos": [],
                }
            )
        )

        result = check_branch(str(tmp_path))
        assert result["score"] == 100
        trinity_checks = [c for c in result["checks"] if c["name"].endswith(".json")]
        assert all(c["passed"] for c in trinity_checks)

    def test_standard_level_bypass(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            check_branch,
        )

        bypass_rules = [{"standard": "template", "reason": "skip all"}]
        result = check_branch(str(tmp_path), bypass_rules=bypass_rules)
        assert result["passed"] is True
        assert result["score"] == 100

    def test_missing_targets_skipped(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            check_branch,
        )

        result = check_branch(str(tmp_path))
        assert result["passed"] is True
        assert result["advisory"] is True

    def test_curly_placeholders_in_prompt(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.template_check import (
            check_branch,
        )

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        (aipass_dir / "aipass_local_prompt.md").write_text(
            "Role: {one-line role description}\nDo: {Primary responsibility}\nCommands: {command1}\n"
        )
        (tmp_path / "README.md").write_text("# Branch\nConfigured.")

        result = check_branch(str(tmp_path))
        prompt_check = next(c for c in result["checks"] if "aipass_local_prompt" in c["name"])
        assert not prompt_check["passed"]
        assert "single-curly" in prompt_check["message"]
