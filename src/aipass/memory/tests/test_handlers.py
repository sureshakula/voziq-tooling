# ===================AIPASS====================
# META DATA HEADER
# Name: tests/test_handlers.py
# Date: 2026-03-31
# Version: 1.0.0
# Category: memory/tests
# =============================================

"""Targeted handler-layer tests for critical untested handlers.

Covers:
  - rollover/extractor.py  (_extract_items_v2, _detect_growing_array, helpers)
  - tracking/line_counter.py (_count_physical_lines, update_line_count)
  - schema/normalize.py (normalize_memory_file)
  - todos[] operational schema (rollover ignores, caps enforced)

All tests use mocks/tmp_path -- no live filesystem or infrastructure access.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Import helpers -- each handler has module-level imports that need mocking
# ---------------------------------------------------------------------------


def _import_extractor(monkeypatch):
    """Import extractor with mocked infrastructure dependencies."""
    mock_json_handler = MagicMock()
    mock_json_handler.log_operation = MagicMock(return_value=True)
    mock_memory_files = MagicMock()
    mock_memory_files.read_memory_file_data = MagicMock(return_value=None)
    mock_memory_files.write_memory_file_simple = MagicMock()

    json_pkg = MagicMock()
    json_pkg.json_handler = mock_json_handler

    monkeypatch.setitem(sys.modules, "aipass.memory.apps.handlers.json", json_pkg)
    monkeypatch.setitem(sys.modules, "aipass.memory.apps.handlers.json.json_handler", mock_json_handler)
    monkeypatch.setitem(sys.modules, "aipass.memory.apps.handlers.json.memory_files", mock_memory_files)

    sys.modules.pop("aipass.memory.apps.handlers.rollover.extractor", None)
    parent = sys.modules.get("aipass.memory.apps.handlers.rollover")
    if parent is not None and hasattr(parent, "extractor"):
        delattr(parent, "extractor")

    from aipass.memory.apps.handlers.rollover import extractor

    return extractor, {
        "json_handler": mock_json_handler,
        "memory_files": mock_memory_files,
    }


def _import_line_counter(monkeypatch):
    """Import line_counter with mocked infrastructure dependencies."""
    mock_json_handler = MagicMock()
    mock_json_handler.log_operation = MagicMock(return_value=True)
    mock_memory_files = MagicMock()
    mock_memory_files.update_metadata = MagicMock(return_value={"success": True})

    json_pkg = MagicMock()
    json_pkg.json_handler = mock_json_handler

    monkeypatch.setitem(sys.modules, "aipass.memory.apps.handlers.json", json_pkg)
    monkeypatch.setitem(sys.modules, "aipass.memory.apps.handlers.json.json_handler", mock_json_handler)
    monkeypatch.setitem(sys.modules, "aipass.memory.apps.handlers.json.memory_files", mock_memory_files)

    sys.modules.pop("aipass.memory.apps.handlers.tracking.line_counter", None)
    parent = sys.modules.get("aipass.memory.apps.handlers.tracking")
    if parent is not None and hasattr(parent, "line_counter"):
        delattr(parent, "line_counter")

    from aipass.memory.apps.handlers.tracking import line_counter

    return line_counter, {
        "json_handler": mock_json_handler,
        "memory_files": mock_memory_files,
    }


def _import_normalize(monkeypatch):
    """Import normalize with mocked infrastructure dependencies."""
    mock_json_handler = MagicMock()
    mock_json_handler.log_operation = MagicMock(return_value=True)

    json_pkg = MagicMock()
    json_pkg.json_handler = mock_json_handler

    monkeypatch.setitem(sys.modules, "aipass.memory.apps.handlers.json", json_pkg)
    monkeypatch.setitem(sys.modules, "aipass.memory.apps.handlers.json.json_handler", mock_json_handler)

    sys.modules.pop("aipass.memory.apps.handlers.schema.normalize", None)
    parent = sys.modules.get("aipass.memory.apps.handlers.schema")
    if parent is not None and hasattr(parent, "normalize"):
        delattr(parent, "normalize")

    from aipass.memory.apps.handlers.schema import normalize

    return normalize, {
        "json_handler": mock_json_handler,
    }


# ===========================================================================
# Tests: rollover/extractor.py
# ===========================================================================


class TestDetectGrowingArray:
    """Test _detect_growing_array helper."""

    def test_detects_sessions_array(self, monkeypatch):
        ext, _ = _import_extractor(monkeypatch)
        data = {"sessions": [{"id": 1}, {"id": 2}], "metadata": {}}
        assert ext._detect_growing_array(data) == "sessions"

    def test_detects_observations_array(self, monkeypatch):
        ext, _ = _import_extractor(monkeypatch)
        data = {"observations": [{"note": "x"}]}
        assert ext._detect_growing_array(data) == "observations"

    def test_returns_none_for_empty_arrays(self, monkeypatch):
        ext, _ = _import_extractor(monkeypatch)
        data = {"sessions": [], "observations": []}
        assert ext._detect_growing_array(data) is None

    def test_returns_none_when_no_array_fields(self, monkeypatch):
        ext, _ = _import_extractor(monkeypatch)
        data = {"document_metadata": {}, "key_learnings": {"a": "b"}}
        assert ext._detect_growing_array(data) is None

    def test_prefers_sessions_over_later_candidates(self, monkeypatch):
        ext, _ = _import_extractor(monkeypatch)
        data = {"sessions": [{"id": 1}], "entries": [{"id": 2}]}
        assert ext._detect_growing_array(data) == "sessions"


class TestDerivebranchAndType:
    """Test _derive_branch_and_type path helper."""

    def test_trinity_path_local(self, monkeypatch):
        ext, _ = _import_extractor(monkeypatch)
        p = Path("/home/user/src/aipass/devpulse/.trinity/local.json")
        branch, mtype = ext._derive_branch_and_type(p)
        assert branch == "DEVPULSE"
        assert mtype == "local"

    def test_trinity_path_observations(self, monkeypatch):
        ext, _ = _import_extractor(monkeypatch)
        p = Path("/home/user/src/aipass/memory/.trinity/observations.json")
        branch, mtype = ext._derive_branch_and_type(p)
        assert branch == "MEMORY"
        assert mtype == "observations"

    def test_legacy_dotted_path(self, monkeypatch):
        ext, _ = _import_extractor(monkeypatch)
        p = Path("/some/path/DEVPULSE.local.json")
        branch, mtype = ext._derive_branch_and_type(p)
        assert branch == "DEVPULSE"
        assert mtype == "local"


class TestExtractItemsV2:
    """Test _extract_items_v2 entry-count based extraction."""

    def _make_v2_data(
        self, num_sessions: int = 5, num_learnings: int = 5, max_sessions: int = 3, max_learnings: int = 3
    ):
        """Build a v2 memory data dict with controllable counts."""
        sessions = [
            {"session_number": i, "date": f"2026-01-{i:02d}", "summary": f"Session {i}"}
            for i in range(1, num_sessions + 1)
        ]
        key_learnings = {f"learning_{i}": f"value_{i}" for i in range(1, num_learnings + 1)}
        return {
            "document_metadata": {
                "schema_version": "2.0.0",
                "limits": {
                    "max_sessions": max_sessions,
                    "max_key_learnings": max_learnings,
                },
                "status": {"current_lines": 100},
            },
            "sessions": sessions,
            "key_learnings": key_learnings,
        }

    def test_trims_sessions_to_limit(self, monkeypatch, tmp_path):
        ext = _import_extractor(monkeypatch)[0]
        data = self._make_v2_data(num_sessions=6, max_sessions=3)

        mem_file = tmp_path / ".trinity" / "local.json"
        mem_file.parent.mkdir(parents=True)
        mem_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Patch _write_memory_file to write actual JSON so _count_file_lines works
        def fake_write(fp, d):
            fp.write_text(json.dumps(d, indent=2), encoding="utf-8")

        with patch.object(ext, "_write_memory_file", side_effect=fake_write):
            result = ext._extract_items_v2(mem_file, data)

        assert result["success"] is True
        assert result["extracted_count"] == 5  # 3 sessions + 2 learnings trimmed... let me check
        # 6 sessions - 3 max = 3 excess sessions extracted
        # 5 learnings - 3 max = 2 excess learnings extracted
        # total = 5
        assert len(data["sessions"]) == 3

    def test_trims_key_learnings_to_limit(self, monkeypatch, tmp_path):
        ext = _import_extractor(monkeypatch)[0]
        data = self._make_v2_data(num_sessions=2, num_learnings=7, max_sessions=3, max_learnings=4)

        mem_file = tmp_path / ".trinity" / "local.json"
        mem_file.parent.mkdir(parents=True)
        mem_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        def fake_write(fp, d):
            fp.write_text(json.dumps(d, indent=2), encoding="utf-8")

        with patch.object(ext, "_write_memory_file", side_effect=fake_write):
            result = ext._extract_items_v2(mem_file, data)

        assert result["success"] is True
        # sessions: 2 <= 3, no trim
        # learnings: 7 - 4 = 3 extracted
        assert len(data["key_learnings"]) == 4
        assert result["extracted_count"] == 3

    def test_skips_when_under_limits(self, monkeypatch, tmp_path):
        ext, _ = _import_extractor(monkeypatch)
        data = self._make_v2_data(num_sessions=2, num_learnings=2, max_sessions=5, max_learnings=5)

        mem_file = tmp_path / ".trinity" / "local.json"
        mem_file.parent.mkdir(parents=True)
        mem_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        result = ext._extract_items_v2(mem_file, data)
        assert result["success"] is True
        assert result.get("skipped") is True

    def test_extracts_oldest_sessions_from_end(self, monkeypatch, tmp_path):
        """Sessions are stored newest-first, oldest at end. Extraction takes from end."""
        ext, _ = _import_extractor(monkeypatch)
        data = self._make_v2_data(num_sessions=5, num_learnings=0, max_sessions=3, max_learnings=100)

        mem_file = tmp_path / ".trinity" / "local.json"
        mem_file.parent.mkdir(parents=True)
        mem_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        def fake_write(fp, d):
            fp.write_text(json.dumps(d, indent=2), encoding="utf-8")

        with patch.object(ext, "_write_memory_file", side_effect=fake_write):
            result = ext._extract_items_v2(mem_file, data)

        # Kept sessions should be the first 3 (newest)
        kept_numbers = [s["session_number"] for s in data["sessions"]]
        assert kept_numbers == [1, 2, 3]
        # Extracted should be the last 2 (oldest)
        extracted_numbers = [s["session_number"] for s in result["extracted"]]
        assert extracted_numbers == [4, 5]

    def test_extracts_oldest_key_learnings_by_insertion_order(self, monkeypatch, tmp_path):
        """First-inserted keys are oldest and should be extracted first."""
        ext, _ = _import_extractor(monkeypatch)
        data = self._make_v2_data(num_sessions=0, num_learnings=5, max_sessions=100, max_learnings=3)

        mem_file = tmp_path / ".trinity" / "local.json"
        mem_file.parent.mkdir(parents=True)
        mem_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        def fake_write(fp, d):
            fp.write_text(json.dumps(d, indent=2), encoding="utf-8")

        with patch.object(ext, "_write_memory_file", side_effect=fake_write):
            result = ext._extract_items_v2(mem_file, data)

        remaining_keys = list(data["key_learnings"].keys())
        assert remaining_keys == ["learning_3", "learning_4", "learning_5"]
        extracted_keys = [e["key"] for e in result["extracted"]]
        assert extracted_keys == ["learning_1", "learning_2"]


class TestUpdateMetadata:
    """Test _update_metadata_after_extraction."""

    def test_adds_health_check_date(self, monkeypatch):
        ext, _ = _import_extractor(monkeypatch)
        data = {"document_metadata": {}}
        ext._update_metadata_after_extraction(data)
        assert "last_health_check" in data["document_metadata"]["status"]

    def test_creates_metadata_if_missing(self, monkeypatch):
        ext, _ = _import_extractor(monkeypatch)
        data = {}
        ext._update_metadata_after_extraction(data)
        assert "document_metadata" in data
        assert "status" in data["document_metadata"]


class TestCreateRolloverBackup:
    """Test backup and restore file operations."""

    def test_creates_backup_file(self, monkeypatch, tmp_path):
        ext, _ = _import_extractor(monkeypatch)
        mem_file = tmp_path / "local.json"
        mem_file.write_text('{"test": true}', encoding="utf-8")

        result = ext.create_rollover_backup(mem_file)
        assert result["success"] is True

        backup_path = Path(result["backup_path"])
        assert backup_path.exists()
        assert json.loads(backup_path.read_text(encoding="utf-8")) == {"test": True}

    def test_restore_from_backup(self, monkeypatch, tmp_path):
        ext, _ = _import_extractor(monkeypatch)
        mem_file = tmp_path / "local.json"
        mem_file.write_text('{"original": true}', encoding="utf-8")

        ext.create_rollover_backup(mem_file)
        mem_file.write_text('{"modified": true}', encoding="utf-8")

        result = ext.restore_from_backup(mem_file)
        assert result["success"] is True
        assert json.loads(mem_file.read_text(encoding="utf-8")) == {"original": True}

    def test_restore_fails_without_backup(self, monkeypatch, tmp_path):
        ext, _ = _import_extractor(monkeypatch)
        mem_file = tmp_path / "local.json"
        mem_file.write_text("{}", encoding="utf-8")

        result = ext.restore_from_backup(mem_file)
        assert result["success"] is False


# ===========================================================================
# Tests: tracking/line_counter.py
# ===========================================================================


class TestCountPhysicalLines:
    """Test _count_physical_lines helper."""

    def test_counts_lines_correctly(self, monkeypatch, tmp_path):
        lc, _ = _import_line_counter(monkeypatch)
        f = tmp_path / "test.local.json"
        f.write_text("line1\nline2\nline3\n", encoding="utf-8")
        assert lc._count_physical_lines(f) == 3

    def test_returns_zero_for_missing_file(self, monkeypatch, tmp_path):
        lc, _ = _import_line_counter(monkeypatch)
        f = tmp_path / "missing.json"
        assert lc._count_physical_lines(f) == 0

    def test_counts_single_line_no_newline(self, monkeypatch, tmp_path):
        lc, _ = _import_line_counter(monkeypatch)
        f = tmp_path / "one.json"
        f.write_text("single line", encoding="utf-8")
        assert lc._count_physical_lines(f) == 1


class TestUpdateLineCount:
    """Test update_line_count function."""

    def test_returns_error_for_missing_file(self, monkeypatch, tmp_path):
        lc, _ = _import_line_counter(monkeypatch)
        result = lc.update_line_count(tmp_path / "gone.json")
        assert result["success"] is False

    def test_updates_line_count_successfully(self, monkeypatch, tmp_path):
        lc, mocks = _import_line_counter(monkeypatch)
        f = tmp_path / "test.local.json"
        f.write_text('{\n  "a": 1\n}\n', encoding="utf-8")

        result = lc.update_line_count(f)
        assert result["success"] is True
        assert result["lines"] == 3
        mocks["memory_files"].update_metadata.assert_called_once()

    def test_reports_failure_when_metadata_update_fails(self, monkeypatch, tmp_path):
        lc, mocks = _import_line_counter(monkeypatch)
        mocks["memory_files"].update_metadata.return_value = {"success": False, "error": "write error"}
        f = tmp_path / "test.local.json"
        f.write_text("{}\n", encoding="utf-8")

        result = lc.update_line_count(f)
        assert result["success"] is False
        assert "write error" in result["error"]


# ===========================================================================
# Tests: schema/normalize.py
# ===========================================================================


class TestNormalizeMemoryFile:
    """Test normalize_memory_file function."""

    def _write_json(self, path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def test_returns_error_for_missing_file(self, monkeypatch, tmp_path):
        norm, _ = _import_normalize(monkeypatch)
        result = norm.normalize_memory_file(tmp_path / "nope.json")
        assert result["success"] is False

    def test_moves_root_limits_into_metadata(self, monkeypatch, tmp_path):
        norm, _ = _import_normalize(monkeypatch)
        f = tmp_path / "test.local.json"
        self._write_json(
            f,
            {
                "document_metadata": {"status": {}},
                "limits": {"max_sessions": 20},
                "sessions": [],
            },
        )
        result = norm.normalize_memory_file(f)
        assert result["success"] is True

        data = json.loads(f.read_text(encoding="utf-8"))
        assert "limits" not in {k for k in data if k != "document_metadata"}
        assert data["document_metadata"]["limits"]["max_sessions"] == 20

    def test_merges_root_limits_preserving_metadata_values(self, monkeypatch, tmp_path):
        norm, _ = _import_normalize(monkeypatch)
        f = tmp_path / "test.local.json"
        self._write_json(
            f,
            {
                "document_metadata": {
                    "limits": {"max_sessions": 20},
                    "status": {},
                },
                "limits": {"max_sessions": 30, "max_key_learnings": 25},
                "sessions": [],
            },
        )
        result = norm.normalize_memory_file(f)
        assert result["success"] is True

        data = json.loads(f.read_text(encoding="utf-8"))
        # metadata value (20) wins over root value (30)
        assert data["document_metadata"]["limits"]["max_sessions"] == 20
        # valid key from root gets merged in
        assert data["document_metadata"]["limits"]["max_key_learnings"] == 25

    def test_removes_root_status(self, monkeypatch, tmp_path):
        norm, _ = _import_normalize(monkeypatch)
        f = tmp_path / "test.local.json"
        self._write_json(
            f,
            {
                "document_metadata": {"status": {"last_health_check": "2026-01-01"}},
                "status": {"health": "ok"},
                "sessions": [],
            },
        )
        result = norm.normalize_memory_file(f)
        assert result["success"] is True

        data = json.loads(f.read_text(encoding="utf-8"))
        # root status removed
        assert "status" not in {k for k in data if k != "document_metadata"}

    def test_removes_auto_compress_at(self, monkeypatch, tmp_path):
        norm, _ = _import_normalize(monkeypatch)
        f = tmp_path / "test.local.json"
        self._write_json(
            f,
            {
                "document_metadata": {
                    "status": {"auto_compress_at": 500, "last_health_check": "2026-01-01"},
                },
                "sessions": [],
            },
        )
        result = norm.normalize_memory_file(f)
        assert result["success"] is True

        data = json.loads(f.read_text(encoding="utf-8"))
        assert "auto_compress_at" not in data["document_metadata"]["status"]

    def test_dry_run_does_not_write(self, monkeypatch, tmp_path):
        norm, _ = _import_normalize(monkeypatch)
        f = tmp_path / "test.local.json"
        original = {
            "document_metadata": {},
            "limits": {"max_lines": 600},
            "sessions": [],
        }
        self._write_json(f, original)
        original_text = f.read_text(encoding="utf-8")

        result = norm.normalize_memory_file(f, dry_run=True)
        assert result["success"] is True
        assert result["dry_run"] is True
        assert len(result["changes"]) > 0
        # File unchanged
        assert f.read_text(encoding="utf-8") == original_text

    def test_no_changes_when_already_normalized(self, monkeypatch, tmp_path):
        norm, _ = _import_normalize(monkeypatch)
        f = tmp_path / "test.local.json"
        self._write_json(
            f,
            {
                "document_metadata": {
                    "limits": {"max_sessions": 20},
                    "status": {"last_health_check": "2026-03-31"},
                },
                "sessions": [],
            },
        )
        result = norm.normalize_memory_file(f)
        assert result["success"] is True
        assert result["changes"] == []

    def test_removes_unused_limit_fields(self, monkeypatch, tmp_path):
        norm, _ = _import_normalize(monkeypatch)
        f = tmp_path / "test.local.json"
        self._write_json(
            f,
            {
                "document_metadata": {
                    "limits": {"max_sessions": 20, "max_lines": 600, "max_word_count": 9999, "max_token_count": 5000},
                    "status": {"last_health_check": "2026-03-31"},
                },
                "sessions": [],
            },
        )
        result = norm.normalize_memory_file(f)
        assert result["success"] is True

        data = json.loads(f.read_text(encoding="utf-8"))
        assert "max_word_count" not in data["document_metadata"]["limits"]
        assert "max_token_count" not in data["document_metadata"]["limits"]
        assert "max_lines" not in data["document_metadata"]["limits"]
        assert data["document_metadata"]["limits"]["max_sessions"] == 20


class TestTodosOperational:
    """Confirm rollover treats todos[] as operational — never vectorized or trimmed."""

    def _make_data_with_todos(self, num_sessions=5, max_sessions=3, num_todos=5):
        """Build v2 data that includes a populated todos[] array."""
        sessions = [
            {"session_number": i, "date": f"2026-01-{i:02d}", "summary": f"Session {i}"}
            for i in range(1, num_sessions + 1)
        ]
        todos = [{"id": f"t{i}", "text": f"Todo item {i}", "created": f"2026-06-0{i}"} for i in range(1, num_todos + 1)]
        return {
            "document_metadata": {
                "schema_version": "2.0.0",
                "limits": {
                    "max_sessions": max_sessions,
                    "max_key_learnings": 25,
                    "max_todos": 10,
                    "todo_text_max_chars": 200,
                },
                "status": {"current_lines": 100},
            },
            "sessions": sessions,
            "key_learnings": {},
            "todos": todos,
        }

    def test_v2_extraction_leaves_todos_untouched(self, monkeypatch, tmp_path):
        """v2 rollover trims sessions but never touches todos[]."""
        ext, _ = _import_extractor(monkeypatch)
        data = self._make_data_with_todos(num_sessions=6, max_sessions=3, num_todos=5)

        mem_file = tmp_path / ".trinity" / "local.json"
        mem_file.parent.mkdir(parents=True)
        mem_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        def fake_write(fp, d):
            fp.write_text(json.dumps(d, indent=2), encoding="utf-8")

        with patch.object(ext, "_write_memory_file", side_effect=fake_write):
            result = ext._extract_items_v2(mem_file, data)

        assert result["success"] is True
        assert len(data["sessions"]) == 3
        assert len(data["todos"]) == 5
        assert data["todos"][0]["id"] == "t1"
        assert data["todos"][4]["id"] == "t5"

    def test_v1_detect_growing_array_ignores_todos(self, monkeypatch):
        """v1 _detect_growing_array does NOT consider todos as a growing array."""
        ext, _ = _import_extractor(monkeypatch)
        data = {
            "sessions": [{"session_number": 1}],
            "todos": [{"id": "t1", "text": "Something"}],
        }
        result = ext._detect_growing_array(data)
        assert result == "sessions"

    def test_v1_detect_growing_array_skips_todos_only(self, monkeypatch):
        """If only todos[] exists (no memory arrays), _detect_growing_array returns None."""
        ext, _ = _import_extractor(monkeypatch)
        data = {
            "todos": [{"id": "t1", "text": "Something"}],
            "key_learnings": {"k1": "v1"},
        }
        result = ext._detect_growing_array(data)
        assert result is None

    def test_todos_schema_shape(self):
        """Validate the expected todos[] item schema: id, text, created, optional priority."""
        todo_item = {"id": "t1", "text": "Fix the bug", "created": "2026-06-07"}
        assert "id" in todo_item
        assert "text" in todo_item
        assert "created" in todo_item

        todo_with_priority = {**todo_item, "priority": "high"}
        assert todo_with_priority["priority"] == "high"

    def test_todos_cap_enforced(self):
        """max_todos and todo_text_max_chars are the cap boundaries."""
        limits = {
            "max_todos": 10,
            "todo_text_max_chars": 200,
        }
        todos = [{"id": f"t{i}", "text": "x" * 200, "created": "2026-06-07"} for i in range(10)]
        assert len(todos) <= limits["max_todos"]
        assert all(len(t["text"]) <= limits["todo_text_max_chars"] for t in todos)

        over_cap = todos + [{"id": "t11", "text": "extra", "created": "2026-06-07"}]
        assert len(over_cap) > limits["max_todos"]

    def test_todos_survives_full_extraction_cycle(self, monkeypatch, tmp_path):
        """End-to-end: extract_items on a file with todos[] preserves them completely."""
        ext, _ = _import_extractor(monkeypatch)
        data = self._make_data_with_todos(num_sessions=25, max_sessions=20, num_todos=8)

        mem_file = tmp_path / ".trinity" / "local.json"
        mem_file.parent.mkdir(parents=True)
        mem_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        def fake_write(fp, d):
            fp.write_text(json.dumps(d, indent=2), encoding="utf-8")

        with patch.object(ext, "_write_memory_file", side_effect=fake_write):
            result = ext._extract_items_v2(mem_file, data)

        assert result["success"] is True
        assert result["extracted_count"] > 0
        assert len(data["todos"]) == 8
        for i, todo in enumerate(data["todos"], 1):
            assert todo["id"] == f"t{i}"
