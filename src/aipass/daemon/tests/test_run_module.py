"""Tests for the drone @daemon run module (decentralized scheduler tick)."""

from unittest.mock import patch

from aipass.daemon.apps.modules.run import (
    run_tick,
    handle_command,
    HANDLED_COMMANDS,
)


class TestHandleCommand:
    def test_handles_run(self):
        assert "run" in HANDLED_COMMANDS

    def test_rejects_unknown(self):
        assert handle_command("unknown", []) is False

    def test_help_flag(self, capsys):
        result = handle_command("run", ["--help"])
        assert result is True


class TestRunTick:
    @patch("aipass.daemon.apps.modules.run.discover_jobs", return_value=[])
    def test_no_jobs(self, mock_discover):
        results = run_tick(dry_run=True)
        assert results["discovered"] == 0
        assert results["fired"] == 0

    @patch("aipass.daemon.apps.modules.run.discover_jobs")
    @patch("aipass.daemon.apps.modules.run.load_runstate", return_value={"jobs": {}})
    def test_dry_run_does_not_fire(self, mock_rs, mock_discover):
        mock_discover.return_value = [
            {
                "owner": "@commons",
                "id": "test",
                "enabled": True,
                "schedule": {"type": "interval", "interval_minutes": 1},
                "wake": {"fresh": True},
                "prompt": "test prompt",
            }
        ]
        results = run_tick(dry_run=True)
        assert results["due"] == 1
        assert results["fired"] == 0

    @patch("aipass.daemon.apps.modules.run.discover_jobs")
    @patch("aipass.daemon.apps.modules.run.load_runstate", return_value={"jobs": {}})
    def test_disabled_jobs_skipped(self, mock_rs, mock_discover):
        mock_discover.return_value = [
            {
                "owner": "@commons",
                "id": "off",
                "enabled": False,
                "schedule": {"type": "interval", "interval_minutes": 1},
                "wake": {},
                "prompt": "disabled",
            }
        ]
        results = run_tick(dry_run=True)
        assert results["enabled"] == 0
        assert results["due"] == 0

    @patch("aipass.daemon.apps.modules.run.save_runstate")
    @patch("aipass.daemon.apps.modules.run._fire_job", return_value=True)
    @patch("aipass.daemon.apps.modules.run.discover_jobs")
    @patch("aipass.daemon.apps.modules.run.load_runstate", return_value={"jobs": {}})
    def test_fires_due_job(self, mock_rs, mock_discover, mock_fire, mock_save):
        mock_discover.return_value = [
            {
                "owner": "@commons",
                "id": "test",
                "enabled": True,
                "schedule": {"type": "interval", "interval_minutes": 1},
                "wake": {"fresh": True},
                "prompt": "test",
            }
        ]
        results = run_tick()
        assert results["fired"] == 1
        assert results["failed"] == 0
        mock_fire.assert_called_once()
        mock_save.assert_called()

    @patch("aipass.daemon.apps.modules.run.save_runstate")
    @patch("aipass.daemon.apps.modules.run._fire_job", return_value=False)
    @patch("aipass.daemon.apps.modules.run.discover_jobs")
    @patch("aipass.daemon.apps.modules.run.load_runstate", return_value={"jobs": {}})
    def test_failed_fire_counted(self, mock_rs, mock_discover, mock_fire, mock_save):
        mock_discover.return_value = [
            {
                "owner": "@commons",
                "id": "test",
                "enabled": True,
                "schedule": {"type": "interval", "interval_minutes": 1},
                "wake": {},
                "prompt": "test",
            }
        ]
        results = run_tick()
        assert results["failed"] == 1
        assert results["fired"] == 0
