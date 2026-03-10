# =================== AIPass ====================
# Name: query_executor.py
# Description: Search Query Execution Handler
# Version: 1.0.0
# Created: 2026-03-08
# Modified: 2026-03-08
# =============================================

"""
Search Query Execution Handler

Contains the core search execution logic: subprocess-based vector search,
query encoding via embedder, similarity calculation, and result filtering.
Called by the search module which handles display/CLI concerns.

Purpose:
    Implementation logic for semantic search, separated from CLI/display
    layer to satisfy thin-module standard.
"""

import subprocess
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

from aipass.prax import logger

# Handler imports
from aipass.memory.apps.handlers.vector import embedder

# ChromaDB search via subprocess
_HANDLERS_DIR = Path(__file__).resolve().parent.parent
CHROMA_SUBPROCESS_SCRIPT = _HANDLERS_DIR / "storage" / "chroma_subprocess.py"

# Use system python by default; can be overridden via environment variable
MEMORY_PYTHON = os.environ.get("AIPASS_MEMORY_PYTHON", sys.executable)

# Minimum similarity threshold - filter out irrelevant results
MIN_SIMILARITY_THRESHOLD = 0.40  # 40% minimum relevance


# =============================================================================
# SUBPROCESS VECTOR SEARCH
# =============================================================================

def search_vectors_subprocess(
    query_embedding: list,
    branch: str | None = None,
    memory_type: str | None = None,
    n_results: int = 5,
    db_path: str | Path | None = None
) -> dict:
    """
    Search vectors via subprocess.

    This ensures ChromaDB compatibility regardless of calling Python version.

    Args:
        query_embedding: Query embedding vector (list of floats)
        branch: Optional branch filter
        memory_type: Optional memory type filter
        n_results: Number of results to return
        db_path: Path to Chroma database (None for global)

    Returns:
        Dict with success status and search results
    """
    input_data = {
        'operation': 'search_vectors',
        'query_embedding': query_embedding,
        'branch': branch,
        'memory_type': memory_type,
        'n_results': n_results,
        'db_path': str(db_path) if db_path else None
    }

    try:
        result = subprocess.run(
            [str(MEMORY_PYTHON), str(CHROMA_SUBPROCESS_SCRIPT)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return {'success': False, 'error': result.stderr or 'Subprocess failed'}

        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Search operation timed out'}
    except json.JSONDecodeError as e:
        return {'success': False, 'error': f'Invalid JSON response: {e}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# =============================================================================
# RESULT PROCESSING
# =============================================================================

def _calculate_similarity(distance: float) -> float:
    """
    Calculate similarity from ChromaDB L2 distance.

    ChromaDB L2 distance: 0=identical, ~2=very different.

    Args:
        distance: L2 distance from ChromaDB

    Returns:
        Similarity score between 0 and 1
    """
    return max(0, 1 - (distance / 2))


def _filter_results(results: list, n_results: int) -> list:
    """
    Filter search results by similarity threshold and quality.

    Removes empty documents and results below the minimum similarity threshold.

    Args:
        results: Raw search results from subprocess
        n_results: Maximum number of results to return

    Returns:
        List of filtered result dicts with similarity scores added
    """
    filtered = []
    for result in results[:n_results]:
        document = result.get('document', '')
        distance = result.get('distance', 0)

        similarity = _calculate_similarity(distance)

        # Skip empty documents and low-relevance results
        if not document or not document.strip():
            continue
        if similarity < MIN_SIMILARITY_THRESHOLD:
            continue

        result['similarity'] = similarity
        filtered.append(result)

    return filtered


# =============================================================================
# PUBLIC API
# =============================================================================

def execute_search(
    query: str,
    branch: str | None = None,
    memory_type: str | None = None,
    n_results: int = 5
) -> Dict[str, Any]:
    """
    Execute semantic search: encode query, search vectors, filter results.

    Workflow:
    1. Encode query to embedding vector via embedder handler
    2. Search ChromaDB via subprocess
    3. Filter and score results by similarity

    Args:
        query: Search query text
        branch: Optional branch filter
        memory_type: Optional memory type filter
        n_results: Number of results to return

    Returns:
        Dict with:
            - success: bool
            - query: original query text
            - branch: branch filter (if any)
            - memory_type: memory type filter (if any)
            - results: list of filtered result dicts with similarity scores
            - collections_searched: number of collections searched
            - total_results: total raw results before filtering
            - error: error message (on failure)
    """
    # Step 1: Encode query
    embed_result = embedder.encode_batch([query])

    if not embed_result['success']:
        error_msg = embed_result.get('error', 'Unknown error')
        logger.error(f"[search] Failed to encode query: {error_msg}")
        return {
            'success': False,
            'error': f'Failed to encode query: {error_msg}',
            'query': query,
        }

    embeddings = embed_result.get('embeddings', [])
    if not embeddings:
        return {
            'success': False,
            'error': 'No embedding generated',
            'query': query,
        }

    query_embedding = embeddings[0]
    # Convert numpy array to list for JSON serialization
    if hasattr(query_embedding, 'tolist'):
        query_embedding = query_embedding.tolist()

    logger.info(f"[search] Encoded query to {len(query_embedding)}-dim vector")

    # Step 2: Search via subprocess
    search_result = search_vectors_subprocess(
        query_embedding=query_embedding,
        branch=branch,
        memory_type=memory_type,
        n_results=n_results
    )

    if not search_result['success']:
        error_msg = search_result.get('error', 'Unknown error')
        logger.error(f"[search] Search failed: {error_msg}")
        return {
            'success': False,
            'error': f'Search failed: {error_msg}',
            'query': query,
        }

    raw_results = search_result.get('results', [])
    collections_searched = search_result.get('collections_searched', 0)
    total_results = search_result.get('total_results', 0)

    logger.info(f"[search] Found {total_results} results across {collections_searched} collections")

    # Step 3: Filter and score results
    filtered_results = _filter_results(raw_results, n_results)

    logger.info(f"[search] Filtered to {len(filtered_results)} relevant results")

    return {
        'success': True,
        'query': query,
        'branch': branch,
        'memory_type': memory_type,
        'results': filtered_results,
        'collections_searched': collections_searched,
        'total_results': total_results,
        'filtered_count': len(filtered_results),
    }
