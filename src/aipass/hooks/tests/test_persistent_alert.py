# =================== AIPass ====================
# Name: test_persistent_alert.py
# Version: 1.0.0
# Description: Tests for persistent_alert handler and alert_dismiss module
# Branch: hooks
# Created: 2026-07-14
# Modified: 2026-07-14
# =============================================

"""Tests for handlers/prompt/persistent_alert.py and modules/alert_dismiss.py."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


def _make_alert(
    alert_id="test-001",
    source="prax",
    severity="warning",
    title="Test alert",
    body="Something happened",
    expires_at=None,
):
    alert = {
        "id": alert_id,
        "source": source,
        "severity": severity,
        "title": title,
        "body": body,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at,
    }
    return alert


def _write_alerts(aipass_dir: Path, alerts: list[dict]):
    alerts_path = aipass_dir / "alerts.json"
    alerts_path.write_text(
        json.dumps({"alerts": alerts}, indent=2) + "\n",
        encoding="utf-8",
    )


class TestPersistentAlertHandler:
    """Banner injection behavior."""

    def test_banner_injected_when_alerts_exist(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.persistent_alert import handle

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        _write_alerts(aipass_dir, [_make_alert()])

        with patch(
            "aipass.hooks.apps.handlers.prompt.persistent_alert._find_aipass_dir",
            return_value=aipass_dir,
        ):
            result = handle({})

        assert result["exit_code"] == 0
        assert "# Active Alerts" in result["stdout"]
        assert "[WARNING] Test alert" in result["stdout"]
        assert "drone @hooks dismiss" in result["stdout"]

    def test_no_banner_when_no_alerts_file(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.persistent_alert import handle

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()

        with patch(
            "aipass.hooks.apps.handlers.prompt.persistent_alert._find_aipass_dir",
            return_value=aipass_dir,
        ):
            result = handle({})

        assert result["stdout"] == ""
        assert result["exit_code"] == 0

    def test_no_banner_when_empty_alerts(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.persistent_alert import handle

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        _write_alerts(aipass_dir, [])

        with patch(
            "aipass.hooks.apps.handlers.prompt.persistent_alert._find_aipass_dir",
            return_value=aipass_dir,
        ):
            result = handle({})

        assert result["stdout"] == ""

    def test_no_banner_when_no_aipass_dir(self):
        from aipass.hooks.apps.handlers.prompt.persistent_alert import handle

        with patch(
            "aipass.hooks.apps.handlers.prompt.persistent_alert._find_aipass_dir",
            return_value=None,
        ):
            result = handle({})

        assert result["stdout"] == ""
        assert result["exit_code"] == 0

    def test_multiple_alerts_all_shown(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.persistent_alert import handle

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        _write_alerts(
            aipass_dir,
            [
                _make_alert(alert_id="a1", title="First"),
                _make_alert(alert_id="a2", title="Second", severity="critical"),
            ],
        )

        with patch(
            "aipass.hooks.apps.handlers.prompt.persistent_alert._find_aipass_dir",
            return_value=aipass_dir,
        ):
            result = handle({})

        assert "[WARNING] First" in result["stdout"]
        assert "[CRITICAL] Second" in result["stdout"]

    def test_source_and_id_in_banner(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.persistent_alert import handle

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        _write_alerts(aipass_dir, [_make_alert(alert_id="abc-123", source="trigger")])

        with patch(
            "aipass.hooks.apps.handlers.prompt.persistent_alert._find_aipass_dir",
            return_value=aipass_dir,
        ):
            result = handle({})

        assert "@trigger" in result["stdout"]
        assert "abc-123" in result["stdout"]

    def test_body_included_in_banner(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.persistent_alert import handle

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        _write_alerts(aipass_dir, [_make_alert(body="Log rate exceeds 50/s")])

        with patch(
            "aipass.hooks.apps.handlers.prompt.persistent_alert._find_aipass_dir",
            return_value=aipass_dir,
        ):
            result = handle({})

        assert "Log rate exceeds 50/s" in result["stdout"]

    def test_no_body_line_when_body_empty(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.persistent_alert import handle

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        _write_alerts(aipass_dir, [_make_alert(body="")])

        with patch(
            "aipass.hooks.apps.handlers.prompt.persistent_alert._find_aipass_dir",
            return_value=aipass_dir,
        ):
            result = handle({})

        lines = result["stdout"].split("\n")
        body_lines = [line for line in lines if line.startswith("  ")]
        assert len(body_lines) == 0


class TestExpiredAlertCleanup:
    """Auto-cleaning of expired alerts."""

    def test_expired_alerts_removed(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.persistent_alert import handle

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        _write_alerts(
            aipass_dir,
            [
                _make_alert(alert_id="expired", expires_at=past),
                _make_alert(alert_id="active", expires_at=None),
            ],
        )

        with patch(
            "aipass.hooks.apps.handlers.prompt.persistent_alert._find_aipass_dir",
            return_value=aipass_dir,
        ):
            result = handle({})

        assert "active" in result["stdout"]
        assert "expired" not in result["stdout"]

        saved = json.loads((aipass_dir / "alerts.json").read_text())
        assert len(saved["alerts"]) == 1
        assert saved["alerts"][0]["id"] == "active"

    def test_all_expired_returns_empty(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.persistent_alert import handle

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        _write_alerts(aipass_dir, [_make_alert(expires_at=past)])

        with patch(
            "aipass.hooks.apps.handlers.prompt.persistent_alert._find_aipass_dir",
            return_value=aipass_dir,
        ):
            result = handle({})

        assert result["stdout"] == ""

    def test_future_expiry_kept(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.persistent_alert import handle

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        _write_alerts(aipass_dir, [_make_alert(alert_id="still-valid", expires_at=future)])

        with patch(
            "aipass.hooks.apps.handlers.prompt.persistent_alert._find_aipass_dir",
            return_value=aipass_dir,
        ):
            result = handle({})

        assert "still-valid" in result["stdout"]

    def test_corrupt_json_returns_empty(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.persistent_alert import handle

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        (aipass_dir / "alerts.json").write_text("{bad json", encoding="utf-8")

        with patch(
            "aipass.hooks.apps.handlers.prompt.persistent_alert._find_aipass_dir",
            return_value=aipass_dir,
        ):
            result = handle({})

        assert result["stdout"] == ""
        assert result["exit_code"] == 0


class TestAlertSound:
    """Sound fires on first injection only."""

    def test_sound_on_first_injection(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt import persistent_alert

        persistent_alert._announced.clear()

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        _write_alerts(aipass_dir, [_make_alert(alert_id="snd-001")])

        with patch.object(persistent_alert, "_find_aipass_dir", return_value=aipass_dir):
            result = persistent_alert.handle({})

        assert "sound" in result
        assert "1 active alert" in result["sound"]

    def test_no_sound_on_repeat_injection(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt import persistent_alert

        persistent_alert._announced.clear()

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        _write_alerts(aipass_dir, [_make_alert(alert_id="snd-002")])

        with patch.object(persistent_alert, "_find_aipass_dir", return_value=aipass_dir):
            persistent_alert.handle({})
            result = persistent_alert.handle({})

        assert "sound" not in result

    def test_sound_on_new_alert_added(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt import persistent_alert

        persistent_alert._announced.clear()

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        _write_alerts(aipass_dir, [_make_alert(alert_id="snd-003")])

        with patch.object(persistent_alert, "_find_aipass_dir", return_value=aipass_dir):
            persistent_alert.handle({})

        _write_alerts(
            aipass_dir,
            [
                _make_alert(alert_id="snd-003"),
                _make_alert(alert_id="snd-004"),
            ],
        )

        with patch.object(persistent_alert, "_find_aipass_dir", return_value=aipass_dir):
            result = persistent_alert.handle({})

        assert "sound" in result
        assert "2 active alerts" in result["sound"]

    def test_no_sound_when_no_alerts(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt import persistent_alert

        persistent_alert._announced.clear()

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        _write_alerts(aipass_dir, [])

        with patch.object(persistent_alert, "_find_aipass_dir", return_value=aipass_dir):
            result = persistent_alert.handle({})

        assert "sound" not in result


class TestAlertDismiss:
    """drone @hooks dismiss behavior."""

    def test_dismiss_removes_by_id(self, tmp_path):
        from aipass.hooks.apps.modules.alert_dismiss import _dismiss_alert

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        _write_alerts(
            aipass_dir,
            [
                _make_alert(alert_id="keep"),
                _make_alert(alert_id="remove"),
            ],
        )

        with patch(
            "aipass.hooks.apps.modules.alert_dismiss._find_aipass_dir",
            return_value=aipass_dir,
        ):
            result = _dismiss_alert("remove")

        assert result is True
        saved = json.loads((aipass_dir / "alerts.json").read_text())
        assert len(saved["alerts"]) == 1
        assert saved["alerts"][0]["id"] == "keep"

    def test_dismiss_nonexistent_returns_false(self, tmp_path):
        from aipass.hooks.apps.modules.alert_dismiss import _dismiss_alert

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        _write_alerts(aipass_dir, [_make_alert(alert_id="exists")])

        with patch(
            "aipass.hooks.apps.modules.alert_dismiss._find_aipass_dir",
            return_value=aipass_dir,
        ):
            result = _dismiss_alert("nope")

        assert result is False

    def test_dismiss_no_alerts_file(self, tmp_path):
        from aipass.hooks.apps.modules.alert_dismiss import _dismiss_alert

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()

        with patch(
            "aipass.hooks.apps.modules.alert_dismiss._find_aipass_dir",
            return_value=aipass_dir,
        ):
            result = _dismiss_alert("any")

        assert result is False

    def test_dismiss_no_aipass_dir(self):
        from aipass.hooks.apps.modules.alert_dismiss import _dismiss_alert

        with patch(
            "aipass.hooks.apps.modules.alert_dismiss._find_aipass_dir",
            return_value=None,
        ):
            result = _dismiss_alert("any")

        assert result is False

    def test_handle_command_routes_dismiss(self, tmp_path):
        from aipass.hooks.apps.modules.alert_dismiss import handle_command

        aipass_dir = tmp_path / ".aipass"
        aipass_dir.mkdir()
        _write_alerts(aipass_dir, [_make_alert(alert_id="cmd-test")])

        with patch(
            "aipass.hooks.apps.modules.alert_dismiss._find_aipass_dir",
            return_value=aipass_dir,
        ):
            result = handle_command("dismiss", ["cmd-test"])

        assert result is True
        saved = json.loads((aipass_dir / "alerts.json").read_text())
        assert len(saved["alerts"]) == 0

    def test_handle_command_ignores_other_commands(self):
        from aipass.hooks.apps.modules.alert_dismiss import handle_command

        assert handle_command("status", []) is False

    def test_handle_command_help(self):
        from aipass.hooks.apps.modules.alert_dismiss import handle_command

        assert handle_command("dismiss", ["--help"]) is True
