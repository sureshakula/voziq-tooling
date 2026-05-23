# =================== AIPass ====================
# Name: test_stop_sound.py
# Version: 1.2.0
# Description: Tests for stop_sound notification handler
# Branch: hooks
# Created: 2026-05-20
# Modified: 2026-05-22
# =============================================

"""Tests for handlers/notification/stop_sound.py."""

from unittest.mock import patch


class TestStopSoundHandler:
    """Core handler behavior tests."""

    def test_handle_returns_result_dict(self):
        from aipass.hooks.apps.handlers.notification.stop_sound import handle

        with patch("aipass.hooks.apps.handlers.notification.stop_sound.speak"):
            result = handle({})

        assert isinstance(result, dict)
        assert result["stdout"] == ""
        assert result["exit_code"] == 0

    def test_handle_speaks_stop_sound(self):
        from aipass.hooks.apps.handlers.notification.stop_sound import handle

        with patch("aipass.hooks.apps.handlers.notification.stop_sound.speak") as mock_speak:
            handle({})

        mock_speak.assert_called_once_with("stop sound")

    def test_handle_skips_when_stop_hook_active(self):
        from aipass.hooks.apps.handlers.notification.stop_sound import handle

        with patch("aipass.hooks.apps.handlers.notification.stop_sound.speak") as mock_speak:
            result = handle({"stop_hook_active": True})

        mock_speak.assert_not_called()
        assert result["exit_code"] == 0
