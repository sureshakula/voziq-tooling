# =================== AIPass ====================
# Name: test_new_project.py
# Description: Tests for aipass new — project creation handler
# Version: 1.0.0
# Created: 2026-07-17
# Modified: 2026-07-17
# =============================================

"""Tests for the new_project handler and module.

All file operations use tmp_path to stay fully isolated from the live
filesystem. Tests mock subprocess calls to avoid real git/drone invocations.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest  # pyright: ignore[reportMissingImports]

from aipass.aipass.apps.handlers.new_project import (
    _registry_name,
    _validate_name,
    _write_agent,
    _write_registry,
    _write_template,
    create_project,
    find_host_root,
)


# ---------------------------------------------------------------------------
# find_host_root
# ---------------------------------------------------------------------------


def test_find_host_root_finds_registry(tmp_path):
    """Finds directory containing *_REGISTRY.json."""
    (tmp_path / "AIPASS_REGISTRY.json").write_text("{}")
    sub = tmp_path / "projects" / "myapp"
    sub.mkdir(parents=True)
    assert find_host_root(sub) == tmp_path


def test_find_host_root_returns_none_without_registry(tmp_path):
    """Returns None when no registry exists above start."""
    assert find_host_root(tmp_path) is None


def test_find_host_root_finds_closest_registry(tmp_path):
    """Walks up and finds the closest *_REGISTRY.json."""
    (tmp_path / "HOST_REGISTRY.json").write_text("{}")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert find_host_root(sub) == tmp_path


# ---------------------------------------------------------------------------
# _validate_name
# ---------------------------------------------------------------------------


def test_validate_name_accepts_valid():
    assert _validate_name("myapp") == "myapp"
    assert _validate_name("My-App_2") == "My-App_2"


def test_validate_name_rejects_empty():
    with pytest.raises(ValueError, match="cannot be empty"):
        _validate_name("")


def test_validate_name_rejects_leading_digit():
    with pytest.raises(ValueError, match="Must start with a letter"):
        _validate_name("2fast")


def test_validate_name_rejects_special_chars():
    with pytest.raises(ValueError, match="Must start with a letter"):
        _validate_name("my app!")


# ---------------------------------------------------------------------------
# _registry_name
# ---------------------------------------------------------------------------


def test_registry_name_uppercases():
    assert _registry_name("myapp") == "MYAPP"


def test_registry_name_replaces_special():
    assert _registry_name("my.app") == "MY_APP"


def test_registry_name_preserves_hyphens():
    assert _registry_name("my-app") == "MY-APP"


# ---------------------------------------------------------------------------
# _write_registry
# ---------------------------------------------------------------------------


def test_write_registry_creates_file(tmp_path):
    rid, fname = _write_registry(tmp_path, "demo")
    path = tmp_path / fname
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["metadata"]["id"] == rid
    assert data["metadata"]["name"] == "DEMO"
    assert fname == "DEMO_REGISTRY.json"
    assert data["branches"] == []


# ---------------------------------------------------------------------------
# _write_template — empty
# ---------------------------------------------------------------------------


def test_write_template_empty(tmp_path):
    created = _write_template(tmp_path, "demo", "empty")
    assert "README.md" in created
    assert ".gitignore" in created
    assert (tmp_path / "README.md").exists()
    assert (tmp_path / ".gitignore").exists()
    assert not (tmp_path / "pyproject.toml").exists()
    assert not (tmp_path / "src").exists()


# ---------------------------------------------------------------------------
# _write_template — python
# ---------------------------------------------------------------------------


def test_write_template_python(tmp_path):
    created = _write_template(tmp_path, "demo", "python")
    assert "pyproject.toml" in created
    assert "src/demo/__init__.py" in created
    assert (tmp_path / "pyproject.toml").exists()
    assert (tmp_path / "src" / "demo" / "__init__.py").exists()
    pyproject = (tmp_path / "pyproject.toml").read_text()
    assert 'name = "demo"' in pyproject


def test_write_template_python_hyphen_name(tmp_path):
    _write_template(tmp_path, "my-app", "python")
    assert (tmp_path / "src" / "my_app" / "__init__.py").exists()


# ---------------------------------------------------------------------------
# create_project — integration (mocked subprocess)
# ---------------------------------------------------------------------------


@pytest.fixture()
def host_env(tmp_path):
    """Set up a minimal AIPass host installation in tmp_path."""
    (tmp_path / "AIPASS_REGISTRY.json").write_text(json.dumps({"metadata": {"id": "host-id"}, "branches": []}))
    (tmp_path / "projects").mkdir()
    (tmp_path / ".aipass").mkdir()
    return tmp_path


def _mock_git_run(args, **kwargs):
    """Stub subprocess.run for git commands — always succeeds."""
    from unittest.mock import MagicMock

    result = MagicMock()
    result.returncode = 0
    result.stdout = ""
    result.stderr = ""
    return result


def test_create_project_empty_template(host_env, monkeypatch):
    monkeypatch.chdir(host_env)
    with (
        patch("subprocess.run", side_effect=_mock_git_run),
        patch(
            "aipass.aipass.apps.handlers.init.bootstrap._detect_aipass_home",
            return_value=None,
        ),
        patch(
            "aipass.aipass.apps.handlers.init.bootstrap._enroll_project",
        ),
    ):
        result = create_project("testproj", template="empty", no_agent=True)

    target = Path(result["target"])
    assert target.exists()
    assert result["name"] == "testproj"
    assert result["template"] == "empty"
    assert result["registry_file"] == "TESTPROJ_REGISTRY.json"
    assert (target / "TESTPROJ_REGISTRY.json").exists()
    assert (target / "README.md").exists()
    assert (target / ".gitignore").exists()
    assert not (target / "pyproject.toml").exists()


def test_create_project_python_template(host_env, monkeypatch):
    monkeypatch.chdir(host_env)
    with (
        patch("subprocess.run", side_effect=_mock_git_run),
        patch(
            "aipass.aipass.apps.handlers.init.bootstrap._detect_aipass_home",
            return_value=None,
        ),
        patch(
            "aipass.aipass.apps.handlers.init.bootstrap._enroll_project",
        ),
    ):
        result = create_project("pyapp", template="python", no_agent=True)

    target = Path(result["target"])
    assert (target / "pyproject.toml").exists()
    assert (target / "src" / "pyapp" / "__init__.py").exists()


def test_create_project_rejects_existing(host_env, monkeypatch):
    monkeypatch.chdir(host_env)
    (host_env / "projects" / "taken").mkdir()
    with pytest.raises(RuntimeError, match="already exists"):
        create_project("taken", no_agent=True)


def test_create_project_rejects_invalid_name(host_env, monkeypatch):
    monkeypatch.chdir(host_env)
    with pytest.raises(ValueError, match="Must start with a letter"):
        create_project("123bad", no_agent=True)


def test_create_project_rejects_bad_template(host_env, monkeypatch):
    monkeypatch.chdir(host_env)
    with pytest.raises(ValueError, match="Unknown template"):
        create_project("foo", template="rust", no_agent=True)


def test_create_project_no_host(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="Not inside an AIPass"):
        create_project("foo", no_agent=True)


def test_create_project_cleans_up_on_failure(host_env, monkeypatch):
    monkeypatch.chdir(host_env)

    def _fail_git(args, **kwargs):
        from unittest.mock import MagicMock

        result = MagicMock()
        result.returncode = 1
        result.stderr = "simulated failure"
        return result

    with (
        patch("subprocess.run", side_effect=_fail_git),
        patch(
            "aipass.aipass.apps.handlers.init.bootstrap._detect_aipass_home",
            return_value=None,
        ),
        patch("aipass.aipass.apps.handlers.init.bootstrap._enroll_project"),
        pytest.raises(RuntimeError, match="simulated failure"),
    ):
        create_project("failproj", no_agent=True)

    assert not (host_env / "projects" / "failproj").exists()


def test_create_project_registry_before_scaffold(host_env, monkeypatch):
    """Registry file must exist before scaffold runs (order invariant)."""
    monkeypatch.chdir(host_env)
    creation_order = []

    original_write_registry = _write_registry
    original_write_template = _write_template

    def track_registry(target, name):
        creation_order.append("registry")
        return original_write_registry(target, name)

    def track_template(target, name, template):
        creation_order.append("template")
        return original_write_template(target, name, template)

    with (
        patch("subprocess.run", side_effect=_mock_git_run),
        patch(
            "aipass.aipass.apps.handlers.new_project._write_registry",
            side_effect=track_registry,
        ),
        patch(
            "aipass.aipass.apps.handlers.new_project._write_template",
            side_effect=track_template,
        ),
        patch(
            "aipass.aipass.apps.handlers.init.bootstrap._detect_aipass_home",
            return_value=None,
        ),
        patch("aipass.aipass.apps.handlers.init.bootstrap._enroll_project"),
    ):
        create_project("ordertest", no_agent=True)

    assert creation_order.index("registry") < creation_order.index("template")


# ---------------------------------------------------------------------------
# _write_agent
# ---------------------------------------------------------------------------


def test_write_agent_creates_passport(tmp_path):
    """Passport is written with correct credential linkage."""
    rid, fname = _write_registry(tmp_path, "agentapp")
    files = _write_agent(tmp_path, "agentapp", rid, fname)
    assert ".trinity/passport.json" in files
    passport = json.loads((tmp_path / ".trinity" / "passport.json").read_text())
    assert passport["citizenship"]["registry_id"] == rid
    assert passport["branch_info"]["branch_name"] == "AGENTAPP"
    assert passport["identity"]["role"] == "project_agent"


def test_write_agent_seats_in_registry(tmp_path):
    """Registry total_branches updated and branch entry added."""
    rid, fname = _write_registry(tmp_path, "seated")
    _write_agent(tmp_path, "seated", rid, fname)
    reg = json.loads((tmp_path / fname).read_text())
    assert reg["metadata"]["total_branches"] == 1
    assert len(reg["branches"]) == 1
    assert reg["branches"][0]["registry_id"] == rid
    assert reg["branches"][0]["name"] == "SEATED"


def test_write_agent_credential_linkage(tmp_path):
    """registry.metadata.id == passport.citizenship.registry_id."""
    rid, fname = _write_registry(tmp_path, "linked")
    _write_agent(tmp_path, "linked", rid, fname)
    reg = json.loads((tmp_path / fname).read_text())
    passport = json.loads((tmp_path / ".trinity" / "passport.json").read_text())
    assert reg["metadata"]["id"] == passport["citizenship"]["registry_id"]


def test_write_agent_creates_entry_point(tmp_path):
    """Entry point apps/<name>.py is created and contains hello handler."""
    rid, fname = _write_registry(tmp_path, "myagent")
    files = _write_agent(tmp_path, "myagent", rid, fname)
    assert "apps/myagent.py" in files
    content = (tmp_path / "apps" / "myagent.py").read_text()
    assert "def main()" in content
    assert "def print_introspection()" in content
    assert "def print_help()" in content
    assert '"hello"' in content


def test_write_agent_creates_apps_skeleton(tmp_path):
    """Apps skeleton: __init__.py, modules/, handlers/."""
    rid, fname = _write_registry(tmp_path, "skel")
    files = _write_agent(tmp_path, "skel", rid, fname)
    assert "apps/__init__.py" in files
    assert "apps/modules/__init__.py" in files
    assert "apps/handlers/__init__.py" in files
    assert (tmp_path / "apps" / "modules" / "__init__.py").exists()
    assert (tmp_path / "apps" / "handlers" / "__init__.py").exists()


def test_write_agent_creates_trinity_full_set(tmp_path):
    """Full .trinity/ set: passport, local.json, observations.json."""
    rid, fname = _write_registry(tmp_path, "fullset")
    files = _write_agent(tmp_path, "fullset", rid, fname)
    assert ".trinity/passport.json" in files
    assert ".trinity/local.json" in files
    assert ".trinity/observations.json" in files
    local = json.loads((tmp_path / ".trinity" / "local.json").read_text())
    assert local["document_metadata"]["managed_by"] == "FULLSET"
    obs = json.loads((tmp_path / ".trinity" / "observations.json").read_text())
    assert obs["document_metadata"]["managed_by"] == "FULLSET"


def test_write_agent_creates_mailbox_and_logs(tmp_path):
    """Mailbox and logs directories created."""
    rid, fname = _write_registry(tmp_path, "dirs")
    _write_agent(tmp_path, "dirs", rid, fname)
    assert (tmp_path / ".ai_mail.local").is_dir()
    assert (tmp_path / "logs").is_dir()


# ---------------------------------------------------------------------------
# create_project — WITH agent
# ---------------------------------------------------------------------------


def test_create_project_with_agent(host_env, monkeypatch):
    """WITH-agent path: full framework agent created."""
    monkeypatch.chdir(host_env)
    with (
        patch("subprocess.run", side_effect=_mock_git_run),
        patch(
            "aipass.aipass.apps.handlers.init.bootstrap._detect_aipass_home",
            return_value=None,
        ),
        patch("aipass.aipass.apps.handlers.init.bootstrap._enroll_project"),
    ):
        result = create_project("withagent", template="empty", no_agent=False)

    assert result["agent_created"] is True
    target = Path(result["target"])
    assert (target / ".trinity" / "passport.json").exists()
    assert (target / ".trinity" / "local.json").exists()
    assert (target / ".trinity" / "observations.json").exists()
    assert (target / "apps" / "withagent.py").exists()
    assert (target / "apps" / "modules" / "__init__.py").exists()
    assert (target / "apps" / "handlers" / "__init__.py").exists()
    assert (target / ".ai_mail.local").is_dir()
    assert (target / "logs").is_dir()
    passport = json.loads((target / ".trinity" / "passport.json").read_text())
    assert passport["citizenship"]["registry_id"] == result["registry_id"]
    reg = json.loads((target / result["registry_file"]).read_text())
    assert reg["metadata"]["total_branches"] == 1
    assert reg["branches"][0]["registry_id"] == result["registry_id"]


def test_create_project_no_agent_flag(host_env, monkeypatch):
    """no_agent=True skips passport and registry seating."""
    monkeypatch.chdir(host_env)
    with (
        patch("subprocess.run", side_effect=_mock_git_run),
        patch(
            "aipass.aipass.apps.handlers.init.bootstrap._detect_aipass_home",
            return_value=None,
        ),
        patch("aipass.aipass.apps.handlers.init.bootstrap._enroll_project"),
    ):
        result = create_project("noagent", template="empty", no_agent=True)

    assert result["agent_created"] is False
    target = Path(result["target"])
    assert not (target / ".trinity").exists()
    reg = json.loads((target / result["registry_file"]).read_text())
    assert reg["metadata"]["total_branches"] == 0


# ---------------------------------------------------------------------------
# is_projects_child (guard relaxation)
# ---------------------------------------------------------------------------


def test_is_projects_child_valid(tmp_path):
    from aipass.aipass.apps.handlers.init.bootstrap import is_projects_child

    (tmp_path / "AIPASS_REGISTRY.json").write_text("{}")
    target = tmp_path / "projects" / "myapp"
    target.mkdir(parents=True)
    assert is_projects_child(target) is True


def test_is_projects_child_not_in_projects(tmp_path):
    from aipass.aipass.apps.handlers.init.bootstrap import is_projects_child

    (tmp_path / "AIPASS_REGISTRY.json").write_text("{}")
    target = tmp_path / "elsewhere" / "myapp"
    target.mkdir(parents=True)
    assert is_projects_child(target) is False


def test_is_projects_child_no_host_registry(tmp_path):
    from aipass.aipass.apps.handlers.init.bootstrap import is_projects_child

    target = tmp_path / "projects" / "myapp"
    target.mkdir(parents=True)
    assert is_projects_child(target) is False


# ---------------------------------------------------------------------------
# _guard_init relaxation
# ---------------------------------------------------------------------------


def test_guard_init_blocks_nested_by_default(tmp_path):
    from aipass.aipass.apps.handlers.init.bootstrap import _guard_init

    (tmp_path / "AIPASS_REGISTRY.json").write_text("{}")
    target = tmp_path / "projects" / "nested"
    target.mkdir(parents=True)
    with pytest.raises(RuntimeError, match="inside AIPass project"):
        _guard_init(target)


def test_guard_init_allows_nested_with_flag(tmp_path):
    from aipass.aipass.apps.handlers.init.bootstrap import _guard_init

    (tmp_path / "AIPASS_REGISTRY.json").write_text("{}")
    target = tmp_path / "projects" / "nested"
    target.mkdir(parents=True)
    _guard_init(target, allow_projects_child=True)


def test_guard_init_still_blocks_non_projects_nested(tmp_path):
    from aipass.aipass.apps.handlers.init.bootstrap import _guard_init

    (tmp_path / "AIPASS_REGISTRY.json").write_text("{}")
    target = tmp_path / "elsewhere" / "nested"
    target.mkdir(parents=True)
    with pytest.raises(RuntimeError, match="inside AIPass project"):
        _guard_init(target, allow_projects_child=True)


# ---------------------------------------------------------------------------
# Module handle_command
# ---------------------------------------------------------------------------


def test_module_handles_new_command():
    from aipass.aipass.apps.modules.new_project import handle_command

    assert handle_command("notmine", []) is False


def test_module_handles_help():
    from aipass.aipass.apps.modules.new_project import handle_command

    assert handle_command("new", ["--help"]) is True


def test_module_handles_no_args():
    from aipass.aipass.apps.modules.new_project import handle_command

    assert handle_command("new", []) is True


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------


def test_prompt_template_default():
    from aipass.aipass.apps.modules.new_project import _prompt_template

    with patch("builtins.input", return_value=""):
        assert _prompt_template(["empty", "python"]) == "empty"


def test_prompt_template_by_number():
    from aipass.aipass.apps.modules.new_project import _prompt_template

    with patch("builtins.input", return_value="2"):
        assert _prompt_template(["empty", "python"]) == "python"


def test_prompt_template_by_name():
    from aipass.aipass.apps.modules.new_project import _prompt_template

    with patch("builtins.input", return_value="python"):
        assert _prompt_template(["empty", "python"]) == "python"


def test_prompt_template_eof():
    from aipass.aipass.apps.modules.new_project import _prompt_template

    with patch("builtins.input", side_effect=EOFError):
        assert _prompt_template(["empty", "python"]) == "empty"


def test_prompt_agent_default_yes():
    from aipass.aipass.apps.modules.new_project import _prompt_agent

    with patch("builtins.input", return_value=""):
        assert _prompt_agent() is False


def test_prompt_agent_no():
    from aipass.aipass.apps.modules.new_project import _prompt_agent

    with patch("builtins.input", return_value="n"):
        assert _prompt_agent() is True


def test_prompt_agent_eof():
    from aipass.aipass.apps.modules.new_project import _prompt_agent

    with patch("builtins.input", side_effect=EOFError):
        assert _prompt_agent() is False


# ---------------------------------------------------------------------------
# aipass.py entry point help (cli_ux)
# ---------------------------------------------------------------------------


def test_aipass_print_introspection():
    from aipass.aipass.apps.aipass import print_introspection

    print_introspection([])


def test_aipass_print_help():
    from aipass.aipass.apps.aipass import print_help

    print_help([])
