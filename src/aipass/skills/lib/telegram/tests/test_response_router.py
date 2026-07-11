# =================== AIPass ====================
# Name: test_response_router.py
# Description: Comprehensive tests for response_router module
# Version: 1.0.0
# Created: 2026-06-15
# Modified: 2026-06-15
# =============================================

"""
Comprehensive tests for response_router.py

Tests cover:
1. is_cwd_in_tree - directory tree matching via relative_to()
2. is_tmux_alive - tmux session existence checks (mocked subprocess)
3. is_pending_expired - TTL + tmux expiry logic
4. find_pending_bot - multi-priority pending file matching (P1/P2/P3)
5. clean_expired_pending - removal of expired files, preservation of valid ones
"""

import json
import subprocess
import time
from pathlib import Path

import pytest
from unittest.mock import MagicMock

import aipass.skills.lib.telegram.apps.handlers.response_router as response_router


# =============================================
# FIXTURES
# =============================================


@pytest.fixture
def pending_dir(tmp_path, monkeypatch):
    """Override PENDING_DIR to use a temp directory."""
    pd = tmp_path / "telegram_pending"
    pd.mkdir()
    monkeypatch.setattr(response_router, "PENDING_DIR", pd)
    return pd


@pytest.fixture
def fresh_timestamp():
    """Return a timestamp within TTL (now)."""
    return time.time()


@pytest.fixture
def stale_timestamp():
    """Return a timestamp well past TTL."""
    return time.time() - response_router.PENDING_TTL - 600


def _write_pending(pending_dir, filename, data):
    """Helper to write a pending JSON file."""
    path = pending_dir / filename
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# =============================================
# 1. is_cwd_in_tree
# =============================================


class TestIsCwdInTree:
    """Test directory tree matching via relative_to()."""

    def test_exact_match(self):
        """CWD equals work_dir exactly."""
        cwd = Path("/home/aipass/aipass_os/dev_central")
        work_dir = "/home/aipass/aipass_os/dev_central"
        assert response_router.is_cwd_in_tree(cwd, work_dir) is True

    def test_subdirectory_match(self):
        """CWD is a subdirectory of work_dir."""
        cwd = Path("/home/aipass/aipass_os/dev_central/git_repo/subdir")
        work_dir = "/home/aipass/aipass_os/dev_central"
        assert response_router.is_cwd_in_tree(cwd, work_dir) is True

    def test_immediate_child(self):
        """CWD is an immediate child of work_dir."""
        cwd = Path("/home/aipass/aipass_os/dev_central/apps")
        work_dir = "/home/aipass/aipass_os/dev_central"
        assert response_router.is_cwd_in_tree(cwd, work_dir) is True

    def test_non_match_sibling(self):
        """CWD is a sibling directory, not a child."""
        cwd = Path("/home/aipass/aipass_os/cortex")
        work_dir = "/home/aipass/aipass_os/dev_central"
        assert response_router.is_cwd_in_tree(cwd, work_dir) is False

    def test_non_match_parent(self):
        """CWD is a parent of work_dir (not a child)."""
        cwd = Path("/home/aipass/aipass_os")
        work_dir = "/home/aipass/aipass_os/dev_central"
        assert response_router.is_cwd_in_tree(cwd, work_dir) is False

    def test_unrelated_paths(self):
        """Completely unrelated paths."""
        cwd = Path("/tmp/some/random/dir")
        work_dir = "/home/aipass/aipass_os/dev_central"
        assert response_router.is_cwd_in_tree(cwd, work_dir) is False

    def test_root_work_dir(self):
        """work_dir is root - everything is a child."""
        cwd = Path("/home/aipass/anything")
        work_dir = "/"
        assert response_router.is_cwd_in_tree(cwd, work_dir) is True

    def test_work_dir_as_path_object(self):
        """work_dir can be a Path object too."""
        cwd = Path("/home/aipass/branch/sub")
        work_dir = Path("/home/aipass/branch")
        assert response_router.is_cwd_in_tree(cwd, work_dir) is True

    def test_similar_prefix_no_match(self):
        """Paths with similar prefix but not actual parent-child."""
        cwd = Path("/home/aipass/dev_central_extra/sub")
        work_dir = "/home/aipass/dev_central"
        assert response_router.is_cwd_in_tree(cwd, work_dir) is False


# =============================================
# 2. is_tmux_alive
# =============================================


class TestIsTmuxAlive:
    """Test tmux session existence checks with mocked subprocess."""

    def test_session_alive(self, monkeypatch):
        """tmux has-session returns 0 -> session alive."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run = MagicMock(return_value=mock_result)
        monkeypatch.setattr(subprocess, "run", mock_run)

        assert response_router.is_tmux_alive("telegram-dev_central") is True
        mock_run.assert_called_once_with(
            ["tmux", "has-session", "-t", "telegram-dev_central"],
            capture_output=True,
            text=True,
            timeout=5,
        )

    def test_session_dead(self, monkeypatch):
        """tmux has-session returns non-zero -> session dead."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run = MagicMock(return_value=mock_result)
        monkeypatch.setattr(subprocess, "run", mock_run)

        assert response_router.is_tmux_alive("telegram-dev_central") is False

    def test_subprocess_timeout(self, monkeypatch):
        """subprocess.run raises TimeoutExpired -> treated as dead."""
        mock_run = MagicMock(side_effect=subprocess.TimeoutExpired(cmd="tmux", timeout=5))
        monkeypatch.setattr(subprocess, "run", mock_run)

        assert response_router.is_tmux_alive("telegram-test") is False

    def test_os_error(self, monkeypatch):
        """subprocess.run raises OSError (tmux not installed) -> treated as dead."""
        mock_run = MagicMock(side_effect=OSError("No such file or directory"))
        monkeypatch.setattr(subprocess, "run", mock_run)

        assert response_router.is_tmux_alive("telegram-test") is False


# =============================================
# 3. is_pending_expired
# =============================================


class TestIsPendingExpired:
    """Test pending file expiry: expired only when BOTH TTL exceeded AND tmux dead."""

    def test_within_ttl(self, monkeypatch):
        """Timestamp within TTL -> not expired regardless of tmux."""
        data = {
            "bot_id": "dev_central",
            "timestamp": time.time(),  # fresh
        }
        # tmux is dead, but TTL not exceeded -> not expired
        monkeypatch.setattr(response_router, "is_tmux_alive", lambda s: False)
        assert response_router.is_pending_expired(data) is False

    def test_past_ttl_tmux_alive(self, monkeypatch):
        """Past TTL but tmux alive -> not expired."""
        data = {
            "bot_id": "dev_central",
            "timestamp": time.time() - response_router.PENDING_TTL - 100,
        }
        monkeypatch.setattr(response_router, "is_tmux_alive", lambda s: True)
        assert response_router.is_pending_expired(data) is False

    def test_past_ttl_tmux_dead(self, monkeypatch):
        """Past TTL AND tmux dead -> expired."""
        data = {
            "bot_id": "dev_central",
            "timestamp": time.time() - response_router.PENDING_TTL - 100,
        }
        monkeypatch.setattr(response_router, "is_tmux_alive", lambda s: False)
        assert response_router.is_pending_expired(data) is True

    def test_past_ttl_branch_name_tmux_alive(self, monkeypatch):
        """v1 format: past TTL but branch tmux alive -> not expired."""
        data = {
            "branch_name": "cortex",
            "timestamp": time.time() - response_router.PENDING_TTL - 100,
        }
        monkeypatch.setattr(
            response_router,
            "is_tmux_alive",
            lambda s: s == "telegram-cortex",
        )
        assert response_router.is_pending_expired(data) is False

    def test_past_ttl_branch_name_tmux_dead(self, monkeypatch):
        """v1 format: past TTL AND branch tmux dead -> expired."""
        data = {
            "branch_name": "cortex",
            "timestamp": time.time() - response_router.PENDING_TTL - 100,
        }
        monkeypatch.setattr(response_router, "is_tmux_alive", lambda s: False)
        assert response_router.is_pending_expired(data) is True

    def test_missing_timestamp_treated_as_epoch_zero(self, monkeypatch):
        """No timestamp field -> defaults to 0, well past TTL."""
        data = {"bot_id": "test"}
        monkeypatch.setattr(response_router, "is_tmux_alive", lambda s: False)
        assert response_router.is_pending_expired(data) is True

    def test_string_timestamp(self, monkeypatch):
        """Timestamp as string is converted to float."""
        data = {
            "bot_id": "dev_central",
            "timestamp": str(time.time()),  # string, but fresh
        }
        monkeypatch.setattr(response_router, "is_tmux_alive", lambda s: False)
        assert response_router.is_pending_expired(data) is False

    def test_invalid_string_timestamp(self, monkeypatch):
        """Invalid string timestamp defaults to 0 -> past TTL."""
        data = {
            "bot_id": "test",
            "timestamp": "not-a-number",
        }
        monkeypatch.setattr(response_router, "is_tmux_alive", lambda s: False)
        assert response_router.is_pending_expired(data) is True

    def test_bot_id_and_branch_name_both_present(self, monkeypatch):
        """Both bot_id and branch_name: if bot_id tmux alive -> not expired."""
        data = {
            "bot_id": "dev_central",
            "branch_name": "dev_central",
            "timestamp": time.time() - response_router.PENDING_TTL - 100,
        }
        # bot_id tmux is alive
        monkeypatch.setattr(
            response_router,
            "is_tmux_alive",
            lambda s: s == "telegram-dev_central",
        )
        assert response_router.is_pending_expired(data) is False

    def test_bot_id_and_branch_name_different(self, monkeypatch):
        """Different bot_id and branch_name: checks both tmux sessions."""
        calls = []

        def mock_tmux(session_name):
            """Record call and return False (dead session)."""
            calls.append(session_name)
            return False

        data = {
            "bot_id": "new_id",
            "branch_name": "old_branch",
            "timestamp": time.time() - response_router.PENDING_TTL - 100,
        }
        monkeypatch.setattr(response_router, "is_tmux_alive", mock_tmux)
        assert response_router.is_pending_expired(data) is True
        # Should have checked both
        assert "telegram-new_id" in calls
        assert "telegram-old_branch" in calls


# =============================================
# 4. find_pending_bot
# =============================================


class TestFindPendingBot:
    """Test multi-priority pending file matching."""

    def test_p1_env_var_v2_match(self, pending_dir, fresh_timestamp, monkeypatch):
        """P1: AIPASS_BOT_ID env var finds bot-{id}.json directly."""
        _write_pending(
            pending_dir,
            "bot-dev_central.json",
            {
                "bot_id": "dev_central",
                "chat_id": 123,
                "bot_token": "tok",
                "work_dir": "/home/aipass/aipass_os/dev_central",
                "session_name": "telegram-dev_central",
                "timestamp": fresh_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: False)

        result = response_router.find_pending_bot(
            cwd=Path("/tmp/unrelated"),
            env_bot_id="dev_central",
        )
        assert result is not None
        assert result["bot_id"] == "dev_central"

    def test_p1_env_var_v1_fallback(self, pending_dir, fresh_timestamp, monkeypatch):
        """P1: AIPASS_BOT_ID with v1 naming telegram-{id}.json."""
        _write_pending(
            pending_dir,
            "telegram-dev_central.json",
            {
                "branch_name": "dev_central",
                "chat_id": 123,
                "bot_token": "tok",
                "session_id": "abc",
                "timestamp": fresh_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: False)

        result = response_router.find_pending_bot(
            cwd=Path("/tmp/unrelated"),
            env_bot_id="dev_central",
        )
        assert result is not None
        assert result["branch_name"] == "dev_central"

    def test_p1_env_var_expired_skipped(self, pending_dir, stale_timestamp, monkeypatch):
        """P1: Expired pending file is skipped even with env var match."""
        _write_pending(
            pending_dir,
            "bot-dev_central.json",
            {
                "bot_id": "dev_central",
                "chat_id": 123,
                "bot_token": "tok",
                "work_dir": "/home/aipass/aipass_os/dev_central",
                "timestamp": stale_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: True)

        result = response_router.find_pending_bot(
            cwd=Path("/tmp/unrelated"),
            env_bot_id="dev_central",
        )
        assert result is None

    def test_p2_cwd_tree_match(self, pending_dir, fresh_timestamp, monkeypatch):
        """P2: CWD is within a bot's work_dir tree."""
        _write_pending(
            pending_dir,
            "bot-dev_central.json",
            {
                "bot_id": "dev_central",
                "chat_id": 123,
                "bot_token": "tok",
                "work_dir": "/home/aipass/aipass_os/dev_central",
                "timestamp": fresh_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: False)

        # CWD is a subdirectory of work_dir
        result = response_router.find_pending_bot(
            cwd=Path("/home/aipass/aipass_os/dev_central/git_repo/subdir"),
            env_bot_id=None,
        )
        assert result is not None
        assert result["bot_id"] == "dev_central"

    def test_p2_cwd_exact_match(self, pending_dir, fresh_timestamp, monkeypatch):
        """P2: CWD exactly equals work_dir."""
        _write_pending(
            pending_dir,
            "bot-flow.json",
            {
                "bot_id": "flow",
                "chat_id": 456,
                "bot_token": "tok",
                "work_dir": "/home/aipass/aipass_os/flow",
                "timestamp": fresh_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: False)

        result = response_router.find_pending_bot(
            cwd=Path("/home/aipass/aipass_os/flow"),
            env_bot_id=None,
        )
        assert result is not None
        assert result["bot_id"] == "flow"

    def test_p2_legacy_branch_name_path_match(self, pending_dir, fresh_timestamp, monkeypatch):
        """P2: Legacy v1 file without work_dir matches branch_name in CWD path."""
        _write_pending(
            pending_dir,
            "telegram-cortex.json",
            {
                "branch_name": "cortex",
                "chat_id": 789,
                "bot_token": "tok",
                "session_id": "xyz",
                "timestamp": fresh_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: False)

        result = response_router.find_pending_bot(
            cwd=Path("/home/aipass/aipass_os/cortex/apps/modules"),
            env_bot_id=None,
        )
        assert result is not None
        assert result["branch_name"] == "cortex"

    def test_p3_session_id_fallback(self, pending_dir, fresh_timestamp, monkeypatch):
        """P3: session_id match when CWD and env var don't match."""
        _write_pending(
            pending_dir,
            "telegram-somebranch.json",
            {
                "branch_name": "somebranch",
                "chat_id": 999,
                "bot_token": "tok",
                "session_id": "my-session-123",
                "timestamp": fresh_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: False)

        result = response_router.find_pending_bot(
            cwd=Path("/tmp/completely/unrelated"),
            session_id="my-session-123",
            env_bot_id=None,
        )
        assert result is not None
        assert result["session_id"] == "my-session-123"

    def test_no_match_at_all(self, pending_dir, fresh_timestamp, monkeypatch):
        """No match across any priority -> returns None."""
        _write_pending(
            pending_dir,
            "bot-dev_central.json",
            {
                "bot_id": "dev_central",
                "chat_id": 123,
                "bot_token": "tok",
                "work_dir": "/home/aipass/aipass_os/dev_central",
                "session_id": "specific-session",
                "timestamp": fresh_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: False)

        result = response_router.find_pending_bot(
            cwd=Path("/tmp/wrong/place"),
            session_id="wrong-session-id",
            env_bot_id=None,
        )
        assert result is None

    def test_expired_skipped_in_p2(self, pending_dir, stale_timestamp, monkeypatch):
        """P2: Expired file is skipped during CWD matching."""
        _write_pending(
            pending_dir,
            "bot-dev_central.json",
            {
                "bot_id": "dev_central",
                "chat_id": 123,
                "bot_token": "tok",
                "work_dir": "/home/aipass/aipass_os/dev_central",
                "timestamp": stale_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: True)

        result = response_router.find_pending_bot(
            cwd=Path("/home/aipass/aipass_os/dev_central/git_repo"),
            env_bot_id=None,
        )
        assert result is None

    def test_expired_skipped_in_p3(self, pending_dir, stale_timestamp, monkeypatch):
        """P3: Expired file is skipped during session_id matching."""
        _write_pending(
            pending_dir,
            "telegram-branch.json",
            {
                "branch_name": "branch",
                "chat_id": 123,
                "bot_token": "tok",
                "session_id": "target-session",
                "timestamp": stale_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: True)

        result = response_router.find_pending_bot(
            cwd=Path("/tmp/unrelated"),
            session_id="target-session",
            env_bot_id=None,
        )
        assert result is None

    def test_pending_dir_missing(self, tmp_path, monkeypatch):
        """PENDING_DIR doesn't exist -> returns None."""
        monkeypatch.setattr(response_router, "PENDING_DIR", tmp_path / "nonexistent")
        result = response_router.find_pending_bot(cwd=Path("/tmp"), env_bot_id=None)
        assert result is None

    def test_p1_takes_priority_over_p2(self, pending_dir, fresh_timestamp, monkeypatch):
        """P1 match returns before P2 is evaluated."""
        # P1 target
        _write_pending(
            pending_dir,
            "bot-alpha.json",
            {
                "bot_id": "alpha",
                "chat_id": 111,
                "bot_token": "tok",
                "work_dir": "/home/aipass/aipass_os/alpha",
                "timestamp": fresh_timestamp,
            },
        )
        # P2 would also match this one
        _write_pending(
            pending_dir,
            "bot-beta.json",
            {
                "bot_id": "beta",
                "chat_id": 222,
                "bot_token": "tok",
                "work_dir": "/home/aipass/aipass_os/beta",
                "timestamp": fresh_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: False)

        # CWD matches beta's work_dir, but env_bot_id=alpha -> P1 wins
        result = response_router.find_pending_bot(
            cwd=Path("/home/aipass/aipass_os/beta/sub"),
            env_bot_id="alpha",
        )
        assert result is not None
        assert result["bot_id"] == "alpha"

    def test_env_bot_id_defaults_to_env_var(self, pending_dir, fresh_timestamp, monkeypatch):
        """When env_bot_id is None, reads from AIPASS_BOT_ID env var."""
        _write_pending(
            pending_dir,
            "bot-from_env.json",
            {
                "bot_id": "from_env",
                "chat_id": 333,
                "bot_token": "tok",
                "work_dir": "/some/path",
                "timestamp": fresh_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: False)
        monkeypatch.setenv("AIPASS_BOT_ID", "from_env")

        result = response_router.find_pending_bot(
            cwd=Path("/tmp/unrelated"),
        )
        assert result is not None
        assert result["bot_id"] == "from_env"

    def test_no_env_var_set(self, pending_dir, fresh_timestamp, monkeypatch):
        """When AIPASS_BOT_ID is not set, P1 is skipped."""
        _write_pending(
            pending_dir,
            "bot-dev_central.json",
            {
                "bot_id": "dev_central",
                "chat_id": 123,
                "bot_token": "tok",
                "work_dir": "/home/aipass/aipass_os/dev_central",
                "timestamp": fresh_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: False)
        monkeypatch.delenv("AIPASS_BOT_ID", raising=False)

        # CWD doesn't match, no session_id -> no match
        result = response_router.find_pending_bot(
            cwd=Path("/tmp/unrelated"),
            env_bot_id=None,
        )
        assert result is None

    def test_pending_path_included_in_result(self, pending_dir, fresh_timestamp, monkeypatch):
        """Result dict includes 'pending_path' key with full file path."""
        _write_pending(
            pending_dir,
            "bot-test.json",
            {
                "bot_id": "test",
                "chat_id": 123,
                "bot_token": "tok",
                "work_dir": "/home/aipass/test",
                "timestamp": fresh_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: False)

        result = response_router.find_pending_bot(
            cwd=Path("/tmp"),
            env_bot_id="test",
        )
        assert result is not None
        assert "pending_path" in result
        assert result["pending_path"] == str(pending_dir / "bot-test.json")

    def test_corrupt_json_file_skipped(self, pending_dir, fresh_timestamp, monkeypatch):
        """Corrupt JSON file doesn't crash, is skipped."""
        # Write a valid file
        _write_pending(
            pending_dir,
            "bot-good.json",
            {
                "bot_id": "good",
                "chat_id": 123,
                "bot_token": "tok",
                "work_dir": "/home/aipass/good",
                "timestamp": fresh_timestamp,
            },
        )
        # Write corrupt file
        (pending_dir / "bot-bad.json").write_text("NOT VALID JSON{{{", encoding="utf-8")
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: False)

        result = response_router.find_pending_bot(
            cwd=Path("/home/aipass/good/sub"),
            env_bot_id=None,
        )
        # Should still find the good file
        assert result is not None
        assert result["bot_id"] == "good"

    def test_multiple_bots_cwd_picks_first_match(self, pending_dir, fresh_timestamp, monkeypatch):
        """When multiple bots could match CWD, first found wins."""
        # Both have overlapping work_dirs (parent contains child)
        _write_pending(
            pending_dir,
            "bot-parent.json",
            {
                "bot_id": "parent",
                "chat_id": 111,
                "bot_token": "tok",
                "work_dir": "/home/aipass",
                "timestamp": fresh_timestamp,
            },
        )
        _write_pending(
            pending_dir,
            "bot-child.json",
            {
                "bot_id": "child",
                "chat_id": 222,
                "bot_token": "tok",
                "work_dir": "/home/aipass/child",
                "timestamp": fresh_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: False)

        result = response_router.find_pending_bot(
            cwd=Path("/home/aipass/child/deep"),
            env_bot_id=None,
        )
        # We get a match (either one is valid)
        assert result is not None
        assert result["bot_id"] in ("parent", "child")


# =============================================
# 5. clean_expired_pending
# =============================================


class TestCleanExpiredPending:
    """Test cleanup of expired pending files."""

    def test_removes_expired_files(self, pending_dir, stale_timestamp, monkeypatch):
        """Expired files are deleted."""
        _write_pending(
            pending_dir,
            "bot-old.json",
            {
                "bot_id": "old",
                "chat_id": 123,
                "bot_token": "tok",
                "work_dir": "/home/aipass/old",
                "timestamp": stale_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: True)

        removed = response_router.clean_expired_pending()
        assert removed == 1
        assert not (pending_dir / "bot-old.json").exists()

    def test_keeps_valid_files(self, pending_dir, fresh_timestamp, monkeypatch):
        """Non-expired files are preserved."""
        _write_pending(
            pending_dir,
            "bot-fresh.json",
            {
                "bot_id": "fresh",
                "chat_id": 123,
                "bot_token": "tok",
                "work_dir": "/home/aipass/fresh",
                "timestamp": fresh_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: False)

        removed = response_router.clean_expired_pending()
        assert removed == 0
        assert (pending_dir / "bot-fresh.json").exists()

    def test_mixed_expired_and_valid(self, pending_dir, fresh_timestamp, stale_timestamp, monkeypatch):
        """Only expired files removed, valid ones kept."""
        _write_pending(
            pending_dir,
            "bot-keep.json",
            {
                "bot_id": "keep",
                "chat_id": 111,
                "bot_token": "tok",
                "work_dir": "/home/aipass/keep",
                "timestamp": fresh_timestamp,
            },
        )
        _write_pending(
            pending_dir,
            "bot-remove.json",
            {
                "bot_id": "remove",
                "chat_id": 222,
                "bot_token": "tok",
                "work_dir": "/home/aipass/remove",
                "timestamp": stale_timestamp,
            },
        )

        def mock_expired(data):
            """Return True only for the bot marked for removal."""
            return data.get("bot_id") == "remove"

        monkeypatch.setattr(response_router, "is_pending_expired", mock_expired)

        removed = response_router.clean_expired_pending()
        assert removed == 1
        assert (pending_dir / "bot-keep.json").exists()
        assert not (pending_dir / "bot-remove.json").exists()

    def test_removes_corrupt_files(self, pending_dir, monkeypatch):
        """Corrupt (unparseable) files are also removed."""
        (pending_dir / "bot-corrupt.json").write_text("{{{INVALID", encoding="utf-8")

        removed = response_router.clean_expired_pending()
        assert removed == 1
        assert not (pending_dir / "bot-corrupt.json").exists()

    def test_removes_non_dict_json(self, pending_dir, monkeypatch):
        """JSON that parses to non-dict (e.g., a list) is treated as corrupt."""
        (pending_dir / "bot-list.json").write_text("[1, 2, 3]", encoding="utf-8")

        removed = response_router.clean_expired_pending()
        assert removed == 1
        assert not (pending_dir / "bot-list.json").exists()

    def test_handles_missing_dir(self, tmp_path, monkeypatch):
        """PENDING_DIR doesn't exist -> returns 0, no error."""
        monkeypatch.setattr(response_router, "PENDING_DIR", tmp_path / "nonexistent")
        removed = response_router.clean_expired_pending()
        assert removed == 0

    def test_handles_v1_and_v2_files(self, pending_dir, stale_timestamp, monkeypatch):
        """Both v1 (telegram-*) and v2 (bot-*) files are cleaned."""
        _write_pending(
            pending_dir,
            "bot-v2bot.json",
            {
                "bot_id": "v2bot",
                "chat_id": 123,
                "bot_token": "tok",
                "work_dir": "/home/aipass/v2bot",
                "timestamp": stale_timestamp,
            },
        )
        _write_pending(
            pending_dir,
            "telegram-v1branch.json",
            {
                "branch_name": "v1branch",
                "chat_id": 456,
                "bot_token": "tok",
                "session_id": "sess",
                "timestamp": stale_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: True)

        removed = response_router.clean_expired_pending()
        assert removed == 2
        assert not (pending_dir / "bot-v2bot.json").exists()
        assert not (pending_dir / "telegram-v1branch.json").exists()

    def test_ignores_non_matching_filenames(self, pending_dir, monkeypatch):
        """Files that don't match bot-*.json or telegram-*.json are ignored."""
        (pending_dir / "random-file.json").write_text("{}", encoding="utf-8")
        (pending_dir / "notes.txt").write_text("hello", encoding="utf-8")
        monkeypatch.setattr(response_router, "is_pending_expired", lambda d: True)

        removed = response_router.clean_expired_pending()
        assert removed == 0
        # Both files still exist
        assert (pending_dir / "random-file.json").exists()
        assert (pending_dir / "notes.txt").exists()

    def test_returns_zero_on_empty_dir(self, pending_dir, monkeypatch):
        """Empty pending directory -> returns 0."""
        removed = response_router.clean_expired_pending()
        assert removed == 0


# =============================================
# EDGE CASES / INTEGRATION-STYLE
# =============================================


class TestEdgeCases:
    """Edge cases and integration-style tests."""

    def test_find_pending_bot_with_real_expiry_logic(self, pending_dir, monkeypatch):
        """Integration: find_pending_bot uses real is_pending_expired (mocked tmux)."""
        fresh_ts = time.time()
        _write_pending(
            pending_dir,
            "bot-live.json",
            {
                "bot_id": "live",
                "chat_id": 123,
                "bot_token": "tok",
                "work_dir": "/home/aipass/live",
                "timestamp": fresh_ts,
            },
        )
        # Mock tmux to be dead - but timestamp is fresh so file is not expired
        monkeypatch.setattr(response_router, "is_tmux_alive", lambda s: False)

        result = response_router.find_pending_bot(
            cwd=Path("/home/aipass/live/deep/path"),
            env_bot_id=None,
        )
        assert result is not None
        assert result["bot_id"] == "live"

    def test_find_pending_bot_stale_but_tmux_alive(self, pending_dir, monkeypatch):
        """Integration: stale timestamp but tmux alive keeps file valid."""
        stale_ts = time.time() - response_router.PENDING_TTL - 500
        _write_pending(
            pending_dir,
            "bot-running.json",
            {
                "bot_id": "running",
                "chat_id": 123,
                "bot_token": "tok",
                "work_dir": "/home/aipass/running",
                "timestamp": stale_ts,
            },
        )
        monkeypatch.setattr(
            response_router,
            "is_tmux_alive",
            lambda s: s == "telegram-running",
        )

        result = response_router.find_pending_bot(
            cwd=Path("/home/aipass/running"),
            env_bot_id=None,
        )
        assert result is not None
        assert result["bot_id"] == "running"

    def test_clean_then_find_returns_none(self, pending_dir, stale_timestamp, monkeypatch):
        """After cleaning expired files, find returns None for those bots."""
        _write_pending(
            pending_dir,
            "bot-dead.json",
            {
                "bot_id": "dead",
                "chat_id": 123,
                "bot_token": "tok",
                "work_dir": "/home/aipass/dead",
                "timestamp": stale_timestamp,
            },
        )
        monkeypatch.setattr(response_router, "is_tmux_alive", lambda s: False)

        # Clean first
        removed = response_router.clean_expired_pending()
        assert removed == 1

        # Now find should return None
        result = response_router.find_pending_bot(
            cwd=Path("/home/aipass/dead"),
            env_bot_id="dead",
        )
        assert result is None

    def test_pending_ttl_constant(self):
        """Verify PENDING_TTL is 3600 seconds (1 hour)."""
        assert response_router.PENDING_TTL == 3600
