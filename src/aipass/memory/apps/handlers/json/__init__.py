"""
Memory JSON Handler Package

Provides three sub-modules:
    json_handler   -- Standard three-JSON logging (read_json, write_json, log_operation)
    memory_files   -- Memory file safe I/O (read_memory_file, write_memory_file, etc.)
    config_loader  -- Unified config reader for memory.config.json
"""

from .json_handler import (
    log_operation,
    read_json,
    write_json,
)

from .memory_files import (
    read_memory_file,
    write_memory_file,
    update_metadata,
    read_memory_file_data,
    write_memory_file_simple,
    validate_memory_file_structure,
)

from . import config_loader

__all__ = [
    # json_handler (three-JSON standard)
    "log_operation",
    "read_json",
    "write_json",
    # memory_files (memory file I/O)
    "read_memory_file",
    "write_memory_file",
    "update_metadata",
    "read_memory_file_data",
    "write_memory_file_simple",
    "validate_memory_file_structure",
    # config_loader (unified config reader)
    "config_loader",
]
