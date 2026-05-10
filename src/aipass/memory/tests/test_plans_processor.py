# ===================AIPASS====================
# META DATA HEADER
# Name: tests/test_plans_processor.py
# Date: 2026-04-26
# Version: 1.0.0
# Category: memory/tests
# =============================================

"""Tests for plans_processor handler -- line coverage for all functions.

Covers: from aipass.memory.apps.handlers.intake.plans_processor import process_plans
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------


def _import_plans_processor(monkeypatch):
    """Import plans_processor with mocked dependencies."""
    mock_memory_files = MagicMock()
    monkeypatch.setitem(
        sys.modules,
        "aipass.memory.apps.handlers.json.memory_files",
        mock_memory_files,
    )

    sys.modules.pop("aipass.memory.apps.handlers.intake.plans_processor", None)
    parent = sys.modules.get("aipass.memory.apps.handlers.intake")
    if parent is not None and hasattr(parent, "plans_processor"):
        delattr(parent, "plans_processor")

    from aipass.memory.apps.handlers.intake import plans_processor

    return plans_processor


# ===========================================================================
# Tests: _chunk_plan_text
# ===========================================================================


class TestChunkPlanText:
    """Test _chunk_plan_text function."""

    def test_chunks_by_markdown_headers(self, monkeypatch):
        mod = _import_plans_processor(monkeypatch)
        text = (
            "## Introduction\n"
            "This is the introduction section with enough text to pass the 30-char threshold easily.\n"
            "## Details\n"
            "Here are the details of the plan with plenty of content to exceed thirty characters.\n"
        )

        result = mod._chunk_plan_text(text, "plan.md")

        assert len(result) == 2
        assert result[0]["section"] == "Introduction"
        assert result[1]["section"] == "Details"
        assert "Introduction" in result[0]["text"] or "introduction" in result[0]["text"]

    def test_flushes_last_section(self, monkeypatch):
        mod = _import_plans_processor(monkeypatch)
        text = (
            "## Header One\n"
            "Content for header one, long enough to pass thirty characters.\n"
            "Trailing content without a following header, also long enough to be a real section."
        )

        result = mod._chunk_plan_text(text, "plan.md")

        assert len(result) == 1
        # The last section should be flushed since there is only one header
        assert result[0]["section"] == "Header One"
        assert "Trailing content" in result[0]["text"]

    def test_skips_short_sections(self, monkeypatch):
        mod = _import_plans_processor(monkeypatch)
        text = (
            "## Short\n"
            "Tiny.\n"
            "## Long Section\n"
            "This section has enough content to pass the thirty-character minimum requirement.\n"
        )

        result = mod._chunk_plan_text(text, "plan.md")

        # The "Short" section has text "## Short\nTiny." stripped -> "## Short\nTiny."
        # which is short, so it should be skipped
        assert len(result) == 1
        assert result[0]["section"] == "Long Section"

    def test_fallback_to_size_chunking(self, monkeypatch):
        mod = _import_plans_processor(monkeypatch)
        # Headers present but every section body is tiny (< 30 chars), so the
        # header-based pass produces zero chunks and the size-based fallback
        # triggers on the full text which exceeds MAX_CHUNK_CHARS.
        # Each pair "## Hxxx\nx\n" is ~12 chars; need > 1500 total.
        num_sections = (mod.MAX_CHUNK_CHARS // 8) + 50
        header_lines = []
        for i in range(num_sections):
            header_lines.append(f"## H{i:04d}")
            header_lines.append("x")
        text = "\n".join(header_lines)
        # Confirm text is actually long enough for the size-based fallback
        assert len(text) > mod.MAX_CHUNK_CHARS

        result = mod._chunk_plan_text(text, "plan.md")

        assert len(result) >= 2
        assert result[0]["section"].startswith("plan.md_part")

    def test_small_text_no_headers(self, monkeypatch):
        mod = _import_plans_processor(monkeypatch)
        text = "This is a plain text plan without any markdown headers at all."

        result = mod._chunk_plan_text(text, "plan.md")

        assert len(result) == 1
        assert result[0]["section"] == "plan.md"
        assert result[0]["text"] == text

    def test_tiny_text_skipped(self, monkeypatch):
        mod = _import_plans_processor(monkeypatch)
        text = "Short."

        result = mod._chunk_plan_text(text, "plan.md")

        assert result == []

    def test_splits_oversized_chunks(self, monkeypatch):
        mod = _import_plans_processor(monkeypatch)
        # Create a markdown section that is > MAX_CHUNK_CHARS * 2
        big_body = "X" * (mod.MAX_CHUNK_CHARS * 3)
        text = f"## Big Section\n{big_body}\n"

        result = mod._chunk_plan_text(text, "plan.md")

        # The single chunk was > MAX_CHUNK_CHARS * 2, so it gets split
        assert len(result) >= 2
        for chunk in result:
            assert "_part" in chunk["section"] or chunk["section"] == "Big Section"

    def test_empty_text(self, monkeypatch):
        mod = _import_plans_processor(monkeypatch)

        result = mod._chunk_plan_text("", "plan.md")

        assert result == []


# ===========================================================================
# Tests: _load_manifest / _save_manifest
# ===========================================================================


class TestManifest:
    """Test _load_manifest and _save_manifest."""

    def test_load_manifest_file_exists(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        manifest_path = tmp_path / "config" / ".plans_processed.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_data = {"plan1.md": "2026-01-01T00:00:00", "plan2.md": "2026-01-02T00:00:00"}
        manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
        monkeypatch.setattr(mod, "_PROCESSED_MANIFEST", manifest_path)

        result = mod._load_manifest()

        assert result == manifest_data

    def test_load_manifest_file_missing(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        manifest_path = tmp_path / "config" / ".plans_processed.json"
        monkeypatch.setattr(mod, "_PROCESSED_MANIFEST", manifest_path)

        result = mod._load_manifest()

        assert result == {}

    def test_load_manifest_bad_json(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        manifest_path = tmp_path / "config" / ".plans_processed.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text("not valid json {{{{", encoding="utf-8")
        monkeypatch.setattr(mod, "_PROCESSED_MANIFEST", manifest_path)

        result = mod._load_manifest()

        assert result == {}

    def test_save_manifest_creates_parent_dirs(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        manifest_path = tmp_path / "deep" / "nested" / "config" / ".plans_processed.json"
        monkeypatch.setattr(mod, "_PROCESSED_MANIFEST", manifest_path)
        data = {"file.md": "2026-04-26T12:00:00"}

        mod._save_manifest(data)

        assert manifest_path.exists()
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert loaded == data


# ===========================================================================
# Tests: _embed_texts
# ===========================================================================


class TestEmbedTexts:
    """Test _embed_texts subprocess wrapper."""

    def test_embed_texts_success(self, monkeypatch):
        mod = _import_plans_processor(monkeypatch)
        expected = {"success": True, "embeddings": [[0.1, 0.2], [0.3, 0.4]]}
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(expected)

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            result = mod._embed_texts(["hello", "world"])

        assert result["success"] is True
        assert result["embeddings"] == [[0.1, 0.2], [0.3, 0.4]]
        mock_run.assert_called_once()

    def test_embed_texts_nonzero_return(self, monkeypatch):
        mod = _import_plans_processor(monkeypatch)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "model not found"

        with patch.object(subprocess, "run", return_value=mock_result):
            result = mod._embed_texts(["hello"])

        assert result["success"] is False
        assert "model not found" in result["error"]

    def test_embed_texts_exception(self, monkeypatch):
        mod = _import_plans_processor(monkeypatch)

        with patch.object(subprocess, "run", side_effect=OSError("no such binary")):
            result = mod._embed_texts(["hello"])

        assert result["success"] is False
        assert "no such binary" in result["error"]


# ===========================================================================
# Tests: _store_vectors
# ===========================================================================


class TestStoreVectors:
    """Test _store_vectors subprocess wrapper."""

    def test_store_vectors_success(self, monkeypatch):
        mod = _import_plans_processor(monkeypatch)
        expected = {"success": True, "stored": 5}
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(expected)

        with patch.object(subprocess, "run", return_value=mock_result):
            result = mod._store_vectors(
                embeddings=[[0.1, 0.2]],
                documents=["doc1"],
                metadatas=[{"key": "val"}],
                collection_name="test_col",
            )

        assert result["success"] is True
        assert result["stored"] == 5

    def test_store_vectors_nonzero_return(self, monkeypatch):
        mod = _import_plans_processor(monkeypatch)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "db locked"

        with patch.object(subprocess, "run", return_value=mock_result):
            result = mod._store_vectors(
                embeddings=[[0.1]],
                documents=["doc"],
                metadatas=[{}],
            )

        assert result["success"] is False
        assert "db locked" in result["error"]

    def test_store_vectors_exception(self, monkeypatch):
        mod = _import_plans_processor(monkeypatch)

        with patch.object(subprocess, "run", side_effect=TimeoutError("timed out")):
            result = mod._store_vectors(
                embeddings=[[0.1]],
                documents=["doc"],
                metadatas=[{}],
            )

        assert result["success"] is False
        assert "timed out" in result["error"]


# ===========================================================================
# Tests: _find_repo_root / _get_memory_python (module-level)
# ===========================================================================


class TestFindRepoRoot:
    """Test _find_repo_root function."""

    def test_find_repo_root_with_registry(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        # Create a fake registry file
        (tmp_path / "AIPASS_REGISTRY.json").write_text("{}", encoding="utf-8")
        sub = tmp_path / "a" / "b" / "c"
        sub.mkdir(parents=True)
        fake_file = sub / "plans_processor.py"
        fake_file.write_text("", encoding="utf-8")

        # Patch __file__ to be inside tmp_path tree
        monkeypatch.setattr(mod, "__file__", str(fake_file))

        # Re-call _find_repo_root which reads __file__ at module level;
        # but the function uses Path(__file__) inside, so we need to patch the
        # function's reference to __file__. We do this by calling it after
        # monkeypatching the module's __file__.
        result = mod._find_repo_root()

        assert result == tmp_path

    def test_find_repo_root_falls_back_to_cwd(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        # Point __file__ to a location with no registry
        nowhere = tmp_path / "nowhere" / "file.py"
        nowhere.parent.mkdir(parents=True)
        nowhere.write_text("", encoding="utf-8")
        monkeypatch.setattr(mod, "__file__", str(nowhere))
        monkeypatch.chdir(tmp_path)

        result = mod._find_repo_root()

        assert result == Path.cwd()


class TestGetMemoryPython:
    """Test _get_memory_python function."""

    def test_env_override(self, monkeypatch):
        mod = _import_plans_processor(monkeypatch)
        monkeypatch.setenv("AIPASS_MEMORY_PYTHON", "/custom/python")

        result = mod._get_memory_python()

        assert result == "/custom/python"

    def test_venv_python_exists(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        monkeypatch.delenv("AIPASS_MEMORY_PYTHON", raising=False)
        venv_python = tmp_path / ".venv" / "bin" / "python"
        venv_python.parent.mkdir(parents=True)
        venv_python.write_text("#!/usr/bin/env python", encoding="utf-8")
        monkeypatch.setattr(mod, "_MEMORY_VENV_PYTHON", venv_python)

        result = mod._get_memory_python()

        assert result == str(venv_python)

    def test_falls_back_to_sys_executable(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        monkeypatch.delenv("AIPASS_MEMORY_PYTHON", raising=False)
        # Point to a non-existent venv
        monkeypatch.setattr(mod, "_MEMORY_VENV_PYTHON", tmp_path / "nonexistent" / "python")

        result = mod._get_memory_python()

        assert result == sys.executable


# ===========================================================================
# Tests: process_plans
# ===========================================================================


class TestProcessPlans:
    """Test process_plans main entry point."""

    def _setup_config(self, tmp_path, config_data):
        """Write a memory.config.json and return its path."""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "memory.config.json"
        config_path.write_text(json.dumps(config_data), encoding="utf-8")
        return config_path

    def test_process_plans_config_load_fails(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        # Point _MEMORY_ROOT to tmp_path -- no config file exists
        monkeypatch.setattr(mod, "_MEMORY_ROOT", tmp_path)

        result = mod.process_plans()

        assert result["success"] is False
        assert "Config load failed" in result["error"]

    def test_process_plans_disabled(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        monkeypatch.setattr(mod, "_MEMORY_ROOT", tmp_path)
        self._setup_config(tmp_path, {"plans": {"enabled": False}})

        result = mod.process_plans()

        assert result["success"] is True
        assert result["skipped"] is True
        assert "disabled" in result["reason"]

    def test_process_plans_dir_not_found(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        monkeypatch.setattr(mod, "_MEMORY_ROOT", tmp_path)
        self._setup_config(
            tmp_path,
            {"plans": {"enabled": True, "path": "nonexistent/plans"}},
        )
        # _find_repo_root will return tmp_path
        monkeypatch.setattr(mod, "_find_repo_root", lambda: tmp_path)

        result = mod.process_plans()

        assert result["success"] is True
        assert result["files_processed"] == 0
        assert "not found" in result.get("reason", "")

    def test_process_plans_no_files(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        monkeypatch.setattr(mod, "_MEMORY_ROOT", tmp_path)
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        self._setup_config(
            tmp_path,
            {"plans": {"enabled": True, "path": str(plans_dir), "supported_extensions": [".md"]}},
        )
        monkeypatch.setattr(mod, "_find_repo_root", lambda: tmp_path)

        result = mod.process_plans()

        assert result["success"] is True
        assert result["files_processed"] == 0

    def test_process_plans_all_already_processed(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        monkeypatch.setattr(mod, "_MEMORY_ROOT", tmp_path)
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan_file = plans_dir / "done.md"
        plan_file.write_text("Already processed plan content that is long enough.", encoding="utf-8")
        self._setup_config(
            tmp_path,
            {"plans": {"enabled": True, "path": str(plans_dir), "supported_extensions": [".md"]}},
        )
        monkeypatch.setattr(mod, "_find_repo_root", lambda: tmp_path)
        # Pre-populate the manifest
        manifest_path = tmp_path / "config" / ".plans_processed.json"
        manifest_path.write_text(json.dumps({"done.md": "2026-01-01T00:00:00"}), encoding="utf-8")
        monkeypatch.setattr(mod, "_PROCESSED_MANIFEST", manifest_path)

        result = mod.process_plans()

        assert result["success"] is True
        assert result["files_processed"] == 0
        assert "already processed" in result.get("reason", "")

    def test_process_plans_success(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        monkeypatch.setattr(mod, "_MEMORY_ROOT", tmp_path)

        # Create plans directory with a file
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan_file = plans_dir / "new_plan.md"
        plan_file.write_text(
            "## Objective\nThis is the objective section with enough content to exceed thirty characters.\n"
            "## Steps\nThese are the steps of the plan with sufficient length for chunking.\n",
            encoding="utf-8",
        )

        self._setup_config(
            tmp_path,
            {
                "plans": {
                    "enabled": True,
                    "path": str(plans_dir),
                    "supported_extensions": [".md"],
                    "collection_name": "test_plans",
                }
            },
        )
        monkeypatch.setattr(mod, "_find_repo_root", lambda: tmp_path)

        # Empty manifest
        manifest_path = tmp_path / "config" / ".plans_processed.json"
        manifest_path.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(mod, "_PROCESSED_MANIFEST", manifest_path)

        # Mock _embed_texts to return success
        monkeypatch.setattr(
            mod,
            "_embed_texts",
            lambda texts: {"success": True, "embeddings": [[0.1, 0.2]] * len(texts)},
        )
        # Mock _store_vectors to return success
        monkeypatch.setattr(
            mod,
            "_store_vectors",
            lambda emb, docs, metas, collection_name="flow_plans": {"success": True, "stored": len(docs)},
        )

        mock_jh = MagicMock()
        monkeypatch.setattr(mod, "json_handler", mock_jh)

        result = mod.process_plans()

        assert result["success"] is True
        assert result["files_processed"] == 1
        assert result["total_chunks"] >= 2
        mock_jh.log_operation.assert_called_once()

        # Manifest should be updated
        updated_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "new_plan.md" in updated_manifest

    def test_process_plans_embed_fails(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        monkeypatch.setattr(mod, "_MEMORY_ROOT", tmp_path)

        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan_file = plans_dir / "plan.md"
        plan_file.write_text(
            "## Section\nThis section has enough content to pass the minimum threshold for chunking.\n",
            encoding="utf-8",
        )

        self._setup_config(
            tmp_path,
            {"plans": {"enabled": True, "path": str(plans_dir), "supported_extensions": [".md"]}},
        )
        monkeypatch.setattr(mod, "_find_repo_root", lambda: tmp_path)

        manifest_path = tmp_path / "config" / ".plans_processed.json"
        manifest_path.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(mod, "_PROCESSED_MANIFEST", manifest_path)

        # Mock _embed_texts to return failure
        monkeypatch.setattr(
            mod,
            "_embed_texts",
            lambda texts: {"success": False, "error": "GPU out of memory"},
        )

        mock_jh = MagicMock()
        monkeypatch.setattr(mod, "json_handler", mock_jh)

        result = mod.process_plans()

        assert result["success"] is False
        assert "errors" in result
        assert any("embed" in e for e in result["errors"])

    def test_process_plans_no_embeddings(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        monkeypatch.setattr(mod, "_MEMORY_ROOT", tmp_path)

        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan_file = plans_dir / "plan.md"
        plan_file.write_text(
            "## Section\nThis section has enough content to pass the minimum threshold for chunking.\n",
            encoding="utf-8",
        )

        self._setup_config(
            tmp_path,
            {"plans": {"enabled": True, "path": str(plans_dir), "supported_extensions": [".md"]}},
        )
        monkeypatch.setattr(mod, "_find_repo_root", lambda: tmp_path)

        manifest_path = tmp_path / "config" / ".plans_processed.json"
        manifest_path.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(mod, "_PROCESSED_MANIFEST", manifest_path)

        # Embed succeeds but returns empty embeddings
        monkeypatch.setattr(
            mod,
            "_embed_texts",
            lambda texts: {"success": True, "embeddings": []},
        )

        mock_jh = MagicMock()
        monkeypatch.setattr(mod, "json_handler", mock_jh)

        result = mod.process_plans()

        assert "errors" in result
        assert any("no embeddings" in e for e in result["errors"])

    def test_process_plans_store_fails(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        monkeypatch.setattr(mod, "_MEMORY_ROOT", tmp_path)

        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan_file = plans_dir / "plan.md"
        plan_file.write_text(
            "## Section\nThis section has enough content to pass the minimum threshold for chunking.\n",
            encoding="utf-8",
        )

        self._setup_config(
            tmp_path,
            {"plans": {"enabled": True, "path": str(plans_dir), "supported_extensions": [".md"]}},
        )
        monkeypatch.setattr(mod, "_find_repo_root", lambda: tmp_path)

        manifest_path = tmp_path / "config" / ".plans_processed.json"
        manifest_path.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(mod, "_PROCESSED_MANIFEST", manifest_path)

        # Embed succeeds
        monkeypatch.setattr(
            mod,
            "_embed_texts",
            lambda texts: {"success": True, "embeddings": [[0.1, 0.2]] * len(texts)},
        )
        # Store fails
        monkeypatch.setattr(
            mod,
            "_store_vectors",
            lambda emb, docs, metas, collection_name="flow_plans": {"success": False, "error": "disk full"},
        )

        mock_jh = MagicMock()
        monkeypatch.setattr(mod, "json_handler", mock_jh)

        result = mod.process_plans()

        assert result["success"] is False
        assert "errors" in result
        assert any("store" in e for e in result["errors"])

    def test_process_plans_empty_chunks(self, monkeypatch, tmp_path):
        mod = _import_plans_processor(monkeypatch)
        monkeypatch.setattr(mod, "_MEMORY_ROOT", tmp_path)

        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan_file = plans_dir / "tiny.md"
        # Content that will produce zero chunks (under 30 chars, no headers)
        plan_file.write_text("Hi.", encoding="utf-8")

        self._setup_config(
            tmp_path,
            {"plans": {"enabled": True, "path": str(plans_dir), "supported_extensions": [".md"]}},
        )
        monkeypatch.setattr(mod, "_find_repo_root", lambda: tmp_path)

        manifest_path = tmp_path / "config" / ".plans_processed.json"
        manifest_path.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(mod, "_PROCESSED_MANIFEST", manifest_path)

        mock_jh = MagicMock()
        monkeypatch.setattr(mod, "json_handler", mock_jh)

        result = mod.process_plans()

        # No chunks produced, but no errors either -- files_without_chunks path
        assert result["success"] is True
        assert result["files_processed"] == 0

        # File should still be marked in manifest (files_without_chunks)
        updated_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "tiny.md" in updated_manifest
