"""
Tests for poll-offset advancement (#668) and /create+/cancel base-bot gate (#644).

Tests cover:
  - Poll loop advances offset past rate-limited updates
  - Poll loop advances offset past rejected (unauthorized) updates
  - Poll loop advances offset on normal processing
  - _dispatch_command gates /create to base bot only (branch_name is None)
  - _dispatch_command gates /cancel to base bot only
  - _dispatch_command allows /create on base bot
  - get_custom_commands omits /create+/cancel for branch bots
  - get_custom_commands includes /create+/cancel for base bot
"""

import pytest
from unittest.mock import patch, MagicMock

from aipass.skills.lib.telegram.apps.handlers.base_bot import BaseBot


@pytest.fixture
def _patch_base_bot_deps(tmp_path):
    patches = [
        patch("aipass.skills.lib.telegram.apps.handlers.base_bot.PENDING_DIR", tmp_path),
        patch("aipass.skills.lib.telegram.apps.handlers.base_bot.signal.signal"),
        patch("aipass.skills.lib.telegram.apps.handlers.base_bot.atexit.register"),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


def _make_bot(tmp_path, _patch_base_bot_deps, branch_name=None):
    workdir = tmp_path / "workdir"
    workdir.mkdir(exist_ok=True)
    bot = BaseBot(
        bot_id="test_bot",
        bot_token="123:FAKETOKEN",
        work_dir=workdir,
        bot_name="Test Bot",
        branch_name=branch_name,
    )
    bot.verify_connection = lambda timeout=15: True
    bot._set_command_menu = lambda: None
    bot._boot_monitor = lambda: None
    bot._check_lock = lambda: False
    bot._create_lock = lambda: None
    bot._remove_lock = lambda: None
    return bot


# =============================================
# 1. Poll offset advancement (#668)
# =============================================


class TestPollOffsetAdvancement:
    """Offset advances past every consumed update regardless of processing outcome."""

    def test_offset_advances_past_rate_limited_update(self, tmp_path, _patch_base_bot_deps):
        """Offset advances even when process_update hits the rate limiter."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)

        updates = [
            {"update_id": 100, "message": {"chat": {"id": 1}, "from": {"id": 99}, "text": "hi"}},
            {"update_id": 101, "message": {"chat": {"id": 1}, "from": {"id": 99}, "text": "hi2"}},
        ]

        call_count = 0

        def fake_poll(offset):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return updates
            bot.state["running"] = False
            return []

        bot.poll_updates = fake_poll
        bot._load_offset = lambda: 0
        saved_offsets = []
        bot._save_offset = lambda o: saved_offsets.append(o)
        bot.check_rate_limit = lambda uid: False
        bot.send_message = MagicMock()

        bot.run()

        assert 102 in saved_offsets
        assert saved_offsets[-1] == 102

    def test_offset_advances_past_unauthorized_update(self, tmp_path, _patch_base_bot_deps):
        """Offset advances even when user is not in the allowlist."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.allowed_user_ids = [777]

        updates = [
            {"update_id": 200, "message": {"chat": {"id": 1}, "from": {"id": 999}, "text": "intruder"}},
        ]

        call_count = 0

        def fake_poll(offset):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return updates
            bot.state["running"] = False
            return []

        bot.poll_updates = fake_poll
        bot._load_offset = lambda: 0
        saved_offsets = []
        bot._save_offset = lambda o: saved_offsets.append(o)

        bot.run()

        assert saved_offsets == [201]

    def test_offset_advances_on_normal_message(self, tmp_path, _patch_base_bot_deps):
        """Offset advances on successfully processed messages."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)

        updates = [
            {"update_id": 50, "message": {"chat": {"id": 1}, "from": {"id": 1}, "text": "/help"}},
        ]

        call_count = 0

        def fake_poll(offset):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return updates
            bot.state["running"] = False
            return []

        bot.poll_updates = fake_poll
        bot._load_offset = lambda: 0
        saved_offsets = []
        bot._save_offset = lambda o: saved_offsets.append(o)
        bot.send_message = MagicMock()

        bot.run()

        assert saved_offsets == [51]


# =============================================
# 2. /create + /cancel base-bot gate (#644)
# =============================================


class TestCreateCancelGate:
    """Only the base bot (branch_name is None) routes /create and /cancel."""

    def test_branch_bot_does_not_route_create(self, tmp_path, _patch_base_bot_deps):
        """A branch bot (branch_name set) falls through on /create."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, branch_name="devpulse")
        bot.send_message = MagicMock()
        result = bot._dispatch_command(42, ("create", "chat devpulse"))
        assert result is False
        bot.send_message.assert_not_called()

    def test_branch_bot_does_not_route_cancel(self, tmp_path, _patch_base_bot_deps):
        """A branch bot (branch_name set) falls through on /cancel."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, branch_name="devpulse")
        bot.send_message = MagicMock()
        result = bot._dispatch_command(42, ("cancel", ""))
        assert result is False
        bot.send_message.assert_not_called()

    def test_base_bot_routes_create(self, tmp_path, _patch_base_bot_deps):
        """The base bot (branch_name is None) handles /create."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, branch_name=None)
        bot.send_message = MagicMock()
        bot._handle_create_command = MagicMock()
        result = bot._dispatch_command(42, ("create", "chat devpulse"))
        assert result is True
        bot._handle_create_command.assert_called_once_with(42, "chat devpulse")

    def test_base_bot_routes_cancel(self, tmp_path, _patch_base_bot_deps):
        """The base bot (branch_name is None) handles /cancel."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, branch_name=None)
        bot.send_message = MagicMock()
        result = bot._dispatch_command(42, ("cancel", ""))
        assert result is True

    def test_branch_bot_still_routes_monitor(self, tmp_path, _patch_base_bot_deps):
        """Branch bots still handle /monitor (not gated)."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, branch_name="devpulse")
        bot._handle_monitor_command = MagicMock()
        result = bot._dispatch_command(42, ("monitor", "status"))
        assert result is True
        bot._handle_monitor_command.assert_called_once()


class TestGetCustomCommandsGate:
    """get_custom_commands only advertises /create+/cancel for the base bot."""

    def test_base_bot_includes_create_cancel(self, tmp_path, _patch_base_bot_deps):
        """Base bot (branch_name is None) advertises /create and /cancel."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, branch_name=None)
        commands = bot.get_custom_commands()
        assert "create" in commands
        assert "cancel" in commands
        assert "monitor" in commands

    def test_branch_bot_omits_create_cancel(self, tmp_path, _patch_base_bot_deps):
        """Branch bot (branch_name set) does NOT advertise /create or /cancel."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, branch_name="devpulse")
        commands = bot.get_custom_commands()
        assert "create" not in commands
        assert "cancel" not in commands
        assert "monitor" in commands
