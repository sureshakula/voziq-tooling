"""Tests for Track A hook scripts — auto_fix_diagnostics, pre_edit_gate, subagent_stop_gate.

# =================== META ====================
# Name: test_hooks_track_a.py
# Description: Track A hook tests — DPLAN-0139 coverage for auto_fix, pre_edit_gate, subagent_stop
# Version: 1.0.0
# Created: 2026-04-20
# Modified: 2026-04-20
# =============================================
"""

import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers — hook loader
# ---------------------------------------------------------------------------


def _find_repo_root() -> Path:
    """Walk up from this file to find the git repo root."""
    current = Path(__file__).resolve().parent
    for parent in (current, *current.parents):
        if (parent / ".git").exists():
            return parent
    return Path(__file__).resolve().parents[4]  # fallback


HOOKS_DIR = _find_repo_root() / ".claude" / "hooks"


def _load_hook(name: str):
    """Import a hook script by filename via importlib (outside package)."""
    path = HOOKS_DIR / name
    if not path.exists():
        pytest.skip(f"Hook script not found: {path}")
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# auto_fix_diagnostics.py tests
# ---------------------------------------------------------------------------


def test_auto_fix_skips_non_edit_tool(capsys):
    """stdin with tool_name=Read → no output (not an edit tool)."""
    mod = _load_hook("auto_fix_diagnostics.py")
    payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "/tmp/foo.py"}})
    with patch("sys.stdin", io.StringIO(payload)):
        mod.main()
    captured = capsys.readouterr()
    assert captured.out == ""


def test_auto_fix_skips_non_py_file(capsys):
    """stdin with tool_name=Edit, file_path ending .md → no output (skipped extension)."""
    mod = _load_hook("auto_fix_diagnostics.py")
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "/tmp/foo.md"}})
    with patch("sys.stdin", io.StringIO(payload)):
        mod.main()
    captured = capsys.readouterr()
    assert captured.out == ""


def test_auto_fix_does_not_crash_empty_stdin():
    """Empty/malformed JSON on stdin → no exception raised."""
    mod = _load_hook("auto_fix_diagnostics.py")
    with patch("sys.stdin", io.StringIO("")):
        mod.main()  # must not raise


def test_auto_fix_does_not_crash_missing_fields():
    """Valid JSON but no tool_name → no exception raised."""
    mod = _load_hook("auto_fix_diagnostics.py")
    payload = json.dumps({"some_other_key": "value"})
    with patch("sys.stdin", io.StringIO(payload)):
        mod.main()  # must not raise


def test_auto_fix_label_is_auto_fix(tmp_path, capsys):
    """When run_python_checks returns an error, output contains [AUTO-FIX] label."""
    mod = _load_hook("auto_fix_diagnostics.py")

    fake_py = tmp_path / "fake.py"
    fake_py.write_text("x = 1\n", encoding="utf-8")

    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(fake_py)}})

    with (
        patch("sys.stdin", io.StringIO(payload)),
        patch.object(mod, "run_python_checks", return_value=["LINT: E501 line too long"]),
        patch.object(mod, "run_seedgo_checklist", return_value=[]),
        patch.object(mod, "run_pyright_check", return_value=[]),
        patch.object(mod, "run_ruff_lint_structured", return_value=[]),
        patch.object(mod, "save_diagnostics_state"),
    ):
        mod.main()

    captured = capsys.readouterr()
    assert captured.out.strip() != ""
    output = json.loads(captured.out)
    context = output["hookSpecificOutput"]["additionalContext"]
    assert "[AUTO-FIX]" in context
    assert "[AUTO-FIX]" in output["systemMessage"]


def test_run_pyright_check_returns_empty_on_file_not_found():
    """run_pyright_check returns [] when pyright binary is missing."""
    mod = _load_hook("auto_fix_diagnostics.py")
    with patch("subprocess.run", side_effect=FileNotFoundError("pyright not found")):
        result = mod.run_pyright_check("/tmp/some_file.py")
    assert result == []


def test_run_pyright_check_returns_empty_on_timeout():
    """run_pyright_check returns [] on timeout."""
    import subprocess

    mod = _load_hook("auto_fix_diagnostics.py")
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pyright", 15)):
        result = mod.run_pyright_check("/tmp/some_file.py")
    assert result == []


def test_run_pyright_check_skips_hook_files():
    """run_pyright_check returns [] for hook files without calling subprocess."""
    mod = _load_hook("auto_fix_diagnostics.py")
    mock_run = MagicMock()
    with patch("subprocess.run", mock_run):
        result = mod.run_pyright_check("/home/user/.claude/hooks/some_hook.py")
    mock_run.assert_not_called()
    assert result == []


# ---------------------------------------------------------------------------
# pre_edit_gate.py tests
# (pre_edit_gate lives in ~/.claude/hooks — load from global location)
# ---------------------------------------------------------------------------


GLOBAL_HOOKS_DIR = Path.home() / ".claude" / "hooks"


def _load_global_hook(name: str):
    """Import a hook script from the global ~/.claude/hooks/ directory."""
    path = GLOBAL_HOOKS_DIR / name
    if not path.exists():
        pytest.skip(f"Global hook script not found: {path}")
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_gate_allows_no_state_file(tmp_path, capsys, monkeypatch):
    """No state file present → no output (allow)."""
    mod = _load_global_hook("pre_edit_gate.py")
    monkeypatch.setattr(mod, "STATE_FILE", tmp_path / "no_such_state.json")

    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "/tmp/seedgo/foo.py"}})
    with patch("sys.stdin", io.StringIO(payload)):
        mod.main()

    captured = capsys.readouterr()
    assert captured.out == ""


def test_gate_allows_same_file(tmp_path, capsys, monkeypatch):
    """State has error for file A, editing file A → allow (no block output)."""
    mod = _load_global_hook("pre_edit_gate.py")

    errored_file = tmp_path / "foo.py"
    errored_file.write_text("x = 1\n", encoding="utf-8")

    state = {"file": str(errored_file), "errors": [{"line": 1, "message": "some error"}]}
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(state), encoding="utf-8")
    monkeypatch.setattr(mod, "STATE_FILE", state_file)

    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(errored_file)}})
    with patch("sys.stdin", io.StringIO(payload)):
        mod.main()

    captured = capsys.readouterr()
    assert captured.out == ""


def test_gate_blocks_different_file_same_branch(tmp_path, capsys, monkeypatch):
    """State has error for seedgo/foo.py, editing seedgo/bar.py → block + sys.exit(2)."""
    mod = _load_global_hook("pre_edit_gate.py")

    # Use real AIPass src paths so _get_branch works
    aipass_src = Path("/home/patrick/Projects/AIPass/src/aipass")
    errored_file = str(aipass_src / "seedgo" / "foo.py")
    edit_target = str(aipass_src / "seedgo" / "bar.py")

    state = {"file": errored_file, "errors": [{"line": 5, "message": "type error here"}]}
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(state), encoding="utf-8")
    monkeypatch.setattr(mod, "STATE_FILE", state_file)

    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": edit_target}})
    with patch("sys.stdin", io.StringIO(payload)):
        with pytest.raises(SystemExit) as exc_info:
            mod.main()

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert captured.out.strip() != ""
    output = json.loads(captured.out)
    assert output["decision"] == "block"


def test_gate_allows_different_branch(tmp_path, capsys, monkeypatch):
    """State has error for flow/foo.py, editing seedgo/bar.py → allow (different branches)."""
    mod = _load_global_hook("pre_edit_gate.py")

    aipass_src = Path("/home/patrick/Projects/AIPass/src/aipass")
    errored_file = str(aipass_src / "flow" / "foo.py")
    edit_target = str(aipass_src / "seedgo" / "bar.py")

    state = {"file": errored_file, "errors": [{"line": 1, "message": "error in flow"}]}
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(state), encoding="utf-8")
    monkeypatch.setattr(mod, "STATE_FILE", state_file)

    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": edit_target}})
    with patch("sys.stdin", io.StringIO(payload)):
        mod.main()

    captured = capsys.readouterr()
    assert captured.out == ""


def test_gate_does_not_crash_malformed_stdin(monkeypatch, tmp_path):
    """Bad JSON on stdin → no exception raised."""
    mod = _load_global_hook("pre_edit_gate.py")
    monkeypatch.setattr(mod, "STATE_FILE", tmp_path / "no_state.json")

    with patch("sys.stdin", io.StringIO("not json!!!!")):
        mod.main()  # must not raise


def test_gate_allows_non_edit_tool(tmp_path, capsys, monkeypatch):
    """Non-edit tool_name → no output regardless of state."""
    mod = _load_global_hook("pre_edit_gate.py")

    aipass_src = Path("/home/patrick/Projects/AIPass/src/aipass")
    errored_file = str(aipass_src / "seedgo" / "foo.py")
    edit_target = str(aipass_src / "seedgo" / "bar.py")

    state = {"file": errored_file, "errors": [{"line": 1, "message": "error"}]}
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(state), encoding="utf-8")
    monkeypatch.setattr(mod, "STATE_FILE", state_file)

    payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": edit_target}})
    with patch("sys.stdin", io.StringIO(payload)):
        mod.main()

    captured = capsys.readouterr()
    assert captured.out == ""


# ---------------------------------------------------------------------------
# subagent_stop_gate.py tests
# ---------------------------------------------------------------------------


def test_subagent_gate_no_crash_empty_stdin():
    """Bad JSON on stdin → no exception raised."""
    mod = _load_hook("subagent_stop_gate.py")
    with patch("sys.stdin", io.StringIO("bad json")):
        mod.main()  # must not raise


def test_subagent_gate_no_crash_no_files(capsys):
    """Valid stdin but no modified files → no exception, no block output."""
    mod = _load_hook("subagent_stop_gate.py")
    payload = json.dumps({"stop_hook_active": True})

    with (
        patch("sys.stdin", io.StringIO(payload)),
        patch.object(mod, "get_modified_py_files", return_value=[]),
    ):
        mod.main()

    captured = capsys.readouterr()
    assert captured.out == ""


def test_subagent_gate_no_block_when_no_violations(capsys):
    """Modified files present but no seedgo violations → no block output."""
    mod = _load_hook("subagent_stop_gate.py")
    payload = json.dumps({"stop_hook_active": True})

    with (
        patch("sys.stdin", io.StringIO(payload)),
        patch.object(mod, "get_modified_py_files", return_value=["/tmp/foo.py"]),
        patch.object(mod, "run_seedgo_checklist", return_value=[]),
    ):
        mod.main()

    captured = capsys.readouterr()
    assert captured.out == ""


def test_subagent_gate_blocks_on_violations(capsys):
    """Modified files with seedgo violations → block decision in output."""
    mod = _load_hook("subagent_stop_gate.py")
    payload = json.dumps({"stop_hook_active": True})

    with (
        patch("sys.stdin", io.StringIO(payload)),
        patch.object(mod, "get_modified_py_files", return_value=["/tmp/foo.py"]),
        patch.object(mod, "run_seedgo_checklist", return_value=["open() without encoding='utf-8'"]),
    ):
        mod.main()

    captured = capsys.readouterr()
    assert captured.out.strip() != ""
    output = json.loads(captured.out)
    assert output["decision"] == "block"
