# =================== AIPass ====================
# Name: test_feedback.py
# Description: Tests for aipass feedback — toggle alias for @hooks feedback pulse
# Version: 1.0.0
# Created: 2026-07-18
# Modified: 2026-07-18
# =============================================

"""Tests for the aipass feedback module."""

from unittest.mock import MagicMock, patch

from aipass.aipass.apps.modules.feedback import handle_command, print_help, print_introspection

_MOD = "aipass.aipass.apps.modules.feedback"


class TestHandleCommand:
    """Command routing for aipass feedback."""

    def test_ignores_other_commands(self) -> None:
        """A non-feedback command is not handled."""
        assert handle_command("doctor", []) is False

    def test_help(self) -> None:
        """--help is handled."""
        assert handle_command("feedback", ["--help"]) is True

    def test_info(self) -> None:
        """--info is handled."""
        assert handle_command("feedback", ["--info"]) is True

    def test_unknown_arg_shows_error(self) -> None:
        """An unknown argument shows an error and help."""
        with patch(f"{_MOD}.error") as mock_err:
            assert handle_command("feedback", ["banana"]) is True
        mock_err.assert_called_once()

    def test_on_delegates_to_hooks(self) -> None:
        """'on' delegates to drone @hooks feedback on."""
        with patch(f"{_MOD}.subprocess.run", return_value=MagicMock(returncode=0)) as run:
            handle_command("feedback", ["on"])
        cmd = run.call_args[0][0]
        assert cmd == ["drone", "@hooks", "feedback", "on"]

    def test_off_delegates_to_hooks(self) -> None:
        """'off' delegates to drone @hooks feedback off."""
        with patch(f"{_MOD}.subprocess.run", return_value=MagicMock(returncode=0)) as run:
            handle_command("feedback", ["off"])
        cmd = run.call_args[0][0]
        assert cmd == ["drone", "@hooks", "feedback", "off"]

    def test_no_args_shows_introspection(self) -> None:
        """No args shows module introspection."""
        with patch(f"{_MOD}.subprocess.run") as run:
            assert handle_command("feedback", []) is True
        run.assert_not_called()

    def test_drone_not_found(self) -> None:
        """Missing drone warns cleanly, no crash."""
        with (
            patch(f"{_MOD}.subprocess.run", side_effect=FileNotFoundError("drone")),
            patch(f"{_MOD}.warning") as warn,
        ):
            handle_command("feedback", ["on"])
        warn.assert_called_once()


class TestSmoke:
    """Help/introspection render without error."""

    def test_print_help_runs(self) -> None:
        print_help()

    def test_print_introspection_runs(self) -> None:
        print_introspection()
