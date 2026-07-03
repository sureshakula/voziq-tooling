# =================== AIPass ====================
# Name: test_timer_install.py
# Description: Tests for the timer_install module (systemd user timer installer)
# Version: 1.0.0
# Created: 2026-06-25
# Modified: 2026-06-25
# =============================================

"""Tests for the timer_install module (systemd user timer installer)."""

import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path

from aipass.daemon.apps.modules.timer_install import (
    handle_command,
    HANDLED_COMMANDS,
    _run_systemctl,
    _install,
    _uninstall,
)


class TestHandleCommand:
    """Tests for command routing."""

    def test_handles_install_timer(self):
        """Verify install-timer is in handled commands."""
        assert "install-timer" in HANDLED_COMMANDS

    def test_handles_uninstall_timer(self):
        """Verify uninstall-timer is in handled commands."""
        assert "uninstall-timer" in HANDLED_COMMANDS

    def test_rejects_unknown(self):
        """Unknown commands return False."""
        assert handle_command("unknown", []) is False

    def test_help_flag(self, capsys):
        """Help flag prints usage and returns True."""
        result = handle_command("install-timer", ["--help"])
        assert result is True


class TestRunSystemctl:
    """Tests for the systemctl wrapper."""

    @patch("subprocess.run")
    def test_success(self, mock_run):
        """Successful systemctl returns True."""
        mock_run.return_value = MagicMock(returncode=0)
        assert _run_systemctl("status", "daemon-tick.timer") is True

    @patch("subprocess.run")
    def test_failure_returncode(self, mock_run):
        """Non-zero returncode returns False."""
        mock_run.return_value = MagicMock(returncode=1, stderr="unit not found")
        assert _run_systemctl("start", "daemon-tick.timer") is False

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_systemctl_not_found(self, mock_run):
        """Missing systemctl returns False."""
        assert _run_systemctl("status", "daemon-tick.timer") is False

    @patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="systemctl", timeout=15),
    )
    def test_timeout(self, mock_run):
        """Timed-out systemctl returns False."""
        assert _run_systemctl("status", "daemon-tick.timer") is False


class TestInstall:
    """Tests for the install flow."""

    def test_install_missing_unit_file(self):
        """Returns 1 when unit files are missing."""
        with patch(
            "aipass.daemon.apps.modules.timer_install._DAEMON_ROOT",
            Path("/nonexistent"),
        ):
            result = _install()
            assert result == 1

    @patch("aipass.daemon.apps.modules.timer_install._run_systemctl", return_value=True)
    @patch("shutil.copy2")
    def test_install_success(self, mock_copy, mock_systemctl, tmp_path):
        """Successful install copies files and calls systemctl 3 times."""
        service = tmp_path / "daemon-tick.service"
        timer = tmp_path / "daemon-tick.timer"
        service.write_text("[Unit]\n")
        timer.write_text("[Unit]\n")

        install_dir = tmp_path / "systemd"
        install_dir.mkdir()

        with (
            patch("aipass.daemon.apps.modules.timer_install._DAEMON_ROOT", tmp_path),
            patch("aipass.daemon.apps.modules.timer_install._UNIT_DIR", install_dir),
        ):
            result = _install()
            assert result == 0
            assert mock_systemctl.call_count == 3

    @patch("aipass.daemon.apps.modules.timer_install._run_systemctl")
    @patch("shutil.copy2")
    def test_install_systemctl_fails(self, mock_copy, mock_systemctl, tmp_path):
        """Returns 1 when systemctl fails."""
        service = tmp_path / "daemon-tick.service"
        timer = tmp_path / "daemon-tick.timer"
        service.write_text("[Unit]\n")
        timer.write_text("[Unit]\n")

        install_dir = tmp_path / "systemd"
        install_dir.mkdir()

        mock_systemctl.return_value = False

        with (
            patch("aipass.daemon.apps.modules.timer_install._DAEMON_ROOT", tmp_path),
            patch("aipass.daemon.apps.modules.timer_install._UNIT_DIR", install_dir),
        ):
            result = _install()
            assert result == 1


class TestUninstall:
    """Tests for the uninstall flow."""

    @patch("aipass.daemon.apps.modules.timer_install._run_systemctl", return_value=True)
    def test_uninstall_files_not_present(self, mock_systemctl, tmp_path):
        """Returns 0 even when unit files are already absent."""
        with patch("aipass.daemon.apps.modules.timer_install._UNIT_DIR", tmp_path):
            result = _uninstall()
            assert result == 0

    @patch("aipass.daemon.apps.modules.timer_install._run_systemctl", return_value=True)
    def test_uninstall_removes_files(self, mock_systemctl, tmp_path):
        """Removes unit files from the target directory."""
        service = tmp_path / "daemon-tick.service"
        timer = tmp_path / "daemon-tick.timer"
        service.write_text("[Unit]\n")
        timer.write_text("[Unit]\n")

        with patch("aipass.daemon.apps.modules.timer_install._UNIT_DIR", tmp_path):
            result = _uninstall()
            assert result == 0
            assert not service.exists()
            assert not timer.exists()
