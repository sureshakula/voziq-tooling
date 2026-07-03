# =================== AIPass ====================
# Name: test_monitor.py
# Description: Tests for /monitor command — system-wide log subscription (DPLAN-0221)
# Version: 1.0.0
# Created: 2026-06-29
# Modified: 2026-06-29
# =============================================

"""
Tests for /monitor command — system-wide log subscription feature (DPLAN-0221).

Tests cover:
  - Subscribe persists {chat_id, mode} to local file
  - _boot_monitor reads persisted subscription and starts the streamer
  - LogStreamer level_filter: default keeps WARNING/ERROR/CRITICAL, drops INFO
  - LogStreamer level_filter: 'all' keeps everything
  - LogStreamer system_wide globs *.log (not branch-specific)
  - /monitor off clears the subscription
  - /monitor command routing (on, all, off, status, bare)
"""

from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock

from apps.handlers.log_streamer import LogStreamer  # type: ignore[import-not-found]


# =============================================
# HELPERS
# =============================================


@pytest.fixture
def _patch_base_bot_deps(tmp_path):
    """Patch heavy BaseBot dependencies to allow lightweight instantiation."""
    sub_file = tmp_path / "monitor_sub.json"
    patches = [
        patch("apps.handlers.base_bot.PENDING_DIR", tmp_path),
        patch("apps.handlers.base_bot.signal.signal"),
        patch("apps.handlers.base_bot.atexit.register"),
    ]
    for p in patches:
        p.start()
    yield sub_file
    for p in patches:
        p.stop()


def _make_bot(tmp_path, _patch_base_bot_deps):
    """Create a BaseBot with monitor subscription redirected to tmp_path."""
    from apps.handlers.base_bot import BaseBot  # type: ignore[import-not-found]

    workdir = tmp_path / "workdir"
    workdir.mkdir()
    bot = BaseBot(
        bot_id="monitor_test",
        bot_token="123:FAKETOKEN",
        work_dir=workdir,
        bot_name="Monitor Test Bot",
        allowed_user_ids=[111],
        branch_name=None,
    )
    # Redirect subscription file to tmp_path so tests don't touch real HOME
    sub_file: Path = _patch_base_bot_deps
    bot._monitor_subscription_file = lambda: sub_file  # type: ignore[assignment]
    return bot


# =============================================
# 1. SUBSCRIBE PERSISTS VIA @API SET_SECRET
# =============================================


class TestSubscribePersists:
    """Verify _monitor_subscribe persists {chat_id, mode} and can be reloaded."""

    def test_subscribe_writes_file(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        sub_file: Path = _patch_base_bot_deps
        with (
            patch.object(bot, "send_message"),
            patch("apps.handlers.base_bot.LogStreamer") as MockStreamer,
        ):
            MockStreamer.return_value = MagicMock()
            bot._monitor_subscribe(42, "default")

            import json

            data = json.loads(sub_file.read_text())
            assert data == {"chat_id": 42, "mode": "default"}

    def test_subscribe_roundtrip_reload(self, tmp_path, _patch_base_bot_deps):
        """Written file can be read back by _load_monitor_subscription."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        sub_file: Path = _patch_base_bot_deps
        import json

        sub_file.write_text(json.dumps({"chat_id": 42, "mode": "all"}))

        result = bot._load_monitor_subscription()

        assert result == {"chat_id": 42, "mode": "all"}
        assert result["chat_id"] == 42
        assert result["mode"] == "all"

    def test_subscribe_starts_streamer(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with (
            patch.object(bot, "send_message"),
            patch("apps.handlers.base_bot.LogStreamer") as MockStreamer,
        ):
            mock_instance = MagicMock()
            MockStreamer.return_value = mock_instance

            bot._monitor_subscribe(42, "default")

            MockStreamer.assert_called_once_with(
                "123:FAKETOKEN",
                42,
                branch_name="monitor",
                system_wide=True,
                level_filter="default",
            )
            mock_instance.start.assert_called_once()
            assert bot._monitor_streamer is mock_instance

    def test_subscribe_sends_confirmation(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with (
            patch.object(bot, "send_message") as mock_send,
            patch("apps.handlers.base_bot.LogStreamer", return_value=MagicMock()),
        ):
            bot._monitor_subscribe(42, "default")
            mock_send.assert_called_once()
            msg = mock_send.call_args[0][1]
            assert "errors & warnings" in msg

    def test_subscribe_stops_existing_streamer(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        old_streamer = MagicMock()
        bot._monitor_streamer = old_streamer

        with (
            patch.object(bot, "send_message"),
            patch("apps.handlers.base_bot.LogStreamer", return_value=MagicMock()),
        ):
            bot._monitor_subscribe(42, "all")
            old_streamer.stop.assert_called_once()

    def test_subscribe_aborts_on_save_failure(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with (
            patch.object(bot, "_save_monitor_subscription", return_value=False),
            patch.object(bot, "send_message") as mock_send,
        ):
            bot._monitor_subscribe(42, "default")
            msg = mock_send.call_args[0][1]
            assert "Failed" in msg
            assert bot._monitor_streamer is None


# =============================================
# 2. BOOT-START READS SUBSCRIPTION
# =============================================


class TestBootMonitor:
    """Verify _boot_monitor reads persisted sub and starts streamer."""

    def test_boot_starts_streamer_from_persisted(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        sub_file: Path = _patch_base_bot_deps
        import json

        sub_file.write_text(json.dumps({"chat_id": 42, "mode": "default"}))

        with patch("apps.handlers.base_bot.LogStreamer") as MockStreamer:
            mock_instance = MagicMock()
            MockStreamer.return_value = mock_instance

            bot._boot_monitor()

            MockStreamer.assert_called_once_with(
                "123:FAKETOKEN",
                42,
                branch_name="monitor",
                system_wide=True,
                level_filter="default",
            )
            mock_instance.start.assert_called_once()
            assert bot._monitor_streamer is mock_instance

    def test_boot_noop_when_no_subscription(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        # No file written — subscription absent
        with patch("apps.handlers.base_bot.LogStreamer") as MockStreamer:
            bot._boot_monitor()
            MockStreamer.assert_not_called()
            assert bot._monitor_streamer is None

    def test_boot_noop_when_empty_subscription(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        sub_file: Path = _patch_base_bot_deps
        sub_file.write_text("{}")

        with patch("apps.handlers.base_bot.LogStreamer") as MockStreamer:
            bot._boot_monitor()
            MockStreamer.assert_not_called()

    def test_boot_respects_mode_all(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        sub_file: Path = _patch_base_bot_deps
        import json

        sub_file.write_text(json.dumps({"chat_id": 99, "mode": "all"}))

        with patch("apps.handlers.base_bot.LogStreamer") as MockStreamer:
            MockStreamer.return_value = MagicMock()
            bot._boot_monitor()
            MockStreamer.assert_called_once_with(
                "123:FAKETOKEN",
                99,
                branch_name="monitor",
                system_wide=True,
                level_filter="all",
            )


# =============================================
# 3. LEVEL FILTER
# =============================================


class TestLevelFilter:
    """Verify LogStreamer._filter_lines keeps/drops by level."""

    @pytest.fixture
    def streamer_default(self, tmp_path):
        logs_dir = tmp_path / "system_logs"
        logs_dir.mkdir()
        with patch("apps.handlers.log_streamer.SYSTEM_LOGS_DIR", logs_dir):
            return LogStreamer("tok", 1, "x", system_wide=True, level_filter="default")

    @pytest.fixture
    def streamer_all(self, tmp_path):
        logs_dir = tmp_path / "system_logs"
        logs_dir.mkdir()
        with patch("apps.handlers.log_streamer.SYSTEM_LOGS_DIR", logs_dir):
            return LogStreamer("tok", 1, "x", system_wide=True, level_filter="all")

    def test_default_keeps_warning(self, streamer_default):
        lines = ["2026-06-24 | WARNING | something bad"]
        assert streamer_default._filter_lines(lines) == lines

    def test_default_keeps_error(self, streamer_default):
        lines = ["2026-06-24 | ERROR | crash"]
        assert streamer_default._filter_lines(lines) == lines

    def test_default_keeps_critical(self, streamer_default):
        lines = ["2026-06-24 | CRITICAL | meltdown"]
        assert streamer_default._filter_lines(lines) == lines

    def test_default_drops_info(self, streamer_default):
        lines = ["2026-06-24 | INFO | all is well"]
        assert streamer_default._filter_lines(lines) == []

    def test_default_drops_debug(self, streamer_default):
        lines = ["2026-06-24 | DEBUG | verbose detail"]
        assert streamer_default._filter_lines(lines) == []

    def test_default_mixed_keeps_only_high_severity(self, streamer_default):
        lines = [
            "2026-06-24 | INFO | routine",
            "2026-06-24 | WARNING | watch out",
            "2026-06-24 | DEBUG | trace",
            "2026-06-24 | ERROR | failure",
        ]
        result = streamer_default._filter_lines(lines)
        assert len(result) == 2
        assert "WARNING" in result[0]
        assert "ERROR" in result[1]

    def test_all_keeps_everything(self, streamer_all):
        lines = [
            "2026-06-24 | INFO | routine",
            "2026-06-24 | WARNING | watch out",
            "2026-06-24 | DEBUG | trace",
        ]
        assert streamer_all._filter_lines(lines) == lines


# =============================================
# 4. SYSTEM-WIDE GLOB
# =============================================


class TestSystemWideGlob:
    """Verify system_wide=True globs *.log, not just branch-specific."""

    def test_system_wide_finds_all_logs(self, tmp_path):
        logs_dir = tmp_path / "system_logs"
        logs_dir.mkdir()
        (logs_dir / "api_main.log").write_text("a\n")
        (logs_dir / "prax_main.log").write_text("b\n")
        (logs_dir / "trigger_events.log").write_text("c\n")

        with patch("apps.handlers.log_streamer.SYSTEM_LOGS_DIR", logs_dir):
            s = LogStreamer("tok", 1, "monitor", system_wide=True, level_filter="all")

        assert len(s.log_positions) == 3

    def test_non_system_wide_finds_only_branch(self, tmp_path):
        logs_dir = tmp_path / "system_logs"
        logs_dir.mkdir()
        (logs_dir / "api_main.log").write_text("a\n")
        (logs_dir / "prax_main.log").write_text("b\n")

        with patch("apps.handlers.log_streamer.SYSTEM_LOGS_DIR", logs_dir):
            s = LogStreamer("tok", 1, "api", system_wide=False, level_filter="all")

        assert len(s.log_positions) == 1
        assert any("api_main" in p for p in s.log_positions)

    def test_system_wide_reads_new_lines_from_all(self, tmp_path):
        logs_dir = tmp_path / "system_logs"
        logs_dir.mkdir()
        f1 = logs_dir / "api_main.log"
        f2 = logs_dir / "prax_main.log"
        f1.write_text("")
        f2.write_text("")

        with patch("apps.handlers.log_streamer.SYSTEM_LOGS_DIR", logs_dir):
            s = LogStreamer("tok", 1, "monitor", system_wide=True, level_filter="all")

        f1.write_text("api line\n")
        f2.write_text("prax line\n")

        with patch("apps.handlers.log_streamer.SYSTEM_LOGS_DIR", logs_dir):
            lines = s._read_new_lines()

        assert "api line" in lines
        assert "prax line" in lines


# =============================================
# 5. MONITOR OFF CLEARS SUBSCRIPTION
# =============================================


class TestMonitorOff:
    """Verify /monitor off stops streamer and clears persisted state."""

    def test_off_stops_streamer(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        mock_streamer = MagicMock()
        bot._monitor_streamer = mock_streamer

        with patch.object(bot, "send_message"):
            bot._monitor_unsubscribe(42)

        mock_streamer.stop.assert_called_once()
        assert bot._monitor_streamer is None

    def test_off_clears_subscription(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        sub_file: Path = _patch_base_bot_deps
        import json

        sub_file.write_text(json.dumps({"chat_id": 42, "mode": "default"}))

        with patch.object(bot, "send_message"):
            bot._monitor_unsubscribe(42)

        assert not sub_file.exists()

    def test_off_sends_confirmation(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message") as mock_send:
            bot._monitor_unsubscribe(42)

        mock_send.assert_called_once()
        assert "unsubscribed" in mock_send.call_args[0][1].lower()

    def test_off_safe_when_no_streamer(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        assert bot._monitor_streamer is None

        with patch.object(bot, "send_message"):
            bot._monitor_unsubscribe(42)

        assert bot._monitor_streamer is None


# =============================================
# 6. COMMAND ROUTING
# =============================================


class TestMonitorCommandRouting:
    """Verify _handle_monitor_command routes subcommands correctly."""

    def test_on_routes_to_subscribe_default(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "_monitor_subscribe") as mock_sub:
            bot._handle_monitor_command(42, "on")
            mock_sub.assert_called_once_with(42, mode="default")

    def test_all_routes_to_subscribe_all(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "_monitor_subscribe") as mock_sub:
            bot._handle_monitor_command(42, "all")
            mock_sub.assert_called_once_with(42, mode="all")

    def test_off_routes_to_unsubscribe(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "_monitor_unsubscribe") as mock_unsub:
            bot._handle_monitor_command(42, "off")
            mock_unsub.assert_called_once_with(42)

    def test_status_routes_to_status(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "_monitor_status") as mock_stat:
            bot._handle_monitor_command(42, "status")
            mock_stat.assert_called_once_with(42)

    def test_bare_monitor_shows_help(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message") as mock_send:
            bot._handle_monitor_command(42, "")
            msg = mock_send.call_args[0][1]
            assert "/monitor on" in msg
            assert "/monitor off" in msg

    def test_unknown_subcommand_shows_help(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch.object(bot, "send_message") as mock_send:
            bot._handle_monitor_command(42, "banana")
            msg = mock_send.call_args[0][1]
            assert "/monitor on" in msg


# =============================================
# 7. STATUS REPORTING
# =============================================


class TestMonitorStatus:
    """Verify _monitor_status shows correct state."""

    def test_status_when_not_subscribed(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        # No file written — no subscription
        with patch.object(bot, "send_message") as mock_send:
            bot._monitor_status(42)
            msg = mock_send.call_args[0][1]
            assert "not subscribed" in msg

    def test_status_when_subscribed_and_running(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        sub_file: Path = _patch_base_bot_deps
        import json

        sub_file.write_text(json.dumps({"chat_id": 42, "mode": "default"}))
        mock_streamer = MagicMock()
        mock_streamer._running = True
        bot._monitor_streamer = mock_streamer

        with patch.object(bot, "send_message") as mock_send:
            bot._monitor_status(42)
            msg = mock_send.call_args[0][1]
            assert "streaming" in msg
            assert "this chat" in msg

    def test_status_shows_mode_label(self, tmp_path, _patch_base_bot_deps):
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        sub_file: Path = _patch_base_bot_deps
        import json

        sub_file.write_text(json.dumps({"chat_id": 42, "mode": "all"}))
        bot._monitor_streamer = MagicMock(_running=True)

        with patch.object(bot, "send_message") as mock_send:
            bot._monitor_status(42)
            msg = mock_send.call_args[0][1]
            assert "firehose" in msg
