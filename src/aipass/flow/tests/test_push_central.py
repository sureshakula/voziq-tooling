# =================== AIPass ====================
# Name: test_push_central.py
# Description: Tests for push_central handler -- push to Plans Central
# Version: 1.0.0
# Created: 2026-05-12
# Modified: 2026-05-12
# =============================================

"""Tests for push_central handler -- push Flow plan data to PLANS.central.json."""

import json
from unittest.mock import patch

_MOD = "aipass.flow.apps.handlers.dashboard.push_central"


def _import_mod():
    import aipass.flow.apps.handlers.dashboard.push_central as mod

    return mod


# =============================================
# 1. _find_repo_root
# =============================================


class TestFindRepoRoot:
    """Tests for _find_repo_root."""

    def test_returns_dir_containing_registry(self, tmp_path):
        """Returns the directory containing AIPASS_REGISTRY.json."""
        mod = _import_mod()
        marker = tmp_path / "AIPASS_REGISTRY.json"
        marker.write_text("{}", encoding="utf-8")
        child = tmp_path / "a" / "b" / "c"
        child.mkdir(parents=True)

        with patch(f"{_MOD}.__file__", str(child / "push_central.py")):
            result = mod._find_repo_root()
        assert result == tmp_path

    def test_falls_back_to_cwd_when_no_marker(self, tmp_path):
        """Returns Path.cwd() when no AIPASS_REGISTRY.json is found."""
        mod = _import_mod()
        sub = tmp_path / "sub"
        sub.mkdir(exist_ok=True)

        with patch(f"{_MOD}.__file__", str(sub / "push_central.py")):
            with patch("pathlib.Path.cwd", return_value=tmp_path):
                result = mod._find_repo_root()
        # No AIPASS_REGISTRY.json in any parent, so cwd is returned
        assert result == tmp_path

    def test_finds_marker_in_immediate_parent(self, tmp_path):
        """Finds AIPASS_REGISTRY.json in the immediate parent directory."""
        mod = _import_mod()
        parent_dir = tmp_path / "parent"
        parent_dir.mkdir()
        (parent_dir / "AIPASS_REGISTRY.json").write_text("{}", encoding="utf-8")
        child_dir = parent_dir / "child"
        child_dir.mkdir()

        with patch(f"{_MOD}.__file__", str(child_dir / "push_central.py")):
            result = mod._find_repo_root()
        assert result == parent_dir


# =============================================
# 2. _get_all_registry_files
# =============================================


class TestGetAllRegistryFiles:
    """Tests for _get_all_registry_files."""

    def test_returns_discovered_registry_files(self):
        """Returns registry filenames from discovered plan types."""
        mod = _import_mod()
        mock_types = {
            "flow_plans": {"registry_file": "fplan_registry.json"},
            "dev_plans": {"registry_file": "dplan_registry.json"},
        }
        with patch(f"{_MOD}.discover_plan_types", mock_types, create=True):
            # The function does a dynamic import; patch the import target
            with patch(
                "aipass.flow.apps.handlers.template.plan_type_loader.discover_plan_types",
                return_value=mock_types,
            ):
                result = mod._get_all_registry_files()

        assert "fplan_registry.json" in result
        assert "dplan_registry.json" in result
        assert len(result) == 2

    def test_deduplicates_registry_files(self):
        """Does not duplicate registry filenames when multiple types share the same file."""
        mod = _import_mod()
        mock_types = {
            "flow_plans": {"registry_file": "fplan_registry.json"},
            "flow_plans_v2": {"registry_file": "fplan_registry.json"},
        }
        with patch(
            "aipass.flow.apps.handlers.template.plan_type_loader.discover_plan_types",
            return_value=mock_types,
        ):
            result = mod._get_all_registry_files()

        assert result.count("fplan_registry.json") == 1

    def test_falls_back_on_discovery_exception(self):
        """Falls back to REGISTRY_FILE.name when discover_plan_types raises."""
        mod = _import_mod()
        with patch(
            "aipass.flow.apps.handlers.template.plan_type_loader.discover_plan_types",
            side_effect=RuntimeError("boom"),
        ):
            result = mod._get_all_registry_files()

        assert result == [mod.REGISTRY_FILE.name]

    def test_falls_back_when_no_registry_file_key(self):
        """Falls back to default when config dicts lack registry_file key."""
        mod = _import_mod()
        mock_types = {
            "flow_plans": {"prefix": "FPLAN"},
            "dev_plans": {"prefix": "DPLAN"},
        }
        with patch(
            "aipass.flow.apps.handlers.template.plan_type_loader.discover_plan_types",
            return_value=mock_types,
        ):
            result = mod._get_all_registry_files()

        # No registry_file keys, so files list is empty -> fallback
        assert result == [mod.REGISTRY_FILE.name]

    def test_skips_none_registry_file(self):
        """Skips entries where registry_file is None."""
        mod = _import_mod()
        mock_types = {
            "flow_plans": {"registry_file": "fplan_registry.json"},
            "special": {"registry_file": None},
        }
        with patch(
            "aipass.flow.apps.handlers.template.plan_type_loader.discover_plan_types",
            return_value=mock_types,
        ):
            result = mod._get_all_registry_files()

        assert result == ["fplan_registry.json"]


# =============================================
# 3. _load_registry
# =============================================


class TestLoadRegistry:
    """Tests for _load_registry."""

    def test_merges_multiple_registries(self, tmp_path):
        """Merges plans from multiple registry files using composite keys."""
        mod = _import_mod()
        fplan_reg = {
            "plans": {"1": {"subject": "fplan one", "file_path": "/p/FPLAN-0001_test.md"}},
            "next_number": 5,
        }
        dplan_reg = {
            "plans": {"2": {"subject": "dplan one", "file_path": "/p/DPLAN-0002_test.md"}},
            "next_number": 10,
        }
        (tmp_path / "fplan_registry.json").write_text(json.dumps(fplan_reg), encoding="utf-8")
        (tmp_path / "dplan_registry.json").write_text(json.dumps(dplan_reg), encoding="utf-8")

        with (
            patch.object(mod, "FLOW_JSON_DIR", tmp_path),
            patch.object(
                mod,
                "_get_all_registry_files",
                return_value=["fplan_registry.json", "dplan_registry.json"],
            ),
        ):
            result = mod._load_registry()

        assert "FPLAN-0001" in result["plans"]
        assert "DPLAN-0002" in result["plans"]
        assert result["next_number"] == 10

    def test_handles_missing_registry(self, tmp_path):
        """Gracefully handles a missing registry file."""
        mod = _import_mod()
        with (
            patch.object(mod, "FLOW_JSON_DIR", tmp_path),
            patch.object(mod, "_get_all_registry_files", return_value=["nonexistent_registry.json"]),
        ):
            result = mod._load_registry()
        assert result["plans"] == {}
        assert result["next_number"] == 1

    def test_keeps_highest_next_number(self, tmp_path):
        """Keeps the highest next_number across registries."""
        mod = _import_mod()
        reg_a = {"plans": {}, "next_number": 3}
        reg_b = {"plans": {}, "next_number": 50}
        reg_c = {"plans": {}, "next_number": 20}
        (tmp_path / "a_registry.json").write_text(json.dumps(reg_a), encoding="utf-8")
        (tmp_path / "b_registry.json").write_text(json.dumps(reg_b), encoding="utf-8")
        (tmp_path / "c_registry.json").write_text(json.dumps(reg_c), encoding="utf-8")

        with (
            patch.object(mod, "FLOW_JSON_DIR", tmp_path),
            patch.object(
                mod,
                "_get_all_registry_files",
                return_value=["a_registry.json", "b_registry.json", "c_registry.json"],
            ),
        ):
            result = mod._load_registry()
        assert result["next_number"] == 50

    def test_handles_corrupt_registry_gracefully(self, tmp_path):
        """Skips a corrupt registry file and continues with others."""
        mod = _import_mod()
        (tmp_path / "bad_registry.json").write_text("not json!", encoding="utf-8")
        good_reg = {
            "plans": {"1": {"subject": "good", "file_path": "/p/GOOD-0001_test.md"}},
            "next_number": 5,
        }
        (tmp_path / "good_registry.json").write_text(json.dumps(good_reg), encoding="utf-8")

        with (
            patch.object(mod, "FLOW_JSON_DIR", tmp_path),
            patch.object(
                mod,
                "_get_all_registry_files",
                return_value=["bad_registry.json", "good_registry.json"],
            ),
        ):
            result = mod._load_registry()

        assert "GOOD-0001" in result["plans"]
        assert result["next_number"] == 5

    def test_uses_prefix_from_filename(self, tmp_path):
        """Extracts prefix from plan file_path filename."""
        mod = _import_mod()
        reg = {
            "plans": {"7": {"subject": "test", "file_path": "/x/XPLAN-0007_test.md"}},
            "next_number": 8,
        }
        (tmp_path / "xplan_registry.json").write_text(json.dumps(reg), encoding="utf-8")

        with (
            patch.object(mod, "FLOW_JSON_DIR", tmp_path),
            patch.object(mod, "_get_all_registry_files", return_value=["xplan_registry.json"]),
        ):
            result = mod._load_registry()

        assert "XPLAN-0007" in result["plans"]

    def test_fallback_prefix_from_registry_filename(self, tmp_path):
        """Uses registry filename prefix when file_path has no recognizable prefix."""
        mod = _import_mod()
        reg = {
            "plans": {"3": {"subject": "no prefix", "file_path": "/x/some_file.md"}},
            "next_number": 4,
        }
        (tmp_path / "custom_registry.json").write_text(json.dumps(reg), encoding="utf-8")

        with (
            patch.object(mod, "FLOW_JSON_DIR", tmp_path),
            patch.object(mod, "_get_all_registry_files", return_value=["custom_registry.json"]),
        ):
            result = mod._load_registry()

        # Falls back to CUSTOM (from custom_registry.json -> custom -> CUSTOM)
        assert "CUSTOM-0003" in result["plans"]

    def test_empty_registry_plans(self, tmp_path):
        """Handles registry file with empty plans dict."""
        mod = _import_mod()
        reg = {"plans": {}, "next_number": 1}
        (tmp_path / "fplan_registry.json").write_text(json.dumps(reg), encoding="utf-8")

        with (
            patch.object(mod, "FLOW_JSON_DIR", tmp_path),
            patch.object(mod, "_get_all_registry_files", return_value=["fplan_registry.json"]),
        ):
            result = mod._load_registry()

        assert result["plans"] == {}
        assert result["next_number"] == 1

    def test_plan_with_empty_file_path(self, tmp_path):
        """Handles plan with empty file_path string."""
        mod = _import_mod()
        reg = {
            "plans": {"1": {"subject": "no path", "file_path": ""}},
            "next_number": 2,
        }
        (tmp_path / "fplan_registry.json").write_text(json.dumps(reg), encoding="utf-8")

        with (
            patch.object(mod, "FLOW_JSON_DIR", tmp_path),
            patch.object(mod, "_get_all_registry_files", return_value=["fplan_registry.json"]),
        ):
            result = mod._load_registry()

        # Falls back to FPLAN prefix from registry filename
        assert "FPLAN-0001" in result["plans"]


# =============================================
# 4. _extract_flow_plans
# =============================================


class TestExtractFlowPlans:
    """Tests for _extract_flow_plans."""

    def test_extracts_active_plans_matching_flow_root(self):
        """Returns active plans where location matches FLOW_ROOT."""
        mod = _import_mod()
        flow_root = str(mod.FLOW_ROOT)
        registry = {
            "plans": {
                "FPLAN-0001": {
                    "subject": "Plan A",
                    "status": "open",
                    "created": "2026-04-20",
                    "file_path": "/p/FPLAN-0001.md",
                    "location": flow_root,
                    "relative_path": "FPLAN-0001.md",
                },
            }
        }
        active, _ = mod._extract_flow_plans(registry)
        assert len(active) == 1
        assert active[0]["plan_id"] == "FPLAN-0001"
        assert active[0]["subject"] == "Plan A"
        assert active[0]["status"] == "open"

    def test_extracts_closed_plans(self):
        """Returns closed plans with closed metadata."""
        mod = _import_mod()
        flow_root = str(mod.FLOW_ROOT)
        registry = {
            "plans": {
                "FPLAN-0001": {
                    "subject": "Done plan",
                    "status": "closed",
                    "created": "2026-04-15",
                    "closed": "2026-04-20",
                    "closed_reason": "completed",
                    "file_path": "/p/FPLAN-0001.md",
                    "location": flow_root,
                    "relative_path": "FPLAN-0001.md",
                },
            }
        }
        active, closed = mod._extract_flow_plans(registry)
        assert len(active) == 0
        assert len(closed) == 1
        assert closed[0]["closed"] == "2026-04-20"
        assert closed[0]["closed_reason"] == "completed"

    def test_excludes_plans_from_other_locations(self):
        """Excludes plans where location does not match FLOW_ROOT."""
        mod = _import_mod()
        registry = {
            "plans": {
                "FPLAN-0001": {
                    "subject": "Other branch plan",
                    "status": "open",
                    "created": "2026-04-20",
                    "file_path": "/other/FPLAN-0001.md",
                    "location": "/some/other/path",
                },
            }
        }
        active, closed = mod._extract_flow_plans(registry)
        assert len(active) == 0
        assert len(closed) == 0

    def test_sorts_active_newest_first(self):
        """Active plans are sorted by created date, newest first."""
        mod = _import_mod()
        flow_root = str(mod.FLOW_ROOT)
        registry = {
            "plans": {
                "FPLAN-0001": {
                    "subject": "Oldest",
                    "status": "open",
                    "created": "2026-04-01",
                    "file_path": "/p/FPLAN-0001.md",
                    "location": flow_root,
                },
                "FPLAN-0002": {
                    "subject": "Newest",
                    "status": "open",
                    "created": "2026-04-25",
                    "file_path": "/p/FPLAN-0002.md",
                    "location": flow_root,
                },
                "FPLAN-0003": {
                    "subject": "Middle",
                    "status": "open",
                    "created": "2026-04-15",
                    "file_path": "/p/FPLAN-0003.md",
                    "location": flow_root,
                },
            }
        }
        active, _ = mod._extract_flow_plans(registry)
        assert active[0]["subject"] == "Newest"
        assert active[1]["subject"] == "Middle"
        assert active[2]["subject"] == "Oldest"

    def test_closed_plans_limited_to_5(self):
        """Recently closed plans are limited to 5."""
        mod = _import_mod()
        flow_root = str(mod.FLOW_ROOT)
        plans = {}
        for i in range(1, 9):
            plans[f"FPLAN-{str(i).zfill(4)}"] = {
                "subject": f"Closed plan {i}",
                "status": "closed",
                "created": "2026-04-01",
                "closed": f"2026-04-{str(i + 10).zfill(2)}",
                "closed_reason": "done",
                "file_path": f"/p/FPLAN-{str(i).zfill(4)}.md",
                "location": flow_root,
            }
        registry = {"plans": plans}
        _, closed = mod._extract_flow_plans(registry)
        assert len(closed) == 5

    def test_closed_sorted_newest_first(self):
        """Closed plans are sorted by closed date, newest first."""
        mod = _import_mod()
        flow_root = str(mod.FLOW_ROOT)
        registry = {
            "plans": {
                "FPLAN-0001": {
                    "subject": "Old close",
                    "status": "closed",
                    "created": "2026-03-01",
                    "closed": "2026-03-10",
                    "file_path": "/p/FPLAN-0001.md",
                    "location": flow_root,
                },
                "FPLAN-0002": {
                    "subject": "New close",
                    "status": "closed",
                    "created": "2026-04-01",
                    "closed": "2026-04-20",
                    "file_path": "/p/FPLAN-0002.md",
                    "location": flow_root,
                },
            }
        }
        _, closed = mod._extract_flow_plans(registry)
        assert closed[0]["subject"] == "New close"
        assert closed[1]["subject"] == "Old close"

    def test_empty_registry(self):
        """Returns empty lists for empty registry."""
        mod = _import_mod()
        active, closed = mod._extract_flow_plans({"plans": {}})
        assert active == []
        assert closed == []

    def test_missing_plans_key(self):
        """Returns empty lists when registry has no plans key."""
        mod = _import_mod()
        active, closed = mod._extract_flow_plans({})
        assert active == []
        assert closed == []

    def test_plan_entry_structure(self):
        """Plan entries have all required keys."""
        mod = _import_mod()
        flow_root = str(mod.FLOW_ROOT)
        registry = {
            "plans": {
                "FPLAN-0001": {
                    "subject": "Structured plan",
                    "status": "open",
                    "created": "2026-04-20",
                    "file_path": "/p/FPLAN-0001.md",
                    "relative_path": "FPLAN-0001.md",
                    "location": flow_root,
                },
            }
        }
        active, _ = mod._extract_flow_plans(registry)
        entry = active[0]
        assert "plan_id" in entry
        assert "subject" in entry
        assert "status" in entry
        assert "created" in entry
        assert "file_path" in entry
        assert "relative_path" in entry


# =============================================
# 5. _load_central
# =============================================


class TestLoadCentral:
    """Tests for _load_central."""

    def test_returns_empty_structure_when_file_missing(self, tmp_path):
        """Returns empty structure when PLANS.central.json does not exist."""
        mod = _import_mod()
        with patch.object(mod, "CENTRAL_FILE", tmp_path / "nonexistent.json"):
            result = mod._load_central()

        assert result["generated_at"] == ""
        assert result["branches"] == {}
        assert result["global_statistics"]["total_active"] == 0
        assert result["global_statistics"]["total_closed"] == 0
        assert result["global_statistics"]["branches_reporting"] == 0

    def test_loads_existing_central_file(self, tmp_path):
        """Loads and returns existing PLANS.central.json data."""
        mod = _import_mod()
        central_data = {
            "generated_at": "2026-04-20T00:00:00Z",
            "branches": {"flow": {"branch_name": "FLOW"}},
            "global_statistics": {"total_active": 5, "total_closed": 10, "branches_reporting": 2},
        }
        central_file = tmp_path / "PLANS.central.json"
        central_file.write_text(json.dumps(central_data), encoding="utf-8")

        with patch.object(mod, "CENTRAL_FILE", central_file):
            result = mod._load_central()

        assert result["generated_at"] == "2026-04-20T00:00:00Z"
        assert result["branches"]["flow"]["branch_name"] == "FLOW"
        assert result["global_statistics"]["total_active"] == 5

    def test_returns_empty_structure_on_corrupt_json(self, tmp_path):
        """Returns empty structure when PLANS.central.json contains invalid JSON."""
        mod = _import_mod()
        central_file = tmp_path / "PLANS.central.json"
        central_file.write_text("not valid json!!!", encoding="utf-8")

        with patch.object(mod, "CENTRAL_FILE", central_file):
            result = mod._load_central()

        assert result["generated_at"] == ""
        assert result["branches"] == {}

    def test_returns_empty_structure_on_read_exception(self, tmp_path):
        """Returns empty structure when file read raises an exception."""
        mod = _import_mod()
        central_file = tmp_path / "PLANS.central.json"
        central_file.write_text("{}", encoding="utf-8")

        with (
            patch.object(mod, "CENTRAL_FILE", central_file),
            patch("builtins.open", side_effect=PermissionError("denied")),
        ):
            result = mod._load_central()

        assert result["branches"] == {}


# =============================================
# 6. _calculate_global_statistics
# =============================================


class TestCalculateGlobalStatistics:
    """Tests for _calculate_global_statistics."""

    def test_sums_across_branches(self):
        """Sums active and closed counts across all branches."""
        mod = _import_mod()
        central_data = {
            "branches": {
                "flow": {"statistics": {"active_count": 3, "total_closed": 5}},
                "drone": {"statistics": {"active_count": 2, "total_closed": 8}},
                "prax": {"statistics": {"active_count": 1, "total_closed": 2}},
            }
        }
        result = mod._calculate_global_statistics(central_data)
        assert result["total_active"] == 6
        assert result["total_closed"] == 15
        assert result["branches_reporting"] == 3

    def test_empty_branches(self):
        """Returns zeros for empty branches dict."""
        mod = _import_mod()
        result = mod._calculate_global_statistics({"branches": {}})
        assert result["total_active"] == 0
        assert result["total_closed"] == 0
        assert result["branches_reporting"] == 0

    def test_no_branches_key(self):
        """Returns zeros when branches key is missing."""
        mod = _import_mod()
        result = mod._calculate_global_statistics({})
        assert result["total_active"] == 0
        assert result["total_closed"] == 0
        assert result["branches_reporting"] == 0

    def test_branch_missing_statistics(self):
        """Handles branches without statistics key."""
        mod = _import_mod()
        central_data = {
            "branches": {
                "flow": {"statistics": {"active_count": 3, "total_closed": 5}},
                "broken": {},
            }
        }
        result = mod._calculate_global_statistics(central_data)
        assert result["total_active"] == 3
        assert result["total_closed"] == 5
        assert result["branches_reporting"] == 2

    def test_single_branch(self):
        """Handles a single branch correctly."""
        mod = _import_mod()
        central_data = {
            "branches": {
                "flow": {"statistics": {"active_count": 7, "total_closed": 12}},
            }
        }
        result = mod._calculate_global_statistics(central_data)
        assert result["total_active"] == 7
        assert result["total_closed"] == 12
        assert result["branches_reporting"] == 1


# =============================================
# 7. push_to_plans_central
# =============================================


class TestPushToPlansCentral:
    """Tests for push_to_plans_central main handler."""

    def test_success_returns_true(self, tmp_path, mock_json_handler):
        """Returns True on successful push."""
        mod = _import_mod()
        central_file = tmp_path / "PLANS.central.json"
        ai_central = tmp_path / ".ai_central"

        mock_registry = {"plans": {}, "next_number": 1}
        mock_active = [{"plan_id": "FPLAN-0001", "subject": "Test", "status": "open"}]
        mock_closed: list = []
        mock_central = {
            "generated_at": "",
            "branches": {},
            "global_statistics": {"total_active": 0, "total_closed": 0, "branches_reporting": 0},
        }

        with (
            patch.object(mod, "AI_CENTRAL_DIR", ai_central),
            patch.object(mod, "CENTRAL_FILE", central_file),
            patch.object(mod, "_load_registry", return_value=mock_registry),
            patch.object(mod, "_extract_flow_plans", return_value=(mock_active, mock_closed)),
            patch.object(mod, "_load_central", return_value=mock_central),
            patch.object(mod, "aggregate_central_impl") as mock_agg,
        ):
            result = mod.push_to_plans_central()

        assert result is True
        mock_agg.assert_called_once_with(heal=True, central_file=central_file, central_dir=ai_central)
        mock_json_handler.assert_called_once()
        call_args = mock_json_handler.call_args
        assert call_args[0][0] == "plans_central_pushed"
        assert call_args[0][1]["success"] is True
        assert call_args[0][1]["active_plans"] == 1

    def test_writes_central_file(self, tmp_path):
        """Writes PLANS.central.json with correct structure."""
        mod = _import_mod()
        central_file = tmp_path / "PLANS.central.json"
        ai_central = tmp_path / ".ai_central"

        mock_registry = {"plans": {}, "next_number": 1}
        mock_central = {
            "generated_at": "",
            "branches": {},
            "global_statistics": {"total_active": 0, "total_closed": 0, "branches_reporting": 0},
        }

        with (
            patch.object(mod, "AI_CENTRAL_DIR", ai_central),
            patch.object(mod, "CENTRAL_FILE", central_file),
            patch.object(mod, "_load_registry", return_value=mock_registry),
            patch.object(mod, "_load_central", return_value=mock_central),
            patch.object(mod, "aggregate_central_impl"),
        ):
            result = mod.push_to_plans_central()

        assert result is True
        assert central_file.exists()
        written = json.loads(central_file.read_text(encoding="utf-8"))
        assert "branches" in written
        assert "flow" in written["branches"]
        assert "global_statistics" in written
        assert "generated_at" in written
        assert written["generated_at"] != ""

    def test_preserves_other_branches(self, tmp_path):
        """Preserves other branch sections when updating flow."""
        mod = _import_mod()
        central_file = tmp_path / "PLANS.central.json"
        ai_central = tmp_path / ".ai_central"

        mock_registry = {"plans": {}, "next_number": 1}
        mock_central = {
            "generated_at": "2026-04-01T00:00:00Z",
            "branches": {
                "drone": {"branch_name": "DRONE", "statistics": {"active_count": 3, "total_closed": 1}},
            },
            "global_statistics": {"total_active": 3, "total_closed": 1, "branches_reporting": 1},
        }

        with (
            patch.object(mod, "AI_CENTRAL_DIR", ai_central),
            patch.object(mod, "CENTRAL_FILE", central_file),
            patch.object(mod, "_load_registry", return_value=mock_registry),
            patch.object(mod, "_load_central", return_value=mock_central),
            patch.object(mod, "aggregate_central_impl"),
        ):
            result = mod.push_to_plans_central()

        assert result is True
        written = json.loads(central_file.read_text(encoding="utf-8"))
        assert "drone" in written["branches"]
        assert "flow" in written["branches"]

    def test_creates_ai_central_dir(self, tmp_path):
        """Creates .ai_central directory if it does not exist."""
        mod = _import_mod()
        ai_central = tmp_path / "new_ai_central"
        central_file = ai_central / "PLANS.central.json"

        mock_registry = {"plans": {}, "next_number": 1}
        mock_central = {
            "generated_at": "",
            "branches": {},
            "global_statistics": {"total_active": 0, "total_closed": 0, "branches_reporting": 0},
        }

        with (
            patch.object(mod, "AI_CENTRAL_DIR", ai_central),
            patch.object(mod, "CENTRAL_FILE", central_file),
            patch.object(mod, "_load_registry", return_value=mock_registry),
            patch.object(mod, "_load_central", return_value=mock_central),
            patch.object(mod, "aggregate_central_impl"),
        ):
            result = mod.push_to_plans_central()

        assert result is True
        assert ai_central.exists()

    def test_returns_false_on_exception(self, tmp_path):
        """Returns False when an exception occurs."""
        mod = _import_mod()
        with (
            patch.object(mod, "AI_CENTRAL_DIR", tmp_path / ".ai_central"),
            patch.object(mod, "_load_registry", side_effect=RuntimeError("registry exploded")),
        ):
            result = mod.push_to_plans_central()

        assert result is False

    def test_flow_section_has_correct_statistics(self, tmp_path):
        """Flow section statistics reflect actual plan counts."""
        mod = _import_mod()
        central_file = tmp_path / "PLANS.central.json"
        ai_central = tmp_path / ".ai_central"
        flow_root_str = str(mod.FLOW_ROOT)

        mock_registry = {
            "plans": {
                "FPLAN-0001": {"status": "open", "location": flow_root_str},
                "FPLAN-0002": {"status": "open", "location": flow_root_str},
                "FPLAN-0003": {"status": "closed", "location": flow_root_str},
            },
            "next_number": 4,
        }
        mock_active = [
            {"plan_id": "FPLAN-0001", "status": "open"},
            {"plan_id": "FPLAN-0002", "status": "open"},
        ]
        mock_closed = [{"plan_id": "FPLAN-0003", "status": "closed"}]
        mock_central = {
            "generated_at": "",
            "branches": {},
            "global_statistics": {"total_active": 0, "total_closed": 0, "branches_reporting": 0},
        }

        with (
            patch.object(mod, "AI_CENTRAL_DIR", ai_central),
            patch.object(mod, "CENTRAL_FILE", central_file),
            patch.object(mod, "_load_registry", return_value=mock_registry),
            patch.object(mod, "_extract_flow_plans", return_value=(mock_active, mock_closed)),
            patch.object(mod, "_load_central", return_value=mock_central),
            patch.object(mod, "aggregate_central_impl"),
        ):
            result = mod.push_to_plans_central()

        assert result is True
        written = json.loads(central_file.read_text(encoding="utf-8"))
        flow = written["branches"]["flow"]
        assert flow["statistics"]["active_count"] == 2
        assert flow["statistics"]["total_closed"] == 1
        assert flow["branch_name"] == "FLOW"

    def test_global_statistics_updated(self, tmp_path):
        """Global statistics are recalculated after flow section update."""
        mod = _import_mod()
        central_file = tmp_path / "PLANS.central.json"
        ai_central = tmp_path / ".ai_central"

        mock_registry = {"plans": {}, "next_number": 1}
        mock_central = {
            "generated_at": "",
            "branches": {
                "drone": {"statistics": {"active_count": 5, "total_closed": 3}},
            },
            "global_statistics": {"total_active": 5, "total_closed": 3, "branches_reporting": 1},
        }

        with (
            patch.object(mod, "AI_CENTRAL_DIR", ai_central),
            patch.object(mod, "CENTRAL_FILE", central_file),
            patch.object(mod, "_load_registry", return_value=mock_registry),
            patch.object(mod, "_load_central", return_value=mock_central),
            patch.object(mod, "aggregate_central_impl"),
        ):
            result = mod.push_to_plans_central()

        assert result is True
        written = json.loads(central_file.read_text(encoding="utf-8"))
        stats = written["global_statistics"]
        # drone(5 active, 3 closed) + flow(0 active, 0 closed)
        assert stats["total_active"] == 5
        assert stats["total_closed"] == 3
        assert stats["branches_reporting"] == 2

    def test_log_operation_contains_expected_fields(self, tmp_path, mock_json_handler):
        """Log operation includes active_plans, recently_closed, branches_reporting."""
        mod = _import_mod()
        central_file = tmp_path / "PLANS.central.json"
        ai_central = tmp_path / ".ai_central"

        mock_registry = {"plans": {}, "next_number": 1}
        mock_active = [{"plan_id": "FPLAN-0001"}]
        mock_closed = [{"plan_id": "FPLAN-0002"}, {"plan_id": "FPLAN-0003"}]
        mock_central = {
            "generated_at": "",
            "branches": {},
            "global_statistics": {"total_active": 0, "total_closed": 0, "branches_reporting": 0},
        }

        with (
            patch.object(mod, "AI_CENTRAL_DIR", ai_central),
            patch.object(mod, "CENTRAL_FILE", central_file),
            patch.object(mod, "_load_registry", return_value=mock_registry),
            patch.object(mod, "_extract_flow_plans", return_value=(mock_active, mock_closed)),
            patch.object(mod, "_load_central", return_value=mock_central),
            patch.object(mod, "aggregate_central_impl"),
        ):
            mod.push_to_plans_central()

        call_args = mock_json_handler.call_args
        log_data = call_args[0][1]
        assert log_data["active_plans"] == 1
        assert log_data["recently_closed"] == 2
        assert "branches_reporting" in log_data
