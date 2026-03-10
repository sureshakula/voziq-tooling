# =================== AIPass ====================
# Name: extractor.py
# Description: Memory Extraction Handler
# Version: 0.4.0
# Created: 2025-11-16
# Modified: 2026-03-06
# =============================================

"""
Memory Extraction Handler

Surgically extracts oldest items from memory files during rollover.
Understands real JSON structure (sessions, observations arrays).

Purpose:
    When file exceeds 600 lines, extract oldest items from growing arrays
    (sessions, observations, etc.), preserve JSON validity, update metadata.

Strategy:
    - Detect which array is growing (sessions, observations, etc.)
    - Calculate how many items to remove to get under limit
    - Extract oldest items (FIFO)
    - Update document_metadata.status
"""

import shutil
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Handler imports (relative within package)
from aipass.memory.apps.handlers.json.json_handler import read_memory_file_data, write_memory_file_simple
from aipass.prax.apps.modules.logger import get_system_logger

logger = get_system_logger()

# No module imports (handler independence)


# =============================================================================
# BACKUP OPERATIONS
# =============================================================================

def create_rollover_backup(file_path: Path) -> Dict[str, Any]:
    """
    Create backup before rollover (safety net)

    Creates backup in branch's .backup/ directory with timestamp.
    Only keeps ONE backup - overwrites previous rollover backup.

    Args:
        file_path: Path to memory file to backup

    Returns:
        Dict with backup path and success status
    """
    try:
        # Create .backup directory in branch root
        backup_dir = file_path.parent / '.backup'
        backup_dir.mkdir(exist_ok=True)

        # Backup filename: rollover_backup.json (always overwrites)
        backup_name = f'rollover_backup_{file_path.name}'
        backup_path = backup_dir / backup_name

        # Copy file
        shutil.copy2(file_path, backup_path)

        return {
            'success': True,
            'backup_path': str(backup_path),
            'message': f'Backup created: {backup_path.name}'
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Backup failed: {e}'
        }


def restore_from_backup(file_path: Path) -> Dict[str, Any]:
    """
    Restore file from rollover backup

    Called when rollover fails to restore original state.

    Args:
        file_path: Path to memory file to restore

    Returns:
        Dict with restore status
    """
    try:
        backup_dir = file_path.parent / '.backup'
        backup_name = f'rollover_backup_{file_path.name}'
        backup_path = backup_dir / backup_name

        if not backup_path.exists():
            return {
                'success': False,
                'error': 'No backup found to restore from'
            }

        # Restore from backup
        shutil.copy2(backup_path, file_path)

        return {
            'success': True,
            'message': f'Restored from backup: {backup_path.name}'
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Restore failed: {e}'
        }


# =============================================================================
# FILE OPERATIONS
# =============================================================================

def _read_memory_file(file_path: Path) -> Dict[str, Any]:
    """Read memory JSON file using json_handler"""
    return read_memory_file_data(file_path)


def _write_memory_file(file_path: Path, data: Dict[str, Any]) -> None:
    """Write memory JSON file using json_handler"""
    write_memory_file_simple(file_path, data)


def _count_file_lines(file_path: Path) -> int:
    """Count physical lines in file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return len(f.readlines())


# =============================================================================
# STRUCTURE DETECTION
# =============================================================================

def _detect_growing_array(data: Dict[str, Any]) -> str | None:
    """
    Detect which array field is growing in memory file

    Memory files have different structures:
    - .local.json → 'sessions' array
    - .observations.json → 'observations' array
    - Future types → other array fields

    Args:
        data: Parsed JSON data

    Returns:
        Array field name (e.g., 'sessions'), or None if not found
    """
    # Known array fields that grow over time
    candidates = ['sessions', 'observations', 'recent_work', 'entries', 'items', 'records']

    for field in candidates:
        if field in data and isinstance(data[field], list) and len(data[field]) > 0:
            return field

    return None


# =============================================================================
# EXTRACTION CALCULATION
# =============================================================================

def _calculate_items_to_extract_by_lines(
    data: Dict[str, Any],
    array_field: str,
    file_path: Path,
    max_lines: int,
    target_buffer: int = 100
) -> int:
    """
    Calculate items to extract by SIMULATING line count (accurate)

    Removes items one by one, counting actual lines after each removal,
    until we reach target line count (max_lines - buffer).

    Args:
        data: Full memory file data
        array_field: Name of array field to extract from
        file_path: Path (for line counting)
        max_lines: Maximum allowed lines
        target_buffer: Lines of buffer to leave (default 100)

    Returns:
        Number of items to extract

    Example:
        File is 645 lines, limit is 600, buffer is 100
        Target: 500 lines (600 - 100)
        Simulate removing items until file is ~500 lines
    """
    import tempfile
    import json

    target_lines = max_lines - target_buffer
    total_items = len(data[array_field])

    # Binary search for optimal item count
    for items_to_remove in range(1, total_items + 1):
        # Simulate removal (remove from END - oldest items)
        test_data = data.copy()
        test_data[array_field] = data[array_field][:-items_to_remove]  # Keep newest

        # Count lines in simulated result
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
            json.dump(test_data, tmp, indent=2, ensure_ascii=False)
            tmp_path = Path(tmp.name)

        with open(tmp_path, 'r') as f:
            line_count = len(f.readlines())

        tmp_path.unlink()

        # Check if we've reached target
        if line_count <= target_lines:
            return items_to_remove

    # Fallback: remove 50% if simulation fails
    return max(1, total_items // 2)


# =============================================================================
# EXTRACTION OPERATIONS
# =============================================================================

def extract_items(
    file_path: Path,
    percentage: int | None = None
) -> Dict[str, Any]:
    """
    Extract items from memory file (WITH BACKUP SAFETY)

    Now includes automatic backup before modification.
    File is modified immediately, but backup exists for recovery.

    Args:
        file_path: Path to memory JSON file
        percentage: Percentage of items to extract (auto-calculated if None)

    Returns:
        Dict with extracted items and metadata
    """
    if not file_path.exists():
        return {
            'success': False,
            'error': f"File not found: {file_path}"
        }

    # Read file
    try:
        data = _read_memory_file(file_path)
        current_lines = _count_file_lines(file_path)
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to read file: {e}"
        }

    # Detect structure
    array_field = _detect_growing_array(data)
    if not array_field:
        return {
            'success': False,
            'error': f"No growing array found in {file_path.name}"
        }

    # Get metadata
    max_lines = data.get('document_metadata', {}).get('limits', {}).get('max_lines', 600)

    # Check if under limit
    if current_lines <= max_lines:
        return {
            'success': True,
            'skipped': True,
            'message': f"File under limit ({current_lines}/{max_lines} lines)"
        }

    # Calculate extraction amount (simulate actual line reduction)
    total_items = len(data[array_field])

    if percentage is None:
        # Use line-based calculation for accuracy
        items_to_extract = _calculate_items_to_extract_by_lines(
            data, array_field, file_path, max_lines, target_buffer=100
        )
    else:
        # Manual percentage override (for testing)
        items_to_extract = max(1, int(total_items * percentage / 100))

    # Extract oldest items (LAST N in array - newest first, oldest last)
    extracted = data[array_field][-items_to_extract:]  # Take from end (oldest)
    remaining = data[array_field][:-items_to_extract]  # Keep from start (newest)

    # Update array
    data[array_field] = remaining

    # Update metadata
    _update_metadata_after_extraction(data)

    # Write back
    try:
        _write_memory_file(file_path, data)
        new_line_count = _count_file_lines(file_path)
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to write file: {e}"
        }

    # Parse branch and type from filename
    parts = file_path.stem.split('.')
    branch_name = parts[0] if len(parts) > 0 else "UNKNOWN"
    memory_type = parts[1] if len(parts) > 1 else "unknown"

    return {
        'success': True,
        'file': str(file_path),
        'branch': branch_name,
        'type': memory_type,
        'array_field': array_field,
        'extracted': extracted,
        'extracted_count': items_to_extract,
        'remaining_count': len(remaining),
        'old_lines': current_lines,
        'new_lines': new_line_count
    }


# =============================================================================
# METADATA OPERATIONS
# =============================================================================

def _update_metadata_after_extraction(data: Dict[str, Any]) -> None:
    """
    Update document_metadata after extraction.

    Updates:
    - status.last_health_check

    Args:
        data: JSON data dict (modified in place)
    """
    # Ensure metadata structure
    if 'document_metadata' not in data:
        data['document_metadata'] = {}

    metadata = data['document_metadata']

    # Update status
    if 'status' not in metadata:
        metadata['status'] = {}

    metadata['status']['last_health_check'] = datetime.now().strftime("%Y-%m-%d")


# =============================================================================
# VECTORIZATION PREPARATION
# =============================================================================

def extract_with_metadata(
    file_path: Path,
    percentage: int | None = None
) -> Dict[str, Any]:
    """
    Extract items with enriched metadata for vectorization

    Same as extract_items but adds metadata needed for vector storage.

    Args:
        file_path: Path to memory JSON file
        percentage: Percentage of items to extract (auto-calculated if None)

    Returns:
        Dict with extracted items + vectorization metadata
    """
    # Do standard extraction
    result = extract_items(file_path, percentage)

    if not result['success']:
        return result

    # Enrich extracted items with metadata
    extracted = result.get('extracted', [])
    branch = result.get('branch')
    memory_type = result.get('type')
    array_field = result.get('array_field')

    extraction_timestamp = datetime.now().isoformat()

    enriched = []
    for item in extracted:
        enriched_item = {
            **item,  # Preserve original item data
            '_metadata': {
                'branch': branch,
                'type': memory_type,
                'array_field': array_field,
                'extracted_at': extraction_timestamp,
                'source_file': file_path.name
            }
        }
        enriched.append(enriched_item)

    # Return enriched version
    return {
        'success': True,
        'file': str(file_path),
        'branch': branch,
        'type': memory_type,
        'array_field': array_field,
        'entries': enriched,
        'count': len(enriched),
        'old_lines': result.get('old_lines'),
        'new_lines': result.get('new_lines')
    }
