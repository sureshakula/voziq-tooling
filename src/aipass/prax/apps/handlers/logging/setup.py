#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: setup.py - Logger Setup & Management
# Date: 2025-11-10
# Version: 1.0.0
# Category: prax/handlers/logging
#
# CHANGELOG (Max 5 entries):
#   - v1.0.0 (2025-11-10): Extracted from archive.temp/prax_handlers.py
# =============================================

"""
PRAX Logger Setup

Creates and configures individual loggers for modules.
Handles dual logging (system-wide + branch-local) and terminal output.
"""

from pathlib import Path

import logging
from typing import Dict, Optional
from logging.handlers import RotatingFileHandler

# Import from prax config
from aipass.prax.apps.handlers.config.load import (
    SYSTEM_LOGS_DIR,
    DEFAULT_LOG_LEVEL,
    load_log_config,
    lines_to_bytes
)

# Import introspection functions
from aipass.prax.apps.handlers.logging.introspection import (
    get_calling_module_path,
    detect_branch_from_path
)

# CLI import
from aipass.cli.apps.modules import console

# Global state for logging system
_system_logger: Optional[logging.Logger] = None
_captured_loggers: Dict[str, logging.Logger] = {}
_terminal_output_enabled = False

# Try to import terminal handler support
_terminal_module_available = False
try:
    from aipass.prax.apps.handlers.logging.terminal.formatting import create_terminal_handler
    from aipass.prax.apps.handlers.logging.terminal.filtering import should_display_terminal
    _terminal_module_available = True
except ImportError:
    pass  # Terminal module not available yet

def setup_individual_logger(module_name: str) -> logging.Logger:
    """Setup individual logger for a specific module with dual logging support

    Creates:
    - System-wide log: /home/aipass/system_logs/prax_{module_name}.log
    - Branch-local log: /home/aipass/{branch}/logs/{module_name}.log (if in a branch)
    - Terminal handler (if enabled)

    Args:
        module_name: Name of the module requesting a logger

    Returns:
        Configured logger instance
    """
    if module_name in _captured_loggers:
        return _captured_loggers[module_name]

    # Log new logger creation
    if _system_logger:
        _system_logger.info(f"Creating logger for module: {module_name}")

    # Create individual logger for this module
    logger = logging.getLogger(f"captured_{module_name}")
    logger.setLevel(DEFAULT_LOG_LEVEL)
    logger.handlers.clear()

    # Load config-driven limits
    log_config = load_log_config()

    # Detect calling branch FIRST (needed for both system and branch logs)
    module_path = get_calling_module_path()
    branch_path = detect_branch_from_path(module_path) if module_path else None

    # Extract branch name from path
    # "aipass_core/cortex" → "cortex"
    # "aipass_core/flow" → "flow"
    # "some_project" → "some_project"
    if branch_path:
        branch_name = branch_path.split('/')[-1]
    else:
        branch_name = "prax"  # Fallback to prax if no branch detected

    # Create formatter (shared by all handlers)
    formatter = logging.Formatter(
        log_config['log_format'],
        log_config['date_format']
    )

    # HANDLER 1: System-wide log (named after calling branch)
    system_log_file = SYSTEM_LOGS_DIR / f"{branch_name}_{module_name}.log"
    system_limits = log_config['system_logs']
    system_max_bytes = lines_to_bytes(system_limits['max_lines'])
    system_handler = RotatingFileHandler(
        system_log_file,
        maxBytes=system_max_bytes,
        backupCount=system_limits['backup_count'],
        encoding='utf-8'
    )
    system_handler.setFormatter(formatter)
    logger.addHandler(system_handler)

    # HANDLER 2: Branch-local log (if module is in a branch)
    branch = branch_path  # Use already detected branch_path

    if branch:
        # Create branch logs directory if it doesn't exist
        # Branch format is now "aipass_core/module" or "project_name"
        branch_logs_dir = Path.home() / branch / "logs"
        branch_logs_dir.mkdir(parents=True, exist_ok=True)

        # Create branch-local log file
        branch_log_file = branch_logs_dir / f"{module_name}.log"
        local_limits = log_config['local_logs']
        local_max_bytes = lines_to_bytes(local_limits['max_lines'])
        branch_handler = RotatingFileHandler(
            branch_log_file,
            maxBytes=local_max_bytes,
            backupCount=local_limits['backup_count'],
            encoding='utf-8'
        )
        branch_handler.setFormatter(formatter)
        logger.addHandler(branch_handler)

        # Log to system logger
        if _system_logger:
            _system_logger.info(f"Logger created for {module_name} → system: {system_log_file} ({system_limits['max_lines']} lines), branch: {branch_log_file} ({local_limits['max_lines']} lines)")
    else:
        # Log to system logger
        if _system_logger:
            _system_logger.info(f"Logger created for {module_name} → {system_log_file} ({system_limits['max_lines']} lines)")

    # HANDLER 3: Terminal output (if enabled)
    if _terminal_output_enabled and _terminal_module_available:
        if should_display_terminal(module_name):
            terminal_handler = create_terminal_handler()
            logger.addHandler(terminal_handler)

    # Store for reuse
    _captured_loggers[module_name] = logger

    return logger

def setup_system_logger() -> logging.Logger:
    """Setup prax_logger's own logging

    Creates the system logger used by prax itself.

    Returns:
        Prax system logger instance
    """
    global _system_logger

    if _system_logger:
        return _system_logger

    # Load config-driven limits
    log_config = load_log_config()

    # Create prax_logger's own logger
    _system_logger = logging.getLogger("prax_system_logger")
    _system_logger.setLevel(DEFAULT_LOG_LEVEL)
    _system_logger.handlers.clear()

    # Create prax_logger's own log file
    log_file = SYSTEM_LOGS_DIR / "prax_logger.log"

    # Create rotating file handler with config-driven limits
    system_limits = log_config['system_logs']
    system_max_bytes = lines_to_bytes(system_limits['max_lines'])
    handler = RotatingFileHandler(
        log_file,
        maxBytes=system_max_bytes,
        backupCount=system_limits['backup_count'],
        encoding='utf-8'
    )

    # Set formatter
    formatter = logging.Formatter(
        log_config['log_format'],
        log_config['date_format']
    )
    handler.setFormatter(formatter)
    _system_logger.addHandler(handler)

    # Log system logger creation
    _system_logger.info("Prax system logger initialized successfully")
    _system_logger.info(f"System logger writing to: {log_file} ({system_limits['max_lines']} lines max)")

    return _system_logger

def get_captured_loggers_count() -> int:
    """Get count of captured loggers

    Returns:
        Number of module loggers created
    """
    return len(_captured_loggers)

def get_captured_loggers() -> Dict[str, logging.Logger]:
    """Get dictionary of captured loggers

    Returns:
        Copy of captured loggers dict
    """
    return _captured_loggers.copy()

def enable_terminal_output():
    """Enable terminal output for all future loggers"""
    global _terminal_output_enabled
    _terminal_output_enabled = True
    console.print("[prax] Terminal output enabled")

def disable_terminal_output():
    """Disable terminal output"""
    global _terminal_output_enabled
    _terminal_output_enabled = False
    console.print("[prax] Terminal output disabled")

def is_terminal_output_enabled() -> bool:
    """Check if terminal output is enabled

    Returns:
        True if terminal output is enabled
    """
    return _terminal_output_enabled
