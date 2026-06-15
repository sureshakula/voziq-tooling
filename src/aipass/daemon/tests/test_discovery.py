"""Tests for decentralized .daemon/ schedule discovery."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from aipass.daemon.apps.handlers.schedule.discovery import (
    discover_jobs,
    _validate_job,
    _load_schedule_file,
    _build_branch_map,
    REQUIRED_JOB_KEYS,
    VALID_SCHEDULE_TYPES,
)


# ── Fixtures ──────────────────────────────────────────


@pytest.fixture
def temp_src_aipass():
    """Create a temp src/aipass tree with .daemon/ files."""
    root = Path(tempfile.mkdtemp())
    src_aipass = root / "src" / "aipass"
    src_aipass.mkdir(parents=True)
    yield root, src_aipass
    shutil.rmtree(root)


@pytest.fixture
def sample_schedule():
    """A valid schedule.json structure."""
    return {
        "version": 1,
        "branch": "@testbranch",
        "jobs": [
            {
                "id": "daily-check",
                "enabled": True,
                "schedule": {"type": "daily", "time": "04:00"},
                "wake": {"fresh": True, "max_turns": 50},
                "prompt": "Run daily check.",
            }
        ],
    }


@pytest.fixture
def sample_registry():
    """A minimal AIPASS_REGISTRY.json."""
    return {
        "branches": [
            {"name": "TESTBRANCH", "email": "@testbranch", "path": "src/aipass/testbranch", "status": "active"},
            {"name": "INACTIVE", "email": "@inactive", "path": "src/aipass/inactive", "status": "inactive"},
        ]
    }


# ── _validate_job ─────────────────────────────────────


class TestValidateJob:
    def test_valid_job(self):
        job = {"id": "test", "schedule": {"type": "daily", "time": "04:00"}, "prompt": "do stuff"}
        assert _validate_job(job, Path("test.json")) is True

    def test_missing_required_key(self):
        job = {"id": "test", "schedule": {"type": "daily"}}
        assert _validate_job(job, Path("test.json")) is False

    def test_non_dict_schedule(self):
        job = {"id": "test", "schedule": "daily", "prompt": "do stuff"}
        assert _validate_job(job, Path("test.json")) is False

    def test_invalid_schedule_type(self):
        job = {"id": "test", "schedule": {"type": "biweekly"}, "prompt": "do stuff"}
        assert _validate_job(job, Path("test.json")) is False

    def test_all_valid_schedule_types(self):
        for stype in VALID_SCHEDULE_TYPES:
            job = {"id": "test", "schedule": {"type": stype}, "prompt": "do stuff"}
            assert _validate_job(job, Path("test.json")) is True

    def test_required_keys_constant(self):
        assert REQUIRED_JOB_KEYS == {"id", "schedule", "prompt"}


# ── _load_schedule_file ──────────────────────────────


class TestLoadScheduleFile:
    def test_valid_file(self, tmp_path):
        f = tmp_path / "schedule.json"
        data = {"version": 1, "jobs": [{"id": "x", "schedule": {"type": "daily"}, "prompt": "y"}]}
        f.write_text(json.dumps(data))
        result = _load_schedule_file(f)
        assert result is not None
        assert len(result["jobs"]) == 1

    def test_missing_file(self, tmp_path):
        result = _load_schedule_file(tmp_path / "nonexistent.json")
        assert result is None

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{invalid json")
        result = _load_schedule_file(f)
        assert result is None

    def test_non_dict_root(self, tmp_path):
        f = tmp_path / "list.json"
        f.write_text("[]")
        result = _load_schedule_file(f)
        assert result is None

    def test_missing_jobs_array(self, tmp_path):
        f = tmp_path / "nojobs.json"
        f.write_text('{"version": 1}')
        result = _load_schedule_file(f)
        assert result is None

    def test_non_list_jobs(self, tmp_path):
        f = tmp_path / "badjobs.json"
        f.write_text('{"jobs": "not a list"}')
        result = _load_schedule_file(f)
        assert result is None


# ── _build_branch_map ────────────────────────────────


class TestBuildBranchMap:
    def test_active_branches_only(self, sample_registry, temp_src_aipass):
        root, src = temp_src_aipass
        (src / "testbranch").mkdir()
        (src / "inactive").mkdir()
        with patch("aipass.daemon.apps.handlers.schedule.discovery._REPO_ROOT", root):
            bmap = _build_branch_map(sample_registry)
        assert "testbranch" in bmap
        assert bmap["testbranch"] == "@testbranch"
        assert "inactive" not in bmap

    def test_empty_registry(self):
        assert _build_branch_map({}) == {}
        assert _build_branch_map({"branches": []}) == {}

    def test_missing_path_skipped(self, sample_registry, temp_src_aipass):
        root, src = temp_src_aipass
        with patch("aipass.daemon.apps.handlers.schedule.discovery._REPO_ROOT", root):
            bmap = _build_branch_map(sample_registry)
        assert len(bmap) == 0


# ── discover_jobs (integration) ──────────────────────


class TestDiscoverJobs:
    def test_discovers_valid_jobs(self, temp_src_aipass, sample_schedule, sample_registry):
        root, src = temp_src_aipass
        branch_dir = src / "testbranch"
        daemon_dir = branch_dir / ".daemon"
        daemon_dir.mkdir(parents=True)
        (daemon_dir / "schedule.json").write_text(json.dumps(sample_schedule))

        reg_file = root / "AIPASS_REGISTRY.json"
        reg_file.write_text(json.dumps(sample_registry))

        with (
            patch("aipass.daemon.apps.handlers.schedule.discovery._REPO_ROOT", root),
            patch("aipass.daemon.apps.handlers.schedule.discovery._SRC_AIPASS", src),
            patch("aipass.daemon.apps.handlers.schedule.discovery._REGISTRY_FILE", reg_file),
        ):
            jobs = discover_jobs()

        assert len(jobs) == 1
        assert jobs[0]["owner"] == "@testbranch"
        assert jobs[0]["id"] == "daily-check"
        assert jobs[0]["schedule"]["type"] == "daily"
        assert jobs[0]["prompt"] == "Run daily check."

    def test_skips_unregistered_branches(self, temp_src_aipass, sample_schedule, sample_registry):
        root, src = temp_src_aipass
        unregistered = src / "unknown_branch"
        daemon_dir = unregistered / ".daemon"
        daemon_dir.mkdir(parents=True)
        (daemon_dir / "schedule.json").write_text(json.dumps(sample_schedule))

        reg_file = root / "AIPASS_REGISTRY.json"
        reg_file.write_text(json.dumps(sample_registry))

        with (
            patch("aipass.daemon.apps.handlers.schedule.discovery._REPO_ROOT", root),
            patch("aipass.daemon.apps.handlers.schedule.discovery._SRC_AIPASS", src),
            patch("aipass.daemon.apps.handlers.schedule.discovery._REGISTRY_FILE", reg_file),
        ):
            jobs = discover_jobs()

        assert len(jobs) == 0

    def test_skips_pycache_and_dotdirs(self, temp_src_aipass, sample_registry):
        root, src = temp_src_aipass
        for name in ["__pycache__", ".hidden", "compass"]:
            d = src / name / ".daemon"
            d.mkdir(parents=True)
            (d / "schedule.json").write_text('{"jobs":[]}')

        reg_file = root / "AIPASS_REGISTRY.json"
        reg_file.write_text(json.dumps(sample_registry))

        with (
            patch("aipass.daemon.apps.handlers.schedule.discovery._REPO_ROOT", root),
            patch("aipass.daemon.apps.handlers.schedule.discovery._SRC_AIPASS", src),
            patch("aipass.daemon.apps.handlers.schedule.discovery._REGISTRY_FILE", reg_file),
        ):
            jobs = discover_jobs()

        assert len(jobs) == 0

    def test_skips_malformed_jobs(self, temp_src_aipass, sample_registry):
        root, src = temp_src_aipass
        branch_dir = src / "testbranch"
        daemon_dir = branch_dir / ".daemon"
        daemon_dir.mkdir(parents=True)
        bad_data = {"version": 1, "jobs": [{"id": "no-schedule"}]}
        (daemon_dir / "schedule.json").write_text(json.dumps(bad_data))

        reg_file = root / "AIPASS_REGISTRY.json"
        reg_file.write_text(json.dumps(sample_registry))

        with (
            patch("aipass.daemon.apps.handlers.schedule.discovery._REPO_ROOT", root),
            patch("aipass.daemon.apps.handlers.schedule.discovery._SRC_AIPASS", src),
            patch("aipass.daemon.apps.handlers.schedule.discovery._REGISTRY_FILE", reg_file),
        ):
            jobs = discover_jobs()

        assert len(jobs) == 0

    def test_disabled_jobs_still_discovered(self, temp_src_aipass, sample_registry):
        root, src = temp_src_aipass
        branch_dir = src / "testbranch"
        daemon_dir = branch_dir / ".daemon"
        daemon_dir.mkdir(parents=True)
        data = {
            "version": 1,
            "jobs": [{"id": "off", "enabled": False, "schedule": {"type": "daily", "time": "04:00"}, "prompt": "x"}],
        }
        (daemon_dir / "schedule.json").write_text(json.dumps(data))

        reg_file = root / "AIPASS_REGISTRY.json"
        reg_file.write_text(json.dumps(sample_registry))

        with (
            patch("aipass.daemon.apps.handlers.schedule.discovery._REPO_ROOT", root),
            patch("aipass.daemon.apps.handlers.schedule.discovery._SRC_AIPASS", src),
            patch("aipass.daemon.apps.handlers.schedule.discovery._REGISTRY_FILE", reg_file),
        ):
            jobs = discover_jobs()

        assert len(jobs) == 1
        assert jobs[0]["enabled"] is False
