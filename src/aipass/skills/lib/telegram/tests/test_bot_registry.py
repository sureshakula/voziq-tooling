"""
Comprehensive pytest tests for bot_registry.py

Covers all public functions with filesystem isolation via tmp_path.
No external dependencies beyond pytest.
"""

import json

import pytest
from aipass.skills.lib.telegram.apps.handlers import bot_registry


# =============================================
# FIXTURES
# =============================================


@pytest.fixture(autouse=True)
def _isolate_registry(tmp_path, monkeypatch):
    """Redirect REGISTRY_DIR and REGISTRY_FILE to tmp_path for every test."""
    reg_dir = tmp_path / "telegram_bots"
    reg_file = reg_dir / "_registry.json"
    monkeypatch.setattr(bot_registry, "REGISTRY_DIR", reg_dir)
    monkeypatch.setattr(bot_registry, "REGISTRY_FILE", reg_file)


def _register_sample(bot_id="bot_alpha", branch="dev_central", work_dir="/home/aipass/dev_central"):
    """Helper to register a sample bot with sensible defaults."""
    return bot_registry.register_bot(
        bot_id=bot_id,
        username=f"{bot_id}_bot",
        branch_name=branch,
        work_dir=work_dir,
        config_path=f"/configs/{bot_id}.json",
    )


# =============================================
# 1. ensure_registry
# =============================================


class TestEnsureRegistry:
    """Tests for ensure_registry()."""

    def test_creates_dir_and_file(self):
        """Should create the registry directory and JSON file from scratch."""
        bot_registry.ensure_registry()

        assert bot_registry.REGISTRY_DIR.is_dir()
        assert bot_registry.REGISTRY_FILE.is_file()

        data = json.loads(bot_registry.REGISTRY_FILE.read_text())
        assert "bots" in data
        assert data["bots"] == {}
        assert "metadata" in data
        assert data["metadata"]["version"] == "1.0.0"
        assert "last_updated" in data["metadata"]

    def test_idempotent_multiple_calls(self):
        """Calling ensure_registry multiple times should not overwrite existing data."""
        bot_registry.ensure_registry()

        # Write a bot entry directly so we can verify it survives a second call
        data = json.loads(bot_registry.REGISTRY_FILE.read_text())
        data["bots"]["test_bot"] = {"bot_id": "test_bot"}
        bot_registry.REGISTRY_FILE.write_text(json.dumps(data))

        bot_registry.ensure_registry()

        reloaded = json.loads(bot_registry.REGISTRY_FILE.read_text())
        assert "test_bot" in reloaded["bots"], "Second ensure_registry should not overwrite existing file"

    def test_creates_parent_dirs(self, tmp_path):
        """Should create nested parent directories if they don't exist."""
        # The autouse fixture already sets a tmp_path-based dir, just verify it works
        assert not bot_registry.REGISTRY_DIR.exists()
        bot_registry.ensure_registry()
        assert bot_registry.REGISTRY_DIR.exists()


# =============================================
# 2. load_registry
# =============================================


class TestLoadRegistry:
    """Tests for load_registry()."""

    def test_returns_empty_when_file_missing(self):
        """Should return empty registry structure when file does not exist."""
        result = bot_registry.load_registry()

        assert isinstance(result, dict)
        assert "bots" in result
        assert result["bots"] == {}
        assert "metadata" in result

    def test_returns_empty_on_corrupt_json(self):
        """Should return empty structure when file contains invalid JSON."""
        bot_registry.REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        bot_registry.REGISTRY_FILE.write_text("this is not json {{{{")

        result = bot_registry.load_registry()

        assert isinstance(result, dict)
        assert result["bots"] == {}

    def test_returns_empty_on_unexpected_structure(self):
        """Should return empty when JSON is valid but missing 'bots' key."""
        bot_registry.REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        bot_registry.REGISTRY_FILE.write_text(json.dumps({"wrong_key": 123}))

        result = bot_registry.load_registry()

        assert "bots" in result
        assert result["bots"] == {}

    def test_returns_empty_on_non_dict(self):
        """Should return empty when file contains a JSON array instead of object."""
        bot_registry.REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        bot_registry.REGISTRY_FILE.write_text(json.dumps([1, 2, 3]))

        result = bot_registry.load_registry()

        assert isinstance(result, dict)
        assert result["bots"] == {}

    def test_loads_valid_data(self):
        """Should correctly load a well-formed registry file."""
        bot_registry.ensure_registry()
        _register_sample()

        result = bot_registry.load_registry()

        assert "bot_alpha" in result["bots"]
        assert result["bots"]["bot_alpha"]["username"] == "bot_alpha_bot"


# =============================================
# 3. save_registry
# =============================================


class TestSaveRegistry:
    """Tests for save_registry()."""

    def test_writes_valid_json(self):
        """Should write valid JSON that can be loaded back."""
        data = {
            "bots": {"test": {"bot_id": "test", "status": "active"}},
            "metadata": {"version": "1.0.0"},
        }

        result = bot_registry.save_registry(data)

        assert result is True
        assert bot_registry.REGISTRY_FILE.is_file()

        loaded = json.loads(bot_registry.REGISTRY_FILE.read_text())
        assert loaded["bots"]["test"]["bot_id"] == "test"

    def test_updates_last_updated_timestamp(self):
        """Should set metadata.last_updated on every save."""
        data = {"bots": {}, "metadata": {}}

        bot_registry.save_registry(data)

        loaded = json.loads(bot_registry.REGISTRY_FILE.read_text())
        assert "last_updated" in loaded["metadata"]

    def test_creates_metadata_if_missing(self):
        """Should create metadata section if the input dict lacks it."""
        data = {"bots": {}}

        bot_registry.save_registry(data)

        loaded = json.loads(bot_registry.REGISTRY_FILE.read_text())
        assert "metadata" in loaded
        assert "last_updated" in loaded["metadata"]

    def test_creates_directory_if_missing(self):
        """Should create the registry directory if it does not exist."""
        assert not bot_registry.REGISTRY_DIR.exists()

        data = {"bots": {}, "metadata": {"version": "1.0.0"}}
        result = bot_registry.save_registry(data)

        assert result is True
        assert bot_registry.REGISTRY_DIR.is_dir()

    def test_returns_false_on_write_failure(self, monkeypatch, tmp_path):
        """Should return False when writing fails (e.g. permission error)."""
        # Put a regular file where a directory is expected. mkdir(parents=True)
        # then fails on every OS (NotADirectoryError/FileExistsError), so this is
        # cross-platform — unlike a hardcoded Unix-only path such as /proc/...
        blocker = tmp_path / "blocker"
        blocker.write_text("x", encoding="utf-8")
        monkeypatch.setattr(bot_registry, "REGISTRY_DIR", blocker / "sub")
        monkeypatch.setattr(bot_registry, "REGISTRY_FILE", blocker / "sub" / "_registry.json")

        result = bot_registry.save_registry({"bots": {}, "metadata": {}})

        assert result is False


# =============================================
# 4. register_bot
# =============================================


class TestRegisterBot:
    """Tests for register_bot()."""

    def test_creates_entry_correctly(self):
        """Should create a complete bot entry with all required fields."""
        result = bot_registry.register_bot(
            bot_id="alpha",
            username="alpha_bot",
            branch_name="dev_central",
            work_dir="/home/aipass/dev_central",
            config_path="/configs/alpha.json",
        )

        assert result is True

        bot = bot_registry.get_bot("alpha")
        assert bot is not None
        assert bot["bot_id"] == "alpha"
        assert bot["username"] == "alpha_bot"
        assert bot["branch_name"] == "dev_central"
        assert bot["work_dir"] == "/home/aipass/dev_central"
        assert bot["config_path"] == "/configs/alpha.json"
        assert bot["service_name"] == "telegram-bot@alpha"
        assert bot["status"] == "active"
        assert "created_at" in bot
        assert "updated_at" in bot

    def test_rejects_duplicate_bot_id(self):
        """Should return False when registering a bot_id that already exists."""
        _register_sample("dup_bot")

        result = _register_sample("dup_bot")

        assert result is False

    def test_token_ref_included_when_provided(self):
        """Should include bot_token_env when bot_token_ref is provided."""
        bot_registry.register_bot(
            bot_id="with_token",
            username="with_token_bot",
            branch_name="flow",
            work_dir="/home/aipass/flow",
            config_path="/configs/with_token.json",
            bot_token_ref="TELEGRAM_BOT_TOKEN_FLOW",
        )

        bot = bot_registry.get_bot("with_token")
        assert bot["bot_token_env"] == "TELEGRAM_BOT_TOKEN_FLOW"

    def test_token_ref_omitted_when_none(self):
        """Should not include bot_token_env when bot_token_ref is None."""
        _register_sample("no_token")

        bot = bot_registry.get_bot("no_token")
        assert "bot_token_env" not in bot

    def test_multiple_bots_coexist(self):
        """Should allow registering multiple distinct bots."""
        _register_sample("bot_a", branch="branch_a", work_dir="/a")
        _register_sample("bot_b", branch="branch_b", work_dir="/b")
        _register_sample("bot_c", branch="branch_c", work_dir="/c")

        bots = bot_registry.list_bots()
        assert len(bots) == 3


# =============================================
# 5. get_bot
# =============================================


class TestGetBot:
    """Tests for get_bot()."""

    def test_returns_correct_entry(self):
        """Should return the matching bot dict."""
        _register_sample("target_bot")
        _register_sample("other_bot", branch="other", work_dir="/other")

        bot = bot_registry.get_bot("target_bot")

        assert bot is not None
        assert bot["bot_id"] == "target_bot"

    def test_returns_none_for_missing(self):
        """Should return None for a bot_id that does not exist."""
        result = bot_registry.get_bot("nonexistent")

        assert result is None

    def test_returns_none_on_empty_registry(self):
        """Should return None when the registry file doesn't exist."""
        result = bot_registry.get_bot("anything")

        assert result is None


# =============================================
# 6. list_bots
# =============================================


class TestListBots:
    """Tests for list_bots()."""

    def test_returns_all_bots(self):
        """Should return all bots when no status filter is provided."""
        _register_sample("bot_1", branch="b1", work_dir="/w1")
        _register_sample("bot_2", branch="b2", work_dir="/w2")

        bots = bot_registry.list_bots()

        assert len(bots) == 2
        bot_ids = {b["bot_id"] for b in bots}
        assert bot_ids == {"bot_1", "bot_2"}

    def test_filter_by_status(self):
        """Should return only bots matching the given status."""
        _register_sample("active_bot", branch="b1", work_dir="/w1")
        _register_sample("to_deactivate", branch="b2", work_dir="/w2")

        # Deactivate one bot
        bot_registry.update_bot("to_deactivate", status="inactive")

        active = bot_registry.list_bots(status="active")
        inactive = bot_registry.list_bots(status="inactive")

        assert len(active) == 1
        assert active[0]["bot_id"] == "active_bot"
        assert len(inactive) == 1
        assert inactive[0]["bot_id"] == "to_deactivate"

    def test_filter_returns_empty_on_no_match(self):
        """Should return empty list when no bots match the status."""
        _register_sample("active_bot")

        result = bot_registry.list_bots(status="inactive")

        assert result == []

    def test_empty_registry_returns_empty_list(self):
        """Should return empty list when no bots are registered."""
        result = bot_registry.list_bots()

        assert result == []


# =============================================
# 7. update_bot
# =============================================


class TestUpdateBot:
    """Tests for update_bot()."""

    def test_updates_fields(self):
        """Should update the specified fields on the bot entry."""
        _register_sample("upd_bot")

        result = bot_registry.update_bot("upd_bot", status="inactive", username="new_name")

        assert result is True

        bot = bot_registry.get_bot("upd_bot")
        assert bot["status"] == "inactive"
        assert bot["username"] == "new_name"

    def test_updates_timestamp(self):
        """Should update the updated_at timestamp on the bot entry."""
        _register_sample("ts_bot")
        original = bot_registry.get_bot("ts_bot")
        original_ts = original["updated_at"]

        bot_registry.update_bot("ts_bot", status="stopped")
        updated = bot_registry.get_bot("ts_bot")

        assert updated["updated_at"] >= original_ts

    def test_returns_false_for_missing_bot(self):
        """Should return False when trying to update a non-existent bot."""
        result = bot_registry.update_bot("ghost", status="active")

        assert result is False

    def test_preserves_other_fields(self):
        """Should not modify fields that were not passed as kwargs."""
        _register_sample("preserve_bot")

        bot_registry.update_bot("preserve_bot", status="paused")

        bot = bot_registry.get_bot("preserve_bot")
        assert bot["username"] == "preserve_bot_bot"
        assert bot["branch_name"] == "dev_central"
        assert bot["status"] == "paused"

    def test_can_add_new_fields(self):
        """Should allow adding entirely new fields to a bot entry."""
        _register_sample("extend_bot")

        bot_registry.update_bot("extend_bot", custom_field="custom_value")

        bot = bot_registry.get_bot("extend_bot")
        assert bot["custom_field"] == "custom_value"


# =============================================
# 8. deregister_bot
# =============================================


class TestDeregisterBot:
    """Tests for deregister_bot()."""

    def test_removes_entry(self):
        """Should remove the bot entry from the registry."""
        _register_sample("doomed_bot")
        assert bot_registry.get_bot("doomed_bot") is not None

        result = bot_registry.deregister_bot("doomed_bot")

        assert result is True
        assert bot_registry.get_bot("doomed_bot") is None

    def test_returns_false_for_missing_bot(self):
        """Should return False when trying to deregister a non-existent bot."""
        result = bot_registry.deregister_bot("nonexistent")

        assert result is False

    def test_other_bots_unaffected(self):
        """Deregistering one bot should not affect others."""
        _register_sample("keep_me", branch="b1", work_dir="/w1")
        _register_sample("delete_me", branch="b2", work_dir="/w2")

        bot_registry.deregister_bot("delete_me")

        assert bot_registry.get_bot("keep_me") is not None
        assert bot_registry.get_bot("delete_me") is None
        assert len(bot_registry.list_bots()) == 1

    def test_can_reregister_after_deregister(self):
        """Should allow re-registering a bot_id after it has been deregistered."""
        _register_sample("recyclable")
        bot_registry.deregister_bot("recyclable")

        result = _register_sample("recyclable")

        assert result is True
        assert bot_registry.get_bot("recyclable") is not None


# =============================================
# 9. get_bot_by_branch
# =============================================


class TestGetBotByBranch:
    """Tests for get_bot_by_branch()."""

    def test_finds_by_branch_name(self):
        """Should return the bot matching the given branch_name."""
        _register_sample("branch_bot", branch="flow")

        result = bot_registry.get_bot_by_branch("flow")

        assert result is not None
        assert result["bot_id"] == "branch_bot"
        assert result["branch_name"] == "flow"

    def test_returns_none_for_unknown_branch(self):
        """Should return None when no bot matches the branch_name."""
        _register_sample("some_bot", branch="seed")

        result = bot_registry.get_bot_by_branch("nonexistent_branch")

        assert result is None

    def test_returns_none_on_empty_registry(self):
        """Should return None when registry is empty."""
        result = bot_registry.get_bot_by_branch("any_branch")

        assert result is None

    def test_handles_none_branch_in_registry(self):
        """Should not crash when some bots have branch_name=None."""
        bot_registry.register_bot(
            bot_id="base_bot",
            username="base_bot",
            branch_name=None,
            work_dir="/base",
            config_path="/configs/base.json",
        )
        _register_sample("named_bot", branch="cortex")

        result = bot_registry.get_bot_by_branch("cortex")

        assert result is not None
        assert result["bot_id"] == "named_bot"


# =============================================
# 10. get_bot_by_work_dir
# =============================================


class TestGetBotByWorkDir:
    """Tests for get_bot_by_work_dir()."""

    def test_matches_exact_path(self, tmp_path):
        """Should find a bot whose work_dir matches exactly."""
        work = tmp_path / "project"
        work.mkdir()

        _register_sample("dir_bot", work_dir=str(work))

        result = bot_registry.get_bot_by_work_dir(str(work))

        assert result is not None
        assert result["bot_id"] == "dir_bot"

    def test_matches_resolved_path(self, tmp_path):
        """Should resolve symlinks and relative components before comparing."""
        real_dir = tmp_path / "real_project"
        real_dir.mkdir()
        link = tmp_path / "link_to_project"
        link.symlink_to(real_dir)

        _register_sample("resolved_bot", work_dir=str(real_dir))

        # Look up using the symlink path - should resolve to the same real path
        result = bot_registry.get_bot_by_work_dir(str(link))

        assert result is not None
        assert result["bot_id"] == "resolved_bot"

    def test_returns_none_for_unregistered_dir(self, tmp_path):
        """Should return None when no bot has the given work_dir."""
        work = tmp_path / "some_dir"
        work.mkdir()

        _register_sample("other_bot", work_dir="/completely/different")

        result = bot_registry.get_bot_by_work_dir(str(work))

        assert result is None

    def test_returns_none_on_empty_registry(self, tmp_path):
        """Should return None when registry is empty."""
        result = bot_registry.get_bot_by_work_dir(str(tmp_path))

        assert result is None

    def test_accepts_path_object(self, tmp_path):
        """Should accept a Path object as well as a string."""
        work = tmp_path / "pathobj_dir"
        work.mkdir()

        _register_sample("pathobj_bot", work_dir=str(work))

        result = bot_registry.get_bot_by_work_dir(work)  # Path, not str

        assert result is not None
        assert result["bot_id"] == "pathobj_bot"

    def test_trailing_slash_normalization(self, tmp_path):
        """Path.resolve() normalizes trailing slashes, so lookup should still match."""
        work = tmp_path / "slash_dir"
        work.mkdir()

        _register_sample("slash_bot", work_dir=str(work))

        # Look up with a trailing slash
        result = bot_registry.get_bot_by_work_dir(str(work) + "/")

        assert result is not None
        assert result["bot_id"] == "slash_bot"


# =============================================
# INTEGRATION / EDGE CASE TESTS
# =============================================


class TestIntegration:
    """End-to-end and edge case tests."""

    def test_full_lifecycle(self):
        """Register, read, update, and deregister a bot in sequence."""
        # Register
        assert (
            bot_registry.register_bot(
                bot_id="lifecycle",
                username="lifecycle_bot",
                branch_name="test_branch",
                work_dir="/lifecycle",
                config_path="/configs/lifecycle.json",
            )
            is True
        )

        # Read
        bot = bot_registry.get_bot("lifecycle")
        assert bot["status"] == "active"

        # Update
        assert bot_registry.update_bot("lifecycle", status="stopped") is True
        bot = bot_registry.get_bot("lifecycle")
        assert bot["status"] == "stopped"

        # Deregister
        assert bot_registry.deregister_bot("lifecycle") is True
        assert bot_registry.get_bot("lifecycle") is None

    def test_ensure_then_operations(self):
        """Calling ensure_registry before CRUD operations works cleanly."""
        bot_registry.ensure_registry()

        _register_sample("ensured_bot")
        assert bot_registry.get_bot("ensured_bot") is not None
        assert len(bot_registry.list_bots()) == 1

    def test_registry_file_is_valid_json_throughout(self):
        """The registry file should always contain valid JSON after operations."""
        bot_registry.ensure_registry()

        _register_sample("json_bot_1", branch="b1", work_dir="/w1")
        data = json.loads(bot_registry.REGISTRY_FILE.read_text())
        assert "bots" in data

        bot_registry.update_bot("json_bot_1", status="inactive")
        data = json.loads(bot_registry.REGISTRY_FILE.read_text())
        assert data["bots"]["json_bot_1"]["status"] == "inactive"

        bot_registry.deregister_bot("json_bot_1")
        data = json.loads(bot_registry.REGISTRY_FILE.read_text())
        assert "json_bot_1" not in data["bots"]

    def test_metadata_version_preserved(self):
        """Metadata version should be preserved across operations."""
        bot_registry.ensure_registry()
        _register_sample("meta_bot")

        data = bot_registry.load_registry()
        assert data["metadata"]["version"] == "1.0.0"
