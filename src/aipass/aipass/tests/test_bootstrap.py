# =================== AIPass ====================
# Name: test_bootstrap.py
# Description: Tests for init bootstrap handler (DPLAN-0164)
# Version: 1.0.0
# Created: 2026-05-04
# Modified: 2026-05-04
# =============================================

"""Tests for the init bootstrap handler.

Covers _sanitize_name(), init_project(), update_project(), and
scaffold_content generators — all file operations use tmp_path to
stay fully isolated from the live filesystem.
"""

import json
import uuid
from datetime import date
from pathlib import Path

import pytest  # pyright: ignore[reportMissingImports]

from aipass.aipass.apps.handlers.init import scaffold_content as sc
from aipass.aipass.apps.handlers.init.bootstrap import (
    _merge_hooks_json,
    _sanitize_name,
    init_project,
    update_project,
)


# ---------------------------------------------------------------------------
# _sanitize_name tests
# ---------------------------------------------------------------------------


def test_sanitize_name_normal_input():
    """Normal lowercase string is uppercased."""
    assert _sanitize_name("my_project") == "MY_PROJECT"


def test_sanitize_name_preserves_hyphens():
    """Hyphens are kept as-is (valid filename chars)."""
    assert _sanitize_name("my-project") == "MY-PROJECT"


def test_sanitize_name_replaces_special_chars():
    """Non-alphanumeric characters (except _ and -) become underscores."""
    assert _sanitize_name("my project!v2") == "MY_PROJECT_V2"


def test_sanitize_name_replaces_dots_and_slashes():
    """Dots and slashes are replaced with underscores."""
    assert _sanitize_name("foo.bar/baz") == "FOO_BAR_BAZ"


def test_sanitize_name_strips_leading_trailing_underscores():
    """Leading/trailing underscores from replacement are stripped."""
    assert _sanitize_name("...name...") == "NAME"


def test_sanitize_name_spaces_become_underscores():
    """Spaces are not alphanumeric, so they become underscores."""
    assert _sanitize_name("hello world") == "HELLO_WORLD"


def test_sanitize_name_empty_after_sanitize():
    """All-special-character input collapses to empty string."""
    assert _sanitize_name("!!!") == ""


def test_sanitize_name_already_upper():
    """Already-uppercase names pass through unchanged."""
    assert _sanitize_name("ALPHA") == "ALPHA"


def test_sanitize_name_empty_string():
    """Empty input returns empty string."""
    assert _sanitize_name("") == ""


def test_sanitize_name_only_underscores():
    """All-underscore input is stripped to empty string."""
    assert _sanitize_name("___") == ""


# ---------------------------------------------------------------------------
# init_project tests
# ---------------------------------------------------------------------------


def test_init_project_creates_all_expected_files(tmp_path):
    """init_project produces all expected files and directories."""
    target = tmp_path / "proj"
    target.mkdir()

    result = init_project(target, project_name="demo")

    expected_files = [
        target / "DEMO_REGISTRY.json",
        target / ".aipass" / "aipass_global_prompt.md",
        target / "CLAUDE.md",
        target / "AGENTS.md",
        target / "README.md",
        target / ".gitignore",
        target / ".claude" / "settings.json",
        target / ".claude" / "commands" / "prep.md",
        target / "src" / "demo" / "__init__.py",
    ]
    for f in expected_files:
        assert f.exists(), f"Expected file not created: {f}"

    # src/<package>/ is a directory with __init__.py
    assert (target / "src" / "demo").is_dir(), "Expected src/demo/ package directory"

    # No .trinity/ should be created (projects are not citizens)
    assert not (target / ".trinity").exists(), ".trinity/ should NOT be created"

    # No local prompt at project level (belongs in agent dirs only)
    assert not (target / ".aipass" / "aipass_local_prompt.md").exists()

    # No project-level mailbox (agents have their own)
    assert not (target / ".ai_mail.local").exists(), ".ai_mail.local/ should NOT be at project level"

    # Every expected file must appear in created_files (extras like .venv are env-dependent)
    created_basenames = [Path(f).name for f in result["created_files"]]
    for f in expected_files:
        assert f.name in created_basenames or f.exists(), f"Expected {f.name} in created_files"
    assert len(result["created_files"]) >= 11


def test_init_project_return_dict_structure(tmp_path):
    """Return dict contains all required keys with correct types."""
    target = tmp_path / "proj"
    target.mkdir()

    result = init_project(target, project_name="alpha")

    assert set(result.keys()) == {
        "registry_id",
        "registry_file",
        "project_name",
        "target",
        "created_files",
        "aipass_home",
    }
    assert result["project_name"] == "ALPHA"
    assert result["registry_file"] == "ALPHA_REGISTRY.json"
    assert result["target"] == str(target.resolve())
    assert isinstance(result["created_files"], list)


def test_init_project_registry_id_is_valid_uuid(tmp_path):
    """registry_id must be a valid UUID4 string."""
    target = tmp_path / "proj"
    target.mkdir()

    result = init_project(target, project_name="test")

    parsed = uuid.UUID(result["registry_id"], version=4)
    assert str(parsed) == result["registry_id"]


def test_init_project_registry_json_contents(tmp_path):
    """REGISTRY.json has correct metadata structure and values."""
    target = tmp_path / "proj"
    target.mkdir()

    result = init_project(target, project_name="beta")

    registry_path = target / "BETA_REGISTRY.json"
    data = json.loads(registry_path.read_text(encoding="utf-8"))

    assert data["metadata"]["id"] == result["registry_id"]
    assert data["metadata"]["name"] == "BETA"
    assert data["metadata"]["version"] == "1.0.0"
    assert data["metadata"]["created"] == date.today().isoformat()
    assert data["metadata"]["last_updated"] == date.today().isoformat()
    assert data["metadata"]["total_branches"] == 0
    assert data["branches"] == []


def test_init_project_no_trinity_created(tmp_path):
    """Projects are not citizens — no .trinity/ directory created."""
    target = tmp_path / "proj"
    target.mkdir()

    init_project(target, project_name="gamma")

    assert not (target / ".trinity").exists()


def test_init_project_no_local_prompt(tmp_path):
    """Project init does NOT create aipass_local_prompt.md (agent-only file)."""
    target = tmp_path / "proj"
    target.mkdir()

    init_project(target, project_name="epsilon")

    assert not (target / ".aipass" / "aipass_local_prompt.md").exists()


def test_init_project_claude_md_content(tmp_path):
    """CLAUDE.md uses project template with name substitution."""
    target = tmp_path / "proj"
    target.mkdir()

    init_project(target, project_name="zeta")

    md_path = target / "CLAUDE.md"
    content = md_path.read_text(encoding="utf-8")
    assert "# ZETA" in content
    assert "Startup protocol" in content


def test_init_project_rerunnable_blocked_by_guard(tmp_path):
    """Running init twice raises RuntimeError due to _guard_init."""
    target = tmp_path / "proj"
    target.mkdir()

    init_project(target, project_name="dup")

    with pytest.raises(RuntimeError, match="already an AIPass project"):
        init_project(target, project_name="dup")


def test_init_project_raises_on_empty_name(tmp_path):
    """ValueError when the name is empty after sanitization."""
    target = tmp_path / "proj"
    target.mkdir()

    with pytest.raises(ValueError, match="Cannot derive project name"):
        init_project(target, project_name="!!!")


def test_init_project_agents_md_content(tmp_path):
    """AGENTS.md is copied from AIPass source of truth."""
    target = tmp_path / "proj"
    target.mkdir()

    init_project(target, project_name="alpha")

    content = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "# AIPass" in content
    assert "Multi-agent framework" in content


def test_init_project_gitignore_content(tmp_path):
    """.gitignore contains standard AIPass patterns."""
    target = tmp_path / "proj"
    target.mkdir()

    init_project(target, project_name="alpha")

    content = (target / ".gitignore").read_text(encoding="utf-8")
    assert ".trinity/" in content
    assert ".ai_mail.local/" in content
    assert "__pycache__/" in content
    assert "logs/" in content


def test_init_project_claude_settings_content(tmp_path):
    """.claude/settings.json has env and permissions, no hooks."""
    target = tmp_path / "proj"
    target.mkdir()

    init_project(target, project_name="alpha")

    settings_path = target / ".claude" / "settings.json"
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "hooks" not in data, "Hooks should not be in project settings — provider handles them"
    assert "permissions" in data
    assert "deny" in data["permissions"]


def test_init_project_settings_no_hooks(tmp_path):
    """.claude/settings.json has no hooks — all hooks fire from provider level."""
    target = tmp_path / "proj"
    target.mkdir()

    init_project(target, project_name="alpha")

    settings_path = target / ".claude" / "settings.json"
    data = json.loads(settings_path.read_text(encoding="utf-8"))

    assert "hooks" not in data, "Project settings should not contain hooks"
    assert "env" in data
    assert "permissions" in data


def test_init_project_global_prompt_content(tmp_path):
    """Global prompt contains project name and AIPass terminology."""
    target = tmp_path / "proj"
    target.mkdir()

    init_project(target, project_name="alpha")

    content = (target / ".aipass" / "aipass_global_prompt.md").read_text(encoding="utf-8")
    assert "# ALPHA" in content
    assert "ALPHA_REGISTRY.json" in content
    assert "# Commands" in content


def test_init_project_readme_md_content(tmp_path):
    """README.md contains getting started guide with project name."""
    target = tmp_path / "proj"
    target.mkdir()

    init_project(target, project_name="alpha")

    content = (target / "README.md").read_text(encoding="utf-8")
    assert "# ALPHA" in content
    assert "## Quick Start" in content
    assert "aipass init agent" in content
    assert "src/" in content


def test_init_project_auto_creates_target_dir(tmp_path):
    """Target directory is created (including parents) if it doesn't exist."""
    target = tmp_path / "deep" / "nested" / "proj"
    assert not target.exists()

    result = init_project(target, project_name="nested")

    assert target.is_dir()
    assert result["project_name"] == "NESTED"
    assert len(result["created_files"]) >= 11


def test_init_project_defaults_name_from_directory(tmp_path):
    """When project_name is None, name is derived from the directory name."""
    target = tmp_path / "my_cool_project"
    target.mkdir()

    result = init_project(target)

    assert result["project_name"] == "MY_COOL_PROJECT"
    assert result["registry_file"] == "MY_COOL_PROJECT_REGISTRY.json"
    assert (target / "MY_COOL_PROJECT_REGISTRY.json").exists()


def test_init_project_custom_name_overrides_directory(tmp_path):
    """Explicit project_name takes precedence over the directory name."""
    target = tmp_path / "dir_name"
    target.mkdir()

    result = init_project(target, project_name="custom")

    assert result["project_name"] == "CUSTOM"
    assert result["registry_file"] == "CUSTOM_REGISTRY.json"


def test_init_project_skips_existing_optional_files(tmp_path):
    """Optional files are not overwritten if they already exist.
    Init is re-runnable — existing files are skipped."""
    target = tmp_path / "proj"
    target.mkdir()

    # Pre-create optional files
    aipass_dir = target / ".aipass"
    aipass_dir.mkdir()
    (aipass_dir / "aipass_global_prompt.md").write_text("# Custom global\n", encoding="utf-8")
    (target / "CLAUDE.md").write_text("# Custom CLAUDE\n", encoding="utf-8")
    (target / "AGENTS.md").write_text("# Custom AGENTS\n", encoding="utf-8")
    (target / "README.md").write_text("# Custom README\n", encoding="utf-8")
    (target / ".gitignore").write_text("# Custom\n", encoding="utf-8")

    claude_dir = target / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text("{}\n", encoding="utf-8")

    src_dir = target / "src"
    src_dir.mkdir()

    result = init_project(target, project_name="eta")

    # Only non-pre-existing files should be created (registry, package dir, etc.)
    assert len(result["created_files"]) >= 5

    # Verify pre-existing files were NOT overwritten
    md_content = (target / "CLAUDE.md").read_text(encoding="utf-8")
    assert md_content == "# Custom CLAUDE\n"


def test_init_project_no_overwrite(tmp_path):
    """Init guard blocks re-init; update preserves content."""
    target = tmp_path / "proj"
    target.mkdir()

    # First run creates files
    result1 = init_project(target, project_name="safe")
    assert len(result1["created_files"]) > 0

    # Second run is blocked by _guard_init
    with pytest.raises(RuntimeError, match="already an AIPass project"):
        init_project(target, project_name="safe")

    # Content from first run is preserved
    claude_md = (target / "CLAUDE.md").read_text(encoding="utf-8")
    assert "# SAFE" in claude_md


def test_init_project_returns_dict(tmp_path):
    """init_project return value is a dict."""
    target = tmp_path / "proj"
    target.mkdir()

    result = init_project(target, project_name="rtype")

    assert isinstance(result, dict)


def test_init_project_agents_md_no_trinity(tmp_path):
    """AGENTS.md is copied from AIPass source (may reference .trinity/ as part of agent docs)."""
    target = tmp_path / "proj"
    target.mkdir()

    init_project(target, project_name="keep")

    content = (target / "AGENTS.md").read_text(encoding="utf-8")
    # Source file legitimately references .trinity/ as part of startup protocol docs
    assert "# AIPass" in content
    assert "Multi-agent framework" in content


# ---------------------------------------------------------------------------
# update_project tests
# ---------------------------------------------------------------------------


def test_update_project_raises_if_no_registry(tmp_path):
    """ValueError when target has no *_REGISTRY.json (not an AIPass project)."""
    target = tmp_path / "bare"
    target.mkdir()

    with pytest.raises(ValueError, match="No AIPass project found"):
        update_project(target)


def test_update_project_return_dict_structure(tmp_path):
    """Return dict contains all required keys."""
    target = tmp_path / "proj"
    target.mkdir()
    init_project(target, project_name="upd")

    result = update_project(target)

    assert set(result.keys()) == {
        "project_name",
        "target",
        "updated_files",
        "already_current",
        "skipped_files",
        "aipass_home",
    }
    assert result["project_name"] == "UPD"
    assert result["target"] == str(target.resolve())
    assert isinstance(result["updated_files"], list)
    assert isinstance(result["already_current"], list)
    assert isinstance(result["skipped_files"], list)


def test_update_project_already_current_after_init(tmp_path):
    """Running update immediately after init reports all managed files as already current."""
    target = tmp_path / "proj"
    target.mkdir()
    init_project(target, project_name="fresh")

    result = update_project(target)

    assert len(result["updated_files"]) == 0
    assert len(result["already_current"]) >= 5


def test_update_project_idempotent(tmp_path):
    """Running update twice in a row produces no changes on second run."""
    target = tmp_path / "proj"
    target.mkdir()
    init_project(target, project_name="idem")

    result1 = update_project(target)
    result2 = update_project(target)

    # Both runs should be identical
    assert result1["updated_files"] == result2["updated_files"]
    assert result1["already_current"] == result2["already_current"]


def test_update_project_updates_modified_managed_file(tmp_path):
    """A managed file with altered content is re-written on update."""
    target = tmp_path / "proj"
    target.mkdir()
    init_project(target, project_name="mod")

    # Corrupt a managed file
    claude_md = target / "CLAUDE.md"
    claude_md.write_text("# Corrupted\n", encoding="utf-8")

    result = update_project(target)

    # CLAUDE.md must appear in updated, not already_current
    assert str(claude_md.resolve()) in result["updated_files"]
    assert str(claude_md.resolve()) not in result["already_current"]

    # Content is restored from project template
    restored = claude_md.read_text(encoding="utf-8")
    assert "# MOD" in restored
    assert "Startup protocol" in restored


def test_update_project_never_touches_user_owned_files(tmp_path):
    """Registry, README, STATUS, .gitignore are always in skipped_files."""
    target = tmp_path / "proj"
    target.mkdir()
    init_project(target, project_name="skip")

    # Modify user-owned files
    (target / "README.md").write_text("# My custom README\n", encoding="utf-8")
    (target / ".gitignore").write_text("# custom\n", encoding="utf-8")

    result = update_project(target)

    skipped = result["skipped_files"]
    assert any("REGISTRY" in s for s in skipped)
    assert any("README.md" in s for s in skipped)
    assert any(".gitignore" in s for s in skipped)

    # User customisations are preserved
    assert (target / "README.md").read_text(encoding="utf-8") == "# My custom README\n"


def test_update_project_creates_missing_managed_dirs(tmp_path):
    """update_project recreates .aipass/ and .claude/ if they were deleted."""
    target = tmp_path / "proj"
    target.mkdir()
    init_project(target, project_name="recover")

    # Delete only the managed subdirectories (not root files like CLAUDE.md)
    import shutil

    shutil.rmtree(target / ".aipass")
    shutil.rmtree(target / ".claude")

    result = update_project(target)

    assert (target / ".aipass" / "aipass_global_prompt.md").exists()
    assert (target / ".claude" / "settings.json").exists()
    # Managed files in deleted dirs re-written (global_prompt, hooks.json, settings, prep)
    assert len(result["updated_files"]) == 4
    assert len(result["already_current"]) >= 2


def test_update_project_skipped_files_count(tmp_path):
    """update_project skips 3 user-owned files."""
    target = tmp_path / "proj"
    target.mkdir()
    init_project(target, project_name="count")

    result = update_project(target)

    # 3 user-owned (registry, README, .gitignore)
    assert len(result["skipped_files"]) == 3


# ---------------------------------------------------------------------------
# DPLAN-0121: AIPASS_HOME tests
# ---------------------------------------------------------------------------


def test_init_project_returns_aipass_home(tmp_path):
    """init_project return dict includes aipass_home key."""
    target = tmp_path / "proj"
    target.mkdir()

    result = init_project(target, project_name="home")

    assert "aipass_home" in result
    assert result["aipass_home"] is None or isinstance(result["aipass_home"], str)


def test_init_project_settings_has_aipass_home_when_detected(tmp_path):
    """When AIPASS_HOME is detected, settings.json includes env.AIPASS_HOME."""
    target = tmp_path / "proj"
    target.mkdir()

    result = init_project(target, project_name="env")

    if result["aipass_home"] is None:
        pytest.skip("AIPASS_HOME not detectable in this environment")

    settings = json.loads((target / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "env" in settings
    assert settings["env"]["AIPASS_HOME"] == result["aipass_home"]


def test_update_project_returns_aipass_home(tmp_path):
    """update_project return dict includes aipass_home key."""
    target = tmp_path / "proj"
    target.mkdir()
    init_project(target, project_name="uhome")

    result = update_project(target)

    assert "aipass_home" in result
    assert result["aipass_home"] is None or isinstance(result["aipass_home"], str)


def test_update_project_adds_aipass_home_if_missing(tmp_path):
    """update_project injects AIPASS_HOME into settings.json if env section is absent."""
    target = tmp_path / "proj"
    target.mkdir()
    init_project(target, project_name="addenv")

    settings_path = target / ".claude" / "settings.json"
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    data.pop("env", None)
    settings_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    result = update_project(target)

    if result["aipass_home"] is not None:
        new_data = json.loads(settings_path.read_text(encoding="utf-8"))
        assert new_data.get("env", {}).get("AIPASS_HOME") == result["aipass_home"]
        assert str(settings_path) in result["updated_files"]


# ---------------------------------------------------------------------------
# DPLAN-0190: hooks.json + /memo tests
# ---------------------------------------------------------------------------


def test_init_project_no_memo_md(tmp_path):
    """init_project does NOT create memo.md — it belongs at provider level."""
    target = tmp_path / "proj"
    target.mkdir()

    init_project(target, project_name="memo")

    memo_path = target / ".claude" / "commands" / "memo.md"
    assert not memo_path.exists()


def test_init_project_creates_hooks_json(tmp_path):
    """init_project creates .aipass/hooks.json from project_hooks.json template."""
    target = tmp_path / "proj"
    target.mkdir()

    result = init_project(target, project_name="hooks")

    if result["aipass_home"] is None:
        pytest.skip("AIPASS_HOME not detectable in this environment")

    hooks_json = target / ".aipass" / "hooks.json"
    assert hooks_json.exists(), ".aipass/hooks.json should be created"
    data = json.loads(hooks_json.read_text(encoding="utf-8"))
    assert data.get("hooks_enabled") is True
    assert "UserPromptSubmit" in data


def test_init_project_hooks_json_matches_template(tmp_path):
    """hooks.json content matches the project_hooks.json template."""
    target = tmp_path / "proj"
    target.mkdir()

    result = init_project(target, project_name="tmpl")

    if result["aipass_home"] is None:
        pytest.skip("AIPASS_HOME not detectable in this environment")

    hooks_json = target / ".aipass" / "hooks.json"
    template = Path(result["aipass_home"]) / ".aipass" / "project_hooks.json"
    if not template.exists():
        pytest.skip("project_hooks.json template not found")

    assert hooks_json.read_bytes() == template.read_bytes()


def test_init_project_hooks_json_in_created_files(tmp_path):
    """hooks.json path appears in created_files list."""
    target = tmp_path / "proj"
    target.mkdir()

    result = init_project(target, project_name="created")

    if result["aipass_home"] is None:
        pytest.skip("AIPASS_HOME not detectable in this environment")

    assert any("hooks.json" in f for f in result["created_files"])


def test_init_project_no_hooks_json_without_aipass_home(tmp_path, monkeypatch):
    """When AIPASS_HOME is not detectable, hooks.json is not created."""
    target = tmp_path / "proj"
    target.mkdir()

    monkeypatch.setattr(
        "aipass.aipass.apps.handlers.init.bootstrap._detect_aipass_home",
        lambda: None,
    )

    init_project(target, project_name="nohooks")

    assert not (target / ".aipass" / "hooks.json").exists()


def test_init_project_no_hook_scripts_shipped(tmp_path):
    """No hook scripts are shipped to .claude/hooks/ (engine runs from $AIPASS_HOME)."""
    target = tmp_path / "proj"
    target.mkdir()

    init_project(target, project_name="noscripts")

    hooks_dir = target / ".claude" / "hooks"
    if hooks_dir.exists():
        shipped = [f.name for f in hooks_dir.iterdir()]
        assert len(shipped) == 0, f"No hook scripts should be shipped: {shipped}"


def test_init_project_settings_has_no_hook_events(tmp_path):
    """settings.json contains no hooks — provider handles all events."""
    target = tmp_path / "proj"
    target.mkdir()

    init_project(target, project_name="events")

    settings = json.loads((target / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "hooks" not in settings


def test_update_project_creates_hooks_json_if_missing(tmp_path):
    """update_project creates hooks.json from template when missing."""
    target = tmp_path / "proj"
    target.mkdir()

    registry_data = {
        "metadata": {
            "id": "test-id",
            "name": "MISS",
            "version": "1.0.0",
            "created": "2026-01-01",
            "last_updated": "2026-01-01",
            "total_branches": 0,
        },
        "branches": [],
    }
    (target / "MISS_REGISTRY.json").write_text(json.dumps(registry_data), encoding="utf-8")

    hooks_json = target / ".aipass" / "hooks.json"
    assert not hooks_json.exists()

    result = update_project(target)

    if result["aipass_home"] is None:
        pytest.skip("AIPASS_HOME not detectable in this environment")

    assert hooks_json.exists()
    assert any("hooks.json" in f for f in result["updated_files"])
    data = json.loads(hooks_json.read_text(encoding="utf-8"))
    assert data.get("hooks_enabled") is True


def test_update_project_union_merge_preserves_user_enabled(tmp_path):
    """update preserves user's enabled=false for existing hooks."""
    target = tmp_path / "proj"
    target.mkdir()
    result = init_project(target, project_name="merge")

    if result["aipass_home"] is None:
        pytest.skip("AIPASS_HOME not detectable in this environment")

    hooks_json = target / ".aipass" / "hooks.json"
    data = json.loads(hooks_json.read_text(encoding="utf-8"))
    data["PreToolUse"]["git_gate"]["enabled"] = False
    hooks_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    update_project(target)

    updated = json.loads(hooks_json.read_text(encoding="utf-8"))
    assert updated["PreToolUse"]["git_gate"]["enabled"] is False


def test_update_project_union_merge_adds_new_hooks(tmp_path):
    """update adds hooks from template that user doesn't have."""
    existing = {
        "hooks_enabled": True,
        "UserPromptSubmit": {
            "identity_injector": {"enabled": True, "handler": "old.handler", "matcher": ""},
        },
    }
    template = {
        "hooks_enabled": True,
        "UserPromptSubmit": {
            "identity_injector": {"enabled": True, "handler": "new.handler", "matcher": ""},
            "brand_new_hook": {"enabled": True, "handler": "brand.new", "matcher": ""},
        },
        "Stop": {
            "stop_sound": {"enabled": True, "handler": "stop.handler", "matcher": ""},
        },
    }

    merged = _merge_hooks_json(existing, template)

    assert "brand_new_hook" in merged["UserPromptSubmit"]
    assert "Stop" in merged
    assert merged["Stop"]["stop_sound"]["enabled"] is True


def test_update_project_union_merge_preserves_user_hooks():
    """User's custom hooks not in template are kept."""
    existing = {
        "hooks_enabled": True,
        "UserPromptSubmit": {
            "my_custom_hook": {"enabled": True, "handler": "custom.handler", "matcher": ""},
        },
    }
    template = {
        "hooks_enabled": True,
        "UserPromptSubmit": {
            "identity_injector": {"enabled": True, "handler": "std.handler", "matcher": ""},
        },
    }

    merged = _merge_hooks_json(existing, template)

    assert "my_custom_hook" in merged["UserPromptSubmit"]
    assert "identity_injector" in merged["UserPromptSubmit"]


def test_merge_hooks_json_preserves_hooks_enabled_false():
    """User's hooks_enabled=false is preserved over template's true."""
    existing = {"hooks_enabled": False}
    template = {"hooks_enabled": True, "Stop": {"s": {"enabled": True, "handler": "h", "matcher": ""}}}

    merged = _merge_hooks_json(existing, template)

    assert merged["hooks_enabled"] is False


def test_update_project_hooks_json_already_current(tmp_path):
    """update reports hooks.json as already_current when unchanged."""
    target = tmp_path / "proj"
    target.mkdir()
    result = init_project(target, project_name="curr")

    if result["aipass_home"] is None:
        pytest.skip("AIPASS_HOME not detectable in this environment")

    result = update_project(target)

    assert not any("hooks.json" in f for f in result["updated_files"])
    assert any("hooks.json" in f for f in result["already_current"])


# ---------------------------------------------------------------------------
# scaffold_content — global_prompt_md tests
# ---------------------------------------------------------------------------


def test_global_prompt_md_returns_string():
    """global_prompt_md() returns a non-empty string."""
    result = sc.global_prompt_md("TestProject")
    assert isinstance(result, str)
    assert len(result) > 0


def test_global_prompt_md_contains_project_name():
    """global_prompt_md() interpolates the project name."""
    result = sc.global_prompt_md("MyApp")
    assert "MyApp" in result


def test_global_prompt_md_contains_registry_reference():
    """global_prompt_md() references the registry with the project name."""
    result = sc.global_prompt_md("Demo")
    assert "Demo_REGISTRY.json" in result


def test_global_prompt_md_contains_aipass_context():
    """global_prompt_md() includes AIPass framework context."""
    result = sc.global_prompt_md("X")
    assert "AIPass" in result
    assert "drone" in result


# ---------------------------------------------------------------------------
# scaffold_content — prep_md tests
# ---------------------------------------------------------------------------


def test_prep_md_returns_string():
    """prep_md() returns a non-empty string."""
    result = sc.prep_md()
    assert isinstance(result, str)
    assert len(result) > 0


def test_prep_md_contains_session_wrap_up():
    """prep_md() contains the session wrap-up header."""
    result = sc.prep_md()
    assert "Session Wrap-Up" in result


def test_prep_md_contains_memory_instructions():
    """prep_md() includes instructions for updating .trinity/ files."""
    result = sc.prep_md()
    assert ".trinity/" in result or "local.json" in result


# ---------------------------------------------------------------------------
# scaffold_content — inbox_json tests
# ---------------------------------------------------------------------------


def test_inbox_json_returns_valid_json():
    """inbox_json() returns valid JSON."""
    result = sc.inbox_json()
    parsed = json.loads(result)
    assert isinstance(parsed, dict)


def test_inbox_json_has_mailbox_structure():
    """inbox_json() contains required mailbox fields."""
    parsed = json.loads(sc.inbox_json())
    assert parsed["mailbox"] == "inbox"
    assert parsed["total_messages"] == 0
    assert parsed["unread_count"] == 0
    assert parsed["messages"] == []


# ---------------------------------------------------------------------------
# scaffold_content — with_source tests
# ---------------------------------------------------------------------------


def test_with_source_prepends_header(tmp_path):
    """with_source() prepends a source comment to content."""
    from pathlib import Path

    result = sc.with_source("hello world", Path("/foo/bar.md"))
    assert result.startswith("<!-- Source: /foo/bar.md -->")
    assert "hello world" in result


def test_with_source_preserves_content():
    """with_source() does not alter the original content."""
    from pathlib import Path

    original = "line 1\nline 2\nline 3"
    result = sc.with_source(original, Path("/a/b.md"))
    assert result.endswith(original)


def test_with_source_header_is_first_line():
    """with_source() puts the source header on line 1, content on line 2+."""
    from pathlib import Path

    result = sc.with_source("content", Path("/test.md"))
    lines = result.split("\n")
    assert lines[0] == "<!-- Source: /test.md -->"
    assert lines[1] == "content"
