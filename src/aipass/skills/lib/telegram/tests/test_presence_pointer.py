# =================== AIPass ====================
# Name: test_presence_pointer.py
# Description: Tests for CC-native session discovery (DPLAN-0226) + transcript tail
# Version: 2.0.0
# Created: 2026-06-29
# Modified: 2026-06-30
# =============================================

"""
Tests for CC-native session discovery (DPLAN-0226).

Covers:
  - _discover_cc_session: enumerate ~/.claude/sessions, filter cwd, validate PID
  - _is_pid_alive: PID liveness check
  - _find_tmux_pane_by_cwd: tmux pane CWD scan
  - _sanitize_path_for_cc: path sanitization for CC projects dir
  - _resolve_cc_transcript_path: transcript JSONL path from session info
  - _extract_assistant_text / _read_transcript_tail: transcript parsing
  - ensure_tmux_session: CC-native-first resolution, legacy spawn retired
  - handle_message: no-session error message
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from apps.handlers.base_bot import BaseBot  # type: ignore[import-not-found]


# =============================================
# Fixtures
# =============================================


@pytest.fixture
def _patch_base_bot_deps(tmp_path):
    """Patch signal and atexit for safe BaseBot construction."""
    patches = [
        patch("apps.handlers.base_bot.PENDING_DIR", tmp_path),
        patch("apps.handlers.base_bot.signal.signal"),
        patch("apps.handlers.base_bot.atexit.register"),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


def _make_bot(tmp_path, _patch_base_bot_deps, branch_name="devpulse"):
    """Create a BaseBot with test defaults."""
    workdir = tmp_path / "workdir"
    workdir.mkdir(exist_ok=True)
    with patch("apps.handlers.base_bot.PENDING_DIR", tmp_path):
        bot = BaseBot(
            bot_id="cc_test",
            bot_token="123:FAKETOKEN",
            work_dir=workdir,
            bot_name="CC Discovery Test Bot",
            allowed_user_ids=[111],
            branch_name=branch_name,
        )
    bot.send_message = MagicMock(return_value={"ok": True, "message_id": 1})
    return bot


def _write_cc_session(sessions_dir, pid, cwd, session_id="sess-001", started_at=1000, **extra):
    """Write a CC session file at sessions_dir/<pid>.json."""
    sessions_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "pid": pid,
        "sessionId": session_id,
        "cwd": cwd,
        "startedAt": started_at,
        "kind": "interactive",
        "name": "test-session",
        **extra,
    }
    f = sessions_dir / f"{pid}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def _write_transcript(projects_dir, cwd, session_id, lines):
    """Write a transcript JSONL file at the CC-native path."""
    slug = BaseBot._sanitize_path_for_cc(cwd)
    transcript_dir = projects_dir / slug
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript_file = transcript_dir / f"{session_id}.jsonl"
    transcript_file.write_text("\n".join(json.dumps(item) for item in lines), encoding="utf-8")
    return transcript_file


# =============================================
# 1. _discover_cc_session
# =============================================


class TestDiscoverCcSession:
    """Enumerate ~/.claude/sessions, filter cwd, validate PID."""

    def test_discovers_live_session(self, tmp_path, _patch_base_bot_deps):
        """Finds a live session whose cwd matches the bot work directory."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        sessions_dir = tmp_path / "sessions"
        _write_cc_session(sessions_dir, os.getpid(), str(bot.work_dir.resolve()))
        with patch("apps.handlers.base_bot.CC_SESSIONS_DIR", sessions_dir):
            result = bot._discover_cc_session()
        assert result is not None
        assert result["pid"] == os.getpid()
        assert result["sessionId"] == "sess-001"

    def test_returns_none_when_no_sessions_dir(self, tmp_path, _patch_base_bot_deps):
        """Returns None when the sessions directory does not exist."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        fake_dir = tmp_path / "no_such_dir"
        with patch("apps.handlers.base_bot.CC_SESSIONS_DIR", fake_dir):
            result = bot._discover_cc_session()
        assert result is None

    def test_returns_none_when_no_matching_cwd(self, tmp_path, _patch_base_bot_deps):
        """Returns None when no session file has a matching cwd."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        sessions_dir = tmp_path / "sessions"
        _write_cc_session(sessions_dir, os.getpid(), "/some/other/dir")
        with patch("apps.handlers.base_bot.CC_SESSIONS_DIR", sessions_dir):
            result = bot._discover_cc_session()
        assert result is None

    def test_returns_none_for_dead_pid(self, tmp_path, _patch_base_bot_deps):
        """Returns None when the session PID is no longer alive."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        sessions_dir = tmp_path / "sessions"
        _write_cc_session(sessions_dir, 99999999, str(bot.work_dir.resolve()))
        with patch("apps.handlers.base_bot.CC_SESSIONS_DIR", sessions_dir):
            result = bot._discover_cc_session()
        assert result is None

    def test_picks_latest_when_multiple(self, tmp_path, _patch_base_bot_deps):
        """Selects the session with the highest startedAt when multiple match."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        sessions_dir = tmp_path / "sessions"
        cwd = str(bot.work_dir.resolve())
        my_pid = os.getpid()
        _write_cc_session(sessions_dir, my_pid, cwd, session_id="old", started_at=100)
        _write_cc_session(sessions_dir, my_pid + 1, cwd, session_id="new", started_at=200)
        with (
            patch("apps.handlers.base_bot.CC_SESSIONS_DIR", sessions_dir),
            patch.object(BaseBot, "_is_pid_alive", return_value=True),
        ):
            result = bot._discover_cc_session()
        assert result is not None
        assert result["sessionId"] == "new"

    def test_skips_non_json_files(self, tmp_path, _patch_base_bot_deps):
        """Ignores non-JSON files and files without numeric PID names."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir(parents=True)
        (sessions_dir / "readme.txt").write_text("ignore me")
        (sessions_dir / "notapid.json").write_text("{}")
        with patch("apps.handlers.base_bot.CC_SESSIONS_DIR", sessions_dir):
            result = bot._discover_cc_session()
        assert result is None

    def test_skips_corrupt_json(self, tmp_path, _patch_base_bot_deps):
        """Gracefully skips session files containing invalid JSON."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir(parents=True)
        (sessions_dir / "12345.json").write_text("not json!")
        with patch("apps.handlers.base_bot.CC_SESSIONS_DIR", sessions_dir):
            result = bot._discover_cc_session()
        assert result is None

    def test_resolves_symlinked_cwd(self, tmp_path, _patch_base_bot_deps):
        """Resolved paths match even through symlinks."""
        real_dir = tmp_path / "real_workdir"
        real_dir.mkdir()
        link = tmp_path / "link_workdir"
        link.symlink_to(real_dir)
        with patch("apps.handlers.base_bot.PENDING_DIR", tmp_path):
            bot = BaseBot(
                bot_id="sym_test",
                bot_token="t",
                work_dir=link,
                branch_name="test",
            )
        sessions_dir = tmp_path / "sessions"
        _write_cc_session(sessions_dir, os.getpid(), str(real_dir))
        with patch("apps.handlers.base_bot.CC_SESSIONS_DIR", sessions_dir):
            result = bot._discover_cc_session()
        assert result is not None


# =============================================
# 2. _is_pid_alive
# =============================================


class TestIsPidAlive:
    """PID liveness check via os.kill(pid, 0)."""

    def test_own_pid_is_alive(self):
        """Reports the current process PID as alive."""
        assert BaseBot._is_pid_alive(os.getpid()) is True

    def test_dead_pid(self):
        """Reports a non-existent PID as dead."""
        assert BaseBot._is_pid_alive(99999999) is False

    def test_zero_pid(self):
        """Reports PID zero as dead."""
        assert BaseBot._is_pid_alive(0) is False

    def test_negative_pid(self):
        """Reports a negative PID as dead."""
        assert BaseBot._is_pid_alive(-1) is False

    def test_permission_error_treated_as_alive(self):
        """Treats PermissionError from os.kill as evidence the PID is alive."""
        with patch("os.kill", side_effect=PermissionError("denied")):
            assert BaseBot._is_pid_alive(42) is True

    def test_os_error_treated_as_dead(self):
        """Treats a generic OSError from os.kill as evidence the PID is dead."""
        with patch("os.kill", side_effect=OSError("some error")):
            assert BaseBot._is_pid_alive(42) is False


# =============================================
# 3. _find_tmux_pane_by_cwd
# =============================================


class TestFindTmuxPaneByCwd:
    """Find tmux session with a pane whose CWD matches work_dir."""

    def test_finds_matching_pane(self, tmp_path, _patch_base_bot_deps):
        """Returns the tmux session name whose pane cwd matches work_dir."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        workdir = str(bot.work_dir.resolve())
        pane_output = f"my-session:{workdir}\nother:{tmp_path}\n"
        with patch(
            "subprocess.run",
            return_value=MagicMock(returncode=0, stdout=pane_output),
        ):
            result = bot._find_tmux_pane_by_cwd()
        assert result == "my-session"

    def test_returns_none_when_no_match(self, tmp_path, _patch_base_bot_deps):
        """Returns None when no tmux pane cwd matches the bot work directory."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        pane_output = f"session1:{tmp_path / 'other'}\n"
        with patch(
            "subprocess.run",
            return_value=MagicMock(returncode=0, stdout=pane_output),
        ):
            result = bot._find_tmux_pane_by_cwd()
        assert result is None

    def test_returns_none_when_tmux_unavailable(self, tmp_path, _patch_base_bot_deps):
        """Returns None when the tmux binary is not found."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch("subprocess.run", side_effect=FileNotFoundError("tmux")):
            result = bot._find_tmux_pane_by_cwd()
        assert result is None

    def test_returns_none_when_tmux_fails(self, tmp_path, _patch_base_bot_deps):
        """Returns None when the tmux list-panes command exits with failure."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            result = bot._find_tmux_pane_by_cwd()
        assert result is None


# =============================================
# 4. _sanitize_path_for_cc
# =============================================


class TestSanitizePathForCc:
    """Path sanitization: every non-alphanumeric char becomes '-'."""

    def test_basic_path(self):
        """Slashes become dashes."""
        assert BaseBot._sanitize_path_for_cc("/opt/work/project") == "-opt-work-project"

    def test_dots_and_underscores(self):
        """Dots and underscores become dashes."""
        assert BaseBot._sanitize_path_for_cc("/opt/work/.my_project") == "-opt-work--my-project"

    def test_backslashes(self):
        """Backslashes become dashes."""
        assert BaseBot._sanitize_path_for_cc("D:\\Work\\project") == "D--Work-project"

    def test_alphanumeric_preserved(self):
        """Alphanumeric characters are kept as-is."""
        assert BaseBot._sanitize_path_for_cc("abc123XYZ") == "abc123XYZ"


# =============================================
# 5. _resolve_cc_transcript_path
# =============================================


class TestResolveCcTranscriptPath:
    """Resolve transcript JSONL path from CC session info."""

    def test_resolves_existing_transcript(self, tmp_path, _patch_base_bot_deps):
        """Returns the transcript path when the JSONL file exists on disk."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        cwd = str(bot.work_dir.resolve())
        session = {"sessionId": "abc-123", "cwd": cwd}
        slug = BaseBot._sanitize_path_for_cc(cwd)
        transcript_dir = tmp_path / ".claude" / "projects" / slug
        transcript_dir.mkdir(parents=True)
        transcript_file = transcript_dir / "abc-123.jsonl"
        transcript_file.write_text("{}", encoding="utf-8")
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = bot._resolve_cc_transcript_path(session)
        assert result is not None
        assert result.name == "abc-123.jsonl"

    def test_returns_none_when_file_missing(self, tmp_path, _patch_base_bot_deps):
        """Returns None when the transcript JSONL file does not exist."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        session = {"sessionId": "nonexistent", "cwd": str(tmp_path)}
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = bot._resolve_cc_transcript_path(session)
        assert result is None

    def test_returns_none_when_no_session_id(self, tmp_path, _patch_base_bot_deps):
        """Returns None when the session dict lacks a sessionId key."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        result = bot._resolve_cc_transcript_path({"cwd": str(tmp_path)})
        assert result is None

    def test_returns_none_when_no_cwd(self, tmp_path, _patch_base_bot_deps):
        """Returns None when the session dict lacks a cwd key."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        result = bot._resolve_cc_transcript_path({"sessionId": "abc"})
        assert result is None


# =============================================
# 6. _extract_assistant_text / _read_transcript_tail
# =============================================


class TestTranscriptParsing:
    """Extract assistant text from transcript JSONL entries."""

    def test_extract_text_from_text_block(self):
        """Extracts text from a content block with type 'text'."""
        entry = {"message": {"role": "assistant", "content": [{"type": "text", "text": "Hello world"}]}}
        assert BaseBot._extract_assistant_text(entry) == "Hello world"

    def test_extract_text_from_string_content(self):
        """Extracts text when content is a plain string instead of a list."""
        entry = {"message": {"role": "assistant", "content": "Plain text"}}
        assert BaseBot._extract_assistant_text(entry) == "Plain text"

    def test_returns_none_for_user_message(self):
        """Returns None for entries with role 'user'."""
        entry = {"message": {"role": "user", "content": "question"}}
        assert BaseBot._extract_assistant_text(entry) is None

    def test_returns_none_for_tool_use_only(self):
        """Returns None when content contains only tool_use blocks."""
        entry = {"message": {"role": "assistant", "content": [{"type": "tool_use", "id": "t1"}]}}
        assert BaseBot._extract_assistant_text(entry) is None

    def test_returns_none_for_empty_entry(self):
        """Returns None for an empty dict entry."""
        assert BaseBot._extract_assistant_text({}) is None

    def test_read_transcript_tail_finds_response(self, tmp_path, _patch_base_bot_deps):
        """Returns the last assistant text from the transcript tail."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        transcript = tmp_path / "transcript.jsonl"
        lines = [
            json.dumps({"message": {"role": "user", "content": "hi"}}),
            json.dumps({"message": {"role": "assistant", "content": [{"type": "text", "text": "Hello!"}]}}),
        ]
        transcript.write_text("\n".join(lines), encoding="utf-8")
        bot._active_transcript_path = transcript
        result = bot._read_transcript_tail()
        assert result == "Hello!"

    def test_read_transcript_tail_returns_none_when_no_path(self, tmp_path, _patch_base_bot_deps):
        """Returns None when no active transcript path is set."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot._active_transcript_path = None
        assert bot._read_transcript_tail() is None

    def test_read_transcript_tail_returns_none_when_file_missing(self, tmp_path, _patch_base_bot_deps):
        """Returns None when the transcript file does not exist on disk."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot._active_transcript_path = tmp_path / "nonexistent.jsonl"
        assert bot._read_transcript_tail() is None


# =============================================
# 7. ensure_tmux_session — CC-native-first
# =============================================


class TestEnsureWithCcDiscovery:
    """ensure_tmux_session follows CC-native session discovery first."""

    def test_attaches_via_cc_session(self, tmp_path, _patch_base_bot_deps):
        """Attaches to a live CC session and sets shared session state."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        workdir = str(bot.work_dir.resolve())
        session = {
            "pid": os.getpid(),
            "sessionId": "s1",
            "cwd": workdir,
            "startedAt": 1000,
            "name": "test",
        }
        pane_output = f"live-tmux:{workdir}\n"
        with (
            patch.object(bot, "_discover_cc_session", return_value=session),
            patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=pane_output)),
            patch.object(bot, "_resolve_cc_transcript_path", return_value=tmp_path / "t.jsonl"),
        ):
            result = bot.ensure_tmux_session()
        assert result is True
        assert bot.session_name == "live-tmux"
        assert bot._using_shared_session is True
        assert bot._active_session_id == "s1"

    def test_cc_no_tmux_pane_falls_through(self, tmp_path, _patch_base_bot_deps):
        """CC session found but no tmux pane → falls through to Strategy 2."""
        workdir = tmp_path / "workdir"
        workdir.mkdir(exist_ok=True)
        with patch("apps.handlers.base_bot.PENDING_DIR", tmp_path):
            bot = BaseBot(
                bot_id="fb_test",
                bot_token="t",
                work_dir=workdir,
                branch_name="devpulse",
                shared_session="explicit-session",
            )
        bot.send_message = MagicMock()
        session = {"pid": os.getpid(), "sessionId": "s1", "cwd": str(workdir.resolve()), "startedAt": 1000}
        with (
            patch.object(bot, "_discover_cc_session", return_value=session),
            patch.object(bot, "_find_tmux_pane_by_cwd", return_value=None),
            patch("subprocess.run", return_value=MagicMock(returncode=0)),
        ):
            result = bot.ensure_tmux_session()
        assert result is True
        assert bot.session_name == "explicit-session"

    def test_fallback_to_shared_session(self, tmp_path, _patch_base_bot_deps):
        """When CC discovery returns None, falls back to shared_session config."""
        workdir = tmp_path / "workdir"
        workdir.mkdir(exist_ok=True)
        with patch("apps.handlers.base_bot.PENDING_DIR", tmp_path):
            bot = BaseBot(
                bot_id="fb_test",
                bot_token="t",
                work_dir=workdir,
                branch_name="devpulse",
                shared_session="explicit-session",
            )
        bot.send_message = MagicMock()
        with (
            patch.object(bot, "_discover_cc_session", return_value=None),
            patch("subprocess.run", return_value=MagicMock(returncode=0)),
        ):
            result = bot.ensure_tmux_session()
        assert result is True
        assert bot.session_name == "explicit-session"

    def test_no_session_returns_false_never_spawns(self, tmp_path, _patch_base_bot_deps):
        """When no CC session and no shared session, returns False — never spawns."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        with (
            patch.object(bot, "_discover_cc_session", return_value=None),
            patch("subprocess.run", return_value=MagicMock(returncode=1)),
        ):
            result = bot.ensure_tmux_session()
        assert result is False
        assert bot._using_shared_session is False

    def test_rebinds_on_session_change(self, tmp_path, _patch_base_bot_deps):
        """Bot re-reads CC sessions on each call, rebinding to new session."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        workdir = str(bot.work_dir.resolve())
        pane_output = f"tmux-pane:{workdir}\n"

        session_v1 = {"pid": os.getpid(), "sessionId": "v1", "cwd": workdir, "startedAt": 100, "name": "v1"}
        session_v2 = {"pid": os.getpid(), "sessionId": "v2", "cwd": workdir, "startedAt": 200, "name": "v2"}

        with (
            patch.object(bot, "_discover_cc_session", return_value=session_v1),
            patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=pane_output)),
            patch.object(bot, "_resolve_cc_transcript_path", return_value=None),
        ):
            bot.ensure_tmux_session()
        assert bot._active_session_id == "v1"

        with (
            patch.object(bot, "_discover_cc_session", return_value=session_v2),
            patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=pane_output)),
            patch.object(bot, "_resolve_cc_transcript_path", return_value=None),
        ):
            bot.ensure_tmux_session()
        assert bot._active_session_id == "v2"

    def test_stores_transcript_path(self, tmp_path, _patch_base_bot_deps):
        """CC discovery stores the resolved transcript path on the bot."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        workdir = str(bot.work_dir.resolve())
        session = {"pid": os.getpid(), "sessionId": "s1", "cwd": workdir, "startedAt": 1000, "name": "t"}
        transcript = tmp_path / "transcript.jsonl"
        pane_output = f"tmux:{workdir}\n"
        with (
            patch.object(bot, "_discover_cc_session", return_value=session),
            patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=pane_output)),
            patch.object(bot, "_resolve_cc_transcript_path", return_value=transcript),
        ):
            bot.ensure_tmux_session()
        assert bot._active_transcript_path == transcript


# =============================================
# 8. handle_message — no-session error
# =============================================


class TestHandleMessageNoSession:
    """Error message when no live session is available."""

    def test_shows_branch_name_in_error(self, tmp_path, _patch_base_bot_deps):
        """Includes the branch name in the no-session error message."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps, branch_name="api")
        with (
            patch.object(bot, "_discover_cc_session", return_value=None),
            patch("subprocess.run", return_value=MagicMock(returncode=1)),
        ):
            bot.handle_message(42, "hello", {"message_id": 1})
        msg = bot.send_message.call_args[0][1]
        assert "No live Claude session" in msg
        assert "api" in msg

    def test_shows_work_dir_name_when_no_branch_name(self, tmp_path, _patch_base_bot_deps):
        """Falls back to work_dir name in the error when branch_name is None."""
        bot = _make_bot(tmp_path, _patch_base_bot_deps)
        bot.branch_name = None
        with (
            patch.object(bot, "_discover_cc_session", return_value=None),
            patch("subprocess.run", return_value=MagicMock(returncode=1)),
        ):
            bot.handle_message(42, "hello", {"message_id": 1})
        msg = bot.send_message.call_args[0][1]
        assert "No live Claude session" in msg
