"""Tests for the aipass_standards handler directory."""

# =================== META ====================
# Name: test_aipass_standards.py
# Description: Unit tests for handlers/aipass_standards/
# Version: 1.0.0
# Created: 2026-03-24
# Modified: 2026-03-24
# =============================================

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
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.json.json_handler", json_mod)

    # Force re-imports of specific checker modules we test
    for mod_name in [
        "aipass.seedgo.apps.handlers.aipass_standards.naming_check",
        "aipass.seedgo.apps.handlers.aipass_standards.json_structure_check",
        "aipass.seedgo.apps.handlers.aipass_standards.meta_check",
    ]:
        monkeypatch.delitem(sys.modules, mod_name, raising=False)


# ---------------------------------------------------------------------------
# Tests -- naming_check.check_module
# ---------------------------------------------------------------------------


def test_naming_check_module_returns_dict(tmp_path):
    """naming_check.check_module returns a dict with expected keys."""
    py_file = tmp_path / "sample.py"
    py_file.write_text(
        '"""Sample module."""\n\ndef my_function():\n    pass\n',
        encoding="utf-8",
    )
    from aipass.seedgo.apps.handlers.aipass_standards.naming_check import check_module

    result = check_module(str(py_file))
    assert isinstance(result, dict)
    assert "passed" in result
    assert "checks" in result
    assert "score" in result
    assert isinstance(result["passed"], bool)
    assert isinstance(result["checks"], list)
    assert isinstance(result["score"], (int, float))


def test_naming_check_module_missing_file():
    """naming_check.check_module handles missing file gracefully."""
    from aipass.seedgo.apps.handlers.aipass_standards.naming_check import check_module

    result = check_module("/nonexistent/path/file.py")
    assert isinstance(result, dict)
    assert "passed" in result


def test_naming_check_module_with_bypass(tmp_path):
    """naming_check.check_module respects bypass rules."""
    py_file = tmp_path / "sample.py"
    py_file.write_text("x = 1\n", encoding="utf-8")
    from aipass.seedgo.apps.handlers.aipass_standards.naming_check import check_module

    bypass = [{"file": "sample.py", "standard": "naming", "reason": "test"}]
    result = check_module(str(py_file), bypass_rules=bypass)
    assert isinstance(result, dict)
    assert result["passed"] is True


# ---------------------------------------------------------------------------
# Tests -- json_structure_check.check_module
# ---------------------------------------------------------------------------


def test_json_structure_check_returns_expected_keys(tmp_path):
    """json_structure_check.check_module returns dict with standard keys."""
    py_file = tmp_path / "sample.py"
    py_file.write_text(
        '"""Sample."""\nimport json\n',
        encoding="utf-8",
    )
    from aipass.seedgo.apps.handlers.aipass_standards.json_structure_check import check_module

    result = check_module(str(py_file))
    assert isinstance(result, dict)
    assert "passed" in result
    assert "score" in result
    assert "checks" in result


def test_json_structure_check_missing_file():
    """json_structure_check.check_module handles missing file."""
    from aipass.seedgo.apps.handlers.aipass_standards.json_structure_check import check_module

    result = check_module("/nonexistent/module.py")
    assert isinstance(result, dict)
    assert "passed" in result


def test_json_structure_check_has_standard_field(tmp_path):
    """json_structure_check.check_module includes 'standard' in output."""
    py_file = tmp_path / "test_mod.py"
    py_file.write_text("x = 1\n", encoding="utf-8")
    from aipass.seedgo.apps.handlers.aipass_standards.json_structure_check import check_module

    result = check_module(str(py_file))
    assert "standard" in result


def test_json_structure_custom_config_subdir_passes(tmp_path):
    """Branch with {branch}_json/custom_config/ passes directory check."""
    from aipass.seedgo.apps.handlers.aipass_standards.json_structure_check import _check_json_dir_structure

    branch = tmp_path / "mybranch"
    branch.mkdir()
    json_dir = branch / "mybranch_json"
    json_dir.mkdir()
    cc = json_dir / "custom_config"
    cc.mkdir()
    (cc / "settings.json").write_text("{}", encoding="utf-8")
    (json_dir / "config.json").write_text("{}", encoding="utf-8")

    violations = _check_json_dir_structure(str(branch))
    assert violations == []


def test_json_structure_random_subdir_fails(tmp_path):
    """Branch with an unsanctioned subdir under {branch}_json/ is flagged."""
    from aipass.seedgo.apps.handlers.aipass_standards.json_structure_check import _check_json_dir_structure

    branch = tmp_path / "mybranch"
    branch.mkdir()
    json_dir = branch / "mybranch_json"
    json_dir.mkdir()
    (json_dir / "custom_config").mkdir()
    (json_dir / "extra_stuff").mkdir()

    violations = _check_json_dir_structure(str(branch))
    assert len(violations) == 1
    assert "extra_stuff" in violations[0]["message"]


def test_json_structure_hidden_subdir_ignored(tmp_path):
    """Hidden subdirs (e.g. .archive) under {branch}_json/ are not flagged."""
    from aipass.seedgo.apps.handlers.aipass_standards.json_structure_check import _check_json_dir_structure

    branch = tmp_path / "mybranch"
    branch.mkdir()
    json_dir = branch / "mybranch_json"
    json_dir.mkdir()
    (json_dir / ".archive").mkdir()

    violations = _check_json_dir_structure(str(branch))
    assert violations == []


def test_json_structure_no_json_dir_passes(tmp_path):
    """Branch with no {branch}_json/ directory produces no violations."""
    from aipass.seedgo.apps.handlers.aipass_standards.json_structure_check import _check_json_dir_structure

    branch = tmp_path / "mybranch"
    branch.mkdir()

    violations = _check_json_dir_structure(str(branch))
    assert violations == []


def test_json_structure_check_branch_post(tmp_path):
    """check_branch_post returns violations and scores."""
    from aipass.seedgo.apps.handlers.aipass_standards.json_structure_check import check_branch_post

    branch = tmp_path / "mybranch"
    branch.mkdir()
    json_dir = branch / "mybranch_json"
    json_dir.mkdir()
    (json_dir / "bad_split").mkdir()

    violations, scores = check_branch_post(str(branch))
    assert len(violations) == 1
    assert scores == [0]

    # Clean branch
    (json_dir / "bad_split").rmdir()
    (json_dir / "custom_config").mkdir()
    violations2, scores2 = check_branch_post(str(branch))
    assert violations2 == []
    assert scores2 == [100]


def test_json_structure_bypassed_subdir_passes(tmp_path):
    """A subdir bypassed via bypass_rules is not flagged."""
    from aipass.seedgo.apps.handlers.aipass_standards.json_structure_check import _check_json_dir_structure

    branch = tmp_path / "mybranch"
    branch.mkdir()
    json_dir = branch / "mybranch_json"
    json_dir.mkdir()
    (json_dir / "compass").mkdir()

    bypass_rules = [{"standard": "json_structure", "file": "mybranch_json/compass", "reason": "test"}]
    violations = _check_json_dir_structure(str(branch), bypass_rules=bypass_rules)
    assert violations == []


def test_json_structure_unbypassed_subdir_still_fails(tmp_path):
    """An unsanctioned subdir without a bypass entry is still flagged."""
    from aipass.seedgo.apps.handlers.aipass_standards.json_structure_check import _check_json_dir_structure

    branch = tmp_path / "mybranch"
    branch.mkdir()
    json_dir = branch / "mybranch_json"
    json_dir.mkdir()
    (json_dir / "compass").mkdir()
    (json_dir / "random_dir").mkdir()

    bypass_rules = [{"standard": "json_structure", "file": "mybranch_json/compass", "reason": "test"}]
    violations = _check_json_dir_structure(str(branch), bypass_rules=bypass_rules)
    assert len(violations) == 1
    assert "random_dir" in violations[0]["message"]


# ---------------------------------------------------------------------------
# Tests -- naming_check.is_bypassed
# ---------------------------------------------------------------------------


def test_naming_is_bypassed_true():
    """is_bypassed returns True when rule matches."""
    from aipass.seedgo.apps.handlers.aipass_standards.naming_check import is_bypassed

    rules = [{"file": "foo.py", "standard": "naming", "reason": "legacy"}]
    assert is_bypassed("some/path/foo.py", "naming", bypass_rules=rules) is True


def test_naming_is_bypassed_false_no_rules():
    """is_bypassed returns False with no rules."""
    from aipass.seedgo.apps.handlers.aipass_standards.naming_check import is_bypassed

    assert is_bypassed("foo.py", "naming", bypass_rules=None) is False


def test_naming_is_bypassed_wrong_standard():
    """is_bypassed returns False when standard does not match."""
    from aipass.seedgo.apps.handlers.aipass_standards.naming_check import is_bypassed

    rules = [{"file": "foo.py", "standard": "imports", "reason": "legacy"}]
    assert is_bypassed("foo.py", "naming", bypass_rules=rules) is False
