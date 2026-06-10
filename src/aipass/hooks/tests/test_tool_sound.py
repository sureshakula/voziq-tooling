# =================== AIPass ====================
# Name: test_tool_sound.py
# Version: 1.3.0
# Description: Tests for tool_sound notification handler
# Branch: hooks
# Created: 2026-05-19
# Modified: 2026-06-09
# =============================================

"""Tests for handlers/notification/tool_sound.py."""


class TestToolSoundHandler:
    """Core handler behavior tests."""

    def test_handle_returns_result_dict(self):
        from aipass.hooks.apps.handlers.notification.tool_sound import handle

        result = handle({"tool_name": "Bash"})

        assert isinstance(result, dict)
        assert "stdout" in result
        assert "exit_code" in result
        assert result["stdout"] == ""
        assert result["exit_code"] == 0

    def test_sound_key_includes_tool_name(self):
        from aipass.hooks.apps.handlers.notification.tool_sound import handle

        result = handle({"tool_name": "Edit"})

        assert result["sound"] == "tool sound: Edit"

    def test_no_sound_when_no_tool_name(self):
        from aipass.hooks.apps.handlers.notification.tool_sound import handle

        result = handle({})

        assert result.get("sound", "") == ""

    def test_no_sound_when_empty_tool_name(self):
        from aipass.hooks.apps.handlers.notification.tool_sound import handle

        result = handle({"tool_name": ""})

        assert result.get("sound", "") == ""
