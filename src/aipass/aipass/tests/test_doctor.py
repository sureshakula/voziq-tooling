# =================== AIPass ====================
# Name: test_doctor.py
# Description: Tests for aipass doctor Phase 1
# Version: 1.0.0
# Created: 2026-04-16
# Modified: 2026-04-16
# =============================================

"""Tests for aipass doctor command — Phase 1 (FPLAN-0188)."""

from unittest.mock import MagicMock, patch

import pytest

from aipass.aipass.apps.handlers.system_detect.system_detector import (
    detect_cpu,
    detect_git,
    detect_os,
    detect_python,
    detect_ram,
    detect_shell,
    detect_docker,
    detect_tmux,
    detect_wt,
)
from aipass.aipass.apps.handlers.ui.progress import (
    GLYPH_FAIL,
    GLYPH_PASS,
    GLYPH_WARN,
    format_check,
    make_doctor_progress,
)
from aipass.aipass.apps.modules.doctor import handle_command, run_doctor


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def clean_env(monkeypatch):
    """Remove AIPASS_HOME from environment."""
    monkeypatch.delenv("AIPASS_HOME", raising=False)


# =============================================================================
# TestDetectPython
# =============================================================================


class TestDetectPython:
    def test_current_python_ok(self) -> None:
        """Running Python is >=3.9 and reports ok=True."""
        result = detect_python()
        import sys

        assert result["major"] == sys.version_info.major
        assert result["minor"] == sys.version_info.minor
        assert "." in result["version"]
        # Running tests on 3.9+ so ok must be True
        assert result["ok"] is True
        assert result["warning"] is False

    def test_python_38_is_warning(self) -> None:
        """Python 3.8 is marked as warning, not ok."""
        with patch("aipass.aipass.apps.handlers.system_detect.system_detector.sys") as mock_sys:
            mock_sys.version_info = MagicMock(major=3, minor=8, micro=0)
            result = detect_python()
        assert result["ok"] is False
        assert result["warning"] is True

    def test_python_37_is_fail(self) -> None:
        """Python 3.7 is not ok and not warning."""
        with patch("aipass.aipass.apps.handlers.system_detect.system_detector.sys") as mock_sys:
            mock_sys.version_info = MagicMock(major=3, minor=7, micro=0)
            result = detect_python()
        assert result["ok"] is False
        assert result["warning"] is False

    def test_version_string_format(self) -> None:
        """Version string contains two dots (major.minor.micro)."""
        result = detect_python()
        assert result["version"].count(".") == 2


# =============================================================================
# TestDetectGit
# =============================================================================


class TestDetectGit:
    def test_git_found(self) -> None:
        """When git is on PATH, found=True and version is non-empty."""
        with patch(
            "aipass.aipass.apps.handlers.system_detect.system_detector.shutil.which", return_value="/usr/bin/git"
        ):
            with patch("aipass.aipass.apps.handlers.system_detect.system_detector.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout="git version 2.43.0\n", returncode=0)
                result = detect_git()
        assert result["found"] is True
        assert result["version"] == "2.43.0"

    def test_git_not_found(self) -> None:
        """When git is not on PATH, found=False."""
        with patch("aipass.aipass.apps.handlers.system_detect.system_detector.shutil.which", return_value=None):
            result = detect_git()
        assert result["found"] is False
        assert result["version"] == ""

    def test_git_version_parse_failure(self) -> None:
        """If git --version fails, found=True but version is raw output."""
        with patch(
            "aipass.aipass.apps.handlers.system_detect.system_detector.shutil.which", return_value="/usr/bin/git"
        ):
            with patch("aipass.aipass.apps.handlers.system_detect.system_detector.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout="weird\n", returncode=0)
                result = detect_git()
        assert result["found"] is True


# =============================================================================
# TestDetectRam
# =============================================================================


class TestDetectRam:
    def test_high_ram_ok(self) -> None:
        """16 GB RAM reports ok=True, warning=False."""
        with patch("aipass.aipass.apps.handlers.system_detect.system_detector._total_ram_gb", return_value=16.0):
            result = detect_ram()
        assert result["ok"] is True
        assert result["warning"] is False
        assert result["total_gb"] == 16.0

    def test_low_ram_warning(self) -> None:
        """3 GB RAM reports ok=False, warning=True."""
        with patch("aipass.aipass.apps.handlers.system_detect.system_detector._total_ram_gb", return_value=3.0):
            result = detect_ram()
        assert result["ok"] is False
        assert result["warning"] is True

    def test_very_low_ram_fail(self) -> None:
        """1 GB RAM reports both ok=False and warning=False."""
        with patch("aipass.aipass.apps.handlers.system_detect.system_detector._total_ram_gb", return_value=1.0):
            result = detect_ram()
        assert result["ok"] is False
        assert result["warning"] is False

    def test_exactly_four_gb_ok(self) -> None:
        """Exactly 4.0 GB is ok (boundary)."""
        with patch("aipass.aipass.apps.handlers.system_detect.system_detector._total_ram_gb", return_value=4.0):
            result = detect_ram()
        assert result["ok"] is True


# =============================================================================
# TestDetectOS
# =============================================================================


class TestDetectOS:
    def test_returns_os_keys(self) -> None:
        """Result has os_name, release, machine keys."""
        result = detect_os()
        assert "os_name" in result
        assert "release" in result
        assert "machine" in result

    def test_os_name_non_empty(self) -> None:
        """os_name is always non-empty."""
        result = detect_os()
        assert result["os_name"] != ""


# =============================================================================
# TestDetectShell
# =============================================================================


class TestDetectShell:
    def test_shell_from_env(self, monkeypatch) -> None:
        """Shell name extracted from SHELL env var."""
        monkeypatch.setenv("SHELL", "/bin/bash")
        result = detect_shell()
        assert result["name"] == "bash"
        assert result["path"] == "/bin/bash"

    def test_shell_missing_env(self, monkeypatch) -> None:
        """Missing SHELL env var returns 'unknown'."""
        monkeypatch.delenv("SHELL", raising=False)
        result = detect_shell()
        assert result["name"] == "unknown"


# =============================================================================
# TestDetectCpu
# =============================================================================


class TestDetectCpu:
    def test_returns_positive_count(self) -> None:
        """CPU count is a positive integer."""
        result = detect_cpu()
        assert isinstance(result["count"], int)
        assert result["count"] >= 1


# =============================================================================
# TestDetectOptionalTools
# =============================================================================


class TestDetectOptionalTools:
    def test_tmux_found(self) -> None:
        """True when tmux binary is on PATH."""
        with patch(
            "aipass.aipass.apps.handlers.system_detect.system_detector.shutil.which", return_value="/usr/bin/tmux"
        ):
            assert detect_tmux() is True

    def test_tmux_not_found(self) -> None:
        """False when tmux is absent from PATH."""
        with patch("aipass.aipass.apps.handlers.system_detect.system_detector.shutil.which", return_value=None):
            assert detect_tmux() is False

    def test_docker_found(self) -> None:
        """True when docker binary is on PATH."""
        with patch(
            "aipass.aipass.apps.handlers.system_detect.system_detector.shutil.which", return_value="/usr/bin/docker"
        ):
            assert detect_docker() is True

    def test_wt_not_on_linux(self) -> None:
        """False when wt.exe (Windows Terminal) is absent from PATH."""
        with patch("aipass.aipass.apps.handlers.system_detect.system_detector.shutil.which", return_value=None):
            assert detect_wt() is False


# =============================================================================
# TestProgressHelpers
# =============================================================================


class TestProgressHelpers:
    def test_glyph_constants(self) -> None:
        """Glyph constants contain Rich markup colour tags."""
        assert "green" in GLYPH_PASS
        assert "yellow" in GLYPH_WARN
        assert "red" in GLYPH_FAIL

    def test_format_check_pass(self) -> None:
        """format_check with GLYPH_PASS includes label."""
        line = format_check("python", GLYPH_PASS, "3.11.5")
        assert "python" in line
        assert "3.11.5" in line

    def test_format_check_with_remediation(self) -> None:
        """Remediation text is included when provided."""
        line = format_check("git", GLYPH_FAIL, "not found", "Install git")
        assert "Install git" in line

    def test_format_check_no_remediation(self) -> None:
        """No remediation means no extra line."""
        line = format_check("shell", GLYPH_PASS, "bash")
        assert "\n" not in line

    def test_make_doctor_progress_returns_progress(self) -> None:
        """make_doctor_progress returns a Rich Progress instance."""
        from rich.progress import Progress

        prog = make_doctor_progress()
        assert isinstance(prog, Progress)


# =============================================================================
# TestDoctorHandleCommand
# =============================================================================


class TestDoctorHandleCommand:
    def test_wrong_command_returns_false(self) -> None:
        """Non-doctor commands are not handled."""
        assert handle_command("help", []) is False
        assert handle_command("init", ["--verbose"]) is False

    def test_no_args_calls_introspection(self, capsys) -> None:
        """No args triggers print_introspection (returns True)."""
        with patch("aipass.aipass.apps.modules.doctor.print_introspection") as mock_intro:
            result = handle_command("doctor", [])
        assert result is True
        mock_intro.assert_called_once()

    def test_help_flag_calls_print_help(self) -> None:
        """--help flag triggers print_help (returns True)."""
        with patch("aipass.aipass.apps.modules.doctor.print_help") as mock_help:
            result = handle_command("doctor", ["--help"])
        assert result is True
        mock_help.assert_called_once()

    def test_h_flag_calls_print_help(self) -> None:
        """-h flag triggers print_help."""
        with patch("aipass.aipass.apps.modules.doctor.print_help") as mock_help:
            result = handle_command("doctor", ["-h"])
        assert result is True
        mock_help.assert_called_once()

    def test_doctor_no_errors_returns_true(self) -> None:
        """When run_doctor returns 0 errors, handle_command returns True."""
        with patch("aipass.aipass.apps.modules.doctor.run_doctor", return_value=0):
            with patch("aipass.aipass.apps.modules.doctor.json_handler"):
                result = handle_command("doctor", ["--check"])
        assert result is True

    def test_doctor_with_errors_raises_system_exit(self) -> None:
        """When run_doctor returns errors, SystemExit(1) is raised."""
        with patch("aipass.aipass.apps.modules.doctor.run_doctor", return_value=2):
            with patch("aipass.aipass.apps.modules.doctor.json_handler"):
                with pytest.raises(SystemExit) as exc_info:
                    handle_command("doctor", ["--check"])
        assert exc_info.value.code == 1

    def test_verbose_flag_passed_to_run_doctor(self) -> None:
        """--verbose flag is forwarded to run_doctor."""
        with patch("aipass.aipass.apps.modules.doctor.run_doctor", return_value=0) as mock_run:
            with patch("aipass.aipass.apps.modules.doctor.json_handler"):
                handle_command("doctor", ["--verbose"])
        mock_run.assert_called_once_with(verbose=True)


# =============================================================================
# TestRunDoctor
# =============================================================================


class TestRunDoctor:
    def _mock_all_checks(self, mock_system, mock_identity, mock_services, mock_community):
        """Set all group mocks to return empty lists (no errors)."""
        mock_system.return_value = []
        mock_identity.return_value = []
        mock_services.return_value = []
        mock_community.return_value = []

    def test_run_doctor_returns_int(self) -> None:
        """run_doctor returns an integer error count."""
        with patch("aipass.aipass.apps.modules.doctor._check_system", return_value=[]):
            with patch("aipass.aipass.apps.modules.doctor._check_identity", return_value=[]):
                with patch("aipass.aipass.apps.modules.doctor._check_services", return_value=[]):
                    with patch("aipass.aipass.apps.modules.doctor._check_community", return_value=[]):
                        result = run_doctor()
        assert isinstance(result, int)
        assert result == 0

    def test_run_doctor_counts_errors(self) -> None:
        """Error glyphs in results increment error count."""
        from aipass.aipass.apps.modules.doctor import CheckResult

        fail_check = CheckResult("test", GLYPH_FAIL, "bad", "fix it")
        with patch("aipass.aipass.apps.modules.doctor._check_system", return_value=[fail_check]):
            with patch("aipass.aipass.apps.modules.doctor._check_identity", return_value=[]):
                with patch("aipass.aipass.apps.modules.doctor._check_services", return_value=[]):
                    with patch("aipass.aipass.apps.modules.doctor._check_community", return_value=[]):
                        result = run_doctor()
        assert result == 1

    def test_run_doctor_counts_only_errors_not_warnings(self) -> None:
        """Warning glyphs do not increment error count."""
        from aipass.aipass.apps.modules.doctor import CheckResult

        warn_check = CheckResult("test", GLYPH_WARN, "minor", "")
        with patch("aipass.aipass.apps.modules.doctor._check_system", return_value=[warn_check]):
            with patch("aipass.aipass.apps.modules.doctor._check_identity", return_value=[]):
                with patch("aipass.aipass.apps.modules.doctor._check_services", return_value=[]):
                    with patch("aipass.aipass.apps.modules.doctor._check_community", return_value=[]):
                        result = run_doctor()
        assert result == 0
