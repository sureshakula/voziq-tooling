"""Tests for output_routing_check.py."""

# =================== META ====================
# Name: test_output_routing.py
# Description: Unit tests for output_routing_check
# Version: 1.0.0
# Created: 2026-07-09
# Modified: 2026-07-09
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
        "aipass.seedgo.apps.handlers.aipass_standards.output_routing_check",
    ]:
        monkeypatch.delitem(sys.modules, mod_name, raising=False)


# ===========================================================================
# 1. _is_status_console_print — detection logic
# ===========================================================================


class TestIsStatusConsolePrint:
    """Tests for the _is_status_console_print helper."""

    def test_red_markup_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert _is_status_console_print('console.print(f"[red]Error: {msg}[/red]")')

    def test_bold_red_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert _is_status_console_print('console.print("[bold red]Failed[/bold red]")')

    def test_red_bold_order_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert _is_status_console_print('console.print("[red bold]Error[/red bold]")')

    def test_status_emoji_cross_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert _is_status_console_print('console.print("❌ Something failed")')

    def test_status_emoji_check_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert _is_status_console_print('console.print("✅ Done")')

    def test_status_emoji_checkmark_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert _is_status_console_print('console.print("✓ Complete")')

    def test_status_emoji_cross_mark_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert _is_status_console_print('console.print("✗ Failed")')

    def test_green_check_pattern_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert _is_status_console_print('console.print("[green]✓[/green] Done")')

    def test_yellow_warning_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert _is_status_console_print('console.print("[yellow]⚠ Warning: check config[/yellow]")')

    def test_err_console_detected(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert _is_status_console_print('err_console.print(f"[red]Error[/red]")')

    def test_plain_console_print_not_flagged(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert not _is_status_console_print('console.print("Hello world")')

    def test_cyan_markup_not_flagged(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert not _is_status_console_print('console.print(f"[cyan]Info: {msg}[/cyan]")')

    def test_dim_markup_not_flagged(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert not _is_status_console_print('console.print(f"[dim]{details}[/dim]")')

    def test_table_object_not_flagged(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert not _is_status_console_print("console.print(table)")

    def test_panel_object_not_flagged(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert not _is_status_console_print("console.print(Panel(title))")

    def test_no_console_print_not_flagged(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert not _is_status_console_print('logger.info("[red]error[/red]")')

    def test_green_without_check_emoji_not_flagged(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert not _is_status_console_print('console.print("[green]name[/green]")')

    def test_yellow_without_warning_not_flagged(self):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import (
            _is_status_console_print,
        )

        assert not _is_status_console_print('console.print("[yellow]note[/yellow]")')


# ===========================================================================
# 2. _scan_file — file scanning
# ===========================================================================


class TestScanFile:
    """Tests for the _scan_file helper."""

    def test_detects_red_markup(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import _scan_file

        f = tmp_path / "test.py"
        f.write_text('console.print(f"[red]Error: {e}[/red]")\n', encoding="utf-8")
        lines, err = _scan_file(f)
        assert err is None
        assert lines == [1]

    def test_skips_docstrings(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import _scan_file

        f = tmp_path / "test.py"
        f.write_text(
            '"""\nconsole.print("[red]error[/red]")\n"""\npass\n',
            encoding="utf-8",
        )
        lines, err = _scan_file(f)
        assert err is None
        assert lines == []

    def test_skips_comments(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import _scan_file

        f = tmp_path / "test.py"
        f.write_text('# console.print("[red]error[/red]")\n', encoding="utf-8")
        lines, err = _scan_file(f)
        assert err is None
        assert lines == []

    def test_skips_inline_comment(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import _scan_file

        f = tmp_path / "test.py"
        f.write_text('x = 1  # console.print("[red]error[/red]")\n', encoding="utf-8")
        lines, err = _scan_file(f)
        assert err is None
        assert lines == []

    def test_detects_multiple_lines(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import _scan_file

        f = tmp_path / "test.py"
        f.write_text(
            'x = 1\nconsole.print("[red]a[/red]")\ny = 2\nconsole.print("✅ done")\n',
            encoding="utf-8",
        )
        lines, err = _scan_file(f)
        assert err is None
        assert lines == [2, 4]

    def test_clean_file(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import _scan_file

        f = tmp_path / "test.py"
        f.write_text('console.print("[cyan]info[/cyan]")\nprint("hello")\n', encoding="utf-8")
        lines, err = _scan_file(f)
        assert err is None
        assert lines == []

    def test_unreadable_file(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import _scan_file

        f = tmp_path / "missing.py"
        lines, err = _scan_file(f)
        assert err is not None
        assert lines == []


# ===========================================================================
# 3. check_module — full checker
# ===========================================================================


class TestCheckModule:
    """Tests for check_module."""

    def test_clean_file_passes(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import check_module

        f = tmp_path / "clean.py"
        f.write_text('from aipass.cli.apps.modules import error\nerror("fail")\n', encoding="utf-8")
        result = check_module(str(f))
        assert result["passed"] is True
        assert result["score"] == 100
        assert result["standard"] == "OUTPUT_ROUTING"

    def test_violation_detected(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import check_module

        f = tmp_path / "bad.py"
        f.write_text('console.print(f"[red]Error: {e}[/red]")\n', encoding="utf-8")
        result = check_module(str(f))
        assert result["passed"] is False
        assert result["score"] == 0

    def test_init_py_skipped(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import check_module

        f = tmp_path / "__init__.py"
        f.write_text('console.print("[red]error[/red]")\n', encoding="utf-8")
        result = check_module(str(f))
        assert result["passed"] is True
        assert result["score"] == 100

    def test_test_file_skipped(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import check_module

        f = tmp_path / "test_something.py"
        f.write_text('console.print("[red]error[/red]")\n', encoding="utf-8")
        result = check_module(str(f))
        assert result["passed"] is True
        assert result["score"] == 100

    def test_conftest_skipped(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import check_module

        f = tmp_path / "conftest.py"
        f.write_text('console.print("[red]error[/red]")\n', encoding="utf-8")
        result = check_module(str(f))
        assert result["passed"] is True
        assert result["score"] == 100

    def test_bypass_returns_100(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import check_module

        f = tmp_path / "bypassed.py"
        f.write_text('console.print("[red]error[/red]")\n', encoding="utf-8")
        bypass = [{"standard": "output_routing", "file": str(f)}]
        result = check_module(str(f), bypass_rules=bypass)
        assert result["passed"] is True
        assert result["score"] == 100

    def test_missing_file(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import check_module

        result = check_module(str(tmp_path / "no_such.py"))
        assert result["passed"] is False
        assert result["score"] == 0

    def test_line_bypass_all_lines_pass(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import check_module

        f = tmp_path / "partial.py"
        f.write_text(
            'console.print("[red]a[/red]")\nconsole.print("[red]b[/red]")\n',
            encoding="utf-8",
        )
        bypass = [{"standard": "output_routing", "file": "partial.py", "lines": [1, 2]}]
        result = check_module(str(f), bypass_rules=bypass)
        assert result["passed"] is True

    def test_violation_message_shows_lines(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import check_module

        f = tmp_path / "multi.py"
        f.write_text('console.print("[red]a[/red]")\nconsole.print("✅ b")\n', encoding="utf-8")
        result = check_module(str(f))
        assert "2 raw" in result["checks"][0]["message"]
        assert "1, 2" in result["checks"][0]["message"]

    def test_more_than_five_violations_truncated(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import check_module

        f = tmp_path / "many.py"
        lines = [f'console.print("[red]err{i}[/red]")\n' for i in range(8)]
        f.write_text("".join(lines), encoding="utf-8")
        result = check_module(str(f))
        assert "and 3 more" in result["checks"][0]["message"]


# ===========================================================================
# 4. False-positive avoidance
# ===========================================================================


class TestFalsePositiveAvoidance:
    """Verify that legitimate patterns are NOT flagged."""

    def test_table_print_not_flagged(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import check_module

        f = tmp_path / "tables.py"
        f.write_text("console.print(table)\nconsole.print(Panel(content))\n", encoding="utf-8")
        result = check_module(str(f))
        assert result["passed"] is True

    def test_blue_markup_not_flagged(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import check_module

        f = tmp_path / "blue.py"
        f.write_text('console.print("[blue]Processing...[/blue]")\n', encoding="utf-8")
        result = check_module(str(f))
        assert result["passed"] is True

    def test_empty_console_print_not_flagged(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import check_module

        f = tmp_path / "blank.py"
        f.write_text('console.print("")\nconsole.print()\n', encoding="utf-8")
        result = check_module(str(f))
        assert result["passed"] is True

    def test_docstring_with_markup_not_flagged(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import check_module

        f = tmp_path / "docs.py"
        content = '"""\nconsole.print("[red]error[/red]")\n"""\ndef foo(): pass\n'
        f.write_text(content, encoding="utf-8")
        result = check_module(str(f))
        assert result["passed"] is True

    def test_green_text_without_emoji_not_flagged(self, tmp_path):
        from aipass.seedgo.apps.handlers.aipass_standards.output_routing_check import check_module

        f = tmp_path / "green.py"
        f.write_text('console.print("[green]branch_name[/green]")\n', encoding="utf-8")
        result = check_module(str(f))
        assert result["passed"] is True
