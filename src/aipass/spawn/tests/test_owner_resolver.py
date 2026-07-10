# =================== META ====================
# Name: test_owner_resolver.py
# Description: Tests for owner resolver and registry authority
# Version: 1.0.0
# Created: 2026-07-10
# Modified: 2026-07-10
# =============================================

"""Tests for owner resolver: get_owner, is_owner, ensure_project_has_owner, backfill."""

import json
import pytest
from unittest.mock import patch


@pytest.fixture
def registry_with_owner(tmp_path):
    """Create a registry file with one owner branch."""
    reg = tmp_path / "AIPASS_REGISTRY.json"
    reg.write_text(
        json.dumps(
            {
                "metadata": {"version": "1.0.0", "last_updated": "2026-07-10", "total_branches": 3},
                "branches": [
                    {
                        "name": "alpha",
                        "path": "src/alpha",
                        "email": "@alpha",
                        "status": "active",
                        "profile": "library",
                        "description": "test",
                        "created": "2026-01-01",
                        "last_active": "2026-01-01",
                    },
                    {
                        "name": "devpulse",
                        "path": "src/devpulse",
                        "email": "@devpulse",
                        "status": "active",
                        "profile": "library",
                        "description": "orchestrator",
                        "created": "2026-01-02",
                        "last_active": "2026-01-02",
                        "owner": True,
                        "registry_id": "abc-123",
                    },
                    {
                        "name": "gamma",
                        "path": "src/gamma",
                        "email": "@gamma",
                        "status": "active",
                        "profile": "library",
                        "description": "test",
                        "created": "2026-01-03",
                        "last_active": "2026-01-03",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return reg


@pytest.fixture
def registry_no_owner(tmp_path):
    """Create a registry file with no owner set."""
    reg = tmp_path / "AIPASS_REGISTRY.json"
    reg.write_text(
        json.dumps(
            {
                "metadata": {"version": "1.0.0", "last_updated": "2026-07-10", "total_branches": 2},
                "branches": [
                    {
                        "name": "alpha",
                        "path": "src/alpha",
                        "email": "@alpha",
                        "status": "active",
                        "profile": "library",
                        "description": "test",
                        "created": "2026-04-16",
                        "last_active": "2026-04-16",
                    },
                    {
                        "name": "devpulse",
                        "path": "src/devpulse",
                        "email": "@devpulse",
                        "status": "active",
                        "profile": "library",
                        "description": "orchestrator",
                        "created": "2026-04-28",
                        "last_active": "2026-04-28",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return reg


class TestGetOwner:
    """Tests for get_owner()."""

    def test_returns_owner_entry(self, registry_with_owner, tmp_path):
        from aipass.spawn.apps.handlers.registry import get_owner

        with patch("aipass.spawn.apps.handlers.registry.find_registry", return_value=registry_with_owner):
            result = get_owner(start_path=tmp_path)

        assert result is not None
        assert result["name"] == "devpulse"
        assert result["owner"] is True

    def test_returns_none_when_no_owner(self, registry_no_owner, tmp_path):
        from aipass.spawn.apps.handlers.registry import get_owner

        with patch("aipass.spawn.apps.handlers.registry.find_registry", return_value=registry_no_owner):
            result = get_owner(start_path=tmp_path)

        assert result is None

    def test_returns_none_when_registry_missing(self, tmp_path):
        from aipass.spawn.apps.handlers.registry import get_owner

        missing = tmp_path / "MISSING_REGISTRY.json"
        with patch("aipass.spawn.apps.handlers.registry.find_registry", return_value=missing):
            result = get_owner(start_path=tmp_path)

        assert result is None

    def test_default_start_path_uses_cwd(self, registry_with_owner):
        from aipass.spawn.apps.handlers.registry import get_owner

        with patch("aipass.spawn.apps.handlers.registry.find_registry", return_value=registry_with_owner):
            result = get_owner()

        assert result is not None
        assert result["name"] == "devpulse"


class TestIsOwner:
    """Tests for is_owner()."""

    def test_true_for_owner_email_with_at(self, registry_with_owner, tmp_path):
        from aipass.spawn.apps.handlers.registry import is_owner

        with patch("aipass.spawn.apps.handlers.registry.find_registry", return_value=registry_with_owner):
            assert is_owner("@devpulse", start_path=tmp_path) is True

    def test_true_for_owner_email_without_at(self, registry_with_owner, tmp_path):
        from aipass.spawn.apps.handlers.registry import is_owner

        with patch("aipass.spawn.apps.handlers.registry.find_registry", return_value=registry_with_owner):
            assert is_owner("devpulse", start_path=tmp_path) is True

    def test_false_for_non_owner(self, registry_with_owner, tmp_path):
        from aipass.spawn.apps.handlers.registry import is_owner

        with patch("aipass.spawn.apps.handlers.registry.find_registry", return_value=registry_with_owner):
            assert is_owner("@alpha", start_path=tmp_path) is False

    def test_false_for_empty_email(self, registry_with_owner, tmp_path):
        from aipass.spawn.apps.handlers.registry import is_owner

        with patch("aipass.spawn.apps.handlers.registry.find_registry", return_value=registry_with_owner):
            assert is_owner("", start_path=tmp_path) is False

    def test_false_for_none_email(self, registry_with_owner, tmp_path):
        from aipass.spawn.apps.handlers.registry import is_owner

        with patch("aipass.spawn.apps.handlers.registry.find_registry", return_value=registry_with_owner):
            assert is_owner(None, start_path=tmp_path) is False

    def test_false_when_no_owner_in_registry(self, registry_no_owner, tmp_path):
        from aipass.spawn.apps.handlers.registry import is_owner

        with patch("aipass.spawn.apps.handlers.registry.find_registry", return_value=registry_no_owner):
            assert is_owner("@devpulse", start_path=tmp_path) is False


class TestEnsureProjectHasOwner:
    """Tests for ensure_project_has_owner() — registry-entry based."""

    def test_sets_owner_on_manager_branch(self, tmp_path):
        from aipass.spawn.apps.handlers.registry import ensure_project_has_owner

        reg = tmp_path / "TEST_REGISTRY.json"
        reg.write_text(
            json.dumps(
                {
                    "metadata": {"version": "1.0.0", "last_updated": "2026-07-10", "total_branches": 2},
                    "branches": [
                        {
                            "name": "alpha",
                            "path": "src/alpha",
                            "email": "@alpha",
                            "status": "active",
                            "profile": "library",
                            "description": "test",
                            "created": "2026-01-01",
                            "last_active": "2026-01-01",
                        },
                        {
                            "name": "devpulse",
                            "path": "src/devpulse",
                            "email": "@devpulse",
                            "status": "active",
                            "profile": "library",
                            "description": "test",
                            "created": "2026-01-02",
                            "last_active": "2026-01-02",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        alpha_dir = tmp_path / "src" / "alpha" / ".trinity"
        alpha_dir.mkdir(parents=True)
        (alpha_dir / "passport.json").write_text(
            json.dumps(
                {
                    "identity": {"citizen_class": "aipass_framework"},
                    "citizenship": {"registry_id": "abc"},
                }
            ),
            encoding="utf-8",
        )

        dp_dir = tmp_path / "src" / "devpulse" / ".trinity"
        dp_dir.mkdir(parents=True)
        (dp_dir / "passport.json").write_text(
            json.dumps(
                {
                    "identity": {"citizen_class": "manager"},
                    "citizenship": {"registry_id": "abc"},
                }
            ),
            encoding="utf-8",
        )

        result = ensure_project_has_owner(reg)
        assert result is True

        data = json.loads(reg.read_text(encoding="utf-8"))
        devpulse_entry = next(b for b in data["branches"] if b["name"] == "devpulse")
        alpha_entry = next(b for b in data["branches"] if b["name"] == "alpha")
        assert devpulse_entry.get("owner") is True
        assert alpha_entry.get("owner") is None or alpha_entry.get("owner") is not True

    def test_noop_when_owner_already_set(self, registry_with_owner):
        from aipass.spawn.apps.handlers.registry import ensure_project_has_owner

        result = ensure_project_has_owner(registry_with_owner)
        assert result is False

    def test_returns_false_for_empty_registry(self, tmp_path):
        from aipass.spawn.apps.handlers.registry import ensure_project_has_owner

        reg = tmp_path / "TEST_REGISTRY.json"
        reg.write_text(
            json.dumps(
                {
                    "metadata": {"version": "1.0.0", "last_updated": "2026-07-10", "total_branches": 0},
                    "branches": [],
                }
            ),
            encoding="utf-8",
        )

        result = ensure_project_has_owner(reg)
        assert result is False


class TestBackfillOwnerAndRegistryId:
    """Tests for backfill_owner_and_registry_id()."""

    def test_backfills_registry_id_and_owner(self, tmp_path):
        from aipass.spawn.apps.handlers.registry import backfill_owner_and_registry_id

        reg = tmp_path / "TEST_REGISTRY.json"
        reg.write_text(
            json.dumps(
                {
                    "metadata": {"version": "1.0.0", "last_updated": "2026-07-10", "total_branches": 2},
                    "branches": [
                        {
                            "name": "alpha",
                            "path": "src/alpha",
                            "email": "@alpha",
                            "status": "active",
                            "profile": "library",
                            "description": "test",
                            "created": "2026-01-01",
                            "last_active": "2026-01-01",
                        },
                        {
                            "name": "devpulse",
                            "path": "src/devpulse",
                            "email": "@devpulse",
                            "status": "active",
                            "profile": "library",
                            "description": "test",
                            "created": "2026-01-02",
                            "last_active": "2026-01-02",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        alpha_dir = tmp_path / "src" / "alpha" / ".trinity"
        alpha_dir.mkdir(parents=True)
        (alpha_dir / "passport.json").write_text(
            json.dumps(
                {
                    "identity": {"citizen_class": "aipass_framework"},
                    "citizenship": {"registry_id": "uuid-alpha"},
                }
            ),
            encoding="utf-8",
        )

        dp_dir = tmp_path / "src" / "devpulse" / ".trinity"
        dp_dir.mkdir(parents=True)
        (dp_dir / "passport.json").write_text(
            json.dumps(
                {
                    "identity": {"citizen_class": "manager"},
                    "citizenship": {"registry_id": "uuid-dp"},
                }
            ),
            encoding="utf-8",
        )

        result = backfill_owner_and_registry_id(reg)
        assert result is True

        data = json.loads(reg.read_text(encoding="utf-8"))
        alpha_entry = next(b for b in data["branches"] if b["name"] == "alpha")
        dp_entry = next(b for b in data["branches"] if b["name"] == "devpulse")

        assert alpha_entry["registry_id"] == "uuid-alpha"
        assert dp_entry["registry_id"] == "uuid-dp"
        assert dp_entry["owner"] is True
        assert alpha_entry.get("owner") is None or alpha_entry.get("owner") is not True

    def test_noop_when_already_backfilled(self, tmp_path):
        from aipass.spawn.apps.handlers.registry import backfill_owner_and_registry_id

        reg = tmp_path / "TEST_REGISTRY.json"
        reg.write_text(
            json.dumps(
                {
                    "metadata": {"version": "1.0.0", "last_updated": "2026-07-10", "total_branches": 1},
                    "branches": [
                        {
                            "name": "devpulse",
                            "path": "src/devpulse",
                            "email": "@devpulse",
                            "status": "active",
                            "profile": "library",
                            "description": "test",
                            "created": "2026-01-01",
                            "last_active": "2026-01-01",
                            "owner": True,
                            "registry_id": "uuid-dp",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        dp_dir = tmp_path / "src" / "devpulse" / ".trinity"
        dp_dir.mkdir(parents=True)
        (dp_dir / "passport.json").write_text(
            json.dumps(
                {
                    "identity": {"citizen_class": "manager"},
                    "citizenship": {"registry_id": "uuid-dp"},
                }
            ),
            encoding="utf-8",
        )

        result = backfill_owner_and_registry_id(reg)
        assert result is False

    def test_skips_branches_without_passport(self, tmp_path):
        from aipass.spawn.apps.handlers.registry import backfill_owner_and_registry_id

        reg = tmp_path / "TEST_REGISTRY.json"
        reg.write_text(
            json.dumps(
                {
                    "metadata": {"version": "1.0.0", "last_updated": "2026-07-10", "total_branches": 1},
                    "branches": [
                        {
                            "name": "ghost",
                            "path": "src/ghost",
                            "email": "@ghost",
                            "status": "active",
                            "profile": "library",
                            "description": "test",
                            "created": "2026-01-01",
                            "last_active": "2026-01-01",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        result = backfill_owner_and_registry_id(reg)
        assert result is False


class TestAddToRegistryWithRegistryId:
    """Tests for add_to_registry with registry_id parameter."""

    def test_includes_registry_id_when_provided(self, tmp_path):
        from aipass.spawn.apps.handlers.registry import add_to_registry

        reg = tmp_path / "TEST_REGISTRY.json"
        reg.write_text(
            json.dumps(
                {
                    "metadata": {"version": "1.0.0", "last_updated": "2026-07-10", "total_branches": 0},
                    "branches": [],
                }
            ),
            encoding="utf-8",
        )

        result = add_to_registry(
            reg,
            "NEW_BRANCH",
            "src/new_branch",
            "library",
            "@new_branch",
            purpose="test branch",
            registry_id="uuid-new",
        )
        assert result is True

        data = json.loads(reg.read_text(encoding="utf-8"))
        entry = data["branches"][0]
        assert entry["registry_id"] == "uuid-new"

    def test_omits_registry_id_when_empty(self, tmp_path):
        from aipass.spawn.apps.handlers.registry import add_to_registry

        reg = tmp_path / "TEST_REGISTRY.json"
        reg.write_text(
            json.dumps(
                {
                    "metadata": {"version": "1.0.0", "last_updated": "2026-07-10", "total_branches": 0},
                    "branches": [],
                }
            ),
            encoding="utf-8",
        )

        add_to_registry(reg, "NEW_BRANCH", "src/new_branch", "library", "@new_branch")

        data = json.loads(reg.read_text(encoding="utf-8"))
        entry = data["branches"][0]
        assert "registry_id" not in entry
