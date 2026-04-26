"""Tests for the CLI init_project module — aipass command routing and init orchestration."""

from io import StringIO
from unittest.mock import patch, MagicMock

import pytest
from rich.console import Console

from aipass.cli.apps.modules import init_project
from aipass.cli.apps.modules.init_project import (
    handle_command,
    _handle_init,
    _handle_init_agent,
    _handle_init_update,
    print_introspection,
    print_help,
    _print_init_help,
)


# =============================================================================
# Helpers
# =============================================================================


def _make_capture_console():
    """Return (console, get_output) for capturing Rich output."""
    buf = StringIO()
    cons = Console(file=buf, no_color=True, width=120, highlight=False)
    return cons, lambda: buf.getvalue()


# =============================================================================
# handle_command routing tests
# =============================================================================


class TestHandleCommandRouting:
    """Verify handle_command dispatches correctly and returns the right boolean."""

    def test_non_aipass_command_returns_false(self):
        """Commands other than 'aipass' should return False."""
        assert handle_command("other", []) is False
        assert handle_command("display", []) is False
        assert handle_command("", []) is False

    def test_aipass_no_args_calls_introspection(self):
        """'aipass' with no args shows introspection."""
        with patch.object(init_project, "print_introspection") as mock:
            result = handle_command("aipass", [])
        assert result is True
        mock.assert_called_once()

    def test_aipass_help_flag(self):
        """'aipass --help' shows full help."""
        with patch.object(init_project, "print_help") as mock:
            result = handle_command("aipass", ["--help"])
        assert result is True
        mock.assert_called_once()

    def test_aipass_dash_h_flag(self):
        """'aipass -h' shows full help."""
        with patch.object(init_project, "print_help") as mock:
            result = handle_command("aipass", ["-h"])
        assert result is True
        mock.assert_called_once()

    def test_aipass_help_word(self):
        """'aipass help' shows full help."""
        with patch.object(init_project, "print_help") as mock:
            result = handle_command("aipass", ["help"])
        assert result is True
        mock.assert_called_once()

    def test_aipass_init_routes_to_handle_init(self):
        """'aipass init' routes to _handle_init."""
        with patch.object(init_project, "_handle_init", return_value=True) as mock:
            result = handle_command("aipass", ["init"])
        assert result is True
        mock.assert_called_once_with([])

    def test_aipass_init_with_args_passes_through(self):
        """'aipass init /path Name' passes args to _handle_init."""
        with patch.object(init_project, "_handle_init", return_value=True) as mock:
            result = handle_command("aipass", ["init", "/path", "MyProj"])
        assert result is True
        mock.assert_called_once_with(["/path", "MyProj"])

    def test_unknown_subcommand_shows_error(self):
        """Unknown aipass subcommand shows error and returns True."""
        cons, get_output = _make_capture_console()
        err_cons, get_err = _make_capture_console()
        with patch.object(init_project, "console", cons), patch.object(init_project, "error") as mock_error:
            result = handle_command("aipass", ["bogus"])
        assert result is True
        mock_error.assert_called_once()
        args = mock_error.call_args
        assert "bogus" in args[0][0]


# =============================================================================
# _handle_init tests
# =============================================================================


class TestHandleInit:
    """Tests for the init subcommand orchestration."""

    def test_init_help_flag(self):
        """'init --help' shows init help and returns True."""
        with patch.object(init_project, "_print_init_help") as mock:
            result = _handle_init(["--help"])
        assert result is True
        mock.assert_called_once()

    def test_init_success_displays_output(self, tmp_path):
        """Successful init displays results and logs the operation."""
        target = tmp_path / "my_project"
        cons, get_output = _make_capture_console()
        err_cons, get_err = _make_capture_console()

        from aipass.cli.apps.modules import display

        with (
            patch.object(init_project, "console", cons),
            patch.object(display, "CONSOLE", cons),
            patch.object(display, "err_console", err_cons),
            patch.object(display, "_TRIGGER", None),
            patch.object(display, "_TRIGGER_LOADED", True),
            patch.object(init_project, "json_handler") as mock_json,
            patch.object(init_project, "logger"),
        ):
            result = _handle_init([str(target)])

        assert result is True
        output = get_output()
        assert "Project Initialized" in output
        mock_json.log_operation.assert_called_once()
        call_args = mock_json.log_operation.call_args
        assert call_args[0][0] == "aipass_init"

    def test_init_displays_aipass_home(self, tmp_path):
        """When aipass_home is in result, displays AIPASS_HOME info."""
        target = tmp_path / "home_proj"
        cons, get_output = _make_capture_console()
        err_cons, _ = _make_capture_console()
        from aipass.cli.apps.modules import display

        mock_result = {
            "project_name": "HOME_PROJ",
            "registry_file": "HOME_PROJ_REGISTRY.json",
            "registry_id": "12345678-abcd-1234-5678-abcdef123456",
            "target": str(target),
            "created_files": ["file1", "file2"],
            "aipass_home": "/fake/aipass",
        }
        with (
            patch.object(init_project, "init_project", return_value=mock_result),
            patch.object(init_project, "console", cons),
            patch.object(display, "CONSOLE", cons),
            patch.object(display, "err_console", err_cons),
            patch.object(display, "_TRIGGER", None),
            patch.object(display, "_TRIGGER_LOADED", True),
            patch.object(init_project, "json_handler"),
            patch.object(init_project, "logger"),
        ):
            _handle_init([str(target)])
        output = get_output()
        assert "AIPASS_HOME" in output
        assert "/fake/aipass" in output

    def test_init_next_steps_shown(self, tmp_path):
        """After init, next steps guidance is shown."""
        target = tmp_path / "steps_proj"
        cons, get_output = _make_capture_console()
        err_cons, _ = _make_capture_console()
        from aipass.cli.apps.modules import display

        with (
            patch.object(init_project, "console", cons),
            patch.object(display, "CONSOLE", cons),
            patch.object(display, "err_console", err_cons),
            patch.object(display, "_TRIGGER", None),
            patch.object(display, "_TRIGGER_LOADED", True),
            patch.object(init_project, "json_handler"),
            patch.object(init_project, "logger"),
        ):
            _handle_init([str(target)])
        output = get_output()
        assert "Next steps" in output

    def test_init_value_error_exits(self, tmp_path):
        """ValueError from init_project causes error display and sys.exit(1)."""
        with (
            patch.object(init_project, "init_project", side_effect=ValueError("bad name")),
            patch.object(init_project, "error") as mock_error,
            patch.object(init_project, "logger"),
            pytest.raises(SystemExit) as exc_info,
        ):
            _handle_init([str(tmp_path)])
        assert exc_info.value.code == 1
        mock_error.assert_called_once()
        assert "bad name" in mock_error.call_args[0][0]

    def test_init_file_exists_error_exits(self, tmp_path):
        """FileExistsError from init_project causes error display and sys.exit(1)."""
        with (
            patch.object(init_project, "init_project", side_effect=FileExistsError("already exists")),
            patch.object(init_project, "error") as mock_error,
            patch.object(init_project, "logger"),
            pytest.raises(SystemExit) as exc_info,
        ):
            _handle_init([str(tmp_path)])
        assert exc_info.value.code == 1
        mock_error.assert_called_once()

    def test_init_os_error_exits(self, tmp_path):
        """OSError from init_project causes error display and sys.exit(1)."""
        with (
            patch.object(init_project, "init_project", side_effect=OSError("disk full")),
            patch.object(init_project, "error") as mock_error,
            patch.object(init_project, "logger"),
            pytest.raises(SystemExit) as exc_info,
        ):
            _handle_init([str(tmp_path)])
        assert exc_info.value.code == 1
        mock_error.assert_called_once()

    def test_init_uses_caller_cwd_env(self, tmp_path):
        """When no target arg, uses AIPASS_CALLER_CWD env var."""
        import os

        target = tmp_path / "env_project"
        target.mkdir()

        cons, get_output = _make_capture_console()
        err_cons, get_err = _make_capture_console()

        from aipass.cli.apps.modules import display

        with (
            patch.dict(os.environ, {"AIPASS_CALLER_CWD": str(target)}),
            patch.object(init_project, "console", cons),
            patch.object(display, "CONSOLE", cons),
            patch.object(display, "err_console", err_cons),
            patch.object(display, "_TRIGGER", None),
            patch.object(display, "_TRIGGER_LOADED", True),
            patch.object(init_project, "json_handler"),
            patch.object(init_project, "logger"),
        ):
            result = _handle_init([])

        assert result is True
        output = get_output()
        assert "Project Initialized" in output


# =============================================================================
# Direct routing tests (command="init", command="update")
# =============================================================================


class TestDirectRouting:
    """Verify direct command routing for PATH-based invocation."""

    def test_command_init_routes_directly(self):
        """command='init' routes directly to _handle_init."""
        with patch.object(init_project, "_handle_init", return_value=True) as mock:
            result = handle_command("init", ["--help"])
        assert result is True
        mock.assert_called_once_with(["--help"])

    def test_command_update_routes_to_init_update(self):
        """command='update' routes to _handle_init with 'update' prepended."""
        with patch.object(init_project, "_handle_init", return_value=True) as mock:
            result = handle_command("update", ["/path"])
        assert result is True
        mock.assert_called_once_with(["update", "/path"])


# =============================================================================
# print_introspection / print_help / _print_init_help body execution
# =============================================================================


class TestOutputFunctions:
    """Verify output functions produce expected content when actually executed."""

    def test_print_introspection_outputs_module_info(self):
        """print_introspection() outputs command table and handler info."""
        cons, get_output = _make_capture_console()
        from aipass.cli.apps.modules import display

        with (
            patch.object(init_project, "console", cons),
            patch.object(display, "CONSOLE", cons),
        ):
            print_introspection()
        output = get_output()
        assert "aipass" in output
        assert "Project Commands" in output
        assert "bootstrap.py" in output

    def test_print_help_outputs_full_help(self):
        """print_help() outputs commands and file list."""
        cons, get_output = _make_capture_console()
        err_cons, _ = _make_capture_console()
        from aipass.cli.apps.modules import display

        with (
            patch.object(init_project, "console", cons),
            patch.object(display, "CONSOLE", cons),
            patch.object(display, "err_console", err_cons),
            patch.object(display, "_TRIGGER", None),
            patch.object(display, "_TRIGGER_LOADED", True),
        ):
            print_help()
        output = get_output()
        assert "COMMANDS:" in output
        assert "WHAT INIT CREATES:" in output
        assert "ARGUMENTS" in output

    def test_print_init_help_outputs_usage(self):
        """_print_init_help() outputs usage examples and arguments."""
        cons, get_output = _make_capture_console()
        err_cons, _ = _make_capture_console()
        from aipass.cli.apps.modules import display

        with (
            patch.object(init_project, "console", cons),
            patch.object(display, "CONSOLE", cons),
            patch.object(display, "err_console", err_cons),
            patch.object(display, "_TRIGGER", None),
            patch.object(display, "_TRIGGER_LOADED", True),
        ):
            _print_init_help()
        output = get_output()
        assert "USAGE:" in output
        assert "WHAT IT CREATES:" in output
        assert "ARGUMENTS:" in output


# =============================================================================
# _handle_init_agent tests
# =============================================================================


class TestHandleInitAgent:
    """Tests for the 'aipass init agent' subcommand."""

    def test_agent_help_no_args(self):
        """'init agent' with no args shows help."""
        cons, get_output = _make_capture_console()
        err_cons, _ = _make_capture_console()
        from aipass.cli.apps.modules import display

        with (
            patch.object(init_project, "console", cons),
            patch.object(display, "CONSOLE", cons),
            patch.object(display, "err_console", err_cons),
            patch.object(display, "_TRIGGER", None),
            patch.object(display, "_TRIGGER_LOADED", True),
        ):
            result = _handle_init_agent([])
        assert result is True
        output = get_output()
        assert "Create an Agent" in output

    def test_agent_help_flag(self):
        """'init agent --help' shows help."""
        cons, get_output = _make_capture_console()
        err_cons, _ = _make_capture_console()
        from aipass.cli.apps.modules import display

        with (
            patch.object(init_project, "console", cons),
            patch.object(display, "CONSOLE", cons),
            patch.object(display, "err_console", err_cons),
            patch.object(display, "_TRIGGER", None),
            patch.object(display, "_TRIGGER_LOADED", True),
        ):
            result = _handle_init_agent(["--help"])
        assert result is True

    def test_agent_success_calls_subprocess(self):
        """'init agent mybot' calls drone @spawn create src/mybot."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        with (
            patch.object(init_project, "subprocess") as mock_sub,
            patch.object(init_project, "logger"),
        ):
            mock_sub.run.return_value = mock_result
            result = _handle_init_agent(["mybot"])
        assert result is True
        mock_sub.run.assert_called_once()
        call_args = mock_sub.run.call_args[0][0]
        assert "src/mybot" in call_args

    def test_agent_subprocess_nonzero_exit(self):
        """Non-zero subprocess exit shows error."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        with (
            patch.object(init_project, "subprocess") as mock_sub,
            patch.object(init_project, "error") as mock_error,
            patch.object(init_project, "logger"),
        ):
            mock_sub.run.return_value = mock_result
            result = _handle_init_agent(["badbot"])
        assert result is True
        mock_error.assert_called_once()

    def test_agent_forwards_extra_flags(self):
        """Extra flags like --role are forwarded to spawn."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        with (
            patch.object(init_project, "subprocess") as mock_sub,
            patch.object(init_project, "logger"),
        ):
            mock_sub.run.return_value = mock_result
            _handle_init_agent(["mybot", "--role", "builder"])
        call_args = mock_sub.run.call_args[0][0]
        assert "--role" in call_args
        assert "builder" in call_args

    def test_agent_file_not_found(self):
        """FileNotFoundError when drone is missing shows error."""
        with (
            patch.object(init_project, "subprocess") as mock_sub,
            patch.object(init_project, "error") as mock_error,
            patch.object(init_project, "logger"),
        ):
            mock_sub.run.side_effect = FileNotFoundError("drone not found")
            result = _handle_init_agent(["mybot"])
        assert result is True
        mock_error.assert_called_once()
        assert "not found" in mock_error.call_args[0][0]


# =============================================================================
# _handle_init_update tests
# =============================================================================


class TestHandleInitUpdate:
    """Tests for the 'aipass init update' subcommand."""

    def test_update_help_flag(self):
        """'init update --help' shows update help."""
        cons, get_output = _make_capture_console()
        err_cons, _ = _make_capture_console()
        from aipass.cli.apps.modules import display

        with (
            patch.object(init_project, "console", cons),
            patch.object(display, "CONSOLE", cons),
            patch.object(display, "err_console", err_cons),
            patch.object(display, "_TRIGGER", None),
            patch.object(display, "_TRIGGER_LOADED", True),
        ):
            result = _handle_init_update(["--help"])
        assert result is True
        output = get_output()
        assert "Refresh Scaffold Files" in output

    def test_update_success_with_updates(self, tmp_path):
        """Successful update with changed files displays updated table."""
        cons, get_output = _make_capture_console()
        err_cons, _ = _make_capture_console()
        from aipass.cli.apps.modules import display

        mock_result = {
            "project_name": "TESTPROJ",
            "target": str(tmp_path),
            "updated_files": ["/a/CLAUDE.md", "/a/AGENTS.md"],
            "already_current": ["/a/settings.json"],
            "skipped_files": ["/a/README.md", "/a/REGISTRY.json"],
        }
        with (
            patch.object(init_project, "update_project", return_value=mock_result),
            patch.object(init_project, "console", cons),
            patch.object(display, "CONSOLE", cons),
            patch.object(display, "err_console", err_cons),
            patch.object(display, "_TRIGGER", None),
            patch.object(display, "_TRIGGER_LOADED", True),
            patch.object(init_project, "json_handler"),
            patch.object(init_project, "logger"),
            patch.dict("os.environ", {"AIPASS_CALLER_CWD": str(tmp_path)}),
        ):
            result = _handle_init_update([])
        assert result is True
        output = get_output()
        assert "Project Updated" in output
        assert "Updated" in output

    def test_update_all_current(self, tmp_path):
        """When nothing changed, displays 'All files already up to date'."""
        cons, get_output = _make_capture_console()
        err_cons, _ = _make_capture_console()
        from aipass.cli.apps.modules import display

        mock_result = {
            "project_name": "TESTPROJ",
            "target": str(tmp_path),
            "updated_files": [],
            "already_current": ["/a/CLAUDE.md", "/a/settings.json"],
            "skipped_files": ["/a/README.md"],
        }
        with (
            patch.object(init_project, "update_project", return_value=mock_result),
            patch.object(init_project, "console", cons),
            patch.object(display, "CONSOLE", cons),
            patch.object(display, "err_console", err_cons),
            patch.object(display, "_TRIGGER", None),
            patch.object(display, "_TRIGGER_LOADED", True),
            patch.object(init_project, "json_handler"),
            patch.object(init_project, "logger"),
            patch.dict("os.environ", {"AIPASS_CALLER_CWD": str(tmp_path)}),
        ):
            result = _handle_init_update([])
        assert result is True
        output = get_output()
        assert "up to date" in output

    def test_update_value_error_exits(self, tmp_path):
        """ValueError from update_project causes sys.exit(1)."""
        with (
            patch.object(init_project, "update_project", side_effect=ValueError("no registry")),
            patch.object(init_project, "error") as mock_error,
            patch.object(init_project, "logger"),
            patch.dict("os.environ", {"AIPASS_CALLER_CWD": str(tmp_path)}),
            pytest.raises(SystemExit) as exc_info,
        ):
            _handle_init_update([])
        assert exc_info.value.code == 1
        mock_error.assert_called_once()

    def test_update_os_error_exits(self, tmp_path):
        """OSError from update_project causes sys.exit(1)."""
        with (
            patch.object(init_project, "update_project", side_effect=OSError("read-only")),
            patch.object(init_project, "error") as mock_error,
            patch.object(init_project, "logger"),
            patch.dict("os.environ", {"AIPASS_CALLER_CWD": str(tmp_path)}),
            pytest.raises(SystemExit) as exc_info,
        ):
            _handle_init_update([])
        assert exc_info.value.code == 1
        mock_error.assert_called_once()

    def test_update_with_target_arg(self, tmp_path):
        """Target arg is passed to update_project."""
        target = tmp_path / "myproj"
        mock_result = {
            "project_name": "MYPROJ",
            "target": str(target),
            "updated_files": [],
            "already_current": [],
            "skipped_files": [],
        }
        cons, _ = _make_capture_console()
        err_cons, _ = _make_capture_console()
        from aipass.cli.apps.modules import display

        with (
            patch.object(init_project, "update_project", return_value=mock_result) as mock_up,
            patch.object(init_project, "console", cons),
            patch.object(display, "CONSOLE", cons),
            patch.object(display, "err_console", err_cons),
            patch.object(display, "_TRIGGER", None),
            patch.object(display, "_TRIGGER_LOADED", True),
            patch.object(init_project, "json_handler"),
            patch.object(init_project, "logger"),
        ):
            _handle_init_update([str(target)])
        mock_up.assert_called_once()

    def test_update_relative_path_resolves_against_caller_cwd(self, tmp_path):
        """Relative path resolves against AIPASS_CALLER_CWD."""
        from pathlib import Path

        mock_result = {
            "project_name": "PROJ",
            "target": str(tmp_path / "rel"),
            "updated_files": [],
            "already_current": [],
            "skipped_files": [],
        }
        cons, _ = _make_capture_console()
        err_cons, _ = _make_capture_console()
        from aipass.cli.apps.modules import display

        with (
            patch.object(init_project, "update_project", return_value=mock_result) as mock_up,
            patch.object(init_project, "console", cons),
            patch.object(display, "CONSOLE", cons),
            patch.object(display, "err_console", err_cons),
            patch.object(display, "_TRIGGER", None),
            patch.object(display, "_TRIGGER_LOADED", True),
            patch.object(init_project, "json_handler"),
            patch.object(init_project, "logger"),
            patch.dict("os.environ", {"AIPASS_CALLER_CWD": str(tmp_path)}),
        ):
            _handle_init_update(["rel"])
        called_target = mock_up.call_args[0][0]
        assert called_target == Path(tmp_path) / "rel"
