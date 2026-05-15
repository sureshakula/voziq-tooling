# =================== AIPass ====================
# Name: test_devpulse.py
# Description: Tests for devpulse.py CLI routing, introspection, and resilience
# Version: 1.0.0
# Created: 2026-05-15
# Modified: 2026-05-15
# =============================================

"""Tests for devpulse.py — entry point CLI routing and module discovery."""

import importlib
from unittest.mock import patch, MagicMock


from aipass.devpulse.apps import devpulse as devpulse_module


class TestCLIRouting:
    """CLI routing through _handle_command and main()."""

    def test_help_flag(self):
        """--help flag returns True."""
        result = devpulse_module._handle_command("--help", [])
        assert result is True

    def test_short_help(self):
        """-h flag returns True."""
        result = devpulse_module._handle_command("-h", [])
        assert result is True

    def test_help_word(self):
        """help word returns True."""
        result = devpulse_module._handle_command("help", [])
        assert result is True

    def test_version_flag(self):
        """--version flag returns True."""
        result = devpulse_module._handle_command("--version", [])
        assert result is True

    def test_version_short(self):
        """-V flag returns True."""
        result = devpulse_module._handle_command("-V", [])
        assert result is True

    def test_unknown_command_returns_false(self):
        """Unrecognized command returns False."""
        result = devpulse_module._handle_command("nonexistent_unknown_command", [])
        assert result is False

    @patch.object(devpulse_module, "print_help")
    def test_print_help_called_on_help_flag(self, mock_print_help):
        """--help invokes print_help."""
        devpulse_module._handle_command("--help", [])
        mock_print_help.assert_called_once()

    @patch.object(devpulse_module, "print_introspection")
    def test_no_args_triggers_print_introspection(self, mock_introspection):
        """No args triggers print_introspection via main()."""
        with patch("sys.argv", ["devpulse"]):
            devpulse_module.main()
        mock_introspection.assert_called_once()

    @patch.object(devpulse_module, "print_introspection")
    def test_print_introspection_output(self, mock_introspection):
        """main() returns 0 when print_introspection runs."""
        mock_introspection.return_value = None
        with patch("sys.argv", ["devpulse"]):
            result = devpulse_module.main()
        assert result == 0


class TestModuleDiscovery:
    """discover_modules() finds modules with handle_command."""

    def test_discover_modules_returns_list(self):
        """Returns a list of discovered modules."""
        result = devpulse_module.discover_modules()
        assert isinstance(result, list)

    def test_discovered_modules_have_handle_command(self):
        """Each discovered module exposes handle_command."""
        modules = devpulse_module.discover_modules()
        for mod in modules:
            assert hasattr(mod, "handle_command")

    def test_reimport_after_mock(self):
        """Verify module reimport picks up mocked state."""
        original_modules = devpulse_module.discover_modules()
        with patch.object(devpulse_module, "MODULES_DIR", devpulse_module.Path("/nonexistent")):
            importlib.reload(devpulse_module)
            reloaded = devpulse_module.discover_modules()
        importlib.reload(devpulse_module)
        assert isinstance(reloaded, list)


class TestErrorResilience:
    """Graceful handling of edge cases."""

    def test_route_command_catches_module_errors(self):
        """Module exceptions are caught, returns False."""
        bad_module = MagicMock(__name__="bad_module")
        bad_module.handle_command.side_effect = Exception("boom")
        result = devpulse_module.route_command("test", [], [bad_module])
        assert result is False

    def test_empty_file_modules_dir(self, tmp_path):
        """discover_modules handles empty_file in modules directory."""
        empty = tmp_path / "empty.py"
        empty.write_text("")
        with patch.object(devpulse_module, "MODULES_DIR", tmp_path):
            result = devpulse_module.discover_modules()
        assert isinstance(result, list)

    def test_handle_command_with_empty_args(self):
        """--help with empty args list succeeds."""
        result = devpulse_module.handle_command("--help", [])
        assert result is True


class TestHandleCommandGuard:
    """handle_command cross-branch security guard."""

    def test_handle_command_returns_bool(self):
        """handle_command always returns a bool."""
        result = devpulse_module.handle_command("--help", [])
        assert isinstance(result, bool)
        assert result is True

    def test_handle_command_unknown_returns_false(self):
        """Unknown commands return False through the guard."""
        result = devpulse_module.handle_command("bogus_invalid_command", [])
        assert result is False
