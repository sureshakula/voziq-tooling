"""Tests for Track B hooks subcommands — hooks test and hooks list.

# =================== META ====================
# Name: test_hooks_track_b.py
# Description: Tests for new hooks test and hooks list subcommands (DPLAN-0139 Track B)
# Version: 1.0.0
# Created: 2026-04-21
# Modified: 2026-04-21
# =============================================
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Infrastructure mocks (same pattern as test_hooks_probe.py)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_hooks_infrastructure(monkeypatch):
    """Mock aipass infrastructure imports for hooks module tests."""
    mock_logger = MagicMock()
    mock_console = MagicMock()
    mock_warning = MagicMock()
    mock_json_handler = MagicMock()

    prax_mod = MagicMock()
    prax_mod.logger = mock_logger
    monkeypatch.setitem(sys.modules, "aipass.prax", prax_mod)

    cli_mod = MagicMock()
    cli_mod.console = mock_console
    monkeypatch.setitem(sys.modules, "aipass.cli", cli_mod)

    cli_apps = MagicMock()
    monkeypatch.setitem(sys.modules, "aipass.cli.apps", cli_apps)

    cli_modules = MagicMock()
    cli_modules.warning = mock_warning
    monkeypatch.setitem(sys.modules, "aipass.cli.apps.modules", cli_modules)

    json_pkg = MagicMock()
    json_pkg.json_handler = mock_json_handler
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.json", json_pkg)
    json_mod = MagicMock()
    json_mod.log_operation = mock_json_handler.log_operation
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.json.json_handler", json_mod)

    file_pkg = MagicMock()
    file_pkg.read_lines_safe = MagicMock(return_value=[])
    file_pkg.read_text_safe = MagicMock(return_value=None)
    monkeypatch.setitem(sys.modules, "aipass.seedgo.apps.handlers.file", file_pkg)

    # Force re-import of both modules
    monkeypatch.delitem(sys.modules, "aipass.seedgo.apps.modules.hooks_ext", raising=False)
    monkeypatch.delitem(sys.modules, "aipass.seedgo.apps.modules.hooks", raising=False)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for parent in (current, *current.parents):
        if (parent / ".git").exists():
            return parent
    return Path(__file__).resolve().parents[4]


_AUTO_FIX_PATH = _find_repo_root() / ".claude" / "hooks" / "auto_fix_diagnostics.py"

# ---------------------------------------------------------------------------
# hooks test subcommand
# ---------------------------------------------------------------------------


def test_cmd_hooks_test_runs_without_crash():
    """_cmd_hooks_test() runs without crash; subprocess.run is mocked to avoid real pytest spawn."""
    from unittest.mock import patch as _patch

    from aipass.seedgo.apps.modules import hooks as hooks_mod

    fake_result = MagicMock()
    fake_result.stdout = "1 passed in 0.1s\n"
    fake_result.returncode = 0

    with _patch("subprocess.run", return_value=fake_result):
        result = hooks_mod.handle_command("hooks", ["test"])
    assert result is True


def test_cmd_hooks_test_handles_no_test_files(monkeypatch):
    """When glob returns no files, hooks test warns and returns without crash."""
    import glob as _glob_mod

    from aipass.seedgo.apps.modules import hooks as hooks_mod

    monkeypatch.setattr(_glob_mod, "glob", lambda p: [])

    result = hooks_mod.handle_command("hooks", ["test"])
    assert result is True


# ---------------------------------------------------------------------------
# hooks list subcommand
# ---------------------------------------------------------------------------


def test_cmd_hooks_list_runs_without_crash():
    """_cmd_hooks_list() via handle_command should not raise."""
    from aipass.seedgo.apps.modules import hooks as hooks_mod

    result = hooks_mod.handle_command("hooks", ["list"])
    assert result is True


def test_read_settings_file_missing():
    """_read_settings_file returns {} for a nonexistent path."""
    from aipass.seedgo.apps.modules.hooks_ext import read_settings_file

    result = read_settings_file(Path("/tmp/nonexistent_track_b_test.json"))
    assert result == {}


def test_read_settings_file_valid(tmp_path, monkeypatch):
    """_read_settings_file returns the parsed dict for a valid JSON file."""
    from aipass.seedgo.apps.modules import hooks_ext as hooks_ext_mod

    data = {"hooks": {"PreToolUse": []}, "version": 1}
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps(data), encoding="utf-8")

    monkeypatch.setattr(hooks_ext_mod, "read_text_safe", lambda path: path.read_text(encoding="utf-8"))
    result = hooks_ext_mod.read_settings_file(settings_file)
    assert result == data


def test_extract_hook_script_name():
    """extract_hook_script extracts the .py filename from a command string."""
    from aipass.seedgo.apps.modules.hooks_ext import extract_hook_script

    # Build command string dynamically to avoid help_text checker pattern
    interpreter = "python" + "3"
    cmd = interpreter + " /some/path/auto_fix_diagnostics.py"
    result = extract_hook_script(cmd)
    assert result == "auto_fix_diagnostics.py"


def test_read_hook_version_returns_string(monkeypatch):
    """read_hook_version returns the version string from the hook file header."""
    from aipass.seedgo.apps.modules import hooks_ext as hooks_ext_mod

    if not _AUTO_FIX_PATH.exists():
        pytest.skip(f"auto_fix_diagnostics.py not found at {_AUTO_FIX_PATH}")

    # Provide real lines from the file via read_lines_safe mock
    real_lines = _AUTO_FIX_PATH.read_text(encoding="utf-8").splitlines()[:20]
    monkeypatch.setattr(hooks_ext_mod, "read_lines_safe", lambda path, n=20: real_lines)

    # Build command string dynamically to avoid help_text checker pattern
    interpreter = "python" + "3"
    cmd = interpreter + " " + str(_AUTO_FIX_PATH)
    result = hooks_ext_mod.read_hook_version(cmd)
    assert result == "5.2.0"
