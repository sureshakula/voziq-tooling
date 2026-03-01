"""
Integration tests for the AIPass routing module (Phase 3).

End-to-end tests that exercise the full workflow using real temp directories
with proper branch file structures. All subprocess calls are mocked so no
real Python processes are spawned.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aipass.routing import (
    BranchNotFoundError,
    CommandExecutionError,
    CommandResult,
    HelpResult,
    branch_exists,
    discover_modules,
    get_branch_info,
    get_help,
    initialize_registry,
    list_branches,
    register_branch,
    reset_registry_path,
    resolve_branch,
    route_all,
    route_command,
    set_registry_path,
)
from aipass.routing.discovery import get_system_help


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cp(stdout=b"", stderr=b"", returncode=0):
    """Build a mock subprocess.CompletedProcess."""
    cp = MagicMock(spec=subprocess.CompletedProcess)
    cp.stdout = stdout
    cp.stderr = stderr
    cp.returncode = returncode
    return cp


def _make_branch(root: Path, name: str) -> Path:
    """
    Create a minimal branch directory layout under root.

    Layout:
        root/{name}/
          apps/
            {name}.py        ← entry point
            modules/
              status.py
              info.py
    """
    branch_dir = root / name
    apps_dir = branch_dir / "apps"
    modules_dir = apps_dir / "modules"
    modules_dir.mkdir(parents=True)
    (apps_dir / f"{name}.py").write_text(f"# {name} entry point\n")
    (modules_dir / "status.py").write_text("")
    (modules_dir / "info.py").write_text("")
    return branch_dir


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry(tmp_path):
    """Isolated registry backed by a temp directory."""
    registry_path = tmp_path / "registry.json"
    set_registry_path(registry_path)
    initialize_registry()
    yield tmp_path
    reset_registry_path()


@pytest.fixture
def multi_branch_registry(tmp_path):
    """
    Registry pre-populated with three branches: alpha, beta, gamma.

    Each has a full apps/{name}.py + apps/modules/ structure.
    """
    registry_path = tmp_path / "registry.json"
    set_registry_path(registry_path)
    initialize_registry()

    for name in ("alpha", "beta", "gamma"):
        branch_dir = _make_branch(tmp_path, name)
        register_branch(name, str(branch_dir), "agent")

    yield tmp_path
    reset_registry_path()


# ---------------------------------------------------------------------------
# 1. Full workflow: initialize → register → resolve → discover → help
# ---------------------------------------------------------------------------


class TestFullWorkflow:
    """End-to-end happy-path tests."""

    def test_initialize_register_resolve(self, tmp_path):
        """Complete init → register → resolve cycle."""
        registry_path = tmp_path / "reg.json"
        set_registry_path(registry_path)
        initialize_registry()

        branch_dir = _make_branch(tmp_path, "mybot")
        register_branch("mybot", str(branch_dir), "agent")

        resolved = resolve_branch("@mybot")
        assert Path(resolved) == branch_dir

        reset_registry_path()

    def test_register_multiple_branches_and_list(self, registry, tmp_path):
        """Register several branches and verify list_branches returns all."""
        names = ["alice", "bob", "charlie"]
        for name in names:
            bd = _make_branch(tmp_path, name)
            register_branch(name, str(bd), "agent")

        found = list_branches()
        for name in names:
            assert f"@{name}" in found
        assert len(found) == 3

    def test_resolve_then_discover_then_help(self, multi_branch_registry):
        """Resolve a branch, discover its modules, then get help."""
        # Resolve
        path = resolve_branch("@alpha")
        assert Path(path).is_dir()

        # Discover — mock help output with a Commands section
        help_bytes = b"Usage: alpha.py\n\nCommands:\n  status  Check status\n  info    Show info\n"
        with patch("subprocess.run", return_value=_make_cp(stdout=help_bytes)):
            modules = discover_modules("@alpha")
        assert "status" in modules
        assert "info" in modules

        # Help — returns structured HelpResult
        with patch("subprocess.run", return_value=_make_cp(stdout=help_bytes)):
            result = get_help("@alpha")
        assert isinstance(result, HelpResult)
        assert result.branch == "alpha"
        assert result.command is None
        assert "status" in result.commands_found

    def test_route_command_after_register(self, multi_branch_registry):
        """route_command reaches a registered branch successfully."""
        cp = _make_cp(stdout=b"alpha is running\n", returncode=0)
        with patch("subprocess.run", return_value=cp):
            result = route_command("@alpha", "status")

        assert result.exit_code == 0
        assert "alpha is running" in result.stdout
        assert result.branch == "alpha"
        assert result.command == "status"

    def test_branch_exists_after_register(self, registry, tmp_path):
        """branch_exists returns True immediately after registration."""
        bd = _make_branch(tmp_path, "sentinel")
        register_branch("sentinel", str(bd), "service")

        assert branch_exists("@sentinel")
        assert branch_exists("sentinel")
        assert not branch_exists("@ghost")

    def test_get_branch_info_after_register(self, registry, tmp_path):
        """get_branch_info returns correct metadata after registration."""
        bd = _make_branch(tmp_path, "worker")
        register_branch("worker", str(bd), "service")

        info = get_branch_info("@worker")
        assert info["name"] == "worker"
        assert info["type"] == "service"
        assert info["status"] == "active"
        assert Path(info["path"]) == bd
        assert "created" in info


# ---------------------------------------------------------------------------
# 2. HelpResult structure
# ---------------------------------------------------------------------------


class TestHelpResult:
    """Verify HelpResult dataclass fields and behaviour."""

    def test_help_result_fields(self, multi_branch_registry):
        """HelpResult exposes branch, command, text, commands_found."""
        help_bytes = b"Usage: beta.py\n\nCommands:\n  run   Run a task\n  stop  Stop\n"
        with patch("subprocess.run", return_value=_make_cp(stdout=help_bytes)):
            result = get_help("@beta")

        assert result.branch == "beta"
        assert result.command is None
        assert "Usage" in result.text
        assert isinstance(result.commands_found, list)
        assert "run" in result.commands_found
        assert "stop" in result.commands_found

    def test_help_result_command_level(self, multi_branch_registry):
        """HelpResult.command is set when a specific command is queried."""
        help_bytes = b"Usage: beta.py run [options]\n  --verbose  Verbose output\n"
        with patch("subprocess.run", return_value=_make_cp(stdout=help_bytes)):
            result = get_help("@beta", command="run")

        assert result.command == "run"
        assert "Usage" in result.text

    def test_help_result_stderr_fallback(self, multi_branch_registry):
        """HelpResult.text comes from stderr when stdout is empty."""
        with patch("subprocess.run", return_value=_make_cp(stdout=b"", stderr=b"from stderr\n")):
            result = get_help("@gamma")

        assert "from stderr" in result.text

    def test_help_result_empty_commands_found(self, multi_branch_registry):
        """commands_found is empty when help text has no commands section."""
        with patch("subprocess.run", return_value=_make_cp(stdout=b"No commands here.\n")):
            result = get_help("@gamma")

        assert result.commands_found == []

    def test_help_result_importable_from_package(self):
        """HelpResult is importable directly from aipass.routing."""
        from aipass.routing import HelpResult as HR
        assert HR is HelpResult


# ---------------------------------------------------------------------------
# 3. @all routing: route_all
# ---------------------------------------------------------------------------


class TestRouteAll:
    """Tests for route_all — fan-out command to all active branches."""

    def test_route_all_reaches_all_branches(self, multi_branch_registry):
        """route_all returns a result for every registered branch."""
        cp = _make_cp(stdout=b"ok\n", returncode=0)
        with patch("subprocess.run", return_value=cp):
            results = route_all("status")

        assert set(results.keys()) == {"alpha", "beta", "gamma"}

    def test_route_all_returns_command_results(self, multi_branch_registry):
        """Each value in route_all output is a CommandResult."""
        cp = _make_cp(stdout=b"running\n", returncode=0)
        with patch("subprocess.run", return_value=cp):
            results = route_all("status")

        for branch_name, result in results.items():
            assert isinstance(result, CommandResult)
            assert result.branch == branch_name
            assert result.command == "status"

    def test_route_all_with_args(self, multi_branch_registry):
        """route_all forwards extra args to every branch."""
        cp = _make_cp(stdout=b"verbose\n", returncode=0)
        with patch("subprocess.run", return_value=cp) as mock_run:
            route_all("run", args=["--verbose"])

        # Every call should include --verbose
        for call in mock_run.call_args_list:
            cmd_list = call[0][0]
            assert "--verbose" in cmd_list

    def test_route_all_continues_on_branch_failure(self, multi_branch_registry):
        """route_all continues even when one branch raises CommandExecutionError."""
        call_count = 0

        def side_effect(*a, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise CommandExecutionError("branch exploded")
            return _make_cp(stdout=b"ok\n", returncode=0)

        with patch("subprocess.run", side_effect=side_effect):
            results = route_all("status")

        # All three branches present in results
        assert len(results) == 3

    def test_route_all_failed_branch_has_negative_exit_code(self, multi_branch_registry):
        """A branch that raises an error gets exit_code=-1 in route_all result."""
        def side_effect(*a, **kw):
            raise CommandExecutionError("no entry point")

        with patch("subprocess.run", side_effect=side_effect):
            results = route_all("status")

        for result in results.values():
            assert result.exit_code == -1
            assert result.stderr != ""

    def test_route_all_empty_registry(self, registry):
        """route_all returns empty dict when no branches are registered."""
        results = route_all("status")
        assert results == {}

    def test_route_all_timeout_per_branch(self, multi_branch_registry):
        """route_all forwards the timeout to each branch call."""
        cp = _make_cp(stdout=b"ok\n", returncode=0)
        with patch("subprocess.run", return_value=cp) as mock_run:
            route_all("status", timeout=5)

        for call in mock_run.call_args_list:
            _, kwargs = call
            assert kwargs.get("timeout") == 5

    def test_route_all_importable_from_package(self):
        """route_all is importable from aipass.routing."""
        from aipass.routing import route_all as ra
        assert callable(ra)


# ---------------------------------------------------------------------------
# 4. get_system_help — aggregated help across all branches
# ---------------------------------------------------------------------------


class TestGetSystemHelp:
    """Tests for get_system_help — fan-out help query across all branches."""

    def test_system_help_returns_dict(self, multi_branch_registry):
        """get_system_help returns a dict keyed by branch name."""
        help_bytes = b"Usage: x.py\n\nCommands:\n  status  Check\n"
        with patch("subprocess.run", return_value=_make_cp(stdout=help_bytes)):
            results = get_system_help()

        assert isinstance(results, dict)
        assert set(results.keys()) == {"alpha", "beta", "gamma"}

    def test_system_help_values_are_help_results(self, multi_branch_registry):
        """Each value in get_system_help output is a HelpResult."""
        with patch("subprocess.run", return_value=_make_cp(stdout=b"help\n")):
            results = get_system_help()

        for result in results.values():
            assert isinstance(result, HelpResult)

    def test_system_help_skips_failing_branches(self, multi_branch_registry):
        """get_system_help omits branches whose help command fails."""
        call_count = 0

        def side_effect(*a, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise CommandExecutionError("boom")
            return _make_cp(stdout=b"help\n")

        with patch("subprocess.run", side_effect=side_effect):
            results = get_system_help()

        # At least two of the three branches should succeed
        assert len(results) >= 2

    def test_system_help_empty_when_no_branches(self, registry):
        """get_system_help returns empty dict with no registered branches."""
        results = get_system_help()
        assert results == {}


# ---------------------------------------------------------------------------
# 5. Error recovery — branches disappear mid-operation
# ---------------------------------------------------------------------------


class TestErrorRecovery:
    """Tests for graceful handling of unexpected runtime conditions."""

    def test_resolve_nonexistent_branch_raises(self, registry):
        """Resolving an unregistered branch raises BranchNotFoundError."""
        with pytest.raises(BranchNotFoundError):
            resolve_branch("@ghost")

    def test_route_command_nonexistent_branch_raises(self, registry):
        """Routing to an unregistered branch raises BranchNotFoundError."""
        with pytest.raises(BranchNotFoundError):
            route_command("@ghost", "status")

    def test_discover_modules_nonexistent_branch_raises(self, registry):
        """discover_modules on unregistered branch raises BranchNotFoundError."""
        with pytest.raises(BranchNotFoundError):
            discover_modules("@ghost")

    def test_get_help_nonexistent_branch_raises(self, registry):
        """get_help on unregistered branch raises BranchNotFoundError."""
        with pytest.raises(BranchNotFoundError):
            get_help("@ghost")

    def test_branch_without_entry_point_raises_on_route(self, tmp_path):
        """route_command raises CommandExecutionError when entry point missing."""
        registry_path = tmp_path / "reg.json"
        set_registry_path(registry_path)
        initialize_registry()

        # Register a branch that has NO apps/{name}.py
        no_entry = tmp_path / "bare"
        no_entry.mkdir()
        register_branch("bare", str(no_entry), "agent")

        with pytest.raises(CommandExecutionError, match="Entry point not found"):
            route_command("@bare", "status")

        reset_registry_path()

    def test_branch_without_entry_point_raises_on_help(self, tmp_path):
        """get_help raises CommandExecutionError when entry point missing."""
        registry_path = tmp_path / "reg.json"
        set_registry_path(registry_path)
        initialize_registry()

        no_entry = tmp_path / "bare2"
        no_entry.mkdir()
        register_branch("bare2", str(no_entry), "agent")

        with pytest.raises(CommandExecutionError, match="Entry point not found"):
            get_help("@bare2")

        reset_registry_path()


# ---------------------------------------------------------------------------
# 6. Registry persistence across multiple operations
# ---------------------------------------------------------------------------


class TestRegistryPersistence:
    """Verify the registry file survives multiple read/write cycles."""

    def test_registry_persists_across_register_calls(self, tmp_path):
        """Each register_branch call is durable in the JSON file."""
        registry_path = tmp_path / "persist.json"
        set_registry_path(registry_path)
        initialize_registry()

        for name in ("p1", "p2", "p3"):
            bd = _make_branch(tmp_path, name)
            register_branch(name, str(bd), "agent")

        # Read the raw JSON and verify all branches are there
        with open(registry_path, encoding="utf-8") as fh:
            data = json.load(fh)

        assert "p1" in data["branches"]
        assert "p2" in data["branches"]
        assert "p3" in data["branches"]

        reset_registry_path()

    def test_registry_metadata_updated_on_write(self, tmp_path):
        """Registry metadata.last_updated is refreshed on each write."""
        registry_path = tmp_path / "meta.json"
        set_registry_path(registry_path)
        initialize_registry()

        bd = _make_branch(tmp_path, "meta_agent")
        register_branch("meta_agent", str(bd), "agent")

        with open(registry_path, encoding="utf-8") as fh:
            data = json.load(fh)

        assert "last_updated" in data["metadata"]
        assert data["metadata"]["managed_by"] == "aipass.routing"

        reset_registry_path()

    def test_list_branches_reflects_all_registrations(self, tmp_path):
        """list_branches always reflects the on-disk state."""
        registry_path = tmp_path / "list_test.json"
        set_registry_path(registry_path)
        initialize_registry()

        bd1 = _make_branch(tmp_path, "lx1")
        bd2 = _make_branch(tmp_path, "lx2")
        register_branch("lx1", str(bd1), "agent")

        assert len(list_branches()) == 1

        register_branch("lx2", str(bd2), "agent")

        assert len(list_branches()) == 2
        assert "@lx1" in list_branches()
        assert "@lx2" in list_branches()

        reset_registry_path()
