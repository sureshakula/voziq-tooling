# =================== AIPass ====================
# Name: test_subcommand_help.py
# Description: Tests for subcommand_help_check.py
# Version: 1.0.0
# Created: 2026-07-10
# Modified: 2026-07-10
# =============================================

"""Tests for subcommand_help_check — subcommand --help guard detection."""

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

    for mod_name in ["aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check"]:
        monkeypatch.delitem(sys.modules, mod_name, raising=False)


def _entry_file(tmp_path, source):
    """Create a file under an apps/ directory to pass entry-point check."""
    apps_dir = tmp_path / "apps"
    apps_dir.mkdir()
    f = apps_dir / "branch.py"
    f.write_text(source)
    return str(f)


# ============================================================
# Non-entry-point files — skipped
# ============================================================


def test_non_entry_point_skipped(tmp_path):
    f = tmp_path / "handler.py"
    f.write_text("def main(): pass\n")
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(str(f))
    assert result["passed"] is True
    assert result["score"] == 100


def test_missing_file():
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module("/nonexistent/apps/branch.py")
    assert result["passed"] is False
    assert result["score"] == 0


def test_no_entry_function(tmp_path):
    src = "def helper(): pass\n"
    f = _entry_file(tmp_path, src)
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(f)
    assert result["passed"] is True
    assert "skipped" in result["checks"][0]["message"]


# ============================================================
# MUST FAIL — top-level --help only, no subcommand guard
# ============================================================


def test_toplevel_only_fails(tmp_path):
    src = """\
import sys
def main():
    args = sys.argv[1:]
    if args[0] in ["--help", "-h"]:
        print_help()
        return 0
    command = args[0]
    remaining = args[1:]
    route_command(command, remaining, modules)
"""
    f = _entry_file(tmp_path, src)
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(f)
    assert result["passed"] is False
    assert result["score"] == 0
    assert "No subcommand --help guard" in result["checks"][0]["message"]


def test_no_help_at_all_fails(tmp_path):
    src = """\
import sys
def main():
    args = sys.argv[1:]
    command = args[0]
    remaining = args[1:]
    route_command(command, remaining, modules)
"""
    f = _entry_file(tmp_path, src)
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(f)
    assert result["passed"] is False


# ============================================================
# MUST PASS — explicit subcommand --help guard
# ============================================================


def test_remaining_subscript_guard_passes(tmp_path):
    src = """\
import sys
def main():
    args = sys.argv[1:]
    if args[0] in ["--help", "-h"]:
        print_help()
        return 0
    command = args[0]
    remaining = args[1:]
    if remaining and remaining[0] in ["--help", "-h"]:
        show_subcommand_help(command)
        return 0
    route_command(command, remaining, modules)
"""
    f = _entry_file(tmp_path, src)
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(f)
    assert result["passed"] is True
    assert result["score"] == 100


def test_remaining_args_variable_passes(tmp_path):
    src = """\
import sys
def main():
    args = sys.argv[1:]
    if args[0] in ["--help", "-h"]:
        print_help()
        return 0
    command = args[0]
    remaining_args = args[1:]
    if remaining_args and remaining_args[0] in ["--help", "-h"]:
        show_subcommand_help(command)
        return 0
    route_command(command, remaining_args, modules)
"""
    f = _entry_file(tmp_path, src)
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(f)
    assert result["passed"] is True


def test_help_in_remaining_passes(tmp_path):
    src = """\
import sys
def main():
    args = sys.argv[1:]
    command = args[0]
    remaining = args[1:]
    if "--help" in remaining:
        show_help(command)
        return 0
    route_command(command, remaining, modules)
"""
    f = _entry_file(tmp_path, src)
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(f)
    assert result["passed"] is True


def test_post_dispatch_fallback_passes(tmp_path):
    src = """\
import sys
def main():
    args = sys.argv[1:]
    if args[0] in ["--help", "-h"]:
        print_help()
        return 0
    command = args[0]
    remaining_args = args[1:]
    if route_command(command, remaining_args, modules):
        return 0
    if remaining_args and remaining_args[0] in ["--help", "-h"]:
        print_module_help(command, modules)
        return 0
"""
    f = _entry_file(tmp_path, src)
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(f)
    assert result["passed"] is True


# ============================================================
# MUST PASS — argparse pattern
# ============================================================


def test_argparse_parse_known_args_passes(tmp_path):
    src = """\
import argparse
def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?")
    parser.add_argument("--help", "-h", action="store_true", dest="show_help")
    parsed_args, remaining = parser.parse_known_args()
    if parsed_args.show_help:
        all_args = ["--help"] + remaining
    route_command(parsed_args.command, all_args, handlers)
"""
    f = _entry_file(tmp_path, src)
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(f)
    assert result["passed"] is True
    assert "parse_known_args" in result["checks"][0]["message"]


# ============================================================
# MUST PASS — handle_command function
# ============================================================


def test_handle_command_function_detected(tmp_path):
    src = """\
def handle_command(command, args):
    if args and args[0] in ["--help", "-h"]:
        return False
    route_command(command, args, modules)
"""
    f = _entry_file(tmp_path, src)
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(f)
    assert result["passed"] is True


# ============================================================
# MUST PASS — bypass
# ============================================================


def test_bypassed_file_passes(tmp_path):
    src = "def main(): pass\n"
    f = _entry_file(tmp_path, src)
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    bypass_rules = [{"file": f, "standard": "subcommand_help"}]
    result = check_module(f, bypass_rules=bypass_rules)
    assert result["passed"] is True
    assert result["score"] == 100


# ============================================================
# Edge cases
# ============================================================


def test_syntax_error_file(tmp_path):
    src = "def main(\n"
    f = _entry_file(tmp_path, src)
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(f)
    assert result["passed"] is False
    assert "Syntax error" in result["checks"][0]["message"]


def test_rest_variable_passes(tmp_path):
    src = """\
import sys
def main():
    args = sys.argv[1:]
    command = args[0]
    rest = args[1:]
    if rest and rest[0] in ["--help", "-h"]:
        show_help(command)
        return 0
    route_command(command, rest, modules)
"""
    f = _entry_file(tmp_path, src)
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(f)
    assert result["passed"] is True


def test_cmd_args_variable_passes(tmp_path):
    src = """\
import sys
def main():
    args = sys.argv[1:]
    command = args[0]
    cmd_args = args[1:]
    if cmd_args and cmd_args[0] in ["--help", "-h"]:
        show_help(command)
        return 0
    route_command(command, cmd_args, modules)
"""
    f = _entry_file(tmp_path, src)
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(f)
    assert result["passed"] is True


def test_name_eq_help_passes(tmp_path):
    src = """\
def main():
    command = args[0]
    remaining = args[1:]
    flag = remaining[0]
    if flag == "--help":
        show_help(command)
        return 0
"""
    f = _entry_file(tmp_path, src)
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(f)
    assert result["passed"] is True


# ============================================================
# Fleet fixtures — real entry points
# ============================================================

_AIPASS_ROOT = Path(__file__).resolve().parents[2]


def test_commons_entry_passes():
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(str(_AIPASS_ROOT / "commons" / "apps" / "commons.py"))
    assert result["passed"] is True, f"commons should pass: {result['checks']}"


def test_prax_entry_passes():
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(str(_AIPASS_ROOT / "prax" / "apps" / "prax.py"))
    assert result["passed"] is True, f"prax should pass: {result['checks']}"


def test_flow_entry_passes():
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(str(_AIPASS_ROOT / "flow" / "apps" / "flow.py"))
    assert result["passed"] is True, f"flow should pass: {result['checks']}"


def test_seedgo_entry_passes():
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(str(_AIPASS_ROOT / "seedgo" / "apps" / "seedgo.py"))
    assert result["passed"] is True, f"seedgo should pass: {result['checks']}"


def test_ai_mail_entry_passes():
    from aipass.seedgo.apps.handlers.aipass_standards.subcommand_help_check import check_module

    result = check_module(str(_AIPASS_ROOT / "ai_mail" / "apps" / "ai_mail.py"))
    assert result["passed"] is True, f"ai_mail should pass: {result['checks']}"
