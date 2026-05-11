# =================== AIPass ====================
# Name: test_update_local.py
# Description: Tests for update_local handler — Flow dashboard updates
# Version: 1.0.0
# Created: 2026-04-26
# Modified: 2026-04-26
# =============================================

"""Tests for update_local handler — Flow dashboard updates."""

import json
from pathlib import Path
import pytest


# ─── Patch targets ───────────────────────────────────────
_MOD = "aipass.flow.apps.handlers.dashboard.update_local"


def _import_mod():
    """Import update_local module and return it."""
    import aipass.flow.apps.handlers.dashboard.update_local as mod

    return mod


# ─── Shared fixtures ─────────────────────────────────────


@pytest.fixture
def setup_paths(tmp_path, monkeypatch):
    """Redirect all module-level path constants into tmp_path."""
    mod = _import_mod()
    flow_root = tmp_path / "flow"
    flow_root.mkdir()
    flow_json = flow_root / "flow_json"
    flow_json.mkdir()
    monkeypatch.setattr(mod, "FLOW_ROOT", flow_root)
    monkeypatch.setattr(mod, "FLOW_JSON_DIR", flow_json)
    monkeypatch.setattr(mod, "REGISTRY_FILE", flow_json / "fplan_registry.json")
    monkeypatch.setattr(mod, "DASHBOARD_FILE", flow_root / "DASHBOARD.local.json")
    return flow_root


def _write_json(path: Path, data: dict) -> None:
    """Helper to write JSON to a file."""
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict:
    """Helper to read JSON from a file."""
    return json.loads(path.read_text(encoding="utf-8"))


def _make_template_registry(flow_json: Path, types: dict | None = None) -> Path:
    """Create a template_registry.json with the given types."""
    if types is None:
        types = {
            "flow_plans": {"prefix": "FPLAN", "shorthand": "fplan"},
            "dev_plans": {"prefix": "DPLAN", "shorthand": "dplan"},
            "test_plans": {"prefix": "TDPLAN", "shorthand": "tdplan"},
        }
    path = flow_json / "template_registry.json"
    _write_json(path, {"types": types})
    return path


def _make_registry(flow_json: Path, filename: str, plans: dict, next_number: int = 10) -> Path:
    """Create a registry file with plans."""
    path = flow_json / filename
    _write_json(path, {"plans": plans, "next_number": next_number})
    return path


# ═══════════════════════════════════════════════════════════
# 1. _get_all_registry_files
# ═══════════════════════════════════════════════════════════


class TestGetAllRegistryFiles:
    """Tests for _get_all_registry_files — template registry parsing."""

    def test_returns_filenames_from_template_registry(self, setup_paths):
        """Should return per-type registry filenames when template exists."""
        mod = _import_mod()
        flow_json = setup_paths / "flow_json"
        _make_template_registry(flow_json)
        result = mod._get_all_registry_files()
        assert "fplan_registry.json" in result
        assert "dplan_registry.json" in result
        assert "tdplan_registry.json" in result

    def test_no_duplicates_in_result(self, setup_paths):
        """Should not produce duplicate filenames."""
        mod = _import_mod()
        flow_json = setup_paths / "flow_json"
        types = {
            "a": {"prefix": "FPLAN"},
            "b": {"prefix": "FPLAN"},
        }
        _make_template_registry(flow_json, types)
        result = mod._get_all_registry_files()
        assert result.count("fplan_registry.json") == 1

    def test_falls_back_when_template_missing(self, setup_paths):
        """Should return default REGISTRY_FILE.name when template is absent."""
        mod = _import_mod()
        result = mod._get_all_registry_files()
        assert result == [mod.REGISTRY_FILE.name]

    def test_falls_back_on_read_error(self, setup_paths):
        """Should return default on JSON decode error."""
        mod = _import_mod()
        flow_json = setup_paths / "flow_json"
        template_path = flow_json / "template_registry.json"
        template_path.write_text("NOT VALID JSON", encoding="utf-8")
        result = mod._get_all_registry_files()
        assert result == [mod.REGISTRY_FILE.name]

    def test_falls_back_when_no_prefixes_found(self, setup_paths):
        """Should return default when types exist but none have a prefix."""
        mod = _import_mod()
        flow_json = setup_paths / "flow_json"
        types = {
            "empty_type": {"shorthand": "nope"},
            "also_empty": {},
        }
        _make_template_registry(flow_json, types)
        result = mod._get_all_registry_files()
        assert result == [mod.REGISTRY_FILE.name]

    def test_skips_entries_with_empty_prefix(self, setup_paths):
        """Should skip types whose prefix is an empty string."""
        mod = _import_mod()
        flow_json = setup_paths / "flow_json"
        types = {
            "good": {"prefix": "FPLAN"},
            "bad": {"prefix": ""},
        }
        _make_template_registry(flow_json, types)
        result = mod._get_all_registry_files()
        assert result == ["fplan_registry.json"]


# ═══════════════════════════════════════════════════════════
# 2. _read_registry
# ═══════════════════════════════════════════════════════════


class TestReadRegistry:
    """Tests for _read_registry — multi-registry merging."""

    def test_merges_multiple_registries(self, setup_paths):
        """Should merge plans from multiple registry files."""
        mod = _import_mod()
        flow_json = setup_paths / "flow_json"
        _make_template_registry(
            flow_json,
            {
                "flow": {"prefix": "FPLAN"},
                "dev": {"prefix": "DPLAN"},
            },
        )
        _make_registry(
            flow_json,
            "fplan_registry.json",
            {
                "1": {"subject": "Plan A", "status": "open", "location": "flow"},
            },
            next_number=5,
        )
        _make_registry(
            flow_json,
            "dplan_registry.json",
            {
                "2": {"subject": "Plan B", "status": "closed", "location": "flow"},
            },
            next_number=8,
        )

        result = mod._read_registry()
        assert result is not None
        assert "FPLAN-0001" in result["plans"]
        assert "DPLAN-0002" in result["plans"]

    def test_keeps_highest_next_number(self, setup_paths):
        """Should keep the highest next_number across registries."""
        mod = _import_mod()
        flow_json = setup_paths / "flow_json"
        _make_template_registry(
            flow_json,
            {
                "a": {"prefix": "FPLAN"},
                "b": {"prefix": "DPLAN"},
            },
        )
        _make_registry(flow_json, "fplan_registry.json", {}, next_number=3)
        _make_registry(flow_json, "dplan_registry.json", {}, next_number=15)

        result = mod._read_registry()
        assert result is not None
        assert result["next_number"] == 15

    def test_returns_none_if_no_registries_found(self, setup_paths):
        """Should return None when no registry files exist on disk."""
        mod = _import_mod()
        result = mod._read_registry()
        assert result is None

    def test_handles_read_error_gracefully(self, setup_paths):
        """Should skip corrupt registry files without crashing."""
        mod = _import_mod()
        flow_json = setup_paths / "flow_json"
        # No template registry, so it falls back to REGISTRY_FILE.name
        corrupt = flow_json / mod.REGISTRY_FILE.name
        corrupt.write_text("{bad json", encoding="utf-8")
        result = mod._read_registry()
        # The file exists but can't be parsed; found_any stays False
        assert result is None

    def test_single_valid_registry(self, setup_paths):
        """Should work with a single valid registry file."""
        mod = _import_mod()
        flow_json = setup_paths / "flow_json"
        _make_registry(
            flow_json,
            mod.REGISTRY_FILE.name,
            {
                "1": {"subject": "Solo plan", "status": "open", "location": "flow"},
            },
            next_number=2,
        )

        result = mod._read_registry()
        assert result is not None
        assert result["plans"]["FPLAN-0001"]["subject"] == "Solo plan"
        assert result["next_number"] == 2


# ═══════════════════════════════════════════════════════════
# 3. _extract_flow_plans
# ═══════════════════════════════════════════════════════════


class TestExtractFlowPlans:
    """Tests for _extract_flow_plans — filtering and partitioning."""

    def test_filters_plans_by_flow_location(self):
        """Should only include plans where location contains 'flow'."""
        mod = _import_mod()
        registry = {
            "plans": {
                "FPLAN-0001": {"subject": "A", "status": "open", "location": "flow", "file_path": "FPLAN-0001.md"},
                "FPLAN-0002": {"subject": "B", "status": "open", "location": "drone", "file_path": "FPLAN-0002.md"},
                "FPLAN-0003": {"subject": "C", "status": "open", "location": "flow/sub", "file_path": "FPLAN-0003.md"},
            }
        }
        active, closed = mod._extract_flow_plans(registry)
        assert len(active) == 2
        plan_ids = [p["plan_id"] for p in active]
        assert "FPLAN-0001" in plan_ids
        assert "FPLAN-0003" in plan_ids

    def test_partitions_by_status(self):
        """Should separate open and closed plans."""
        mod = _import_mod()
        registry = {
            "plans": {
                "FPLAN-0001": {"subject": "Open", "status": "open", "location": "flow", "file_path": "FPLAN-0001.md"},
                "FPLAN-0002": {
                    "subject": "Closed",
                    "status": "closed",
                    "location": "flow",
                    "file_path": "FPLAN-0002.md",
                },
            }
        }
        active, closed = mod._extract_flow_plans(registry)
        assert len(active) == 1
        assert len(closed) == 1
        assert active[0]["status"] == "open"
        assert closed[0]["status"] == "closed"

    def test_extracts_prefix_from_composite_key(self):
        """Should use composite key as plan_id directly."""
        mod = _import_mod()
        registry = {
            "plans": {
                "DPLAN-0004": {
                    "subject": "Dev",
                    "status": "open",
                    "location": "flow",
                    "file_path": "/some/path/DPLAN-0004_dev_thing.md",
                },
            }
        }
        active, _ = mod._extract_flow_plans(registry)
        assert active[0]["plan_id"] == "DPLAN-0004"

    def test_extracts_tdplan_prefix(self):
        """Should handle TDPLAN prefix correctly."""
        mod = _import_mod()
        registry = {
            "plans": {
                "TDPLAN-0007": {
                    "subject": "Test plan",
                    "status": "open",
                    "location": "flow",
                    "file_path": "TDPLAN-0007_test.md",
                },
            }
        }
        active, _ = mod._extract_flow_plans(registry)
        assert active[0]["plan_id"] == "TDPLAN-0007"

    def test_uses_key_as_plan_id(self):
        """Should use the composite key directly as plan_id."""
        mod = _import_mod()
        registry = {
            "plans": {
                "FPLAN-0009": {
                    "subject": "Mystery",
                    "status": "open",
                    "location": "flow",
                    "file_path": "random_file.md",
                },
            }
        }
        active, _ = mod._extract_flow_plans(registry)
        assert active[0]["plan_id"] == "FPLAN-0009"

    def test_sorts_active_and_closed_by_plan_id(self):
        """Should sort both lists by plan_id."""
        mod = _import_mod()
        registry = {
            "plans": {
                "FPLAN-0003": {"subject": "C", "status": "open", "location": "flow", "file_path": "FPLAN-0003.md"},
                "FPLAN-0001": {"subject": "A", "status": "open", "location": "flow", "file_path": "FPLAN-0001.md"},
                "FPLAN-0005": {"subject": "E", "status": "closed", "location": "flow", "file_path": "FPLAN-0005.md"},
                "FPLAN-0002": {"subject": "B", "status": "closed", "location": "flow", "file_path": "FPLAN-0002.md"},
            }
        }
        active, closed = mod._extract_flow_plans(registry)
        assert [p["plan_id"] for p in active] == ["FPLAN-0001", "FPLAN-0003"]
        assert [p["plan_id"] for p in closed] == ["FPLAN-0002", "FPLAN-0005"]

    def test_handles_timestamps(self):
        """Should include created and closed timestamps when present."""
        mod = _import_mod()
        registry = {
            "plans": {
                "FPLAN-0001": {
                    "subject": "With timestamps",
                    "status": "closed",
                    "location": "flow",
                    "file_path": "FPLAN-0001.md",
                    "created": "2026-01-01T00:00:00Z",
                    "closed": "2026-01-02T00:00:00Z",
                    "closed_reason": "completed",
                },
            }
        }
        _, closed = mod._extract_flow_plans(registry)
        assert closed[0]["created"] == "2026-01-01T00:00:00Z"
        assert closed[0]["closed"] == "2026-01-02T00:00:00Z"
        assert closed[0]["closed_reason"] == "completed"

    def test_plan_without_timestamps(self):
        """Should not include timestamp keys when absent from source data."""
        mod = _import_mod()
        registry = {
            "plans": {
                "FPLAN-0001": {
                    "subject": "No times",
                    "status": "open",
                    "location": "flow",
                    "file_path": "FPLAN-0001.md",
                },
            }
        }
        active, _ = mod._extract_flow_plans(registry)
        assert "created" not in active[0]
        assert "closed" not in active[0]

    def test_empty_plans_dict(self):
        """Should return empty lists when no plans exist."""
        mod = _import_mod()
        active, closed = mod._extract_flow_plans({"plans": {}})
        assert active == []
        assert closed == []

    def test_case_insensitive_location_match(self):
        """Should match location 'Flow', 'FLOW', etc."""
        mod = _import_mod()
        registry = {
            "plans": {
                "FPLAN-0001": {"subject": "A", "status": "open", "location": "Flow", "file_path": "FPLAN-0001.md"},
                "FPLAN-0002": {"subject": "B", "status": "open", "location": "FLOW", "file_path": "FPLAN-0002.md"},
            }
        }
        active, _ = mod._extract_flow_plans(registry)
        assert len(active) == 2


# ═══════════════════════════════════════════════════════════
# 4. _calculate_statistics
# ═══════════════════════════════════════════════════════════


class TestCalculateStatistics:
    """Tests for _calculate_statistics — stats computation."""

    def test_returns_correct_counts(self):
        """Should return active_count, total_closed, and next_number."""
        mod = _import_mod()
        active = [{"plan_id": "FPLAN-1"}, {"plan_id": "FPLAN-2"}]
        closed = [{"plan_id": "FPLAN-3"}]
        registry = {"next_number": 10}
        stats = mod._calculate_statistics(active, closed, registry)
        assert stats == {"active_count": 2, "total_closed": 1, "next_number": 10}

    def test_empty_lists(self):
        """Should handle empty active and closed lists."""
        mod = _import_mod()
        stats = mod._calculate_statistics([], [], {"next_number": 1})
        assert stats == {"active_count": 0, "total_closed": 0, "next_number": 1}

    def test_defaults_next_number_to_one(self):
        """Should default next_number to 1 when missing from registry."""
        mod = _import_mod()
        stats = mod._calculate_statistics([], [], {})
        assert stats["next_number"] == 1


# ═══════════════════════════════════════════════════════════
# 5. _read_existing_dashboard
# ═══════════════════════════════════════════════════════════


class TestReadExistingDashboard:
    """Tests for _read_existing_dashboard — safe file reading."""

    def test_returns_empty_dict_if_file_missing(self, setup_paths):
        """Should return {} when DASHBOARD_FILE does not exist."""
        mod = _import_mod()
        result = mod._read_existing_dashboard()
        assert result == {}

    def test_returns_empty_dict_for_old_markdown_format(self, setup_paths):
        """Should return {} if content starts with warning emoji."""
        mod = _import_mod()
        dashboard_file = setup_paths / "DASHBOARD.local.json"
        dashboard_file.write_text("⚠️ Old markdown content here", encoding="utf-8")
        result = mod._read_existing_dashboard()
        assert result == {}

    def test_returns_empty_dict_if_empty_content(self, setup_paths):
        """Should return {} if file is empty or whitespace only."""
        mod = _import_mod()
        dashboard_file = setup_paths / "DASHBOARD.local.json"
        dashboard_file.write_text("   \n  ", encoding="utf-8")
        result = mod._read_existing_dashboard()
        assert result == {}

    def test_handles_corrupt_json(self, setup_paths):
        """Should return {} on JSON parse error."""
        mod = _import_mod()
        dashboard_file = setup_paths / "DASHBOARD.local.json"
        dashboard_file.write_text("{broken json", encoding="utf-8")
        result = mod._read_existing_dashboard()
        assert result == {}

    def test_returns_parsed_json(self, setup_paths):
        """Should return parsed dict for valid JSON."""
        mod = _import_mod()
        dashboard_file = setup_paths / "DASHBOARD.local.json"
        data = {"branch": "FLOW", "custom_section": {"key": "value"}}
        _write_json(dashboard_file, data)
        result = mod._read_existing_dashboard()
        assert result == data


# ═══════════════════════════════════════════════════════════
# 6. _build_dashboard_data
# ═══════════════════════════════════════════════════════════


class TestBuildDashboardData:
    """Tests for _build_dashboard_data — dashboard assembly."""

    def test_preserves_existing_sections(self):
        """Should keep existing data from other branches."""
        mod = _import_mod()
        existing = {"other_branch_section": {"plans": [1, 2, 3]}}
        result = mod._build_dashboard_data([], [], {"active_count": 0, "total_closed": 0, "next_number": 1}, existing)
        assert "other_branch_section" in result
        assert result["other_branch_section"] == {"plans": [1, 2, 3]}

    def test_sets_branch_and_last_updated(self):
        """Should set branch to FLOW and include last_updated."""
        mod = _import_mod()
        result = mod._build_dashboard_data([], [], {"active_count": 0, "total_closed": 0, "next_number": 1}, {})
        assert result["branch"] == "FLOW"
        assert "last_updated" in result

    def test_updates_flow_plans_section(self):
        """Should populate flow_plans with active, recently_closed, statistics."""
        mod = _import_mod()
        active = [{"plan_id": "FPLAN-1"}]
        closed = [{"plan_id": "FPLAN-2"}]
        stats = {"active_count": 1, "total_closed": 1, "next_number": 3}
        result = mod._build_dashboard_data(active, closed, stats, {})
        assert result["flow_plans"]["active"] == active
        assert result["flow_plans"]["recently_closed"] == closed
        assert result["flow_plans"]["statistics"] == stats

    def test_limits_recently_closed_to_last_five(self):
        """Should keep only the last 5 closed plans."""
        mod = _import_mod()
        closed = [{"plan_id": f"FPLAN-{i}"} for i in range(10)]
        stats = {"active_count": 0, "total_closed": 10, "next_number": 11}
        result = mod._build_dashboard_data([], closed, stats, {})
        assert len(result["flow_plans"]["recently_closed"]) == 5
        # Should be the last 5 items
        assert result["flow_plans"]["recently_closed"] == closed[5:]

    def test_recently_closed_empty_when_no_closed(self):
        """Should return empty list for recently_closed when none exist."""
        mod = _import_mod()
        result = mod._build_dashboard_data([], [], {"active_count": 0, "total_closed": 0, "next_number": 1}, {})
        assert result["flow_plans"]["recently_closed"] == []

    def test_does_not_mutate_existing_dict(self):
        """Should not modify the original existing dict."""
        mod = _import_mod()
        existing = {"keep": "me"}
        original_copy = existing.copy()
        mod._build_dashboard_data([], [], {"active_count": 0, "total_closed": 0, "next_number": 1}, existing)
        assert existing == original_copy


# ═══════════════════════════════════════════════════════════
# 7. _write_dashboard
# ═══════════════════════════════════════════════════════════


class TestWriteDashboard:
    """Tests for _write_dashboard — file writing."""

    def test_writes_json_to_file(self, setup_paths):
        """Should write valid JSON to DASHBOARD_FILE."""
        mod = _import_mod()
        data = {"branch": "FLOW", "test": True}
        result = mod._write_dashboard(data)
        assert result is True
        written = _read_json(mod.DASHBOARD_FILE)
        assert written == data

    def test_creates_parent_dirs(self, tmp_path, monkeypatch):
        """Should create parent directories if they do not exist."""
        mod = _import_mod()
        deep_path = tmp_path / "a" / "b" / "c" / "DASHBOARD.local.json"
        monkeypatch.setattr(mod, "DASHBOARD_FILE", deep_path)
        result = mod._write_dashboard({"branch": "FLOW"})
        assert result is True
        assert deep_path.exists()

    def test_returns_false_on_write_error(self, setup_paths, monkeypatch, tmp_path):
        """Should return False when writing fails."""
        mod = _import_mod()
        # Use a file as parent so mkdir fails on all platforms
        blocker = tmp_path / "blocker"
        blocker.write_text("I am a file", encoding="utf-8")
        monkeypatch.setattr(mod, "DASHBOARD_FILE", blocker / "subdir" / "DASHBOARD.local.json")
        result = mod._write_dashboard({"branch": "FLOW"})
        assert result is False


# ═══════════════════════════════════════════════════════════
# 8. update_dashboard_local (full pipeline)
# ═══════════════════════════════════════════════════════════


class TestUpdateDashboardLocal:
    """Tests for update_dashboard_local — end-to-end pipeline."""

    def test_full_pipeline_success(self, setup_paths):
        """Should read registry, extract, compute stats, and write dashboard."""
        mod = _import_mod()
        flow_json = setup_paths / "flow_json"
        _make_registry(
            flow_json,
            mod.REGISTRY_FILE.name,
            {
                "1": {
                    "subject": "Active plan",
                    "status": "open",
                    "location": "flow",
                    "file_path": "FPLAN-0001_active.md",
                    "created": "2026-04-01",
                },
                "2": {
                    "subject": "Closed plan",
                    "status": "closed",
                    "location": "flow",
                    "file_path": "FPLAN-0002_closed.md",
                    "created": "2026-03-15",
                    "closed": "2026-03-20",
                    "closed_reason": "done",
                },
            },
            next_number=5,
        )

        result = mod.update_dashboard_local()
        assert result is True

        dashboard = _read_json(mod.DASHBOARD_FILE)
        assert dashboard["branch"] == "FLOW"
        assert len(dashboard["flow_plans"]["active"]) == 1
        assert len(dashboard["flow_plans"]["recently_closed"]) == 1
        assert dashboard["flow_plans"]["statistics"]["active_count"] == 1
        assert dashboard["flow_plans"]["statistics"]["total_closed"] == 1
        assert dashboard["flow_plans"]["statistics"]["next_number"] == 5

    def test_returns_false_when_registry_is_none(self, setup_paths):
        """Should return False when no registry files exist."""
        mod = _import_mod()
        result = mod.update_dashboard_local()
        assert result is False

    def test_logs_via_json_handler_on_success(self, setup_paths, mock_json_handler):
        """Should call json_handler.log_operation on success."""
        mod = _import_mod()
        flow_json = setup_paths / "flow_json"
        _make_registry(
            flow_json,
            mod.REGISTRY_FILE.name,
            {
                "1": {"subject": "P", "status": "open", "location": "flow", "file_path": "FPLAN-0001.md"},
            },
            next_number=2,
        )

        mod.update_dashboard_local()
        mock_json_handler.assert_called_once()
        call_args = mock_json_handler.call_args
        assert call_args[0][0] == "dashboard_local_updated"
        assert call_args[0][1]["success"] is True

    def test_preserves_other_sections_in_existing_dashboard(self, setup_paths):
        """Should preserve non-flow sections from existing dashboard."""
        mod = _import_mod()
        flow_json = setup_paths / "flow_json"
        _make_registry(
            flow_json,
            mod.REGISTRY_FILE.name,
            {
                "1": {"subject": "P", "status": "open", "location": "flow", "file_path": "FPLAN-0001.md"},
            },
            next_number=2,
        )

        # Pre-populate dashboard with another branch's section
        existing = {"drone_plans": {"active": [{"plan_id": "DPLAN-99"}]}}
        _write_json(mod.DASHBOARD_FILE, existing)

        mod.update_dashboard_local()
        dashboard = _read_json(mod.DASHBOARD_FILE)
        assert "drone_plans" in dashboard
        assert dashboard["drone_plans"]["active"][0]["plan_id"] == "DPLAN-99"

    def test_does_not_log_on_failure(self, setup_paths, mock_json_handler):
        """Should not call json_handler when pipeline fails."""
        mod = _import_mod()
        # No registry files exist => returns False
        mod.update_dashboard_local()
        mock_json_handler.assert_not_called()

    def test_pipeline_with_multiple_registries(self, setup_paths):
        """Should merge plans from multiple registry types."""
        mod = _import_mod()
        flow_json = setup_paths / "flow_json"
        _make_template_registry(
            flow_json,
            {
                "flow": {"prefix": "FPLAN"},
                "dev": {"prefix": "DPLAN"},
            },
        )
        _make_registry(
            flow_json,
            "fplan_registry.json",
            {
                "1": {"subject": "Flow plan", "status": "open", "location": "flow", "file_path": "FPLAN-0001.md"},
            },
            next_number=3,
        )
        _make_registry(
            flow_json,
            "dplan_registry.json",
            {
                "2": {"subject": "Dev plan", "status": "open", "location": "flow", "file_path": "DPLAN-0002.md"},
            },
            next_number=7,
        )

        result = mod.update_dashboard_local()
        assert result is True

        dashboard = _read_json(mod.DASHBOARD_FILE)
        assert len(dashboard["flow_plans"]["active"]) == 2
        assert dashboard["flow_plans"]["statistics"]["next_number"] == 7

    def test_pipeline_filters_non_flow_plans(self, setup_paths):
        """Should exclude plans located in other branches."""
        mod = _import_mod()
        flow_json = setup_paths / "flow_json"
        _make_registry(
            flow_json,
            mod.REGISTRY_FILE.name,
            {
                "1": {"subject": "Flow plan", "status": "open", "location": "flow", "file_path": "FPLAN-0001.md"},
                "2": {"subject": "Drone plan", "status": "open", "location": "drone", "file_path": "FPLAN-0002.md"},
                "3": {"subject": "Memory plan", "status": "open", "location": "memory", "file_path": "FPLAN-0003.md"},
            },
            next_number=4,
        )

        mod.update_dashboard_local()
        dashboard = _read_json(mod.DASHBOARD_FILE)
        assert len(dashboard["flow_plans"]["active"]) == 1
        assert dashboard["flow_plans"]["active"][0]["plan_id"] == "FPLAN-0001"
