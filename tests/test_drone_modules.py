"""
Tests for the drone module routing system (aipass.drone.modules).

Covers:
  - Module registry: list, lookup, register
  - Module info retrieval
  - Module command routing
  - Module help retrieval
  - CLI integration: drone systems shows modules, drone @seedgo routes correctly
"""

from __future__ import annotations

from unittest.mock import patch

from aipass.drone.cli import main
from aipass.drone.modules import (
    ModuleInfo,
    get_module_help,
    get_module_info,
    is_module,
    list_modules,
    register_module,
    route_module_command,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_cli(*args: str) -> tuple[int, str, str]:
    """Call main() with the given argv, capturing stdout/stderr and exit code."""
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    class _Cap:
        def __init__(self, buf: list[str]) -> None:
            self._buf = buf

        def write(self, s: str) -> int:
            self._buf.append(s)
            return len(s)

        def flush(self) -> None:
            pass

    exit_code = 0

    def _exit(code: int = 0) -> None:
        nonlocal exit_code
        exit_code = code
        raise SystemExit(code)

    with (
        patch("sys.argv", ["drone", *args]),
        patch("sys.stdout", _Cap(stdout_lines)),
        patch("sys.stderr", _Cap(stderr_lines)),
        patch("sys.exit", side_effect=_exit),
    ):
        try:
            main()
        except SystemExit:
            pass

    return exit_code, "".join(stdout_lines), "".join(stderr_lines)


# ---------------------------------------------------------------------------
# Module registry
# ---------------------------------------------------------------------------


class TestModuleRegistry:
    """Test the internal module registry."""

    def test_seedgo_is_registered(self):
        """seedgo is in the default module registry."""
        assert is_module("seedgo")

    def test_unknown_module_not_registered(self):
        """Unknown names return False."""
        assert not is_module("nonexistent")

    def test_list_modules_includes_seedgo(self):
        """list_modules includes seedgo."""
        modules = list_modules()
        assert "seedgo" in modules

    def test_list_modules_returns_sorted(self):
        """list_modules returns sorted names."""
        modules = list_modules()
        assert modules == sorted(modules)

    def test_register_module_adds_new(self):
        """register_module adds a new module."""
        register_module("test_mod", "test.path.adapter")
        assert is_module("test_mod")
        # Clean up
        from aipass.drone.modules import _MODULE_REGISTRY
        del _MODULE_REGISTRY["test_mod"]


class TestModuleInfo:
    """Test module info retrieval."""

    def test_seedgo_info_returns_module_info(self):
        """get_module_info for seedgo returns valid ModuleInfo."""
        info = get_module_info("seedgo")
        assert info is not None
        assert isinstance(info, ModuleInfo)
        assert info.name == "seedgo"
        assert info.version == "1.0.0"
        assert info.description != ""

    def test_unknown_module_returns_none(self):
        """get_module_info for unknown module returns None."""
        assert get_module_info("nonexistent") is None

    def test_unimportable_module_returns_none(self):
        """get_module_info returns None if adapter can't be imported."""
        register_module("broken", "nonexistent.module.path")
        info = get_module_info("broken")
        assert info is None
        # Clean up
        from aipass.drone.modules import _MODULE_REGISTRY
        del _MODULE_REGISTRY["broken"]


# ---------------------------------------------------------------------------
# Module command routing
# ---------------------------------------------------------------------------


class TestModuleRouting:
    """Test routing commands to modules."""

    def test_route_seedgo_list(self):
        """route_module_command to seedgo 'list' returns output."""
        result = route_module_command("seedgo", "list")
        assert isinstance(result, dict)
        assert "stdout" in result
        assert "exit_code" in result
        # seedgo list should succeed and show plugins
        assert result["exit_code"] == 0
        assert "plugin" in result["stdout"].lower() or "PLUGIN" in result["stdout"]

    def test_route_unknown_command(self):
        """Unknown seedgo command returns error."""
        result = route_module_command("seedgo", "nonexistent")
        assert result["exit_code"] == 1
        assert "unknown command" in result["stderr"]

    def test_route_unknown_module_raises(self):
        """Routing to unregistered module raises KeyError."""
        import pytest
        with pytest.raises(KeyError):
            route_module_command("nonexistent", "list")


# ---------------------------------------------------------------------------
# Module help
# ---------------------------------------------------------------------------


class TestModuleHelp:
    """Test module help retrieval."""

    def test_seedgo_help_returns_text(self):
        """get_module_help for seedgo returns non-empty help text."""
        help_text = get_module_help("seedgo")
        assert help_text != ""
        assert "seedgo" in help_text
        assert "check" in help_text or "audit" in help_text

    def test_unknown_module_help_returns_empty(self):
        """get_module_help for unknown module returns empty string."""
        assert get_module_help("nonexistent") == ""


# ---------------------------------------------------------------------------
# CLI integration — drone systems shows modules
# ---------------------------------------------------------------------------


class TestCLISystemsModules:
    """drone systems includes modules."""

    def test_systems_shows_modules(self):
        """drone systems output includes modules section."""
        with patch("aipass.drone.cli.list_branches", return_value=[]):
            code, out, _ = _run_cli("systems")
        assert code == 0
        assert "Modules" in out
        assert "@seedgo" in out

    def test_systems_shows_module_description(self):
        """drone systems shows module descriptions."""
        with patch("aipass.drone.cli.list_branches", return_value=[]):
            code, out, _ = _run_cli("systems")
        assert "standards" in out.lower() or "Standards" in out

    def test_systems_shows_both_modules_and_branches(self):
        """drone systems shows both modules and branches."""
        with patch("aipass.drone.cli.list_branches", return_value=["@flow", "@prax"]):
            code, out, _ = _run_cli("systems")
        assert code == 0
        assert "Modules" in out
        assert "Branches" in out
        assert "@seedgo" in out
        assert "@flow" in out


# ---------------------------------------------------------------------------
# CLI integration — drone @seedgo routes to module
# ---------------------------------------------------------------------------


class TestCLIModuleRouting:
    """drone @seedgo commands route through module system."""

    def test_seedgo_help(self):
        """drone @seedgo --help shows seedgo help text."""
        code, out, _ = _run_cli("@seedgo", "--help")
        assert code == 0
        assert "seedgo" in out
        assert "check" in out

    def test_seedgo_no_args_shows_help(self):
        """drone @seedgo with no command shows help."""
        code, out, _ = _run_cli("@seedgo")
        assert code == 0
        assert "seedgo" in out

    def test_seedgo_list(self):
        """drone @seedgo list shows plugins."""
        code, out, _ = _run_cli("@seedgo", "list")
        assert code == 0
        assert "plugin" in out.lower() or "PLUGIN" in out

    def test_seedgo_unknown_command(self):
        """drone @seedgo nonexistent exits with error."""
        code, _, err = _run_cli("@seedgo", "nonexistent")
        assert code == 1
        assert "unknown command" in err

    def test_seedgo_check_specific_file(self):
        """drone @seedgo check on a file runs checks."""
        code, out, _ = _run_cli("@seedgo", "check", "src/seedgo/__init__.py")
        assert code == 0 or code == 1  # May pass or fail, but should run
        # Should produce output from seedgo
        assert out != "" or _ != ""

    def test_module_takes_priority_over_branch(self):
        """Module routing takes priority over branch registry."""
        # Even if a branch named 'seedgo' existed, the module should handle it
        # We verify by NOT mocking route_command — if branch routing were tried,
        # it would fail because no registry exists
        code, out, _ = _run_cli("@seedgo", "--help")
        assert code == 0
        assert "seedgo" in out
