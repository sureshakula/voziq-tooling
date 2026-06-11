# =================== AIPass ====================
# Name: test_stop_sound.py
# Version: 1.3.0
# Description: Tests for stop_sound notification handler
# Branch: hooks
# Created: 2026-05-20
# Modified: 2026-06-09
# =============================================

"""Tests for handlers/notification/stop_sound.py."""


class TestStopSoundHandler:
    """Core handler behavior tests."""

    def test_handle_returns_result_dict(self):
        from aipass.hooks.apps.handlers.notification.stop_sound import handle

        result = handle({})

        assert isinstance(result, dict)
        assert result["stdout"] == ""
        assert result["exit_code"] == 0

    def test_handle_sets_sound_key(self):
        from aipass.hooks.apps.handlers.notification.stop_sound import handle

        result = handle({})

        assert result["sound"] == "stop sound"

    def test_handle_no_sound_when_stop_hook_active(self):
        from aipass.hooks.apps.handlers.notification.stop_sound import handle

        result = handle({"stop_hook_active": True})

        assert result.get("sound", "") == ""
        assert result["exit_code"] == 0
