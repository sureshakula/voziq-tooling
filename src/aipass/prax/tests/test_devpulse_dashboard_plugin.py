# =================== AIPass ====================
# Name: test_devpulse_dashboard_plugin.py
# Description: Tests for devpulse dashboard plugin
# Version: 1.0.0
# Created: 2026-05-16
# Modified: 2026-05-16
# =============================================

"""Tests for devpulse dashboard plugin (git, session, dispatch sections + refresh)."""

import json
from unittest.mock import patch, MagicMock

import pytest


def _git_subprocess_responses(cmd, **kwargs):
    """Mock subprocess.run responses for git commands."""
    result = MagicMock()
    result.returncode = 0
    args = cmd[1:]  # strip 'git'
    responses = {
        ("rev-parse", "--abbrev-ref", "HEAD"): "dev\n",
        ("status", "--porcelain"): " M file1.py\n M file2.py\n",
        ("rev-list", "--count", "origin/main..HEAD"): "5\n",
        ("log", "-1", "--format=%s"): "feat: add dashboard plugin\n",
        ("log", "-1", "--format=%cs"): "2026-05-16\n",
    }
    result.stdout = responses.get(tuple(args), "")
    return result


@pytest.fixture
def branch_path(tmp_path):
    """Create a minimal branch directory structure."""
    (tmp_path / "DASHBOARD.local.json").write_text(
        json.dumps(
            {
                "_warning": "AUTO-GENERATED",
                "branch": "DEVPULSE",
                "last_updated": "",
                "quick_status": {"action_required": False},
                "sections": {},
            }
        )
    )
    return tmp_path


@pytest.fixture
def branch_with_trinity(branch_path):
    """Branch path with .trinity/local.json."""
    trinity = branch_path / ".trinity"
    trinity.mkdir()
    local_data = {
        "sessions": [{"id": "S162", "d": "2026-05-16", "sum": "Test session summary", "st": "+"}],
        "active_tasks": {
            "today_focus": "Testing the plugin",
            "pending": ["Task 1", "Task 2"],
            "recently_completed": [],
        },
    }
    (trinity / "local.json").write_text(json.dumps(local_data))
    return branch_path


@pytest.fixture
def branch_with_git(branch_path):
    """Branch path inside a fake git repo."""
    (branch_path / ".git").mkdir()
    return branch_path


class TestGitSection:
    """Tests for git_section.py."""

    @patch("aipass.prax.apps.plugins.devpulse_dashboard.git_section.subprocess.run")
    def test_build_git_section_success(self, mock_run, branch_with_git):
        """Test successful git section build with mocked subprocess."""
        from aipass.prax.apps.plugins.devpulse_dashboard.git_section import build_git_section

        mock_run.side_effect = _git_subprocess_responses
        result = build_git_section(branch_with_git)
        assert result is True

        # Verify dashboard was written
        dash = json.loads((branch_with_git / "DASHBOARD.local.json").read_text())
        git = dash["sections"]["git"]
        assert git["managed_by"] == "devpulse"
        assert git["branch"] == "dev"
        assert git["files_changed"] == 2
        assert git["ahead_of_main"] == 5
        assert git["last_commit_msg"] == "feat: add dashboard plugin"
        assert git["last_commit_date"] == "2026-05-16"

    @patch("aipass.prax.apps.plugins.devpulse_dashboard.git_section.subprocess.run")
    def test_build_git_section_subprocess_failure(self, mock_run, branch_with_git):
        """Test git section handles subprocess failures gracefully."""
        from aipass.prax.apps.plugins.devpulse_dashboard.git_section import build_git_section

        mock_run.side_effect = OSError("git not found")
        # Should not raise — handles errors internally
        result = build_git_section(branch_with_git)
        # Still writes section with empty/default values
        assert result is True

    @patch("aipass.prax.apps.plugins.devpulse_dashboard.git_section._find_repo_root")
    def test_build_git_section_no_git_dir(self, mock_find_root, branch_path):
        """Test git section when no .git directory exists."""
        from aipass.prax.apps.plugins.devpulse_dashboard.git_section import build_git_section

        mock_find_root.side_effect = FileNotFoundError("No .git found above " + str(branch_path))
        with pytest.raises(FileNotFoundError):
            build_git_section(branch_path)


class TestSessionSection:
    """Tests for session_section.py."""

    def test_build_session_section_success(self, branch_with_trinity):
        """Test session section reads local.json correctly."""
        from aipass.prax.apps.plugins.devpulse_dashboard.session_section import build_session_section

        result = build_session_section(branch_with_trinity)
        assert result is True

        dash = json.loads((branch_with_trinity / "DASHBOARD.local.json").read_text())
        session = dash["sections"]["session"]
        assert session["managed_by"] == "devpulse"
        assert session["current_session"] == "S162"
        assert session["session_date"] == "2026-05-16"
        assert session["today_focus"] == "Testing the plugin"
        assert session["active_tasks"] == ["Task 1", "Task 2"]
        assert session["last_session_summary"] == "Test session summary"

    def test_build_session_section_no_local_json(self, branch_path):
        """Test session section when local.json doesn't exist."""
        from aipass.prax.apps.plugins.devpulse_dashboard.session_section import build_session_section

        result = build_session_section(branch_path)
        assert result is True

        dash = json.loads((branch_path / "DASHBOARD.local.json").read_text())
        session = dash["sections"]["session"]
        assert session["current_session"] == "unknown"

    def test_build_session_section_corrupt_json(self, branch_path):
        """Test session section handles corrupt local.json."""
        from aipass.prax.apps.plugins.devpulse_dashboard.session_section import build_session_section

        trinity = branch_path / ".trinity"
        trinity.mkdir()
        (trinity / "local.json").write_text("not valid json{{{")

        result = build_session_section(branch_path)
        assert result is True

        dash = json.loads((branch_path / "DASHBOARD.local.json").read_text())
        session = dash["sections"]["session"]
        assert session["current_session"] == "error"


class TestDispatchSection:
    """Tests for dispatch_section.py."""

    def test_build_dispatch_section_no_locks(self, branch_path):
        """Test dispatch section when no agents are active."""
        from aipass.prax.apps.plugins.devpulse_dashboard.dispatch_section import build_dispatch_section

        # Create sibling branch dirs (dispatch scans parent for all branches)
        parent = branch_path.parent
        for name in ["ai_mail", "prax", "seedgo"]:
            (parent / name / ".ai_mail.local").mkdir(parents=True, exist_ok=True)

        result = build_dispatch_section(branch_path)
        assert result is True

        dash = json.loads((branch_path / "DASHBOARD.local.json").read_text())
        dispatch = dash["sections"]["dispatch"]
        assert dispatch["managed_by"] == "devpulse"
        assert dispatch["agents_active"] == []
        assert dispatch["agents_active_count"] == 0

    def test_build_dispatch_section_with_locks(self, branch_path):
        """Test dispatch section detects active dispatch locks."""
        from aipass.prax.apps.plugins.devpulse_dashboard.dispatch_section import build_dispatch_section

        parent = branch_path.parent
        # Create lock for "prax"
        prax_mail = parent / "prax" / ".ai_mail.local"
        prax_mail.mkdir(parents=True, exist_ok=True)
        lock_data = {"pid": 12345, "subject": "Build dashboard view", "started": "2026-05-16T14:00:00"}
        (prax_mail / ".dispatch.lock").write_text(json.dumps(lock_data))

        result = build_dispatch_section(branch_path)
        assert result is True

        dash = json.loads((branch_path / "DASHBOARD.local.json").read_text())
        dispatch = dash["sections"]["dispatch"]
        assert "prax" in dispatch["agents_active"]
        assert dispatch["agents_active_count"] == 1
        assert dispatch["details"]["prax"]["subject"] == "Build dashboard view"

    def test_build_dispatch_section_corrupt_lock(self, branch_path):
        """Test dispatch section handles corrupt lock files."""
        from aipass.prax.apps.plugins.devpulse_dashboard.dispatch_section import build_dispatch_section

        parent = branch_path.parent
        seedgo_mail = parent / "seedgo" / ".ai_mail.local"
        seedgo_mail.mkdir(parents=True, exist_ok=True)
        (seedgo_mail / ".dispatch.lock").write_text("broken json{{{")

        result = build_dispatch_section(branch_path)
        assert result is True

        dash = json.loads((branch_path / "DASHBOARD.local.json").read_text())
        dispatch = dash["sections"]["dispatch"]
        assert "seedgo" in dispatch["agents_active"]
        assert dispatch["details"]["seedgo"]["subject"] == "unknown"


class TestTodoSection:
    """Tests for todo_section.py."""

    def test_build_todo_section_with_todos(self, branch_path):
        """Test todo section reads todos[] from local.json correctly."""
        from aipass.prax.apps.plugins.devpulse_dashboard.todo_section import build_todo_section

        trinity = branch_path / ".trinity"
        trinity.mkdir()
        local_data = {
            "todos": [
                {"id": "t1", "text": "Fix the bug", "created": "2026-06-07"},
                {"id": "t2", "text": "Write tests", "created": "2026-06-07", "priority": "high"},
            ],
        }
        (trinity / "local.json").write_text(json.dumps(local_data))

        result = build_todo_section(branch_path)
        assert result is True

        dash = json.loads((branch_path / "DASHBOARD.local.json").read_text())
        todo = dash["sections"]["todo"]
        assert todo["managed_by"] == "devpulse"
        assert todo["todo_count"] == 2
        assert len(todo["todos"]) == 2
        assert todo["todos"][0]["id"] == "t1"

    def test_build_todo_section_empty_todos(self, branch_path):
        """Test todo section with empty todos list."""
        from aipass.prax.apps.plugins.devpulse_dashboard.todo_section import build_todo_section

        trinity = branch_path / ".trinity"
        trinity.mkdir()
        (trinity / "local.json").write_text(json.dumps({"todos": []}))

        result = build_todo_section(branch_path)
        assert result is True

        dash = json.loads((branch_path / "DASHBOARD.local.json").read_text())
        todo = dash["sections"]["todo"]
        assert todo["todo_count"] == 0
        assert todo["todos"] == []

    def test_build_todo_section_no_local_json(self, branch_path):
        """Test todo section when local.json doesn't exist."""
        from aipass.prax.apps.plugins.devpulse_dashboard.todo_section import build_todo_section

        result = build_todo_section(branch_path)
        assert result is True

        dash = json.loads((branch_path / "DASHBOARD.local.json").read_text())
        todo = dash["sections"]["todo"]
        assert todo["todo_count"] == 0
        assert todo["todos"] == []

    def test_build_todo_section_corrupt_json(self, branch_path):
        """Test todo section handles corrupt local.json."""
        from aipass.prax.apps.plugins.devpulse_dashboard.todo_section import build_todo_section

        trinity = branch_path / ".trinity"
        trinity.mkdir()
        (trinity / "local.json").write_text("not valid json{{{")

        result = build_todo_section(branch_path)
        assert result is True

        dash = json.loads((branch_path / "DASHBOARD.local.json").read_text())
        todo = dash["sections"]["todo"]
        assert todo["todo_count"] == 0

    def test_build_todo_section_no_todos_key(self, branch_path):
        """Test todo section when local.json has no todos key."""
        from aipass.prax.apps.plugins.devpulse_dashboard.todo_section import build_todo_section

        trinity = branch_path / ".trinity"
        trinity.mkdir()
        (trinity / "local.json").write_text(json.dumps({"sessions": []}))

        result = build_todo_section(branch_path)
        assert result is True

        dash = json.loads((branch_path / "DASHBOARD.local.json").read_text())
        todo = dash["sections"]["todo"]
        assert todo["todo_count"] == 0
        assert todo["todos"] == []


class TestRefresh:
    """Tests for refresh.py orchestrator."""

    @patch("aipass.prax.apps.plugins.devpulse_dashboard.todo_section.build_todo_section")
    @patch("aipass.prax.apps.plugins.devpulse_dashboard.git_section.build_git_section")
    @patch("aipass.prax.apps.plugins.devpulse_dashboard.session_section.build_session_section")
    @patch("aipass.prax.apps.plugins.devpulse_dashboard.dispatch_section.build_dispatch_section")
    def test_refresh_all_success(self, mock_dispatch, mock_session, mock_git, mock_todo, branch_path):
        """Test refresh orchestrator calls all builders."""
        from aipass.prax.apps.plugins.devpulse_dashboard.refresh import refresh

        results = refresh(branch_path)
        assert results["git"]["success"] is True
        assert results["session"]["success"] is True
        assert results["dispatch"]["success"] is True
        assert results["todo"]["success"] is True
        mock_git.assert_called_once_with(branch_path)
        mock_session.assert_called_once_with(branch_path)
        mock_dispatch.assert_called_once_with(branch_path)
        mock_todo.assert_called_once_with(branch_path)

    @patch("aipass.prax.apps.plugins.devpulse_dashboard.todo_section.build_todo_section")
    @patch("aipass.prax.apps.plugins.devpulse_dashboard.git_section.build_git_section")
    @patch("aipass.prax.apps.plugins.devpulse_dashboard.session_section.build_session_section")
    @patch("aipass.prax.apps.plugins.devpulse_dashboard.dispatch_section.build_dispatch_section")
    def test_refresh_partial_failure(self, mock_dispatch, mock_session, mock_git, mock_todo, branch_path):
        """Test refresh continues when one section fails."""
        from aipass.prax.apps.plugins.devpulse_dashboard.refresh import refresh

        mock_git.side_effect = FileNotFoundError("No .git")
        results = refresh(branch_path)
        assert results["git"]["success"] is False
        assert "No .git" in results["git"]["error"]
        assert results["session"]["success"] is True
        assert results["dispatch"]["success"] is True
        assert results["todo"]["success"] is True

    def test_refresh_default_path(self):
        """Test refresh uses DEVPULSE_PATH by default."""
        from aipass.prax.apps.plugins.devpulse_dashboard.refresh import DEVPULSE_PATH

        assert DEVPULSE_PATH.name == "devpulse"
        assert "src" in DEVPULSE_PATH.parts and "aipass" in DEVPULSE_PATH.parts
