# ===================AIPASS====================
# META DATA HEADER
# Name: tests/test_search_extras.py
# Date: 2026-04-25
# Version: 1.0.0
# Category: memory/tests
# =============================================

"""Tests for search handler internals (query_executor and vector_search).

Covers:
    from aipass.memory.apps.handlers.search.query_executor import encode_query_subprocess
    from aipass.memory.apps.handlers.search.query_executor import search_vectors_subprocess
    from aipass.memory.apps.handlers.search.vector_search import search_collection
    from aipass.memory.apps.handlers.search.vector_search import encode_query
    from aipass.memory.apps.handlers.search.vector_search import search_all_collections

Tests subprocess-based encoding/search, ChromaDB collection queries,
query encoding via the singleton QueryEncoder, and multi-collection search.
All tests use mocks -- no live subprocess, ML model, or ChromaDB access.
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers: prepare the mock graph needed to import search handlers
# ---------------------------------------------------------------------------


def _prepare_query_executor_mocks(monkeypatch):
    """Insert mocks for query_executor module-level imports.

    Returns a dict of key mock objects so tests can assert against them.
    """
    # Mock the chroma_subprocess and embed_subprocess script paths
    mock_chroma_script = MagicMock()
    mock_embed_script = MagicMock()

    return {
        "chroma_script": mock_chroma_script,
        "embed_script": mock_embed_script,
    }


def _import_query_executor(monkeypatch):
    """Prepare mocks and import (or reimport) query_executor.

    Returns (module, mocks_dict).
    """
    mocks = _prepare_query_executor_mocks(monkeypatch)

    # Remove cached module so it gets re-imported with our mocks
    sys.modules.pop("aipass.memory.apps.handlers.search.query_executor", None)

    # Clear parent package attribute so Python re-executes module code
    parent = sys.modules.get("aipass.memory.apps.handlers.search")
    if parent is not None and hasattr(parent, "query_executor"):
        delattr(parent, "query_executor")

    from aipass.memory.apps.handlers.search import query_executor  # noqa: E402

    return query_executor, mocks


def _prepare_vector_search_mocks(monkeypatch):
    """Insert mocks for vector_search module-level imports.

    Returns a dict of key mock objects for assertions.
    """
    # Mock chromadb client via the chroma module
    mock_client = MagicMock()
    mock_chroma = MagicMock()
    mock_chroma.get_client = MagicMock(return_value=mock_client)
    monkeypatch.setitem(
        sys.modules,
        "aipass.memory.apps.handlers.storage.chroma",
        mock_chroma,
    )
    monkeypatch.setitem(
        sys.modules,
        "aipass.memory.apps.handlers.storage",
        MagicMock(),
    )

    # Mock sentence_transformers and torch for QueryEncoder
    mock_model = MagicMock()
    mock_model.encode.return_value = MagicMock(tolist=MagicMock(return_value=[0.1] * 384))
    mock_model.to.return_value = mock_model

    mock_st_cls = MagicMock(return_value=mock_model)

    mock_sentence_transformers = MagicMock()
    mock_sentence_transformers.SentenceTransformer = mock_st_cls
    monkeypatch.setitem(sys.modules, "sentence_transformers", mock_sentence_transformers)

    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = False
    monkeypatch.setitem(sys.modules, "torch", mock_torch)

    return {
        "client": mock_client,
        "model": mock_model,
        "st_cls": mock_st_cls,
        "torch": mock_torch,
    }


def _import_vector_search(monkeypatch):
    """Prepare mocks and import (or reimport) vector_search.

    Returns (module, mocks_dict).
    """
    mocks = _prepare_vector_search_mocks(monkeypatch)

    # Remove cached modules so they get re-imported with our mocks
    sys.modules.pop("aipass.memory.apps.handlers.search.vector_search", None)

    # Clear parent package attribute so Python re-executes module code
    parent = sys.modules.get("aipass.memory.apps.handlers.search")
    if parent is not None and hasattr(parent, "vector_search"):
        delattr(parent, "vector_search")

    from aipass.memory.apps.handlers.search import vector_search  # noqa: E402

    # Reset singletons for a clean slate
    setattr(vector_search, "_query_encoder", None)
    setattr(vector_search, "_search_service", None)
    setattr(vector_search, "_local_services", {})

    return vector_search, mocks


# ===========================================================================
# Tests: encode_query_subprocess
# ===========================================================================


class TestEncodeQuerySubprocess:
    """Verify encode_query_subprocess subprocess-based encoding."""

    def test_encode_returns_embedding_on_success(self, monkeypatch):
        """Successful subprocess returns embedding and dimension."""
        mod, mocks = _import_query_executor(monkeypatch)

        fake_output = json.dumps({"success": True, "embeddings": [[0.1, 0.2, 0.3]], "dimension": 3})
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = fake_output

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            result = mod.encode_query_subprocess("test query")

        assert result["success"] is True
        assert result["embedding"] == [0.1, 0.2, 0.3]
        assert result["dimension"] == 3
        mock_run.assert_called_once()

    def test_encode_returns_error_on_nonzero_exit(self, monkeypatch):
        """Non-zero return code produces error dict."""
        mod, mocks = _import_query_executor(monkeypatch)

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Model not found"

        with patch.object(subprocess, "run", return_value=mock_result):
            result = mod.encode_query_subprocess("test query")

        assert result["success"] is False
        assert "Model not found" in result["error"]

    def test_encode_handles_timeout(self, monkeypatch):
        """TimeoutExpired produces a timeout error."""
        mod, mocks = _import_query_executor(monkeypatch)

        with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd="python", timeout=120)):
            result = mod.encode_query_subprocess("slow query")

        assert result["success"] is False
        assert "timed out" in result["error"].lower()

    def test_encode_handles_invalid_json(self, monkeypatch):
        """Invalid JSON from subprocess produces error dict."""
        mod, mocks = _import_query_executor(monkeypatch)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"

        with patch.object(subprocess, "run", return_value=mock_result):
            result = mod.encode_query_subprocess("test query")

        assert result["success"] is False
        assert "json" in result["error"].lower()

    def test_encode_handles_empty_embeddings(self, monkeypatch):
        """Response with empty embeddings list produces error."""
        mod, mocks = _import_query_executor(monkeypatch)

        fake_output = json.dumps({"success": True, "embeddings": [], "dimension": 384})
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = fake_output

        with patch.object(subprocess, "run", return_value=mock_result):
            result = mod.encode_query_subprocess("test query")

        assert result["success"] is False
        assert "no embedding" in result["error"].lower()

    def test_encode_handles_generic_exception(self, monkeypatch):
        """Unexpected exception produces error dict."""
        mod, mocks = _import_query_executor(monkeypatch)

        with patch.object(subprocess, "run", side_effect=OSError("Cannot execute")):
            result = mod.encode_query_subprocess("test query")

        assert result["success"] is False
        assert "Cannot execute" in result["error"]


# ===========================================================================
# Tests: search_vectors_subprocess
# ===========================================================================


class TestSearchVectorsSubprocess:
    """Verify search_vectors_subprocess subprocess-based search."""

    def test_search_returns_results_on_success(self, monkeypatch):
        """Successful subprocess returns parsed results."""
        mod, mocks = _import_query_executor(monkeypatch)

        fake_output = json.dumps(
            {"success": True, "results": [{"document": "hello", "distance": 0.1}], "total_results": 1}
        )
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = fake_output

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            result = mod.search_vectors_subprocess(
                query_embedding=[0.1, 0.2, 0.3],
                branch="TEST",
                n_results=5,
            )

        assert result["success"] is True
        assert result["total_results"] == 1
        mock_run.assert_called_once()

    def test_search_returns_error_on_nonzero_exit(self, monkeypatch):
        """Non-zero exit code produces error dict."""
        mod, mocks = _import_query_executor(monkeypatch)

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "DB not found"

        with patch.object(subprocess, "run", return_value=mock_result):
            result = mod.search_vectors_subprocess(query_embedding=[0.1])

        assert result["success"] is False
        assert "DB not found" in result["error"]

    def test_search_handles_timeout(self, monkeypatch):
        """TimeoutExpired produces a timeout error."""
        mod, mocks = _import_query_executor(monkeypatch)

        with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd="python", timeout=60)):
            result = mod.search_vectors_subprocess(query_embedding=[0.1])

        assert result["success"] is False
        assert "timed out" in result["error"].lower()

    def test_search_handles_invalid_json(self, monkeypatch):
        """Invalid JSON from subprocess produces error dict."""
        mod, mocks = _import_query_executor(monkeypatch)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "{{bad json"

        with patch.object(subprocess, "run", return_value=mock_result):
            result = mod.search_vectors_subprocess(query_embedding=[0.1])

        assert result["success"] is False
        assert "json" in result["error"].lower()

    def test_search_passes_db_path_as_string(self, monkeypatch):
        """db_path is converted to string in the input data."""
        mod, mocks = _import_query_executor(monkeypatch)

        fake_output = json.dumps({"success": True, "results": []})
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = fake_output

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            mod.search_vectors_subprocess(
                query_embedding=[0.1],
                db_path=Path("/tmp/test_chroma"),
            )

        call_args = mock_run.call_args
        input_data = json.loads(call_args.kwargs.get("input", call_args[1].get("input", "")))
        assert input_data["db_path"] == "/tmp/test_chroma"

    def test_search_handles_generic_exception(self, monkeypatch):
        """Unexpected exception produces error dict."""
        mod, mocks = _import_query_executor(monkeypatch)

        with patch.object(subprocess, "run", side_effect=OSError("Cannot execute")):
            result = mod.search_vectors_subprocess(query_embedding=[0.1])

        assert result["success"] is False
        assert "Cannot execute" in result["error"]


# ===========================================================================
# Tests: search_collection (vector_search)
# ===========================================================================


class TestSearchCollection:
    """Verify search_collection wraps SearchService.query_collection."""

    def test_search_returns_results_on_success(self, monkeypatch, tmp_path):
        """Successful collection query returns success with results."""
        mod, mocks = _import_vector_search(monkeypatch)

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"branch": "TEST"}, {"branch": "TEST"}]],
            "distances": [[0.1, 0.2]],
        }
        mocks["client"].get_collection.return_value = mock_collection

        result = mod.search_collection(
            query_embedding=[0.1] * 384,
            collection_name="test_collection",
            n_results=5,
            db_path=tmp_path / ".chroma",
        )

        assert result["success"] is True
        assert result["count"] == 2
        assert "doc1" in result["documents"]

    def test_search_returns_error_for_missing_collection(self, monkeypatch, tmp_path):
        """Missing collection returns success=False with error message."""
        mod, mocks = _import_vector_search(monkeypatch)

        mocks["client"].get_collection.side_effect = ValueError("Collection not found")

        result = mod.search_collection(
            query_embedding=[0.1] * 384,
            collection_name="nonexistent",
            db_path=tmp_path / ".chroma",
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_search_returns_error_for_empty_embedding(self, monkeypatch):
        """Empty query embedding returns error."""
        mod, mocks = _import_vector_search(monkeypatch)

        result = mod.search_collection(
            query_embedding=[],
            collection_name="test_collection",
        )

        assert result["success"] is False
        assert "no query embedding" in result["error"].lower()

    def test_search_accepts_string_db_path(self, monkeypatch, tmp_path):
        """String db_path is converted to Path internally."""
        mod, mocks = _import_vector_search(monkeypatch)

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "metadatas": [[{}]],
            "distances": [[0.05]],
        }
        mocks["client"].get_collection.return_value = mock_collection

        result = mod.search_collection(
            query_embedding=[0.1] * 384,
            collection_name="test_collection",
            db_path=str(tmp_path / ".chroma"),
        )

        assert result["success"] is True

    def test_search_passes_where_filter(self, monkeypatch, tmp_path):
        """Metadata where filter is forwarded to collection.query."""
        mod, mocks = _import_vector_search(monkeypatch)

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        mocks["client"].get_collection.return_value = mock_collection

        mod.search_collection(
            query_embedding=[0.1] * 384,
            collection_name="test_collection",
            where={"branch": "SEEDGO"},
            db_path=tmp_path / ".chroma",
        )

        call_kwargs = mock_collection.query.call_args.kwargs
        assert call_kwargs["where"] == {"branch": "SEEDGO"}


# ===========================================================================
# Tests: encode_query (vector_search)
# ===========================================================================


class TestEncodeQuery:
    """Verify encode_query uses QueryEncoder singleton."""

    def test_encode_returns_embedding(self, monkeypatch):
        """Successful encoding returns embedding with dimension."""
        mod, mocks = _import_vector_search(monkeypatch)

        result = mod.encode_query("test query")

        assert result["success"] is True
        assert len(result["embedding"]) == 384
        assert result["dimension"] == 384
        assert result["model"] == "all-MiniLM-L6-v2"

    def test_encode_rejects_empty_query(self, monkeypatch):
        """Empty query string returns error."""
        mod, mocks = _import_vector_search(monkeypatch)

        result = mod.encode_query("")

        assert result["success"] is False
        assert "empty" in result["error"].lower()

    def test_encode_rejects_whitespace_only_query(self, monkeypatch):
        """Whitespace-only query string returns error."""
        mod, mocks = _import_vector_search(monkeypatch)

        result = mod.encode_query("   ")

        assert result["success"] is False
        assert "empty" in result["error"].lower()

    def test_encode_handles_model_error(self, monkeypatch):
        """If model.encode raises, error is caught and returned."""
        mod, mocks = _import_vector_search(monkeypatch)

        mocks["model"].encode.side_effect = RuntimeError("CUDA out of memory")

        result = mod.encode_query("test query")

        assert result["success"] is False
        assert "CUDA" in result["error"]

    def test_encode_uses_singleton(self, monkeypatch):
        """Successive calls reuse the same QueryEncoder instance."""
        mod, mocks = _import_vector_search(monkeypatch)

        mod.encode_query("first query")
        mod.encode_query("second query")

        # SentenceTransformer should only be constructed once
        mocks["st_cls"].assert_called_once()


# ===========================================================================
# Tests: search_all_collections (vector_search)
# ===========================================================================


class TestSearchAllCollections:
    """Verify search_all_collections aggregates results across collections."""

    def test_search_all_returns_aggregated_results(self, monkeypatch, tmp_path):
        """Searching all collections returns results from each."""
        mod, mocks = _import_vector_search(monkeypatch)

        mock_coll_a = MagicMock()
        mock_coll_a.name = "coll_a"
        mock_coll_b = MagicMock()
        mock_coll_b.name = "coll_b"
        mocks["client"].list_collections.return_value = [mock_coll_a, mock_coll_b]

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "metadatas": [[{"branch": "TEST"}]],
            "distances": [[0.1]],
        }
        mocks["client"].get_collection.return_value = mock_collection

        result = mod.search_all_collections(
            query_embedding=[0.1] * 384,
            n_results=3,
            db_path=tmp_path / ".chroma",
        )

        assert result["success"] is True
        assert result["collections_searched"] == 2
        assert result["total_results"] == 2
        assert "coll_a" in result["results"]
        assert "coll_b" in result["results"]

    def test_search_all_returns_empty_when_no_collections(self, monkeypatch, tmp_path):
        """No collections returns success with empty results."""
        mod, mocks = _import_vector_search(monkeypatch)

        mocks["client"].list_collections.return_value = []

        result = mod.search_all_collections(
            query_embedding=[0.1] * 384,
            db_path=tmp_path / ".chroma",
        )

        assert result["success"] is True
        assert result["results"] == {}
        assert "no collections" in result["message"].lower()

    def test_search_all_returns_error_for_empty_embedding(self, monkeypatch):
        """Empty embedding returns error."""
        mod, mocks = _import_vector_search(monkeypatch)

        result = mod.search_all_collections(query_embedding=[])

        assert result["success"] is False
        assert "no query embedding" in result["error"].lower()

    def test_search_all_handles_exception(self, monkeypatch, tmp_path):
        """Exception during search returns error dict."""
        mod, mocks = _import_vector_search(monkeypatch)

        mocks["client"].list_collections.side_effect = RuntimeError("DB corrupted")

        result = mod.search_all_collections(
            query_embedding=[0.1] * 384,
            db_path=tmp_path / ".chroma",
        )

        assert result["success"] is False
        assert "DB corrupted" in result["error"]

    def test_search_all_accepts_string_db_path(self, monkeypatch, tmp_path):
        """String db_path is accepted and converted."""
        mod, mocks = _import_vector_search(monkeypatch)

        mocks["client"].list_collections.return_value = []

        result = mod.search_all_collections(
            query_embedding=[0.1] * 384,
            db_path=str(tmp_path / ".chroma"),
        )

        assert result["success"] is True

    def test_search_all_skips_nonexistent_collections(self, monkeypatch, tmp_path):
        """Collections that fail get_collection are excluded from results."""
        mod, mocks = _import_vector_search(monkeypatch)

        mock_coll_a = MagicMock()
        mock_coll_a.name = "coll_a"
        mocks["client"].list_collections.return_value = [mock_coll_a]

        # get_collection raises => query_collection returns exists=False
        mocks["client"].get_collection.side_effect = ValueError("Collection not found")

        result = mod.search_all_collections(
            query_embedding=[0.1] * 384,
            db_path=tmp_path / ".chroma",
        )

        assert result["success"] is True
        assert result["collections_searched"] == 0
        assert result["total_results"] == 0
