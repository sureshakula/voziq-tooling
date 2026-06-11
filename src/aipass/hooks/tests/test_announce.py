# =================== AIPass ====================
# Name: test_announce.py
# Version: 1.3.0
# Description: Tests for announce notification handler
# Branch: hooks
# Created: 2026-05-20
# Modified: 2026-06-09
# =============================================

"""Tests for handlers/notification/announce.py."""


class TestAnnounceHandler:
    """Core handler behavior tests."""

    def test_handle_returns_result_dict(self):
        from aipass.hooks.apps.handlers.notification.announce import handle

        result = handle({})

        assert isinstance(result, dict)
        assert result["stdout"] == ""
        assert result["exit_code"] == 0

    def test_handle_sets_sound_key(self):
        from aipass.hooks.apps.handlers.notification.announce import handle

        result = handle({})

        assert result["sound"] == "notification sound"
