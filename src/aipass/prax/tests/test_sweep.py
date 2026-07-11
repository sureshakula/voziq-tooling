# =================== AIPass ====================
# Name: test_sweep.py
# Description: Tests for stale log sweep in log_audit
# Version: 1.0.0
# Created: 2026-07-10
# Modified: 2026-07-10
# =============================================

"""
Tests for sweep_stale_logs — the 30-day stale log cleanup policy.

Verifies: age-based deletion, pattern matching (.log, .jsonl, .1 siblings),
directory scanning across system_logs/ and branch logs/.
All imports go through the module layer (log_audit).
"""

import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock


def _make_old_file(path: Path, age_days: int) -> None:
    """Create a file and backdate its mtime."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stale log content\n")
    old_time = time.time() - (age_days * 86400)
    os.utime(path, (old_time, old_time))


def _get_sweep():
    """Import sweep_stale_logs from the module layer after conftest mocks are active."""
    mod_name = "aipass.prax.apps.modules.log_audit"
    sys.modules.pop(mod_name, None)
    from aipass.prax.apps.modules.log_audit import sweep_stale_logs

    return sweep_stale_logs


def _ensure_watchdog_mock(monkeypatch):
    """Inject a mock for log_watchdog so handle_command('sweep') works."""
    mock_watchdog = MagicMock()
    mock_watchdog.sweep_stale_logs = MagicMock(
        return_value={
            "max_age_days": 30,
            "files_removed": 1,
            "total_reclaimed_kb": 12.5,
            "removed": [
                {"path": "/fake/logs/old.log", "name": "old.log", "age_days": 45.2, "size_kb": 12.5},
            ],
        }
    )
    monkeypatch.setitem(
        sys.modules,
        "aipass.prax.apps.handlers.logging.log_watchdog",
        mock_watchdog,
    )
    return mock_watchdog


class TestSweepIntegration:
    """Integration: sweep across system_logs and branch logs."""

    def test_deletes_old_system_log(self, tmp_path):
        """Verify sweep deletes old files from system_logs/."""
        sweep_stale_logs = _get_sweep()

        sys_logs = tmp_path / "system_logs"
        sys_logs.mkdir()
        _make_old_file(sys_logs / "old_module.log", 45)

        with (
            patch(
                "aipass.prax.apps.handlers.logging.log_watchdog._get_system_logs_dir",
                return_value=sys_logs,
            ),
            patch(
                "aipass.prax.apps.handlers.logging.log_watchdog._get_ecosystem_root",
                return_value=tmp_path / "src" / "aipass",
            ),
        ):
            result = sweep_stale_logs()

        assert result["files_removed"] == 1
        assert not (sys_logs / "old_module.log").exists()

    def test_deletes_old_branch_jsonl(self, tmp_path):
        """Verify sweep deletes old .jsonl files from branch logs/."""
        sweep_stale_logs = _get_sweep()

        eco = tmp_path / "src" / "aipass"
        branch_logs = eco / "testbranch" / "logs"
        branch_logs.mkdir(parents=True)
        _make_old_file(branch_logs / "ops.jsonl", 35)

        with (
            patch(
                "aipass.prax.apps.handlers.logging.log_watchdog._get_system_logs_dir",
                return_value=tmp_path / "system_logs",
            ),
            patch(
                "aipass.prax.apps.handlers.logging.log_watchdog._get_ecosystem_root",
                return_value=eco,
            ),
        ):
            result = sweep_stale_logs()

        assert result["files_removed"] == 1
        assert not (branch_logs / "ops.jsonl").exists()

    def test_keeps_fresh_files(self, tmp_path):
        """Verify sweep leaves files younger than 30 days untouched."""
        sweep_stale_logs = _get_sweep()

        sys_logs = tmp_path / "system_logs"
        sys_logs.mkdir()
        fresh = sys_logs / "recent.log"
        fresh.write_text("fresh content\n")

        with (
            patch(
                "aipass.prax.apps.handlers.logging.log_watchdog._get_system_logs_dir",
                return_value=sys_logs,
            ),
            patch(
                "aipass.prax.apps.handlers.logging.log_watchdog._get_ecosystem_root",
                return_value=tmp_path / "src" / "aipass",
            ),
        ):
            result = sweep_stale_logs()

        assert result["files_removed"] == 0
        assert fresh.exists()

    def test_deletes_rotation_siblings(self, tmp_path):
        """Verify sweep also removes stale .log.1 rotation backups."""
        sweep_stale_logs = _get_sweep()

        sys_logs = tmp_path / "system_logs"
        sys_logs.mkdir()
        _make_old_file(sys_logs / "module.log", 40)
        _make_old_file(sys_logs / "module.log.1", 40)

        with (
            patch(
                "aipass.prax.apps.handlers.logging.log_watchdog._get_system_logs_dir",
                return_value=sys_logs,
            ),
            patch(
                "aipass.prax.apps.handlers.logging.log_watchdog._get_ecosystem_root",
                return_value=tmp_path / "src" / "aipass",
            ),
        ):
            result = sweep_stale_logs()

        assert result["files_removed"] == 2
        assert not (sys_logs / "module.log").exists()
        assert not (sys_logs / "module.log.1").exists()

    def test_returns_structured_summary(self, tmp_path):
        """Verify sweep returns summary with counts and reclaimed size."""
        sweep_stale_logs = _get_sweep()

        sys_logs = tmp_path / "system_logs"
        sys_logs.mkdir()
        _make_old_file(sys_logs / "stale.log", 60)

        with (
            patch(
                "aipass.prax.apps.handlers.logging.log_watchdog._get_system_logs_dir",
                return_value=sys_logs,
            ),
            patch(
                "aipass.prax.apps.handlers.logging.log_watchdog._get_ecosystem_root",
                return_value=tmp_path / "src" / "aipass",
            ),
        ):
            result = sweep_stale_logs()

        assert result["max_age_days"] == 30
        assert result["files_removed"] == 1
        assert result["total_reclaimed_kb"] >= 0
        assert len(result["removed"]) == 1
        entry = result["removed"][0]
        assert entry["name"] == "stale.log"
        assert entry["age_days"] > 50


class TestSweepCommand:
    """Test the 'sweep' subcommand routing in handle_command."""

    def test_sweep_subcommand_routes(self, monkeypatch, capsys):
        """Verify 'drone @prax log-audit sweep' routes to _run_sweep."""
        _ensure_watchdog_mock(monkeypatch)

        mod_name = "aipass.prax.apps.modules.log_audit"
        sys.modules.pop(mod_name, None)
        from aipass.prax.apps.modules.log_audit import handle_command

        result = handle_command("log-audit", ["sweep"])

        assert result is True
