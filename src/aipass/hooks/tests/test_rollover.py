# =================== AIPass ====================
# Name: test_rollover.py
# Version: 2.0.0
# Description: Tests for rollover lifecycle handler
# Branch: hooks
# Created: 2026-05-22
# Modified: 2026-06-19
# =============================================

"""Tests for handlers/lifecycle/rollover.py."""

from unittest.mock import patch, MagicMock
import subprocess


MOD = "aipass.hooks.apps.handlers.lifecycle.rollover"

CHECK_OVERDUE_OUTPUT = (
    "Found 3 files ready for rollover:\n"
    "  * HOOKS.local (15/15 sessions)\n"
    "  * aipass.local (15/15 key_learnings)\n"
    "  * devpulse.local (15/15 key_learnings)\n"
)

CHECK_CLEAN_OUTPUT = "No files need rollover.\n"


def _mock_run(stdout="", returncode=0):
    m = MagicMock()
    m.stdout = stdout
    m.stderr = ""
    m.returncode = returncode
    return m


class TestRolloverHandler:
    def test_no_repo_root_returns_empty(self):
        from aipass.hooks.apps.handlers.lifecycle.rollover import handle

        with patch(f"{MOD}._find_repo_root", return_value=None):
            result = handle({})

        assert result["exit_code"] == 0
        assert result["stdout"] == ""
        assert "sound" not in result

    def test_no_overdue_returns_empty(self):
        from aipass.hooks.apps.handlers.lifecycle.rollover import handle

        with patch(f"{MOD}._find_repo_root", return_value=MagicMock()):
            with patch(f"{MOD}._run_check", return_value=(False, CHECK_CLEAN_OUTPUT)):
                result = handle({})

        assert result["exit_code"] == 0
        assert result["stdout"] == ""
        assert "sound" not in result

    def test_overdue_triggers_rollover(self):
        from aipass.hooks.apps.handlers.lifecycle.rollover import handle

        with patch(f"{MOD}._find_repo_root", return_value=MagicMock()):
            with patch(f"{MOD}._run_check", return_value=(True, CHECK_OVERDUE_OUTPUT)):
                with patch(f"{MOD}._run_rollover", return_value=(True, "ok")):
                    result = handle({})

        assert result["exit_code"] == 0
        assert result["sound"] == "pre compact rollover"

    def test_overdue_rollover_failure_still_returns_sound(self):
        from aipass.hooks.apps.handlers.lifecycle.rollover import handle

        with patch(f"{MOD}._find_repo_root", return_value=MagicMock()):
            with patch(f"{MOD}._run_check", return_value=(True, CHECK_OVERDUE_OUTPUT)):
                with patch(f"{MOD}._run_rollover", return_value=(False, "error")):
                    result = handle({})

        assert result["exit_code"] == 0
        assert result["sound"] == "pre compact rollover"

    def test_run_check_parses_overdue(self):
        from aipass.hooks.apps.handlers.lifecycle.rollover import _run_check

        mock_result = _mock_run(stdout=CHECK_OVERDUE_OUTPUT)
        with patch("subprocess.run", return_value=mock_result):
            has_overdue, summary = _run_check(MagicMock())

        assert has_overdue
        assert "ready for rollover" in summary.lower()

    def test_run_check_parses_clean(self):
        from aipass.hooks.apps.handlers.lifecycle.rollover import _run_check

        mock_result = _mock_run(stdout=CHECK_CLEAN_OUTPUT)
        with patch("subprocess.run", return_value=mock_result):
            has_overdue, _ = _run_check(MagicMock())

        assert not has_overdue

    def test_run_check_timeout_returns_false(self):
        from aipass.hooks.apps.handlers.lifecycle.rollover import _run_check

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)):
            has_overdue, _ = _run_check(MagicMock())

        assert not has_overdue

    def test_run_rollover_success(self):
        from aipass.hooks.apps.handlers.lifecycle.rollover import _run_rollover

        mock_result = _mock_run(stdout="done", returncode=0)
        with patch("subprocess.run", return_value=mock_result):
            success, _ = _run_rollover(MagicMock())

        assert success

    def test_run_rollover_failure(self):
        from aipass.hooks.apps.handlers.lifecycle.rollover import _run_rollover

        mock_result = _mock_run(stdout="error", returncode=1)
        with patch("subprocess.run", return_value=mock_result):
            success, _ = _run_rollover(MagicMock())

        assert not success

    def test_run_rollover_timeout(self):
        from aipass.hooks.apps.handlers.lifecycle.rollover import _run_rollover

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 110)):
            success, msg = _run_rollover(MagicMock())

        assert not success
        assert "timed out" in msg


class TestFindRepoRootFailLoud:
    """_find_repo_root logs error (not silent skip) when no AIPASS_REGISTRY.json found."""

    def test_bad_root_logs_error(self, tmp_path, caplog):
        """No AIPASS_REGISTRY.json anywhere -> logger.error with AIPASS_HOME + cwd."""
        import logging
        from aipass.hooks.apps.handlers.lifecycle.rollover import _find_repo_root

        with caplog.at_level(logging.ERROR):
            with patch.dict("os.environ", {"AIPASS_HOME": ""}):
                with patch(f"{MOD}.Path") as mock_path_cls:
                    mock_path_cls.cwd.return_value = tmp_path
                    result = _find_repo_root()

        assert result is None
        assert "_find_repo_root failed" in caplog.text
        assert "AIPASS_REGISTRY.json" in caplog.text

    def test_bad_aipass_home_falls_through_to_cwd(self, tmp_path, caplog):
        """AIPASS_HOME set but no registry there -> falls through, still logs error if cwd also fails."""
        import logging
        from aipass.hooks.apps.handlers.lifecycle.rollover import _find_repo_root

        bad_home = str(tmp_path / "nonexistent")

        with caplog.at_level(logging.ERROR):
            with patch.dict("os.environ", {"AIPASS_HOME": bad_home}):
                with patch(f"{MOD}.Path") as mock_path_cls:
                    mock_path_cls.return_value = tmp_path / "nonexistent"
                    mock_path_cls.cwd.return_value = tmp_path
                    result = _find_repo_root()

        assert result is None
        assert "_find_repo_root failed" in caplog.text
        assert repr(bad_home) in caplog.text
