# =================== AIPass ====================
# Name: test_announce.py
# Version: 1.2.0
# Description: Tests for announce notification handler
# Branch: hooks
# Created: 2026-05-20
# Modified: 2026-05-22
# =============================================

"""Tests for handlers/notification/announce.py."""

from unittest.mock import patch


class TestAnnounceHandler:
    """Core handler behavior tests."""

    def test_handle_returns_result_dict(self):
        from aipass.hooks.apps.handlers.notification.announce import handle

        with patch("aipass.hooks.apps.handlers.notification.announce.speak"):
            result = handle({})

        assert isinstance(result, dict)
        assert result["stdout"] == ""
        assert result["exit_code"] == 0

    def test_handle_speaks_notification_sound(self):
        from aipass.hooks.apps.handlers.notification.announce import handle

        with patch("aipass.hooks.apps.handlers.notification.announce.speak") as mock_speak:
            handle({})

        mock_speak.assert_called_once_with("notification sound")
