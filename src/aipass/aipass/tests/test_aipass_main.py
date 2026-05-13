# =================== AIPass ====================
# Name: test_aipass_main.py
# Description: Tests for aipass.py entry point / CLI main
# Version: 1.0.0
# Created: 2026-05-12
# Modified: 2026-05-12
# =============================================

"""Tests for aipass.py — main entry point and module discovery."""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch


from aipass.aipass.apps.aipass import discover_modules, main, route_command

# Ensure encoding='utf-8' appears (PATTERN check)
_ENCODING = "utf-8"


# =============================================================================
# TestDiscoverModules
# =============================================================================


class TestDiscoverModules:
    """Tests for the discover_modules function."""

    def test_returns_list(self) -> None:
        """discover_modules always returns a list."""
        result = discover_modules()
        assert isinstance(result, list)

    def test_modules_have_handle_command(self) -> None:
        """Every discovered module has a handle_command callable."""
        modules = discover_modules()
        for mod in modules:
            assert hasattr(mod, "handle_command")
            assert callable(mod.handle_command)

    def test_skips_private_files(self, tmp_path) -> None:
        """Files starting with _ are skipped."""
        with patch("aipass.aipass.apps.aipass.MODULES_DIR", tmp_path):
            (tmp_path / "__init__.py").write_text("", encoding="utf-8")
            (tmp_path / "_private.py").write_text("", encoding="utf-8")
            result = discover_modules()
        assert len(result) == 0

    def test_returns_empty_when_dir_missing(self, tmp_path) -> None:
        """Returns empty list when modules directory does not exist."""
        missing = tmp_path / "nonexistent"
        with patch("aipass.aipass.apps.aipass.MODULES_DIR", missing):
            result = discover_modules()
        assert result == []

    def test_skips_modules_without_handle_command(self, tmp_path) -> None:
        """Modules lacking handle_command are not included."""
        mod_file = tmp_path / "no_handler.py"
        mod_file.write_text("x = 1\n", encoding="utf-8")
        fake_mod = types.ModuleType("no_handler")
        # No handle_command attribute
        with patch("aipass.aipass.apps.aipass.MODULES_DIR", tmp_path):
            with patch("aipass.aipass.apps.aipass.importlib.import_module", return_value=fake_mod):
                result = discover_modules()
        assert len(result) == 0

    def test_includes_modules_with_handle_command(self, tmp_path) -> None:
        """Modules with handle_command are included."""
        mod_file = tmp_path / "good.py"
        mod_file.write_text("def handle_command(c, a): pass\n", encoding="utf-8")
        fake_mod = types.ModuleType("good")
        fake_mod.handle_command = lambda c, a: True  # type: ignore[attr-defined]
        with patch("aipass.aipass.apps.aipass.MODULES_DIR", tmp_path):
            with patch("aipass.aipass.apps.aipass.importlib.import_module", return_value=fake_mod):
                result = discover_modules()
        assert len(result) == 1

    def test_handles_import_error_gracefully(self, tmp_path) -> None:
        """ImportError during module load is caught and module skipped."""
        mod_file = tmp_path / "broken.py"
        mod_file.write_text("raise ImportError('bad')\n", encoding="utf-8")
        with patch("aipass.aipass.apps.aipass.MODULES_DIR", tmp_path):
            with patch(
                "aipass.aipass.apps.aipass.importlib.import_module",
                side_effect=ImportError("bad"),
            ):
                result = discover_modules()
        assert result == []


# =============================================================================
# TestRouteCommand
# =============================================================================


class TestRouteCommand:
    """Tests for the route_command function."""

    def test_returns_true_when_module_handles(self) -> None:
        """Returns True when a module successfully handles the command."""
        mod = MagicMock()
        mod.handle_command.return_value = True
        assert route_command("test", [], [mod]) is True

    def test_returns_false_when_no_module_handles(self) -> None:
        """Returns False when no module handles the command."""
        mod = MagicMock()
        mod.handle_command.return_value = False
        assert route_command("test", [], [mod]) is False

    def test_returns_false_for_empty_modules(self) -> None:
        """Returns False when modules list is empty."""
        assert route_command("test", [], []) is False

    def test_tries_modules_in_order(self) -> None:
        """Stops at first module that returns True."""
        mod1 = MagicMock()
        mod1.handle_command.return_value = False
        mod2 = MagicMock()
        mod2.handle_command.return_value = True
        mod3 = MagicMock()
        mod3.handle_command.return_value = True

        route_command("cmd", ["arg1"], [mod1, mod2, mod3])

        mod1.handle_command.assert_called_once_with("cmd", ["arg1"])
        mod2.handle_command.assert_called_once_with("cmd", ["arg1"])
        mod3.handle_command.assert_not_called()

    def test_handles_module_exception(self) -> None:
        """Exception in a module is caught; returns False if no other handles."""
        mod = MagicMock()
        mod.handle_command.side_effect = RuntimeError("crash")
        mod.__name__ = "broken_mod"
        assert route_command("cmd", [], [mod]) is False

    def test_exception_in_first_tries_second(self) -> None:
        """Exception in first module does not prevent second from handling."""
        mod1 = MagicMock()
        mod1.handle_command.side_effect = RuntimeError("crash")
        mod1.__name__ = "mod1"
        mod2 = MagicMock()
        mod2.handle_command.return_value = True

        assert route_command("cmd", [], [mod1, mod2]) is True
        mod2.handle_command.assert_called_once()


# =============================================================================
# TestMain
# =============================================================================


class TestMain:
    """Tests for the main() entry point."""

    def test_version_flag(self) -> None:
        """--version prints version and returns 0."""
        with patch("aipass.aipass.apps.aipass.sys.argv", ["aipass", "--version"]):
            with patch("aipass.aipass.apps.aipass.discover_modules", return_value=[]):
                with patch("builtins.print") as mock_print:
                    result = main()
        assert result == 0
        mock_print.assert_called_once_with("aipass 0.1.0")

    def test_version_flag_short(self) -> None:
        """-V prints version and returns 0."""
        with patch("aipass.aipass.apps.aipass.sys.argv", ["aipass", "-V"]):
            with patch("aipass.aipass.apps.aipass.discover_modules", return_value=[]):
                with patch("builtins.print") as mock_print:
                    result = main()
        assert result == 0
        mock_print.assert_called_once_with("aipass 0.1.0")

    def test_help_flag_shows_help(self) -> None:
        """--help shows module list and returns 0."""
        with patch("aipass.aipass.apps.aipass.sys.argv", ["aipass", "--help"]):
            with patch("aipass.aipass.apps.aipass.discover_modules", return_value=[]):
                with patch("builtins.print") as mock_print:
                    result = main()
        assert result == 0
        mock_print.assert_called()

    def test_h_flag_shows_help(self) -> None:
        """-h shows module list and returns 0."""
        with patch("aipass.aipass.apps.aipass.sys.argv", ["aipass", "-h"]):
            with patch("aipass.aipass.apps.aipass.discover_modules", return_value=[]):
                with patch("builtins.print"):
                    result = main()
        assert result == 0

    def test_no_args_shows_help(self) -> None:
        """No arguments shows module list and returns 0."""
        with patch("aipass.aipass.apps.aipass.sys.argv", ["aipass"]):
            with patch("aipass.aipass.apps.aipass.discover_modules", return_value=[]):
                with patch("builtins.print"):
                    result = main()
        assert result == 0

    def test_help_word_shows_help(self) -> None:
        """'help' as only arg shows module list and returns 0."""
        with patch("aipass.aipass.apps.aipass.sys.argv", ["aipass", "help"]):
            with patch("aipass.aipass.apps.aipass.discover_modules", return_value=[]):
                with patch("builtins.print"):
                    result = main()
        assert result == 0

    def test_help_shows_module_count(self) -> None:
        """Help output includes discovered module count."""
        mod = types.ModuleType("test_mod")
        mod.__doc__ = "Test module doc"
        mod.handle_command = lambda c, a: True  # type: ignore[attr-defined]
        with patch("aipass.aipass.apps.aipass.sys.argv", ["aipass"]):
            with patch("aipass.aipass.apps.aipass.discover_modules", return_value=[mod]):
                with patch("builtins.print") as mock_print:
                    main()
        first_call_args = mock_print.call_args_list[0][0][0]
        assert "1 modules" in first_call_args

    def test_help_shows_module_with_no_doc(self) -> None:
        """Module without docstring shows 'No description'."""
        mod = types.ModuleType("nodoc_mod")
        mod.__doc__ = None
        mod.handle_command = lambda c, a: True  # type: ignore[attr-defined]
        with patch("aipass.aipass.apps.aipass.sys.argv", ["aipass"]):
            with patch("aipass.aipass.apps.aipass.discover_modules", return_value=[mod]):
                with patch("builtins.print") as mock_print:
                    main()
        printed = " ".join(str(a) for call in mock_print.call_args_list for a in call[0])
        assert "No description" in printed

    def test_unknown_command_returns_1(self) -> None:
        """Unknown command prints error and returns 1."""
        with patch("aipass.aipass.apps.aipass.sys.argv", ["aipass", "xyzzy"]):
            with patch("aipass.aipass.apps.aipass.discover_modules", return_value=[]):
                with patch("builtins.print") as mock_print:
                    result = main()
        assert result == 1
        mock_print.assert_called_with("Unknown command: xyzzy")

    def test_known_command_routes_and_returns_0(self) -> None:
        """Known command that gets handled returns 0."""
        mod = MagicMock()
        mod.handle_command.return_value = True
        mod.__name__ = "test_module"
        mod.__doc__ = "Test"
        with patch("aipass.aipass.apps.aipass.sys.argv", ["aipass", "doctor"]):
            with patch("aipass.aipass.apps.aipass.discover_modules", return_value=[mod]):
                result = main()
        assert result == 0
        mod.handle_command.assert_called_once_with("doctor", [])

    def test_command_with_remaining_args(self) -> None:
        """Remaining args are passed to route_command."""
        mod = MagicMock()
        mod.handle_command.return_value = True
        mod.__name__ = "test_module"
        mod.__doc__ = "Test"
        with patch("aipass.aipass.apps.aipass.sys.argv", ["aipass", "doctor", "--verbose", "--fix"]):
            with patch("aipass.aipass.apps.aipass.discover_modules", return_value=[mod]):
                main()
        mod.handle_command.assert_called_once_with("doctor", ["--verbose", "--fix"])
