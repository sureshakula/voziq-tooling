# =================== AIPass ====================
# Name: test_tool_sound.py
# Version: 1.2.0
# Description: Tests for tool_sound notification handler
# Branch: hooks
# Created: 2026-05-19
# Modified: 2026-05-22
# =============================================

"""Tests for handlers/notification/tool_sound.py."""

from unittest.mock import patch


class TestToolSoundHandler:
    """Core handler behavior tests."""

    def test_handle_returns_result_dict(self):
        from aipass.hooks.apps.handlers.notification.tool_sound import handle

        with patch("aipass.hooks.apps.handlers.notification.tool_sound.speak"):
            result = handle({"tool_name": "Bash"})

        assert isinstance(result, dict)
        assert "stdout" in result
        assert "exit_code" in result
        assert result["stdout"] == ""
        assert result["exit_code"] == 0

    def test_speaks_tool_name(self):
        from aipass.hooks.apps.handlers.notification.tool_sound import handle

        with patch("aipass.hooks.apps.handlers.notification.tool_sound.speak") as mock_speak:
            handle({"tool_name": "Edit"})

        mock_speak.assert_called_once_with("tool sound: Edit")

    def test_no_speak_when_no_tool_name(self):
        from aipass.hooks.apps.handlers.notification.tool_sound import handle

        with patch("aipass.hooks.apps.handlers.notification.tool_sound.speak") as mock_speak:
            handle({})

        mock_speak.assert_not_called()

    def test_no_speak_when_empty_tool_name(self):
        from aipass.hooks.apps.handlers.notification.tool_sound import handle

        with patch("aipass.hooks.apps.handlers.notification.tool_sound.speak") as mock_speak:
            handle({"tool_name": ""})

        mock_speak.assert_not_called()
