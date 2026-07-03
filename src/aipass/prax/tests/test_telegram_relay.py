# =================== AIPass ====================
# Name: test_telegram_relay.py
# Description: Tests for the Telegram relay handler
# Version: 1.0.0
# Created: 2026-06-24
# Modified: 2026-06-24
# =============================================

"""Tests for apps/handlers/monitoring/telegram_relay.py

Covers:
- Event formatting (log, command, hook types, PID labels)
- init_relay: disabled path, missing config, incomplete config, successful start
- Fail-silent-once: exactly one log line when config absent, zero sends
- stop_relay: final flush and thread join, no-op when inactive
- relay_event: buffering when active, no-op when inactive
- Batching: 4000-char split across messages
- Flood cap: truncation at 150 lines with suppression notice
- _render_event calls relay_event in monitor.py
- is_relay_enabled_by_env for env var detection
"""

import importlib
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock, patch


@dataclass
class FakeEvent:
    """Minimal MonitoringEvent stand-in for tests."""

    priority: int = 3
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: str = ""
    branch: str = ""
    action: str = ""
    message: str = ""
    level: str = "info"
    caller: Optional[str] = None
    pid: Optional[int] = None


def _import_relay():
    """Import (or reload) telegram_relay with mocked dependencies."""
    fresh_mocks = {
        "aipass.prax.apps.modules.logger": MagicMock(),
        "aipass.prax.apps.handlers.json": MagicMock(),
        "aipass.prax.apps.handlers.json.json_handler": MagicMock(),
    }
    with patch.dict(sys.modules, fresh_mocks):
        if "aipass.prax.apps.handlers.monitoring.telegram_relay" in sys.modules:
            mod = importlib.reload(sys.modules["aipass.prax.apps.handlers.monitoring.telegram_relay"])
        else:
            mod = importlib.import_module("aipass.prax.apps.handlers.monitoring.telegram_relay")

    setattr(mod, "_RELAY_ACTIVE", False)
    setattr(mod, "_bot_token", None)
    setattr(mod, "_chat_id", None)
    mod._buffer.clear()
    mod._stop_event.clear()
    setattr(mod, "_thread", None)
    return mod


# ---------------------------------------------------------------------------
# Event formatting
# ---------------------------------------------------------------------------


class TestFormatEvent:
    """Test _format_event produces correct plain-text lines."""

    def test_log_event_basic(self):
        """Log event includes uppercased branch and message."""
        relay = _import_relay()
        event = FakeEvent(event_type="log", branch="seedgo", message="Audit started")
        result = relay._format_event(event)
        assert "[SEEDGO]" in result
        assert "Audit started" in result

    def test_log_event_with_pid(self):
        """Log event with PID shows BRANCH:PID label."""
        relay = _import_relay()
        event = FakeEvent(event_type="log", branch="devpulse", message="Working", pid=12345)
        result = relay._format_event(event)
        assert "[DEVPULSE:12345]" in result

    def test_command_event(self):
        """Command event shows arrow prefix."""
        relay = _import_relay()
        event = FakeEvent(event_type="command", branch="drone", message="seedgo audit", action="")
        result = relay._format_event(event)
        assert "▶ seedgo audit" in result

    def test_command_event_with_caller_and_target(self):
        """Command event with caller and target shows attribution line."""
        relay = _import_relay()
        event = FakeEvent(
            event_type="command",
            branch="drone",
            message="seedgo audit",
            action="run:prax",
            caller="devpulse",
        )
        result = relay._format_event(event)
        assert "devpulse → prax" in result
        assert "▶ seedgo audit" in result

    def test_command_event_unknown_caller_omitted(self):
        """Command event with UNKNOWN caller omits caller line."""
        relay = _import_relay()
        event = FakeEvent(
            event_type="command",
            branch="drone",
            message="test",
            caller="UNKNOWN",
        )
        result = relay._format_event(event)
        assert "UNKNOWN" not in result

    def test_hook_event_fired(self):
        """Fired hook event uses lightning bolt symbol."""
        relay = _import_relay()
        event = FakeEvent(event_type="hook", branch="hooks", message="cadence:fired", action="fired")
        result = relay._format_event(event)
        assert result == "⚡ HOOK cadence:fired"

    def test_hook_event_skipped(self):
        """Skipped hook event uses dot symbol."""
        relay = _import_relay()
        event = FakeEvent(event_type="hook", branch="hooks", message="cadence:skipped", action="skipped")
        result = relay._format_event(event)
        assert result == "· HOOK cadence:skipped"

    def test_hook_event_unknown_action(self):
        """Unknown hook action uses question mark symbol."""
        relay = _import_relay()
        event = FakeEvent(event_type="hook", branch="hooks", message="something", action="other")
        result = relay._format_event(event)
        assert result.startswith("? HOOK")

    def test_file_event(self):
        """File event formats like a log event with branch and message."""
        relay = _import_relay()
        event = FakeEvent(event_type="file", branch="prax", message="monitor.py modified")
        result = relay._format_event(event)
        assert "[PRAX]" in result
        assert "monitor.py modified" in result


# ---------------------------------------------------------------------------
# init_relay
# ---------------------------------------------------------------------------


class TestInitRelay:
    """Test init_relay activation and fail-silent behavior."""

    def test_disabled_is_noop(self):
        """Disabled flag skips all initialization."""
        relay = _import_relay()
        relay.init_relay(enabled=False)
        assert relay._RELAY_ACTIVE is False
        assert relay._thread is None

    def test_no_config_stays_inactive(self):
        """None config keeps relay inactive."""
        relay = _import_relay()
        relay.init_relay(enabled=True, config=None)
        assert relay._RELAY_ACTIVE is False

    def test_no_config_logs_exactly_once(self):
        """Missing config produces exactly one info log, not per-cycle spam."""
        relay = _import_relay()
        relay.init_relay(enabled=True, config=None)
        calls = [c for c in relay.logger.info.call_args_list if "inactive" in str(c)]
        assert len(calls) == 1

    def test_incomplete_config_missing_chat_id(self):
        """Config without chat_id stays inactive."""
        relay = _import_relay()
        relay.init_relay(enabled=True, config={"bot_token": "tok123"})
        assert relay._RELAY_ACTIVE is False

    def test_incomplete_config_missing_token(self):
        """Config without bot_token stays inactive."""
        relay = _import_relay()
        relay.init_relay(enabled=True, config={"chat_id": 123})
        assert relay._RELAY_ACTIVE is False

    def test_valid_config_activates(self):
        """Valid config sets active flag and stores credentials."""
        relay = _import_relay()
        relay.init_relay(enabled=True, config={"bot_token": "tok123", "chat_id": 456})
        assert relay._RELAY_ACTIVE is True
        assert relay._bot_token == "tok123"
        assert relay._chat_id == 456
        assert relay._thread is not None
        relay.stop_relay()

    def test_valid_config_starts_daemon_thread(self):
        """Valid config starts a named daemon thread."""
        relay = _import_relay()
        relay.init_relay(enabled=True, config={"bot_token": "t", "chat_id": 1})
        assert relay._thread.daemon is True
        assert relay._thread.name == "telegram-relay"
        relay.stop_relay()


# ---------------------------------------------------------------------------
# relay_event
# ---------------------------------------------------------------------------


class TestRelayEvent:
    """Test relay_event buffering."""

    def test_noop_when_inactive(self):
        """Inactive relay does not buffer events."""
        relay = _import_relay()
        event = FakeEvent(event_type="log", branch="test", message="hello")
        relay.relay_event(event)
        assert len(relay._buffer) == 0

    def test_buffers_when_active(self):
        """Active relay appends formatted line to buffer."""
        relay = _import_relay()
        setattr(relay, "_RELAY_ACTIVE", True)
        event = FakeEvent(event_type="log", branch="test", message="hello")
        relay.relay_event(event)
        assert len(relay._buffer) == 1
        assert "hello" in relay._buffer[0]


# ---------------------------------------------------------------------------
# stop_relay
# ---------------------------------------------------------------------------


class TestStopRelay:
    """Test stop_relay cleanup."""

    def test_noop_when_inactive(self):
        """Stopping an inactive relay is a safe no-op."""
        relay = _import_relay()
        relay.stop_relay()
        assert relay._RELAY_ACTIVE is False

    def test_flushes_and_joins(self):
        """Stopping an active relay clears state and joins thread."""
        relay = _import_relay()
        relay.init_relay(enabled=True, config={"bot_token": "t", "chat_id": 1})
        assert relay._RELAY_ACTIVE is True
        relay.stop_relay()
        assert relay._RELAY_ACTIVE is False
        assert relay._thread is None


# ---------------------------------------------------------------------------
# Batching
# ---------------------------------------------------------------------------


class TestBatching:
    """Test _send_batched 4000-char splitting."""

    def test_single_message_under_limit(self):
        """Short content sends as one message."""
        relay = _import_relay()
        sent = []
        setattr(relay, "_send_message", lambda text: sent.append(text) or True)
        relay._send_batched(["short line"])
        assert len(sent) == 1
        assert sent[0] == "short line"

    def test_splits_at_4000_chars(self):
        """Lines exceeding 4000 chars are split across multiple messages."""
        relay = _import_relay()
        sent = []
        setattr(relay, "_send_message", lambda text: sent.append(text) or True)
        lines = [f"line-{i:04d}-" + "x" * 90 for i in range(50)]
        relay._send_batched(lines)
        assert len(sent) > 1
        for msg in sent:
            assert len(msg) <= relay.TELEGRAM_MAX_LENGTH + 200

    def test_empty_lines_sends_nothing(self):
        """Empty list sends no messages."""
        relay = _import_relay()
        sent = []
        setattr(relay, "_send_message", lambda text: sent.append(text) or True)
        relay._send_batched([])
        assert len(sent) == 0


# ---------------------------------------------------------------------------
# Flood cap
# ---------------------------------------------------------------------------


class TestFloodCap:
    """Test flood cap truncation."""

    def test_under_cap_sends_all(self):
        """Lines under FLOOD_CAP are all delivered."""
        relay = _import_relay()
        setattr(relay, "_bot_token", "t")
        setattr(relay, "_chat_id", 1)
        sent = []
        setattr(relay, "_send_batched", lambda lines: sent.extend(lines))
        relay._buffer.extend([f"line {i}" for i in range(100)])
        setattr(relay, "_RELAY_ACTIVE", True)
        relay._flush_buffer()
        assert len(sent) == 100

    def test_over_cap_truncates_with_notice(self):
        """Lines over FLOOD_CAP are truncated with a suppression notice."""
        relay = _import_relay()
        setattr(relay, "_bot_token", "t")
        setattr(relay, "_chat_id", 1)
        sent_lines = []
        setattr(relay, "_send_batched", lambda lines: sent_lines.extend(lines))
        relay._buffer.extend([f"line {i}" for i in range(200)])
        setattr(relay, "_RELAY_ACTIVE", True)
        relay._flush_buffer()
        assert len(sent_lines) == relay.FLOOD_CAP + 1
        assert "50 more suppressed" in sent_lines[-1]


# ---------------------------------------------------------------------------
# _render_event calls relay_event
# ---------------------------------------------------------------------------


class TestRenderEventCallsRelay:
    """Test that monitor._render_event calls relay_event."""

    def test_render_event_calls_relay(self):
        """_render_event in monitor.py calls relay_event after console render."""
        fresh_mocks = {
            "aipass.prax.apps.handlers.monitoring": MagicMock(),
            "aipass.prax.apps.handlers.monitoring.event_queue": MagicMock(),
            "aipass.prax.apps.handlers.monitoring.filesystem_handler": MagicMock(),
            "aipass.prax.apps.handlers.monitoring.log_watcher": MagicMock(),
            "aipass.prax.apps.handlers.monitoring.unified_stream": MagicMock(),
            "aipass.prax.apps.handlers.monitoring.module_tracker": MagicMock(),
            "aipass.prax.apps.handlers.monitoring.branch_detector": MagicMock(),
            "aipass.prax.apps.handlers.monitoring.interactive_filter": MagicMock(),
            "aipass.prax.apps.handlers.monitoring.monitoring_filters": MagicMock(),
            "aipass.prax.apps.handlers.monitoring.file_watcher_integration": MagicMock(),
            "aipass.prax.apps.handlers.monitoring.telegram_relay": MagicMock(),
        }
        with patch.dict(sys.modules, fresh_mocks):
            if "aipass.prax.apps.modules.monitor" in sys.modules:
                mod = importlib.reload(sys.modules["aipass.prax.apps.modules.monitor"])
            else:
                mod = importlib.import_module("aipass.prax.apps.modules.monitor")

        event = MagicMock()
        event.event_type = "log"
        event.branch = "TEST"
        event.message = "hello"
        event.level = "info"
        event.action = ""

        with patch.object(mod, "_get_pid_for_branch", return_value=None):
            mod._render_event(event)

        mod.relay_event.assert_called_once_with(event)


# ---------------------------------------------------------------------------
# is_relay_enabled_by_env
# ---------------------------------------------------------------------------


class TestRelayEnabledByEnv:
    """Test environment variable detection."""

    def test_not_set(self):
        """Unset env var returns False."""
        relay = _import_relay()
        with patch.dict("os.environ", {}, clear=True):
            assert relay.is_relay_enabled_by_env() is False

    def test_set_to_1(self):
        """AIPASS_PRAX_MONITOR_RELAY=1 returns True."""
        relay = _import_relay()
        with patch.dict("os.environ", {"AIPASS_PRAX_MONITOR_RELAY": "1"}):
            assert relay.is_relay_enabled_by_env() is True

    def test_set_to_true(self):
        """AIPASS_PRAX_MONITOR_RELAY=true returns True."""
        relay = _import_relay()
        with patch.dict("os.environ", {"AIPASS_PRAX_MONITOR_RELAY": "true"}):
            assert relay.is_relay_enabled_by_env() is True

    def test_set_to_yes(self):
        """AIPASS_PRAX_MONITOR_RELAY=yes returns True."""
        relay = _import_relay()
        with patch.dict("os.environ", {"AIPASS_PRAX_MONITOR_RELAY": "yes"}):
            assert relay.is_relay_enabled_by_env() is True

    def test_set_to_0(self):
        """AIPASS_PRAX_MONITOR_RELAY=0 returns False."""
        relay = _import_relay()
        with patch.dict("os.environ", {"AIPASS_PRAX_MONITOR_RELAY": "0"}):
            assert relay.is_relay_enabled_by_env() is False
