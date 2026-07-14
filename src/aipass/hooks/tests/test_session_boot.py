"""Tests for session boot wrapper (menu-based attach/start/close)."""

from unittest.mock import MagicMock, patch

from aipass.hooks.apps.handlers.lifecycle import session_boot

_MOD = "aipass.hooks.apps.handlers.lifecycle.session_boot"


class TestResolveClaudeBinary:
    def test_found_on_path(self):
        with patch(f"{_MOD}.shutil.which", return_value="/usr/local/bin/claude"):
            assert session_boot._resolve_claude_binary() == "/usr/local/bin/claude"

    def test_not_found_fallback(self):
        with patch(f"{_MOD}.shutil.which", return_value=None):
            assert session_boot._resolve_claude_binary() == "claude"


class TestFindTmux:
    def test_found(self):
        with patch("shutil.which", return_value="/usr/bin/tmux"):
            assert session_boot._find_tmux() == "/usr/bin/tmux"

    def test_not_found(self):
        with patch("shutil.which", return_value=None):
            assert session_boot._find_tmux() is None


class TestTmuxSessionExists:
    def test_exists(self):
        with patch(f"{_MOD}.subprocess.run", return_value=MagicMock(returncode=0)):
            assert session_boot._tmux_session_exists("hooks") is True

    def test_not_exists(self):
        with patch(f"{_MOD}.subprocess.run", return_value=MagicMock(returncode=1)):
            assert session_boot._tmux_session_exists("hooks") is False


class TestFindTmuxSessionForPid:
    def test_finds_session(self):
        output = "1234 hooks\n5678 devpulse\n"
        with (
            patch(f"{_MOD}.subprocess.run", return_value=MagicMock(returncode=0, stdout=output)),
            patch.object(session_boot, "_is_descendant", side_effect=lambda t, a: t == 9999 and a == 1234),
        ):
            assert session_boot._find_tmux_session_for_pid(9999) == "hooks"

    def test_not_found(self):
        output = "1234 hooks\n"
        with (
            patch(f"{_MOD}.subprocess.run", return_value=MagicMock(returncode=0, stdout=output)),
            patch.object(session_boot, "_is_descendant", return_value=False),
        ):
            assert session_boot._find_tmux_session_for_pid(9999) is None

    def test_tmux_not_running(self):
        with patch(f"{_MOD}.subprocess.run", return_value=MagicMock(returncode=1)):
            assert session_boot._find_tmux_session_for_pid(9999) is None


class TestGetPpid:
    def test_returns_parent_pid(self):
        mock_result = MagicMock(returncode=0, stdout="  1234\n")
        with patch(f"{_MOD}.subprocess.run", return_value=mock_result):
            assert session_boot._get_ppid(5678) == 1234

    def test_returns_none_on_failure(self):
        mock_result = MagicMock(returncode=1, stdout="")
        with patch(f"{_MOD}.subprocess.run", return_value=mock_result):
            assert session_boot._get_ppid(5678) is None

    def test_returns_none_on_oserror(self):
        with patch(f"{_MOD}.subprocess.run", side_effect=OSError("no ps")):
            assert session_boot._get_ppid(5678) is None

    def test_returns_none_on_timeout(self):
        import subprocess

        with patch(f"{_MOD}.subprocess.run", side_effect=subprocess.TimeoutExpired("ps", 5)):
            assert session_boot._get_ppid(5678) is None


class TestIsDescendant:
    def test_direct_match(self):
        assert session_boot._is_descendant(100, 100) is True

    def test_pid_one_not_descendant(self):
        assert session_boot._is_descendant(1, 999) is False

    def test_walks_via_ps(self):
        def mock_ppid(pid):
            return {200: 150, 150: 100}.get(pid)

        with patch.object(session_boot, "_get_ppid", side_effect=mock_ppid):
            assert session_boot._is_descendant(200, 100) is True

    def test_not_descendant(self):
        def mock_ppid(pid):
            return {200: 150, 150: 1}.get(pid)

        with patch.object(session_boot, "_get_ppid", side_effect=mock_ppid):
            assert session_boot._is_descendant(200, 100) is False

    def test_ppid_none_stops_walk(self):
        with patch.object(session_boot, "_get_ppid", return_value=None):
            assert session_boot._is_descendant(200, 100) is False


class TestMakeSessionName:
    def test_with_session_id(self):
        assert session_boot._make_session_name("hooks", "abcdef1234") == "hooks-abcdef12"

    def test_without_session_id(self):
        assert session_boot._make_session_name("hooks") == "hooks"

    def test_empty_session_id(self):
        assert session_boot._make_session_name("hooks", "") == "hooks"


class TestSessionLabel:
    def test_formats_label(self):
        session = {"pid": 1234, "sessionId": "abcdef1234", "kind": "interactive"}
        label = session_boot._session_label(session, "hooks")
        assert "1234" in label
        assert "abcdef12" in label
        assert "interactive" in label


class TestBoot:
    def test_already_in_tmux_execs_directly(self, tmp_path):
        with (
            patch.dict("os.environ", {"TMUX": "/tmp/tmux-1000/default,123,0"}),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path))
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        assert args[0] == "/usr/local/bin/claude"
        assert "--permission-mode" in args[1]
        assert "bypassPermissions" in args[1]

    def test_already_in_tmux_passes_extra_args(self, tmp_path):
        with (
            patch.dict("os.environ", {"TMUX": "/tmp/tmux-1000/default,123,0"}),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path), extra_args=["--resume"])
        args = mock_exec.call_args[0][1]
        assert "--resume" in args

    def test_no_tmux_errors(self, tmp_path):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch.object(session_boot, "_find_tmux", return_value=None),
        ):
            result = session_boot.boot(cwd=str(tmp_path))
        assert result["exit_code"] == 1
        assert "tmux not found" in result["error"]

    def test_live_session_resume_via_tmux(self, tmp_path):
        live = [{"pid": 1234, "sessionId": "abc", "cwd": str(tmp_path), "kind": "interactive"}]
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch.object(session_boot, "_find_tmux", return_value="/usr/bin/tmux"),
            patch.object(session_boot, "_find_live_sessions", return_value=live),
            patch.object(session_boot, "_read_choice", return_value=""),
            patch.object(session_boot, "_find_tmux_session_for_pid", return_value="hooks"),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path))
        mock_exec.assert_called_once_with("tmux", ["tmux", "attach-session", "-t", "hooks"])

    def test_live_session_resume_continues_dead_window(self, tmp_path):
        live = [{"pid": 1234, "sessionId": "abc", "cwd": str(tmp_path), "kind": "interactive"}]
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch.object(session_boot, "_find_tmux", return_value="/usr/bin/tmux"),
            patch.object(session_boot, "_find_live_sessions", return_value=live),
            patch.object(session_boot, "_read_choice", return_value=""),
            patch.object(session_boot, "_find_tmux_session_for_pid", return_value=None),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path))
        args = mock_exec.call_args[0][1]
        assert "--continue" in args

    def test_live_session_resume_bg_opens_agents(self, tmp_path):
        live = [{"pid": 1234, "sessionId": "abc", "cwd": str(tmp_path), "kind": "bg"}]
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch.object(session_boot, "_find_tmux", return_value="/usr/bin/tmux"),
            patch.object(session_boot, "_find_live_sessions", return_value=live),
            patch.object(session_boot, "_read_choice", return_value=""),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path))
        args = mock_exec.call_args[0][1]
        assert "agents" in args

    def test_live_session_new_stops_old(self, tmp_path):
        live = [{"pid": 1234, "sessionId": "abc", "cwd": str(tmp_path), "kind": "interactive"}]
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch.object(session_boot, "_find_tmux", return_value="/usr/bin/tmux"),
            patch.object(session_boot, "_find_live_sessions", return_value=live),
            patch.object(session_boot, "_read_choice", return_value="n"),
            patch.object(session_boot, "_stop_session") as mock_stop,
            patch.object(session_boot, "_tmux_session_exists", return_value=False),
            patch(f"{_MOD}.os.execvp"),
        ):
            session_boot.boot(cwd=str(tmp_path))
        mock_stop.assert_called_once()

    def test_live_session_close_stops_and_exits(self, tmp_path):
        live = [{"pid": 1234, "sessionId": "abc", "cwd": str(tmp_path), "kind": "interactive"}]
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch.object(session_boot, "_find_tmux", return_value="/usr/bin/tmux"),
            patch.object(session_boot, "_find_live_sessions", return_value=live),
            patch.object(session_boot, "_read_choice", return_value="c"),
            patch.object(session_boot, "_stop_session") as mock_stop,
        ):
            result = session_boot.boot(cwd=str(tmp_path))
        mock_stop.assert_called_once()
        assert result["action"] == "closed"

    def test_no_live_continue_last(self, tmp_path):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch.object(session_boot, "_find_tmux", return_value="/usr/bin/tmux"),
            patch.object(session_boot, "_find_live_sessions", return_value=[]),
            patch.object(session_boot, "_read_choice", return_value=""),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path))
        args = mock_exec.call_args[0][1]
        assert "--continue" in args

    def test_no_live_new_starts_fresh(self, tmp_path):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch.object(session_boot, "_find_tmux", return_value="/usr/bin/tmux"),
            patch.object(session_boot, "_find_live_sessions", return_value=[]),
            patch.object(session_boot, "_read_choice", return_value="n"),
            patch.object(session_boot, "_tmux_session_exists", return_value=False),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path))
        args = mock_exec.call_args[0]
        assert args[0] == "tmux"
        assert "new-session" in args[1]
        assert "/usr/local/bin/claude" in args[1]

    def test_stale_tmux_session_killed_on_fresh_start(self, tmp_path):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch.object(session_boot, "_find_tmux", return_value="/usr/bin/tmux"),
            patch.object(session_boot, "_find_live_sessions", return_value=[]),
            patch.object(session_boot, "_read_choice", return_value="n"),
            patch.object(session_boot, "_tmux_session_exists", return_value=True),
            patch(f"{_MOD}.subprocess.run") as mock_run,
            patch(f"{_MOD}.os.execvp"),
        ):
            session_boot.boot(cwd=str(tmp_path))
        kill_calls = [c for c in mock_run.call_args_list if "kill-session" in str(c)]
        assert len(kill_calls) == 1

    def test_extra_args_passed_on_fresh_start(self, tmp_path):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch.object(session_boot, "_find_tmux", return_value="/usr/bin/tmux"),
            patch.object(session_boot, "_find_live_sessions", return_value=[]),
            patch.object(session_boot, "_read_choice", return_value="n"),
            patch.object(session_boot, "_tmux_session_exists", return_value=False),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path), extra_args=["--resume"])
        args = mock_exec.call_args[0][1]
        assert "--resume" in args


class TestStopSession:
    def test_bg_job_uses_agents_stop(self):
        session = {"pid": 1234, "kind": "bg", "jobId": "job-abc"}
        with patch(f"{_MOD}.subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            session_boot._stop_session(session, "/usr/local/bin/claude")
        cmd = mock_run.call_args[0][0]
        assert "agents" in cmd
        assert "stop" in cmd
        assert "job-abc" in cmd

    def test_tmux_session_killed(self):
        session = {"pid": 1234, "kind": "interactive"}
        with (
            patch.object(session_boot, "_find_tmux_session_for_pid", return_value="hooks"),
            patch(f"{_MOD}.subprocess.run") as mock_run,
        ):
            session_boot._stop_session(session, "/usr/local/bin/claude")
        kill_calls = [c for c in mock_run.call_args_list if "kill-session" in str(c)]
        assert len(kill_calls) == 1

    def test_plain_session_sigterm(self):
        session = {"pid": 1234, "kind": "interactive"}
        with (
            patch.object(session_boot, "_find_tmux_session_for_pid", return_value=None),
            patch(f"{_MOD}.os.kill") as mock_kill,
        ):
            session_boot._stop_session(session, "/usr/local/bin/claude")
        mock_kill.assert_called_once()


class TestMain:
    def test_success(self):
        with patch.object(session_boot, "boot", return_value={"exit_code": 0, "action": "started"}):
            session_boot.main()

    def test_failure_exits(self):
        import pytest

        with (
            patch.object(session_boot, "boot", return_value={"exit_code": 1, "error": "tmux not found"}),
            pytest.raises(SystemExit, match="1"),
        ):
            session_boot.main()

    def test_passes_sys_argv(self):
        with (
            patch.object(session_boot, "boot", return_value={"exit_code": 0}) as mock_boot,
            patch(f"{_MOD}.sys.argv", ["session_boot", "--resume", "--verbose"]),
        ):
            session_boot.main()
        mock_boot.assert_called_once_with(extra_args=["--resume", "--verbose"])

    def test_no_extra_args_when_no_argv(self):
        with (
            patch.object(session_boot, "boot", return_value={"exit_code": 0}) as mock_boot,
            patch(f"{_MOD}.sys.argv", ["session_boot"]),
        ):
            session_boot.main()
        mock_boot.assert_called_once_with(extra_args=None)


class TestHeadlessBypass:
    def test_p_flag_skips_tmux_and_runs_directly(self, tmp_path):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path), extra_args=["-p", "do something"])
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0][1]
        assert args[0] == "/usr/local/bin/claude"
        assert "-p" in args
        assert "do something" in args

    def test_p_flag_does_not_look_for_live_sessions(self, tmp_path):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch.object(session_boot, "_find_live_sessions") as mock_live,
            patch(f"{_MOD}.os.execvp"),
        ):
            session_boot.boot(cwd=str(tmp_path), extra_args=["-p", "query"])
        mock_live.assert_not_called()

    def test_p_flag_does_not_require_tmux(self, tmp_path):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch.object(session_boot, "_find_tmux", return_value=None),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            result = session_boot.boot(cwd=str(tmp_path), extra_args=["-p", "query"])
        assert result["action"] == "direct"
        assert result["reason"] == "headless -p mode"
        mock_exec.assert_called_once()

    def test_p_flag_still_gets_permission_mode_default(self, tmp_path):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path), extra_args=["-p", "query"])
        cmd = mock_exec.call_args[0][1]
        assert "--permission-mode" in cmd
        assert "bypassPermissions" in cmd

    def test_p_flag_respects_custom_permission_mode(self, tmp_path):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path), extra_args=["-p", "query", "--permission-mode", "default"])
        cmd = mock_exec.call_args[0][1]
        assert cmd.count("--permission-mode") == 1
        assert "default" in cmd


class TestPermissionModeDedupe:
    def test_no_extra_args_includes_default(self, tmp_path):
        with (
            patch.dict("os.environ", {"TMUX": "/tmp/tmux-1000/default,1,0"}),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path))
        cmd = mock_exec.call_args[0][1]
        assert cmd.count("--permission-mode") == 1
        assert "bypassPermissions" in cmd

    def test_extra_args_with_permission_mode_no_double(self, tmp_path):
        with (
            patch.dict("os.environ", {"TMUX": "/tmp/tmux-1000/default,1,0"}),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path), extra_args=["--permission-mode", "default"])
        cmd = mock_exec.call_args[0][1]
        assert cmd.count("--permission-mode") == 1
        assert "default" in cmd
        assert "bypassPermissions" not in cmd

    def test_extra_args_without_permission_mode_gets_default(self, tmp_path):
        with (
            patch.dict("os.environ", {"TMUX": "/tmp/tmux-1000/default,1,0"}),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path), extra_args=["--resume"])
        cmd = mock_exec.call_args[0][1]
        assert cmd.count("--permission-mode") == 1
        assert "bypassPermissions" in cmd
        assert "--resume" in cmd

    def test_fresh_start_dedupes_too(self, tmp_path):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch.object(session_boot, "_find_tmux", return_value="/usr/bin/tmux"),
            patch.object(session_boot, "_find_live_sessions", return_value=[]),
            patch.object(session_boot, "_read_choice", return_value="n"),
            patch.object(session_boot, "_tmux_session_exists", return_value=False),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path), extra_args=["--permission-mode", "acceptEdits"])
        cmd = mock_exec.call_args[0][1]
        assert cmd.count("--permission-mode") == 1
        assert "acceptEdits" in cmd


class TestMultipleLiveSessions:
    def test_close_all(self, tmp_path):
        live = [
            {"pid": 1234, "sessionId": "abc", "cwd": str(tmp_path), "kind": "interactive"},
            {"pid": 5678, "sessionId": "def", "cwd": str(tmp_path), "kind": "bg"},
        ]
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch.object(session_boot, "_find_tmux", return_value="/usr/bin/tmux"),
            patch.object(session_boot, "_find_live_sessions", return_value=live),
            patch.object(session_boot, "_read_choice", return_value="c"),
            patch.object(session_boot, "_stop_session") as mock_stop,
        ):
            result = session_boot.boot(cwd=str(tmp_path))
        assert result["action"] == "closed_all"
        assert mock_stop.call_count == 2

    def test_pick_by_number(self, tmp_path):
        live = [
            {"pid": 1234, "sessionId": "abc", "cwd": str(tmp_path), "kind": "interactive"},
            {"pid": 5678, "sessionId": "def", "cwd": str(tmp_path), "kind": "bg"},
        ]
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(session_boot, "_resolve_claude_binary", return_value="/usr/local/bin/claude"),
            patch.object(session_boot, "_find_tmux", return_value="/usr/bin/tmux"),
            patch.object(session_boot, "_find_live_sessions", return_value=live),
            patch.object(session_boot, "_read_choice", return_value="2"),
            patch.object(session_boot, "_find_tmux_session_for_pid", return_value=None),
            patch(f"{_MOD}.os.execvp") as mock_exec,
        ):
            session_boot.boot(cwd=str(tmp_path))
        args = mock_exec.call_args[0][1]
        assert "agents" in args
