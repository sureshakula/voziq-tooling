# =================== AIPass ====================
# Name: test_hook_bridge.py
# Description: Tests for hook bridge installer (DPLAN-0141 Phase 2)
# Version: 1.0.0
# Created: 2026-04-22
# Modified: 2026-04-22
# =============================================
"""Tests for hook bridge installer — bridge_handler.py + hook_bridge.py."""

import json
from unittest.mock import patch


# ---------------------------------------------------------------------------
# bridge_handler tests
# ---------------------------------------------------------------------------


def test_resolve_aipass_home_from_env(tmp_path):
    """resolve_aipass_home returns path from AIPASS_HOME env var."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import resolve_aipass_home

    with patch.dict("os.environ", {"AIPASS_HOME": str(tmp_path)}):
        result = resolve_aipass_home()
    assert result == tmp_path


def test_resolve_aipass_home_returns_none_when_all_fail():
    """resolve_aipass_home returns None when env var is bad and importlib fallback disabled."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import resolve_aipass_home

    with (
        patch.dict("os.environ", {"AIPASS_HOME": "/nonexistent/path/xyz"}),
        patch("importlib.util.find_spec", return_value=None),
    ):
        result = resolve_aipass_home()
    assert result is None


def test_is_aipass_hook_entry_detects_marker():
    """is_aipass_hook_entry returns True for entries with _aipass marker."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import is_aipass_hook_entry

    entry = {"_aipass": True, "hooks": [{"type": "command", "command": "echo test"}]}
    assert is_aipass_hook_entry(entry) is True


def test_is_aipass_hook_entry_detects_pattern():
    """is_aipass_hook_entry returns True for entries with AIPass path patterns."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import is_aipass_hook_entry

    entry = {"hooks": [{"type": "command", "command": "python3 /home/user/AIPass/.claude/hooks/foo.py"}]}
    assert is_aipass_hook_entry(entry) is True


def test_is_aipass_hook_entry_detects_env_var():
    """is_aipass_hook_entry returns True for entries using $AIPASS_HOME."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import is_aipass_hook_entry

    entry = {"hooks": [{"type": "command", "command": "python3 $AIPASS_HOME/.claude/hooks/bar.py"}]}
    assert is_aipass_hook_entry(entry) is True


def test_is_aipass_hook_entry_ignores_non_aipass():
    """is_aipass_hook_entry returns False for unrelated entries."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import is_aipass_hook_entry

    entry = {"hooks": [{"type": "command", "command": "echo hello"}]}
    assert is_aipass_hook_entry(entry) is False


def test_count_aipass_hooks_empty():
    """count_aipass_hooks returns 0 for empty settings."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import count_aipass_hooks

    assert count_aipass_hooks({}) == 0
    assert count_aipass_hooks({"hooks": {}}) == 0


def test_count_aipass_hooks_counts_marked():
    """count_aipass_hooks counts entries with _aipass marker."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import count_aipass_hooks

    settings = {
        "hooks": {
            "Stop": [
                {"_aipass": True, "hooks": [{"type": "command", "command": "echo"}]},
                {"hooks": [{"type": "command", "command": "other"}]},
            ]
        }
    }
    assert count_aipass_hooks(settings) == 1


def test_install_hooks_adds_entries():
    """install_hooks adds manifest entries to empty settings."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import (
        AIPASS_HOOK_MANIFEST,
        install_hooks,
    )

    settings = {"hooks": {}}
    settings, added = install_hooks(settings)
    assert added > 0
    total_manifest = sum(len(v) for v in AIPASS_HOOK_MANIFEST.values())
    assert added == total_manifest


def test_install_hooks_idempotent():
    """install_hooks does not duplicate entries on second call."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import install_hooks

    settings = {"hooks": {}}
    settings, first_added = install_hooks(settings)
    settings, second_added = install_hooks(settings)
    assert first_added > 0
    assert second_added == 0


def test_install_hooks_preserves_existing():
    """install_hooks preserves non-AIPass hooks in same event."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import install_hooks

    user_hook = {"hooks": [{"type": "command", "command": "echo user-hook"}]}
    settings = {"hooks": {"Stop": [user_hook]}}
    settings, added = install_hooks(settings)
    stop_entries = settings["hooks"]["Stop"]
    assert user_hook in stop_entries
    assert added > 0


def test_install_hooks_skips_event_with_existing_aipass():
    """install_hooks skips events that already contain AIPass entries."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import install_hooks

    existing = {
        "_aipass": True,
        "hooks": [{"type": "command", "command": "python3 $AIPASS_HOME/.claude/hooks/stop_sound.py"}],
    }
    settings = {"hooks": {"Stop": [existing]}}
    settings, added = install_hooks(settings)
    assert len(settings["hooks"]["Stop"]) == 1


def test_uninstall_hooks_removes_marked():
    """uninstall_hooks removes entries with _aipass marker."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import uninstall_hooks

    settings = {
        "hooks": {
            "Stop": [
                {"_aipass": True, "hooks": [{"type": "command", "command": "echo aipass"}]},
                {"hooks": [{"type": "command", "command": "echo user"}]},
            ]
        }
    }
    settings, removed = uninstall_hooks(settings)
    assert removed == 1
    assert len(settings["hooks"]["Stop"]) == 1
    assert settings["hooks"]["Stop"][0]["hooks"][0]["command"] == "echo user"


def test_uninstall_hooks_removes_empty_events():
    """uninstall_hooks deletes event keys that become empty."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import uninstall_hooks

    settings = {
        "hooks": {
            "Stop": [
                {"_aipass": True, "hooks": [{"type": "command", "command": "echo"}]},
            ]
        }
    }
    settings, removed = uninstall_hooks(settings)
    assert removed == 1
    assert "Stop" not in settings["hooks"]


def test_uninstall_hooks_preserves_non_aipass():
    """uninstall_hooks never touches non-AIPass entries."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import uninstall_hooks

    user_hook = {"hooks": [{"type": "command", "command": "echo user"}]}
    settings = {"hooks": {"Stop": [user_hook]}}
    settings, removed = uninstall_hooks(settings)
    assert removed == 0
    assert settings["hooks"]["Stop"] == [user_hook]


def test_ensure_aipass_env_adds_when_missing():
    """ensure_aipass_env adds AIPASS_HOME to env section."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import ensure_aipass_env

    settings = {}
    added = ensure_aipass_env(settings, "/home/user/AIPass")
    assert added is True
    assert settings["env"]["AIPASS_HOME"] == "/home/user/AIPass"


def test_ensure_aipass_env_skips_when_present():
    """ensure_aipass_env does not overwrite existing AIPASS_HOME."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import ensure_aipass_env

    settings = {"env": {"AIPASS_HOME": "/existing/path"}}
    added = ensure_aipass_env(settings, "/new/path")
    assert added is False
    assert settings["env"]["AIPASS_HOME"] == "/existing/path"


def test_read_settings_returns_empty_for_missing(tmp_path):
    """read_settings returns {} when file does not exist."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import read_settings

    result = read_settings(tmp_path / "missing.json")
    assert result == {}


def test_read_settings_parses_json(tmp_path):
    """read_settings parses valid JSON."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import read_settings

    f = tmp_path / "settings.json"
    f.write_text(json.dumps({"hooks": {}}), encoding="utf-8")
    result = read_settings(f)
    assert result == {"hooks": {}}


def test_write_settings_creates_backup(tmp_path):
    """write_settings creates .json.bak before overwriting."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import write_settings

    f = tmp_path / "settings.json"
    f.write_text('{"old": true}', encoding="utf-8")
    write_settings(f, {"new": True})
    bak = tmp_path / "settings.json.bak"
    assert bak.exists()
    assert json.loads(bak.read_text()) == {"old": True}
    assert json.loads(f.read_text()) == {"new": True}


def test_write_settings_creates_parent_dirs(tmp_path):
    """write_settings creates parent directories if needed."""
    from aipass.seedgo.apps.handlers.hooks.bridge_handler import write_settings

    f = tmp_path / "sub" / "dir" / "settings.json"
    result = write_settings(f, {"test": True})
    assert result is True
    assert f.exists()


# ---------------------------------------------------------------------------
# hook_bridge module tests
# ---------------------------------------------------------------------------


def test_handle_command_rejects_non_bridge():
    """handle_command returns False for non-bridge commands."""
    from aipass.seedgo.apps.modules.hook_bridge import handle_command

    assert handle_command("audit", ["install"]) is False
    assert handle_command("hooks", ["install"]) is False


def test_handle_command_accepts_bridge():
    """handle_command returns True for bridge command."""
    from aipass.seedgo.apps.modules.hook_bridge import handle_command

    assert handle_command("bridge", []) is True


def test_handle_command_accepts_help():
    """handle_command returns True for bridge --help."""
    from aipass.seedgo.apps.modules.hook_bridge import handle_command

    assert handle_command("bridge", ["--help"]) is True
    assert handle_command("bridge", ["-h"]) is True
    assert handle_command("bridge", ["help"]) is True


def test_handle_command_routes_install():
    """handle_command routes 'install' subcommand."""
    from aipass.seedgo.apps.modules.hook_bridge import handle_command

    with patch("aipass.seedgo.apps.modules.hook_bridge._run_install"):
        result = handle_command("bridge", ["install"])
    assert result is True


def test_handle_command_routes_uninstall():
    """handle_command routes 'uninstall' subcommand."""
    from aipass.seedgo.apps.modules.hook_bridge import handle_command

    with patch("aipass.seedgo.apps.modules.hook_bridge._run_uninstall"):
        result = handle_command("bridge", ["uninstall"])
    assert result is True


def test_handle_command_routes_status():
    """handle_command routes 'status' subcommand."""
    from aipass.seedgo.apps.modules.hook_bridge import handle_command

    with patch("aipass.seedgo.apps.modules.hook_bridge._run_status"):
        result = handle_command("bridge", ["status"])
    assert result is True


def test_handle_command_unknown_subcommand():
    """handle_command returns True for unknown subcommand (shows help)."""
    from aipass.seedgo.apps.modules.hook_bridge import handle_command

    assert handle_command("bridge", ["bogus"]) is True
