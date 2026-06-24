"""Tests for seedgo checker handlers -- batch 10 (hardcoded_path_check)."""

# =================== META ====================
# Name: test_checkers_batch10.py
# Description: Unit tests for hardcoded_path_check
# Version: 1.0.0
# Created: 2026-06-18
# Modified: 2026-06-18
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

    prax_mod = MagicMock()
    prax_mod.logger = mock_logger
    monkeypatch.setitem(sys.modules, "aipass.prax", prax_mod)

    json_pkg = MagicMock()
    json_pkg.json_handler = mock_json_handler
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.json", json_pkg)
    json_mod = MagicMock()
    json_mod.log_operation = mock_json_handler.log_operation
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.json.json_handler", json_mod)

    from aipass.seedgo.apps.handlers.bypass.utils import is_bypassed as real_is_bypassed

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
        "aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check",
    ]:
        monkeypatch.delitem(sys.modules, mod_name, raising=False)


# ===========================================================================
# 1. _scan_file — core scanning logic
# ===========================================================================


class TestScanFile:
    """Tests for the _scan_file helper."""

    def test_posix_home_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import _scan_file

        content = 'ROOT = "/home/patrick/Projects/AIPass"\n'
        result = _scan_file(content)
        assert len(result) == 1
        assert result[0][1] == "POSIX home path"

    def test_macos_home_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import _scan_file

        content = 'ROOT = "/Users/patrick/Projects/AIPass"\n'
        result = _scan_file(content)
        assert len(result) == 1
        assert result[0][1] == "macOS home path"

    def test_windows_home_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import _scan_file

        content = 'ROOT = "C:\\\\Users\\\\patrick\\\\Projects"\n'
        result = _scan_file(content)
        assert len(result) == 1
        assert result[0][1] == "Windows home path"

    def test_dash_encoded_posix_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import _scan_file

        content = 'dirs = ["-home-patrick-Projects-AIPass"]\n'
        result = _scan_file(content)
        assert len(result) == 1
        assert result[0][1] == "dash-encoded POSIX home"

    def test_dash_encoded_macos_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import _scan_file

        content = 'dirs = ["-Users-patrick-Projects-AIPass"]\n'
        result = _scan_file(content)
        assert len(result) == 1
        assert result[0][1] == "dash-encoded macOS home"

    def test_comment_skipped(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import _scan_file

        content = '# ROOT = "/home/patrick/Projects/AIPass"\n'
        result = _scan_file(content)
        assert len(result) == 0

    def test_indented_comment_skipped(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import _scan_file

        content = '    # path = "/home/patrick/test"\n'
        result = _scan_file(content)
        assert len(result) == 0

    def test_docstring_skipped(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import _scan_file

        content = '"""\nExample: /home/patrick/Projects\n"""\nx = 1\n'
        result = _scan_file(content)
        assert len(result) == 0

    def test_clean_file(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import _scan_file

        content = "from pathlib import Path\nROOT = Path(__file__).parent\n"
        result = _scan_file(content)
        assert len(result) == 0

    def test_generic_user_not_flagged(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import _scan_file

        content = 'path = "/home/user/Projects/AIPass"\n'
        result = _scan_file(content)
        assert len(result) == 1
        assert result[0][1] == "POSIX home path"

    def test_multiple_violations_same_file(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import _scan_file

        content = 'A = "/home/alice/foo"\nB = "/Users/bob/bar"\nC = "-home-charlie-baz"\n'
        result = _scan_file(content)
        assert len(result) == 3

    def test_line_numbers_correct(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import _scan_file

        content = 'clean = 1\nbad = "/home/patrick/x"\nalso_clean = 2\n'
        result = _scan_file(content)
        assert len(result) == 1
        assert result[0][0] == 2


# ===========================================================================
# 2. check_module — full integration via tmp files
# ===========================================================================


class TestCheckModule:
    """Tests for check_module entry point."""

    def test_clean_file_passes(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import check_module

        f = tmp_path / "clean.py"
        f.write_text("from pathlib import Path\nROOT = Path(__file__).parent\n")
        result = check_module(str(f))
        assert result["passed"] is True
        assert result["score"] == 100
        assert result["standard"] == "HARDCODED_PATH"

    def test_violation_fails(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import check_module

        f = tmp_path / "bad.py"
        f.write_text('ROOT = "/home/patrick/Projects/AIPass"\n')
        result = check_module(str(f))
        assert result["passed"] is False
        assert result["score"] == 0

    def test_bypass_whole_standard(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import check_module

        f = tmp_path / "bypassed.py"
        f.write_text('ROOT = "/home/patrick/Projects/AIPass"\n')
        rules = [{"standard": "hardcoded_path", "file": "bypassed.py"}]
        result = check_module(str(f), bypass_rules=rules)
        assert result["passed"] is True
        assert result["score"] == 100

    def test_bypass_specific_line(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import check_module

        f = tmp_path / "partial.py"
        f.write_text('A = "/home/alice/ok"\nB = "/home/bob/also_ok"\n')
        rules = [
            {"standard": "hardcoded_path", "file": "partial.py", "lines": [1, 2]},
        ]
        result = check_module(str(f), bypass_rules=rules)
        assert result["passed"] is True

    def test_init_py_skipped(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import check_module

        f = tmp_path / "__init__.py"
        f.write_text('X = "/home/patrick/nope"\n')
        result = check_module(str(f))
        assert result["passed"] is True
        assert "skipped" in result["checks"][0]["message"].lower()

    def test_nonexistent_file(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import check_module

        result = check_module("/no/such/file.py")
        assert result["passed"] is False
        assert result["score"] == 0

    def test_non_python_skipped(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import check_module

        f = tmp_path / "readme.md"
        f.write_text("/home/patrick/whatever\n")
        result = check_module(str(f))
        assert result["passed"] is True

    def test_violation_message_includes_line_info(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import check_module

        f = tmp_path / "info.py"
        f.write_text('x = "/home/alice/stuff"\n')
        result = check_module(str(f))
        msg = result["checks"][0]["message"]
        assert "L1" in msg
        assert "POSIX home path" in msg

    def test_more_than_three_violations_truncates(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import check_module

        f = tmp_path / "many.py"
        lines = [f'v{i} = "/home/u{i}/x"\n' for i in range(5)]
        f.write_text("".join(lines))
        result = check_module(str(f))
        msg = result["checks"][0]["message"]
        assert "and 2 more" in msg


# ===========================================================================
# 3. _in_docstring — edge cases
# ===========================================================================


class TestInDocstring:
    """Tests for docstring detection."""

    def test_single_line_docstring(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import _in_docstring

        lines = ['"""This is a docstring."""', 'x = "/home/pat/y"']
        assert _in_docstring(lines, 0) is False
        assert _in_docstring(lines, 1) is False

    def test_multiline_docstring(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import _in_docstring

        lines = ['"""', "/home/patrick/inside", '"""', "/home/patrick/outside"]
        assert _in_docstring(lines, 1) is True
        assert _in_docstring(lines, 3) is False

    def test_single_quote_docstring(self):
        from aipass.seedgo.apps.handlers.aipass_standards.hardcoded_path_check import _in_docstring

        lines = ["'''", "/home/patrick/inside", "'''", "/home/patrick/outside"]
        assert _in_docstring(lines, 1) is True
        assert _in_docstring(lines, 3) is False
