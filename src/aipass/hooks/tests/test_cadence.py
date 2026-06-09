# =================== AIPass ====================
# Name: test_cadence.py
# Version: 1.0.0
# Description: Tests for cadence module (DPLAN-0200)
# Branch: hooks
# Created: 2026-06-08
# Modified: 2026-06-08
# =============================================

"""Tests for apps/modules/cadence.py."""

import json
import importlib
from unittest.mock import patch

MODULE = "aipass.hooks.apps.modules.cadence"


def _reset_module_globals():
    """Reset module-level caches between tests."""
    import aipass.hooks.apps.modules.cadence as mod

    mod._turn = None
    mod._config = None


class TestShouldFire:
    def setup_method(self):
        _reset_module_globals()

    def test_turn_0_always_fires(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import should_fire

        state_file = tmp_path / "aipass-cadence-test-session.json"

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
            patch(f"{MODULE}._CONFIG_PATH", tmp_path / "cadence.json"),
        ):
            assert should_fire("global") is True
            assert json.loads(state_file.read_text())["turn"] == 0

    def test_turn_0_fires_all_loaders(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import should_fire

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
            patch(f"{MODULE}._CONFIG_PATH", tmp_path / "cadence.json"),
        ):
            assert should_fire("global") is True
            assert should_fire("branch") is True

    def test_non_fire_turn_returns_false(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import should_fire

        state_file = tmp_path / "aipass-cadence-test-session.json"
        state_file.write_text(json.dumps({"turn": 0}))

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
            patch(f"{MODULE}._CONFIG_PATH", tmp_path / "cadence.json"),
        ):
            assert should_fire("global") is False

    def test_fire_turn_returns_true(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import should_fire

        state_file = tmp_path / "aipass-cadence-test-session.json"
        state_file.write_text(json.dumps({"turn": 3}))

        config = tmp_path / "cadence.json"
        config.write_text(json.dumps({"enabled": True, "period": 5, "loaders": {"global": {"offset": 4}}}))

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
            patch(f"{MODULE}._CONFIG_PATH", config),
        ):
            assert should_fire("global") is True

    def test_cadence_disabled_always_fires(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import should_fire

        state_file = tmp_path / "aipass-cadence-test-session.json"
        state_file.write_text(json.dumps({"turn": 1}))

        config = tmp_path / "cadence.json"
        config.write_text(json.dumps({"enabled": False}))

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
            patch(f"{MODULE}._CONFIG_PATH", config),
        ):
            assert should_fire("global") is True

    def test_no_session_id_fires(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import should_fire

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {}, clear=False),
            patch(f"{MODULE}._CONFIG_PATH", tmp_path / "cadence.json"),
        ):
            env = dict(__import__("os").environ)
            env.pop("CLAUDE_CODE_SESSION_ID", None)
            with patch.dict("os.environ", env, clear=True):
                assert should_fire("global") is True

    def test_counter_increments_once_per_process(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import should_fire

        state_file = tmp_path / "aipass-cadence-test-session.json"
        state_file.write_text(json.dumps({"turn": 3}))

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
            patch(f"{MODULE}._CONFIG_PATH", tmp_path / "cadence.json"),
        ):
            should_fire("global")
            should_fire("branch")
            data = json.loads(state_file.read_text())
            assert data["turn"] == 4

    def test_period_zero_always_fires(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import should_fire

        state_file = tmp_path / "aipass-cadence-test-session.json"
        state_file.write_text(json.dumps({"turn": 2}))

        config = tmp_path / "cadence.json"
        config.write_text(json.dumps({"enabled": True, "period": 0}))

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
            patch(f"{MODULE}._CONFIG_PATH", config),
        ):
            assert should_fire("global") is True

    def test_stagger_offsets(self, tmp_path):
        config = tmp_path / "cadence.json"
        config.write_text(
            json.dumps({"enabled": True, "period": 5, "loaders": {"global": {"offset": 0}, "branch": {"offset": 2}}})
        )

        state_file = tmp_path / "aipass-cadence-test-session.json"
        state_file.write_text(json.dumps({"turn": 4}))

        from aipass.hooks.apps.modules.cadence import should_fire

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
            patch(f"{MODULE}._CONFIG_PATH", config),
        ):
            assert should_fire("global") is True
            assert should_fire("branch") is False

    def test_unknown_loader_uses_offset_zero(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import should_fire

        state_file = tmp_path / "aipass-cadence-test-session.json"
        state_file.write_text(json.dumps({"turn": 4}))

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
            patch(f"{MODULE}._CONFIG_PATH", tmp_path / "cadence.json"),
        ):
            assert should_fire("unknown_loader") is True


class TestResetCounter:
    def setup_method(self):
        _reset_module_globals()

    def test_reset_writes_minus_one(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import reset_counter

        state_file = tmp_path / "aipass-cadence-test-session.json"
        state_file.write_text(json.dumps({"turn": 7}))

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
        ):
            reset_counter()

        data = json.loads(state_file.read_text())
        assert data["turn"] == -1

    def test_reset_then_next_turn_is_zero(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import reset_counter, should_fire

        state_file = tmp_path / "aipass-cadence-test-session.json"
        state_file.write_text(json.dumps({"turn": 7}))

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
            patch(f"{MODULE}._CONFIG_PATH", tmp_path / "cadence.json"),
        ):
            reset_counter()

        _reset_module_globals()

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
            patch(f"{MODULE}._CONFIG_PATH", tmp_path / "cadence.json"),
        ):
            assert should_fire("global") is True
            data = json.loads(state_file.read_text())
            assert data["turn"] == 0

    def test_reset_no_session_id_is_noop(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import reset_counter

        with patch(f"{MODULE}._GUARD_DIR", tmp_path):
            env = dict(__import__("os").environ)
            env.pop("CLAUDE_CODE_SESSION_ID", None)
            with patch.dict("os.environ", env, clear=True):
                reset_counter()

        assert not list(tmp_path.glob("aipass-cadence-*"))

    def test_reset_creates_file_if_missing(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import reset_counter

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
        ):
            reset_counter()

        state_file = tmp_path / "aipass-cadence-test-session.json"
        assert state_file.exists()
        assert json.loads(state_file.read_text())["turn"] == -1


class TestConfig:
    def setup_method(self):
        _reset_module_globals()

    def test_defaults_used_when_no_config_file(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import _load_config

        with patch(f"{MODULE}._CONFIG_PATH", tmp_path / "nonexistent.json"):
            config = _load_config()

        assert config["enabled"] is True
        assert config["period"] == 5
        assert config["loaders"]["global"]["offset"] == 0
        assert config["loaders"]["branch"]["offset"] == 0

    def test_config_deep_merges_over_defaults(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import _load_config

        config_file = tmp_path / "cadence.json"
        config_file.write_text(json.dumps({"period": 10, "loaders": {"global": {"offset": 3}}}))

        with patch(f"{MODULE}._CONFIG_PATH", config_file):
            config = _load_config()

        assert config["period"] == 10
        assert config["loaders"]["global"]["offset"] == 3
        assert config["loaders"]["branch"]["offset"] == 0
        assert config["enabled"] is True

    def test_bad_config_falls_back_to_defaults(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import _load_config

        config_file = tmp_path / "cadence.json"
        config_file.write_text("not valid json{{{")

        with patch(f"{MODULE}._CONFIG_PATH", config_file):
            config = _load_config()

        assert config["period"] == 5


class TestDeepMerge:
    def test_nested_merge(self):
        from aipass.hooks.apps.modules.cadence import _deep_merge

        base = {"a": 1, "b": {"c": 2, "d": 3}}
        updates = {"b": {"c": 99}, "e": 4}
        result = _deep_merge(base, updates)

        assert result["a"] == 1
        assert result["b"]["c"] == 99
        assert result["b"]["d"] == 3
        assert result["e"] == 4

    def test_overwrites_non_dict(self):
        from aipass.hooks.apps.modules.cadence import _deep_merge

        base = {"a": [1, 2]}
        result = _deep_merge(base, {"a": [3]})
        assert result["a"] == [3]


class TestPerSessionIsolation:
    def setup_method(self):
        _reset_module_globals()

    def test_different_sessions_use_different_files(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import should_fire

        state_a = tmp_path / "aipass-cadence-session-a.json"
        state_a.write_text(json.dumps({"turn": 4}))

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "session-a"}),
            patch(f"{MODULE}._CONFIG_PATH", tmp_path / "cadence.json"),
        ):
            should_fire("global")
            data_a = json.loads(state_a.read_text())
            assert data_a["turn"] == 5

        _reset_module_globals()

        state_b = tmp_path / "aipass-cadence-session-b.json"
        assert not state_b.exists()

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "session-b"}),
            patch(f"{MODULE}._CONFIG_PATH", tmp_path / "cadence.json"),
        ):
            assert should_fire("global") is True
            data_b = json.loads(state_b.read_text())
            assert data_b["turn"] == 0


class TestModuleInterface:
    def setup_method(self):
        _reset_module_globals()

    def test_handle_command_cadence_returns_true(self):
        from aipass.hooks.apps.modules.cadence import handle_command

        with patch(f"{MODULE}.print_introspection"):
            assert handle_command("cadence", []) is True

    def test_handle_command_unknown_returns_false(self):
        from aipass.hooks.apps.modules.cadence import handle_command

        assert handle_command("other", []) is False

    def test_print_introspection_runs(self, tmp_path):
        from aipass.hooks.apps.modules.cadence import print_introspection

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
            patch(f"{MODULE}._CONFIG_PATH", tmp_path / "cadence.json"),
        ):
            print_introspection()


class TestCompactIntegration:
    def setup_method(self):
        _reset_module_globals()

    def test_compact_handler_resets_cadence(self, tmp_path):
        state_file = tmp_path / "aipass-cadence-test-session.json"
        state_file.write_text(json.dumps({"turn": 7}))

        import aipass.hooks.apps.modules.cadence as cadence_mod

        with (
            patch.object(cadence_mod, "_GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
        ):
            mock_cadence = importlib.import_module("aipass.hooks.apps.modules.cadence")
            mock_cadence.reset_counter()

        data = json.loads(state_file.read_text())
        assert data["turn"] == -1


class TestLoaderCadenceGuard:
    def setup_method(self):
        _reset_module_globals()

    def test_global_loader_skips_on_non_fire_turn(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.global_loader import handle

        state_file = tmp_path / "aipass-cadence-test-session.json"
        state_file.write_text(json.dumps({"turn": 0}))

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
            patch(f"{MODULE}._CONFIG_PATH", tmp_path / "cadence.json"),
            patch("aipass.hooks.apps.handlers.prompt.global_loader.speak"),
        ):
            result = handle({})

        assert result["stdout"] == ""
        assert result["exit_code"] == 0

    def test_branch_loader_skips_on_non_fire_turn(self, tmp_path):
        from aipass.hooks.apps.handlers.prompt.branch_loader import handle

        state_file = tmp_path / "aipass-cadence-test-session.json"
        state_file.write_text(json.dumps({"turn": 0}))

        with (
            patch(f"{MODULE}._GUARD_DIR", tmp_path),
            patch.dict("os.environ", {"CLAUDE_CODE_SESSION_ID": "test-session"}),
            patch(f"{MODULE}._CONFIG_PATH", tmp_path / "cadence.json"),
            patch("aipass.hooks.apps.handlers.prompt.branch_loader.speak"),
        ):
            result = handle({})

        assert result["stdout"] == ""
        assert result["exit_code"] == 0
