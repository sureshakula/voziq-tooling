# =================== AIPass ====================
# Name: test_cli_ux.py
# Description: Tests for cli_ux_check.py
# Version: 1.0.0
# Created: 2026-07-17
# Modified: 2026-07-17
# =============================================

"""Tests for cli_ux_check — CLI UX house pattern detection."""

from pathlib import Path

import pytest
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def _mock_infrastructure(monkeypatch):
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

    bypass_pkg = MagicMock()
    bypass_ignore = MagicMock()
    bypass_ignore.get_template_ignore_patterns = MagicMock(return_value=[])
    from aipass.seedgo.apps.handlers.bypass.utils import is_bypassed as real_is_bypassed

    bypass_utils = MagicMock()
    bypass_utils.is_bypassed = real_is_bypassed
    bypass_pkg.utils = bypass_utils
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.bypass", bypass_pkg)
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.bypass.ignore_handler", bypass_ignore)
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.bypass.utils", bypass_utils)

    for mod_name in ["aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check"]:
        monkeypatch.delitem(sys.modules, mod_name, raising=False)


def _entry_file(tmp_path, source):
    apps_dir = tmp_path / "apps"
    apps_dir.mkdir()
    f = apps_dir / "branch.py"
    f.write_text(source)
    return str(f)


# ============================================================
# Skip / edge cases
# ============================================================


def test_init_file_skipped(tmp_path):
    apps_dir = tmp_path / "apps"
    apps_dir.mkdir()
    f = apps_dir / "__init__.py"
    f.write_text("# init\n")
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(str(f))
    assert result["passed"] is True
    assert result["score"] == 100


def test_non_entry_point_skipped(tmp_path):
    handler_dir = tmp_path / "apps" / "handlers"
    handler_dir.mkdir(parents=True)
    f = handler_dir / "helper.py"
    f.write_text("def main(): pass\n")
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(str(f))
    assert result["passed"] is True
    assert result["score"] == 100


def test_missing_file():
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module("/nonexistent/apps/branch.py")
    assert result["passed"] is False
    assert result["score"] == 0


def test_empty_file(tmp_path):
    path = _entry_file(tmp_path, "")
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(path)
    assert result["passed"] is True


def test_syntax_error(tmp_path):
    path = _entry_file(tmp_path, "def broken(:\n")
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(path)
    assert result["passed"] is False


# ============================================================
# Good entry point — all checks pass
# ============================================================

GOOD_ENTRY = """
from aipass.cli import console

def print_introspection():
    console.print("[bold cyan]Branch Name[/bold cyan]")
    console.print("[dim]Does something useful[/dim]")
    console.print("[dim]Run --help for more[/dim]")

def print_help():
    console.print("[yellow]Usage:[/yellow]")
    console.print("  drone @branch command")
    console.print("[yellow]Examples:[/yellow]")
    console.print("  drone @branch do-stuff")

def main():
    pass
"""


def test_good_entry_passes_all(tmp_path):
    path = _entry_file(tmp_path, GOOD_ENTRY)
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(path)
    assert result["passed"] is True
    assert result["score"] == 100
    names = {c["name"] for c in result["checks"] if c["passed"]}
    assert "two_tier_help" in names
    assert "rich_console" in names
    assert "title_markup" in names
    assert "purpose_line" in names
    assert "help_pointer" in names
    assert "usage_section" in names
    assert "examples_section" in names
    assert "no_internal_modules" in names


# ============================================================
# Bad entry point — no print_introspection/print_help
# ============================================================

BAD_ENTRY = """
def main():
    print("BRANCH - 5 modules discovered")
    for m in modules:
        print(f"  {m}")
"""


def test_bad_entry_fails_two_tier(tmp_path):
    path = _entry_file(tmp_path, BAD_ENTRY)
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(path)
    assert result["passed"] is False
    checks = {c["name"]: c["passed"] for c in result["checks"]}
    assert checks["two_tier_help"] is False
    assert checks["rich_console"] is False
    assert checks["title_markup"] is False


# ============================================================
# Bare print in help functions
# ============================================================

BARE_PRINT_ENTRY = """
def print_introspection():
    print("[bold cyan]Title[/bold cyan]")
    print("[dim]Purpose[/dim]")
    print("Run --help for more")

def print_help():
    print("Usage: command")
    print("Examples: stuff")
"""


def test_bare_print_fails_rich_console(tmp_path):
    path = _entry_file(tmp_path, BARE_PRINT_ENTRY)
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(path)
    checks = {c["name"]: c["passed"] for c in result["checks"]}
    assert checks["two_tier_help"] is True
    assert checks["rich_console"] is False


# ============================================================
# Missing title markup
# ============================================================

NO_TITLE_ENTRY = """
from aipass.cli import console

def print_introspection():
    console.print("Branch Name")
    console.print("[dim]Purpose[/dim]")
    console.print("Run --help for more")

def print_help():
    console.print("[yellow]Usage:[/yellow]")
    console.print("[yellow]Examples:[/yellow]")
"""


def test_missing_title_markup(tmp_path):
    path = _entry_file(tmp_path, NO_TITLE_ENTRY)
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(path)
    checks = {c["name"]: c["passed"] for c in result["checks"]}
    assert checks["title_markup"] is False
    assert checks["purpose_line"] is True
    assert checks["help_pointer"] is True


# ============================================================
# Missing purpose line
# ============================================================

NO_PURPOSE_ENTRY = """
from aipass.cli import console

def print_introspection():
    console.print("[bold cyan]Branch Name[/bold cyan]")
    console.print("Run --help for more info")

def print_help():
    console.print("[yellow]Usage:[/yellow]")
    console.print("[yellow]Examples:[/yellow]")
"""


def test_missing_purpose_line(tmp_path):
    path = _entry_file(tmp_path, NO_PURPOSE_ENTRY)
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(path)
    checks = {c["name"]: c["passed"] for c in result["checks"]}
    assert checks["title_markup"] is True
    assert checks["purpose_line"] is False
    assert checks["help_pointer"] is True


# ============================================================
# Missing help pointer
# ============================================================

NO_POINTER_ENTRY = """
from aipass.cli import console

def print_introspection():
    console.print("[bold cyan]Branch Name[/bold cyan]")
    console.print("[dim]Does stuff[/dim]")

def print_help():
    console.print("[yellow]Usage:[/yellow]")
    console.print("[yellow]Examples:[/yellow]")
"""


def test_missing_help_pointer(tmp_path):
    path = _entry_file(tmp_path, NO_POINTER_ENTRY)
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(path)
    checks = {c["name"]: c["passed"] for c in result["checks"]}
    assert checks["help_pointer"] is False
    assert checks["title_markup"] is True
    assert checks["purpose_line"] is True


# ============================================================
# Missing usage section
# ============================================================

NO_USAGE_ENTRY = """
from aipass.cli import console

def print_introspection():
    console.print("[bold cyan]Branch[/bold cyan]")
    console.print("[dim]Purpose[/dim]")
    console.print("--help for more")

def print_help():
    console.print("[yellow]Commands:[/yellow]")
    console.print("[yellow]Examples:[/yellow]")
"""


def test_missing_usage_section(tmp_path):
    path = _entry_file(tmp_path, NO_USAGE_ENTRY)
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(path)
    checks = {c["name"]: c["passed"] for c in result["checks"]}
    assert checks["usage_section"] is False
    assert checks["examples_section"] is True


# ============================================================
# Missing examples section
# ============================================================

NO_EXAMPLES_ENTRY = """
from aipass.cli import console

def print_introspection():
    console.print("[bold cyan]Branch[/bold cyan]")
    console.print("[dim]Purpose[/dim]")
    console.print("--help for more")

def print_help():
    console.print("[yellow]Usage:[/yellow]")
    console.print("  drone @branch command")
"""


def test_missing_examples_section(tmp_path):
    path = _entry_file(tmp_path, NO_EXAMPLES_ENTRY)
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(path)
    checks = {c["name"]: c["passed"] for c in result["checks"]}
    assert checks["examples_section"] is False
    assert checks["usage_section"] is True


# ============================================================
# Internal modules exposed
# ============================================================


def test_internal_modules_detected(tmp_path):
    apps_dir = tmp_path / "apps"
    apps_dir.mkdir()
    modules_dir = apps_dir / "modules"
    modules_dir.mkdir()
    (modules_dir / "doctor_wire.py").write_text("def handle_command(): pass\n")
    (modules_dir / "doctor_fix.py").write_text("def handle_command(): pass\n")
    (modules_dir / "good_module.py").write_text("def handle_command(): pass\n")
    (modules_dir / "__init__.py").write_text("")

    source = """
from aipass.cli import console

def print_introspection():
    console.print("[bold cyan]Branch[/bold cyan]")
    console.print("[dim]Purpose[/dim]")
    console.print("--help for more")

def print_help():
    console.print("[yellow]Usage:[/yellow]")
    console.print("[yellow]Examples:[/yellow]")
"""
    f = apps_dir / "branch.py"
    f.write_text(source)

    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(str(f))
    checks = {c["name"]: c for c in result["checks"]}
    assert checks["no_internal_modules"]["passed"] is False
    assert "doctor_fix.py" in checks["no_internal_modules"]["message"]
    assert "doctor_wire.py" in checks["no_internal_modules"]["message"]


def test_underscore_prefixed_internal_ok(tmp_path):
    apps_dir = tmp_path / "apps"
    apps_dir.mkdir()
    modules_dir = apps_dir / "modules"
    modules_dir.mkdir()
    (modules_dir / "_doctor_wire.py").write_text("def handle_command(): pass\n")
    (modules_dir / "__init__.py").write_text("")

    source = """
from aipass.cli import console

def print_introspection():
    console.print("[bold cyan]Branch[/bold cyan]")
    console.print("[dim]Purpose[/dim]")
    console.print("--help for more")

def print_help():
    console.print("[yellow]Usage:[/yellow]")
    console.print("[yellow]Examples:[/yellow]")
"""
    f = apps_dir / "branch.py"
    f.write_text(source)

    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(str(f))
    checks = {c["name"]: c["passed"] for c in result["checks"]}
    assert checks["no_internal_modules"] is True


# ============================================================
# Bypass
# ============================================================


def test_bypass_passes(tmp_path):
    path = _entry_file(tmp_path, "def main(): print('hello')\n")
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    bypass = [{"standard": "cli_ux", "file": Path(path).as_posix()}]
    result = check_module(path, bypass_rules=bypass)
    assert result["passed"] is True
    assert result["score"] == 100


# ============================================================
# Score calculation
# ============================================================


def test_partial_score(tmp_path):
    source = """
from aipass.cli import console

def print_introspection():
    console.print("[bold cyan]Title[/bold cyan]")

def print_help():
    console.print("commands go here")
"""
    path = _entry_file(tmp_path, source)
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(path)
    assert 0 < result["score"] < 100
    assert result["passed"] is False


# ============================================================
# f-string extraction
# ============================================================


def test_fstring_title_detected(tmp_path):
    source = """
from aipass.cli import console

VERSION = "1.0"

def print_introspection():
    console.print(f"[bold cyan]Branch v{VERSION}[/bold cyan]")
    console.print("[dim]Purpose line[/dim]")
    console.print("Run --help for info")

def print_help():
    console.print("[yellow]Usage:[/yellow]")
    console.print("[yellow]Examples:[/yellow]")
"""
    path = _entry_file(tmp_path, source)
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(path)
    checks = {c["name"]: c["passed"] for c in result["checks"]}
    assert checks["title_markup"] is True


# ============================================================
# Real entry point validation
# ============================================================


def test_seedgo_entry_passes():
    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    _root = Path(__file__).resolve().parents[1]
    path = str(_root / "apps" / "seedgo.py")
    result = check_module(path)
    assert result["passed"] is True, f"seedgo.py should pass cli_ux: {[c for c in result['checks'] if not c['passed']]}"
    assert result["score"] == 100


def test_uppercase_registry_name_lowercase_path(tmp_path):
    """Regression: uppercase registry name (BACKUP) with lowercase filesystem path
    must still resolve and score correctly through the checker."""
    branch_dir = tmp_path / "backup"
    branch_dir.mkdir()
    apps_dir = branch_dir / "apps"
    apps_dir.mkdir()

    source = """
from aipass.cli import console

def print_introspection():
    console.print("[bold cyan]Backup Manager[/bold cyan]")
    console.print("[dim]Manages backups for AIPass[/dim]")
    console.print("[dim]Run --help for more[/dim]")

def print_help():
    console.print("[yellow]Usage:[/yellow]")
    console.print("  drone @backup run")
    console.print("[yellow]Examples:[/yellow]")
    console.print("  drone @backup snapshot")

def main():
    pass
"""
    entry = apps_dir / "backup.py"
    entry.write_text(source)

    from aipass.seedgo.apps.handlers.aipass_standards.cli_ux_check import check_module

    result = check_module(str(entry))
    assert result["passed"] is True
    assert result["score"] == 100
