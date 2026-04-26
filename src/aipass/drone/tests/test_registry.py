# =================== AIPass ====================
# Name: test_registry.py
# Description: Tests for the registry module orchestrator
# Version: 1.0.0
# Created: 2026-04-26
# Modified: 2026-04-26
# =============================================

"""Tests for the registry module orchestrator (apps/modules/registry.py).

Covers:
- print_introspection() output
- print_help() output
- handle_command() dispatch: load, branches, lookup, help, introspection, unknown
"""

from unittest.mock import patch

import pytest

_REG = "aipass.drone.apps.modules.registry"


# ===========================================================================
# print_introspection
# ===========================================================================


class TestPrintIntrospection:
    """print_introspection() output."""

    def test_prints_module_info(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Prints registry module info to stdout."""
        from aipass.drone.apps.modules.registry import print_introspection

        print_introspection()
        captured = capsys.readouterr()
        assert "registry" in captured.out.lower()
        assert "handler" in captured.out.lower()

    def test_fallback_console(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Falls back to rich.Console when CLI console unavailable."""
        import importlib
        import sys

        import aipass.drone.apps.modules.registry as reg_mod

        saved = sys.modules.pop("aipass.cli.apps.modules.display", None)
        sys.modules["aipass.cli.apps.modules.display"] = None  # type: ignore[assignment]
        try:
            importlib.reload(reg_mod)
            reg_mod.print_introspection()
            captured = capsys.readouterr()
            assert "registry" in captured.out.lower()
        finally:
            if saved is not None:
                sys.modules["aipass.cli.apps.modules.display"] = saved
            else:
                sys.modules.pop("aipass.cli.apps.modules.display", None)
            importlib.reload(reg_mod)


# ===========================================================================
# print_help
# ===========================================================================


class TestPrintHelp:
    """print_help() output."""

    def test_prints_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Prints help text with command list."""
        from aipass.drone.apps.modules.registry import print_help

        print_help()
        captured = capsys.readouterr()
        assert "load" in captured.out
        assert "branches" in captured.out
        assert "lookup" in captured.out


# ===========================================================================
# handle_command — introspection and help
# ===========================================================================


class TestHandleCommandIntrospection:
    """handle_command() introspection and help paths."""

    def test_no_command_no_args_introspection(self) -> None:
        """No command + no args triggers introspection."""
        from aipass.drone.apps.modules.registry import handle_command

        with patch(f"{_REG}.print_introspection") as mock_intro:
            result = handle_command()
        assert result is True
        mock_intro.assert_called_once()

    def test_help_flag_command(self) -> None:
        """--help as command triggers print_help."""
        from aipass.drone.apps.modules.registry import handle_command

        with patch(f"{_REG}.print_help") as mock_help:
            result = handle_command("--help")
        assert result is True
        mock_help.assert_called_once()

    def test_h_flag_command(self) -> None:
        """-h as command triggers print_help."""
        from aipass.drone.apps.modules.registry import handle_command

        with patch(f"{_REG}.print_help") as mock_help:
            result = handle_command("-h")
        assert result is True
        mock_help.assert_called_once()

    def test_help_in_args(self) -> None:
        """--help in args triggers print_help."""
        from aipass.drone.apps.modules.registry import handle_command

        with patch(f"{_REG}.print_help") as mock_help:
            result = handle_command("load", ["--help"])
        assert result is True
        mock_help.assert_called_once()


# ===========================================================================
# handle_command — load
# ===========================================================================


class TestHandleCommandLoad:
    """handle_command('load') path."""

    def test_load_success(self) -> None:
        """load returns True and calls load_registry."""
        from aipass.drone.apps.modules.registry import handle_command

        mock_registry = {"branches": {"drone": {}, "seedgo": {}}}
        with patch(f"{_REG}.load_registry", return_value=mock_registry):
            result = handle_command("load", [])
        assert result is True

    def test_load_empty_registry(self) -> None:
        """load with empty registry still returns True."""
        from aipass.drone.apps.modules.registry import handle_command

        with patch(f"{_REG}.load_registry", return_value={}):
            result = handle_command("load", [])
        assert result is True


# ===========================================================================
# handle_command — branches
# ===========================================================================


class TestHandleCommandBranches:
    """handle_command('branches') path."""

    def test_branches_no_filter(self) -> None:
        """branches with no args lists all branches."""
        from aipass.drone.apps.modules.registry import handle_command

        mock_branches = [{"name": "drone"}, {"name": "seedgo"}]
        with patch(f"{_REG}.get_all_branches", return_value=mock_branches) as mock_gab:
            result = handle_command("branches", [])
        assert result is True
        mock_gab.assert_called_once_with(branch_type=None)

    def test_branches_with_type_filter(self) -> None:
        """branches with type arg filters by type."""
        from aipass.drone.apps.modules.registry import handle_command

        with patch(f"{_REG}.get_all_branches", return_value=[]) as mock_gab:
            result = handle_command("branches", ["library"])
        assert result is True
        mock_gab.assert_called_once_with(branch_type="library")


# ===========================================================================
# handle_command — lookup
# ===========================================================================


class TestHandleCommandLookup:
    """handle_command('lookup') path."""

    def test_lookup_no_args(self) -> None:
        """lookup with no args returns False."""
        from aipass.drone.apps.modules.registry import handle_command

        result = handle_command("lookup", [])
        assert result is False

    def test_lookup_found(self) -> None:
        """lookup with existing branch returns True."""
        from aipass.drone.apps.modules.registry import handle_command

        mock_branch = {"name": "drone", "profile": "library"}
        with patch(f"{_REG}.get_branch_by_name", return_value=mock_branch):
            result = handle_command("lookup", ["drone"])
        assert result is True

    def test_lookup_not_found(self) -> None:
        """lookup with missing branch returns False."""
        from aipass.drone.apps.modules.registry import handle_command

        with patch(f"{_REG}.get_branch_by_name", return_value=None):
            result = handle_command("lookup", ["ghost"])
        assert result is False


# ===========================================================================
# handle_command — unknown
# ===========================================================================


class TestHandleCommandUnknown:
    """handle_command() unknown command path."""

    def test_unknown_command(self) -> None:
        """Unknown command returns False."""
        from aipass.drone.apps.modules.registry import handle_command

        result = handle_command("nonexistent", ["arg"])
        assert result is False

    def test_none_command_with_args(self) -> None:
        """None command with args (no --help) falls through to unknown."""
        from aipass.drone.apps.modules.registry import handle_command

        result = handle_command(None, ["some_arg"])
        assert result is False
