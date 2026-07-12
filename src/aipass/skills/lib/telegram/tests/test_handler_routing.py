"""Tests for handler.py action routing."""

from unittest.mock import patch

from aipass.skills.lib.telegram.handler import run, _ok, _err, _ACTIONS, _DISPATCH


class TestHelpers:
    def test_ok_returns_success_dict(self):
        result = _ok("hello")
        assert result == {"success": True, "output": "hello", "error": None}

    def test_err_returns_failure_dict(self):
        result = _err("bad thing")
        assert result == {"success": False, "output": "", "error": "bad thing"}


class TestRunRouting:
    def test_empty_action_returns_error(self):
        result = run("", [], {})
        assert result["success"] is False
        assert "No action specified" in result["error"]

    def test_unknown_action_returns_error(self):
        result = run("bogus", [], {})
        assert result["success"] is False
        assert "Unknown action 'bogus'" in result["error"]
        assert "create" in result["error"]

    def test_all_actions_have_dispatch_entry(self):
        for action in _ACTIONS:
            assert action in _DISPATCH

    def test_dispatch_covers_all_actions(self):
        assert set(_DISPATCH.keys()) == _ACTIONS


class TestStartAction:
    def test_start_no_args_returns_error(self):
        result = run("start", [], {})
        assert result["success"] is False
        assert "bot_id" in result["error"]

    @patch("aipass.skills.lib.telegram.apps.handlers.bot_operations.start_bot", return_value=0)
    def test_start_routes_to_start_bot(self, mock_start):
        result = run("start", ["base"], {})
        mock_start.assert_called_once_with("base")
        assert result["success"] is True
        assert "base" in result["output"]

    @patch("aipass.skills.lib.telegram.apps.handlers.bot_operations.start_bot", return_value=None)
    def test_start_config_fail_returns_error(self, mock_start):
        result = run("start", ["missing"], {})
        assert result["success"] is False
        assert "missing" in result["error"]


class TestStopAction:
    def test_stop_no_args_returns_error(self):
        result = run("stop", [], {})
        assert result["success"] is False
        assert "bot_id" in result["error"]

    @patch(
        "aipass.skills.lib.telegram.apps.handlers.bot_operations.stop_bot",
        return_value=(True, "Stopped telegram-bot@base"),
    )
    def test_stop_success(self, mock_stop):
        result = run("stop", ["base"], {})
        mock_stop.assert_called_once_with("base")
        assert result["success"] is True

    @patch(
        "aipass.skills.lib.telegram.apps.handlers.bot_operations.stop_bot", return_value=(False, "Service not found")
    )
    def test_stop_failure(self, mock_stop):
        result = run("stop", ["base"], {})
        assert result["success"] is False


class TestStatusAction:
    @patch("aipass.skills.lib.telegram.apps.handlers.bot_operations.get_status", return_value=[])
    def test_status_no_bots(self, mock_status):
        result = run("status", [], {})
        assert result["success"] is True
        assert "No bots registered" in result["output"]

    @patch("aipass.skills.lib.telegram.apps.handlers.bot_operations.get_status", return_value=[])
    def test_status_specific_bot_not_found(self, mock_status):
        result = run("status", ["missing"], {})
        assert result["success"] is True
        assert "missing" in result["output"]

    @patch(
        "aipass.skills.lib.telegram.apps.handlers.bot_operations.format_bot_details",
        return_value=["Bot ID: base", "Status: running"],
    )
    @patch(
        "aipass.skills.lib.telegram.apps.handlers.bot_operations.get_status",
        return_value=[{"bot_id": "base", "status": "running"}],
    )
    def test_status_specific_bot_found(self, mock_status, mock_format):
        result = run("status", ["base"], {})
        assert result["success"] is True
        assert "Bot ID: base" in result["output"]

    @patch(
        "aipass.skills.lib.telegram.apps.handlers.bot_operations.format_bot_table",
        return_value=["Bot ID  Branch  Status", "base    -       running"],
    )
    @patch(
        "aipass.skills.lib.telegram.apps.handlers.bot_operations.get_status",
        return_value=[{"bot_id": "base"}, {"bot_id": "dev"}],
    )
    def test_status_all_bots(self, mock_status, mock_table):
        result = run("status", [], {})
        assert result["success"] is True
        assert "Bot ID" in result["output"]


class TestCreateAction:
    def test_create_no_args_returns_error(self):
        result = run("create", [], {})
        assert result["success"] is False
        assert "requires" in result["error"]

    def test_create_missing_token_returns_error(self):
        result = run("create", ["mybot"], {})
        assert result["success"] is False

    @patch("aipass.skills.lib.telegram.apps.handlers.bot_factory.create_bot", return_value={"bot_id": "mybot"})
    def test_create_success(self, mock_create):
        result = run("create", ["mybot", "123:ABC"], {})
        mock_create.assert_called_once_with(bot_id="mybot", bot_token="123:ABC", branch_name=None, work_dir=None)
        assert result["success"] is True
        assert "mybot" in result["output"]

    @patch("aipass.skills.lib.telegram.apps.handlers.bot_factory.create_bot", return_value=None)
    def test_create_failure(self, mock_create):
        result = run("create", ["mybot", "123:ABC"], {})
        assert result["success"] is False

    @patch("aipass.skills.lib.telegram.apps.handlers.bot_factory.create_bot", return_value={"bot_id": "mybot"})
    def test_create_with_branch_flag(self, mock_create):
        result = run("create", ["mybot", "123:ABC", "--branch", "dev"], {})
        mock_create.assert_called_once_with(bot_id="mybot", bot_token="123:ABC", branch_name="dev", work_dir=None)
        assert result["success"] is True


class TestDeleteAction:
    def test_delete_no_args_returns_error(self):
        result = run("delete", [], {})
        assert result["success"] is False
        assert "bot_id" in result["error"]

    @patch("aipass.skills.lib.telegram.apps.handlers.bot_factory.delete_bot", return_value=True)
    def test_delete_success(self, mock_delete):
        result = run("delete", ["base"], {})
        mock_delete.assert_called_once_with("base")
        assert result["success"] is True

    @patch("aipass.skills.lib.telegram.apps.handlers.bot_factory.delete_bot", return_value=False)
    def test_delete_failure(self, mock_delete):
        result = run("delete", ["base"], {})
        assert result["success"] is False


class TestNotifyAction:
    def test_notify_no_args_returns_error(self):
        result = run("notify", [], {})
        assert result["success"] is False
        assert "message" in result["error"]

    @patch("aipass.skills.lib.telegram.apps.handlers.notifier.send_telegram_notification", return_value=True)
    def test_notify_success(self, mock_notify):
        result = run("notify", ["hello", "world"], {})
        mock_notify.assert_called_once_with("hello world")
        assert result["success"] is True

    @patch("aipass.skills.lib.telegram.apps.handlers.notifier.send_telegram_notification", return_value=False)
    def test_notify_failure(self, mock_notify):
        result = run("notify", ["fail"], {})
        assert result["success"] is False


class TestExceptionHandling:
    @patch("aipass.skills.lib.telegram.apps.handlers.bot_operations.get_status", side_effect=RuntimeError("boom"))
    def test_exception_caught_and_returned(self, mock_status):
        result = run("status", [], {})
        assert result["success"] is False
        assert "boom" in result["error"]
