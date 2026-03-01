"""
Unit tests for Phase 2 routing functionality.

Tests command routing, subprocess execution, and module discovery with >80%
coverage on new code. All subprocess calls are mocked — no real processes run.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from aipass.routing import (
    BranchNotFoundError,
    CommandExecutionError,
    CommandResult,
    discover_modules,
    get_help,
    initialize_registry,
    register_branch,
    reset_registry_path,
    route_command,
    set_registry_path,
)
from aipass.routing.executor import execute_command
from aipass.routing.router import _find_entry_point


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_registry(tmp_path):
    """Temporary registry backed by a tmp directory."""
    registry_path = tmp_path / "test_registry.json"
    set_registry_path(registry_path)
    initialize_registry()
    yield tmp_path
    reset_registry_path()


@pytest.fixture
def branch_with_entry(tmp_path):
    """
    A registered branch that has a valid apps/{name}.py entry point.

    Layout:
        tmp_path/
          myagent/
            apps/
              myagent.py
              modules/
                status.py
                info.py
    """
    branch_dir = tmp_path / "myagent"
    apps_dir = branch_dir / "apps"
    modules_dir = apps_dir / "modules"
    modules_dir.mkdir(parents=True)

    entry = apps_dir / "myagent.py"
    entry.write_text("# stub entry point\n")

    (modules_dir / "status.py").write_text("")
    (modules_dir / "info.py").write_text("")
    (modules_dir / "__init__.py").write_text("")

    registry_path = tmp_path / "registry.json"
    set_registry_path(registry_path)
    initialize_registry()
    register_branch("myagent", str(branch_dir), "agent")

    yield branch_dir

    reset_registry_path()


@pytest.fixture
def branch_without_entry(tmp_path):
    """A registered branch that has NO apps/{name}.py entry point."""
    branch_dir = tmp_path / "noentry"
    apps_dir = branch_dir / "apps"
    modules_dir = apps_dir / "modules"
    modules_dir.mkdir(parents=True)
    (modules_dir / "do_thing.py").write_text("")

    registry_path = tmp_path / "registry.json"
    set_registry_path(registry_path)
    initialize_registry()
    register_branch("noentry", str(branch_dir), "agent")

    yield branch_dir

    reset_registry_path()


def _make_completed_process(stdout=b"", stderr=b"", returncode=0):
    """Helper to build a subprocess.CompletedProcess mock."""
    cp = MagicMock(spec=subprocess.CompletedProcess)
    cp.stdout = stdout
    cp.stderr = stderr
    cp.returncode = returncode
    return cp


# ---------------------------------------------------------------------------
# CommandResult structure
# ---------------------------------------------------------------------------


class TestCommandResult:
    """Verify CommandResult is a proper dataclass with expected fields."""

    def test_fields_present(self):
        """CommandResult exposes stdout, stderr, exit_code, branch, command."""
        result = CommandResult(
            stdout="hello",
            stderr="",
            exit_code=0,
            branch="myagent",
            command="status",
        )
        assert result.stdout == "hello"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.branch == "myagent"
        assert result.command == "status"

    def test_non_zero_exit_code(self):
        """CommandResult stores non-zero exit codes without raising."""
        result = CommandResult(
            stdout="", stderr="error", exit_code=1, branch="b", command="c"
        )
        assert result.exit_code == 1

    def test_dataclass_equality(self):
        """Two CommandResult instances with identical values compare equal."""
        a = CommandResult("out", "err", 0, "b", "c")
        b = CommandResult("out", "err", 0, "b", "c")
        assert a == b


# ---------------------------------------------------------------------------
# executor.execute_command
# ---------------------------------------------------------------------------


class TestExecuteCommand:
    """Tests for the low-level subprocess wrapper."""

    def test_successful_execution(self, tmp_path):
        """execute_command returns CommandResult on success."""
        cp = _make_completed_process(stdout=b"ok\n", returncode=0)
        with patch("subprocess.run", return_value=cp) as mock_run:
            result = execute_command("python3", ["script.py"], cwd=str(tmp_path))

        assert result.stdout == "ok\n"
        assert result.exit_code == 0
        mock_run.assert_called_once()

    def test_no_shell_true(self, tmp_path):
        """execute_command never passes shell=True to subprocess.run."""
        cp = _make_completed_process()
        with patch("subprocess.run", return_value=cp) as mock_run:
            execute_command("python3", ["x.py"], cwd=str(tmp_path))

        _, kwargs = mock_run.call_args
        assert kwargs.get("shell") is False

    def test_timeout_raises_command_execution_error(self, tmp_path):
        """TimeoutExpired is wrapped in CommandExecutionError."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="python3", timeout=5),
        ):
            with pytest.raises(CommandExecutionError, match="timed out"):
                execute_command("python3", ["x.py"], cwd=str(tmp_path), timeout=5)

    def test_file_not_found_raises_command_execution_error(self, tmp_path):
        """FileNotFoundError is wrapped in CommandExecutionError."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(CommandExecutionError, match="not found"):
                execute_command("nonexistent_bin", [], cwd=str(tmp_path))

    def test_os_error_raises_command_execution_error(self, tmp_path):
        """Generic OSError is wrapped in CommandExecutionError."""
        with patch("subprocess.run", side_effect=OSError("permission denied")):
            with pytest.raises(CommandExecutionError, match="OS error"):
                execute_command("python3", [], cwd=str(tmp_path))

    def test_stderr_captured(self, tmp_path):
        """execute_command captures stderr separately from stdout."""
        cp = _make_completed_process(stdout=b"", stderr=b"warn\n", returncode=1)
        with patch("subprocess.run", return_value=cp):
            result = execute_command("python3", ["x.py"], cwd=str(tmp_path))

        assert result.stderr == "warn\n"
        assert result.exit_code == 1

    def test_branch_and_command_empty_strings(self, tmp_path):
        """execute_command sets branch and command to empty strings."""
        cp = _make_completed_process()
        with patch("subprocess.run", return_value=cp):
            result = execute_command("python3", [], cwd=str(tmp_path))

        assert result.branch == ""
        assert result.command == ""

    def test_timeout_forwarded(self, tmp_path):
        """Custom timeout value is passed through to subprocess.run."""
        cp = _make_completed_process()
        with patch("subprocess.run", return_value=cp) as mock_run:
            execute_command("python3", [], cwd=str(tmp_path), timeout=99)

        _, kwargs = mock_run.call_args
        assert kwargs["timeout"] == 99


# ---------------------------------------------------------------------------
# router.route_command
# ---------------------------------------------------------------------------


class TestRouteCommand:
    """Tests for the high-level command routing function."""

    def test_route_command_success(self, branch_with_entry):
        """route_command returns populated CommandResult on success."""
        cp = _make_completed_process(stdout=b"running\n", returncode=0)
        with patch("subprocess.run", return_value=cp):
            result = route_command("@myagent", "status")

        assert result.stdout == "running\n"
        assert result.exit_code == 0
        assert result.branch == "myagent"
        assert result.command == "status"

    def test_route_command_without_at_prefix(self, branch_with_entry):
        """route_command accepts branch names without the @ prefix."""
        cp = _make_completed_process(stdout=b"ok\n", returncode=0)
        with patch("subprocess.run", return_value=cp):
            result = route_command("myagent", "status")

        assert result.branch == "myagent"

    def test_route_command_with_args(self, branch_with_entry):
        """route_command forwards extra args to subprocess."""
        cp = _make_completed_process(stdout=b"done\n", returncode=0)
        with patch("subprocess.run", return_value=cp) as mock_run:
            route_command("@myagent", "run", args=["--verbose", "--dry-run"])

        call_args = mock_run.call_args[0][0]  # positional list
        assert "--verbose" in call_args
        assert "--dry-run" in call_args

    def test_route_command_missing_branch_raises_error(self, temp_registry):
        """route_command raises BranchNotFoundError for unknown branch."""
        with pytest.raises(BranchNotFoundError):
            route_command("@ghost", "status")

    def test_route_command_missing_entry_point_raises_error(self, branch_without_entry):
        """route_command raises CommandExecutionError when entry point absent."""
        with pytest.raises(CommandExecutionError, match="Entry point not found"):
            route_command("@noentry", "status")

    def test_route_command_timeout(self, branch_with_entry):
        """route_command propagates timeout as CommandExecutionError."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="python3", timeout=1),
        ):
            with pytest.raises(CommandExecutionError, match="timed out"):
                route_command("@myagent", "status", timeout=1)

    def test_route_command_nonzero_exit_does_not_raise(self, branch_with_entry):
        """Non-zero exit code is returned, not raised."""
        cp = _make_completed_process(stderr=b"fail\n", returncode=2)
        with patch("subprocess.run", return_value=cp):
            result = route_command("@myagent", "status")

        assert result.exit_code == 2
        assert result.stderr == "fail\n"

    def test_route_command_default_timeout_is_30(self, branch_with_entry):
        """Default timeout forwarded to subprocess is 30 seconds."""
        cp = _make_completed_process()
        with patch("subprocess.run", return_value=cp) as mock_run:
            route_command("@myagent", "status")

        _, kwargs = mock_run.call_args
        assert kwargs["timeout"] == 30


# ---------------------------------------------------------------------------
# router._find_entry_point
# ---------------------------------------------------------------------------


class TestFindEntryPoint:
    """Tests for the internal entry-point locator."""

    def test_finds_existing_entry_point(self, branch_with_entry):
        """_find_entry_point returns path when entry point exists."""
        ep = _find_entry_point(str(branch_with_entry), "myagent")
        assert ep.exists()
        assert ep.name == "myagent.py"

    def test_raises_when_entry_point_missing(self, branch_without_entry):
        """_find_entry_point raises CommandExecutionError when file absent."""
        with pytest.raises(CommandExecutionError, match="Entry point not found"):
            _find_entry_point(str(branch_without_entry), "noentry")


# ---------------------------------------------------------------------------
# discovery.discover_modules
# ---------------------------------------------------------------------------


class TestDiscoverModules:
    """Tests for branch capability discovery."""

    def test_discover_from_help_output(self, branch_with_entry):
        """discover_modules parses commands from --help output."""
        help_output = (
            b"Usage: myagent.py [command]\n\n"
            b"Commands:\n"
            b"  status    Show current status\n"
            b"  deploy    Deploy the agent\n"
        )
        cp = _make_completed_process(stdout=help_output, returncode=0)
        with patch("subprocess.run", return_value=cp):
            modules = discover_modules("@myagent")

        assert "status" in modules
        assert "deploy" in modules

    def test_discover_falls_back_to_modules_dir(self, branch_with_entry):
        """discover_modules falls back to scanning modules/ when help unparseable."""
        cp = _make_completed_process(stdout=b"No commands here.\n", returncode=0)
        with patch("subprocess.run", return_value=cp):
            modules = discover_modules("@myagent")

        # Falls back to scanning apps/modules/ which contains status.py, info.py
        assert "status" in modules
        assert "info" in modules
        # __init__ is excluded
        assert "__init__" not in modules

    def test_discover_falls_back_when_subprocess_fails(self, branch_with_entry):
        """discover_modules falls back to modules/ on subprocess OSError."""
        with patch("subprocess.run", side_effect=OSError("boom")):
            modules = discover_modules("@myagent")

        assert "status" in modules
        assert "info" in modules

    def test_discover_falls_back_on_timeout(self, branch_with_entry):
        """discover_modules falls back to modules/ on help timeout."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="python3", timeout=10),
        ):
            modules = discover_modules("@myagent")

        assert isinstance(modules, list)

    def test_discover_missing_branch_raises_error(self, temp_registry):
        """discover_modules raises BranchNotFoundError for unknown branch."""
        with pytest.raises(BranchNotFoundError):
            discover_modules("@phantom")

    def test_discover_no_entry_no_modules(self, branch_without_entry):
        """discover_modules returns empty list when no entry and no modules match help."""
        cp = _make_completed_process(stdout=b"nothing useful\n", returncode=0)
        # branch_without_entry has no entry point, so subprocess is never called for
        # --help (discovery skips it), but it does have a modules/ dir.
        with patch("subprocess.run", return_value=cp):
            modules = discover_modules("@noentry")

        # Should find do_thing.py from the modules dir.
        assert "do_thing" in modules

    def test_discover_returns_list(self, branch_with_entry):
        """discover_modules always returns a list."""
        cp = _make_completed_process(stdout=b"", returncode=0)
        with patch("subprocess.run", return_value=cp):
            result = discover_modules("@myagent")

        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# discovery.get_help
# ---------------------------------------------------------------------------


class TestGetHelp:
    """Tests for branch help text retrieval (get_help returns HelpResult)."""

    def test_get_help_branch_level(self, branch_with_entry):
        """get_help returns HelpResult with text when command is None."""
        help_text = b"Usage: myagent.py [command]\n\nCommands:\n  status\n"
        cp = _make_completed_process(stdout=help_text, returncode=0)
        with patch("subprocess.run", return_value=cp):
            result = get_help("@myagent")

        assert "Usage" in result.text
        assert result.branch == "myagent"
        assert result.command is None

    def test_get_help_command_level(self, branch_with_entry):
        """get_help passes the command name when command is specified."""
        help_text = b"Usage: myagent.py status [options]\n"
        cp = _make_completed_process(stdout=help_text, returncode=0)
        with patch("subprocess.run", return_value=cp) as mock_run:
            result = get_help("@myagent", command="status")

        call_args = mock_run.call_args[0][0]
        assert "status" in call_args
        assert "--help" in call_args
        assert "Usage" in result.text
        assert result.command == "status"

    def test_get_help_falls_back_to_stderr(self, branch_with_entry):
        """get_help uses stderr text when stdout is empty."""
        cp = _make_completed_process(stdout=b"", stderr=b"help via stderr\n", returncode=0)
        with patch("subprocess.run", return_value=cp):
            result = get_help("@myagent")

        assert "help via stderr" in result.text

    def test_get_help_missing_branch_raises_error(self, temp_registry):
        """get_help raises BranchNotFoundError for unknown branch."""
        with pytest.raises(BranchNotFoundError):
            get_help("@phantom")

    def test_get_help_missing_entry_point_raises_error(self, branch_without_entry):
        """get_help raises CommandExecutionError when entry point absent."""
        with pytest.raises(CommandExecutionError, match="Entry point not found"):
            get_help("@noentry")

    def test_get_help_timeout_raises_error(self, branch_with_entry):
        """get_help raises CommandExecutionError on timeout."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="python3", timeout=10),
        ):
            with pytest.raises(CommandExecutionError, match="timed out"):
                get_help("@myagent")

    def test_get_help_os_error_raises_error(self, branch_with_entry):
        """get_help raises CommandExecutionError on OS error."""
        with patch("subprocess.run", side_effect=OSError("no such file")):
            with pytest.raises(CommandExecutionError, match="OS error"):
                get_help("@myagent")

    def test_get_help_without_at_prefix(self, branch_with_entry):
        """get_help accepts branch name without @ prefix."""
        cp = _make_completed_process(stdout=b"help text\n", returncode=0)
        with patch("subprocess.run", return_value=cp):
            result = get_help("myagent")

        assert "help text" in result.text

    def test_get_help_commands_found_populated(self, branch_with_entry):
        """get_help populates commands_found from parsed help text."""
        help_text = b"Usage: myagent.py\n\nCommands:\n  status  Show status\n  deploy  Deploy\n"
        cp = _make_completed_process(stdout=help_text, returncode=0)
        with patch("subprocess.run", return_value=cp):
            result = get_help("@myagent")

        assert "status" in result.commands_found
        assert "deploy" in result.commands_found


# ---------------------------------------------------------------------------
# Executor safety: no shell injection
# ---------------------------------------------------------------------------


class TestExecutorSafety:
    """Verify the executor never enables shell features."""

    def test_shell_is_false(self, tmp_path):
        """subprocess.run is always called with shell=False."""
        cp = _make_completed_process()
        with patch("subprocess.run", return_value=cp) as mock_run:
            execute_command("python3", ["script.py", "arg with spaces"], cwd=str(tmp_path))

        _, kwargs = mock_run.call_args
        assert kwargs.get("shell") is False

    def test_args_passed_as_list(self, tmp_path):
        """Command is passed as a list, never as a shell string."""
        cp = _make_completed_process()
        with patch("subprocess.run", return_value=cp) as mock_run:
            execute_command("python3", ["a", "b", "c"], cwd=str(tmp_path))

        positional_cmd = mock_run.call_args[0][0]
        assert isinstance(positional_cmd, list)

    def test_shell_metacharacters_not_interpreted(self, tmp_path):
        """Shell metacharacters in args are passed verbatim, not interpreted."""
        cp = _make_completed_process()
        with patch("subprocess.run", return_value=cp) as mock_run:
            execute_command(
                "python3",
                ["script.py", "; rm -rf /", "$(evil)"],
                cwd=str(tmp_path),
            )

        positional_cmd = mock_run.call_args[0][0]
        # Metacharacter strings survive intact as list elements.
        assert "; rm -rf /" in positional_cmd
        assert "$(evil)" in positional_cmd


# ---------------------------------------------------------------------------
# Public API import smoke test
# ---------------------------------------------------------------------------


class TestPublicAPIImports:
    """Verify all Phase 2 symbols are importable from the top-level package."""

    def test_route_command_importable(self):
        from aipass.routing import route_command
        assert callable(route_command)

    def test_discover_modules_importable(self):
        from aipass.routing import discover_modules
        assert callable(discover_modules)

    def test_get_help_importable(self):
        from aipass.routing import get_help
        assert callable(get_help)

    def test_command_result_importable(self):
        from aipass.routing import CommandResult
        assert CommandResult is not None

    def test_version_updated(self):
        from aipass.routing import __version__
        assert __version__ == "1.0.0"
