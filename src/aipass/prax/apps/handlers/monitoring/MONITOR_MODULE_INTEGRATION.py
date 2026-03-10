# =================== AIPass ====================
# Name: MONITOR_MODULE_INTEGRATION.py
# Description: EXAMPLE: How to integrate log_watcher into monitor_module.py
# Version: 1.0.0
# Created: 2026-03-09
# Modified: 2026-03-09
# =============================================

"""
EXAMPLE: How to integrate log_watcher into monitor_module.py

This is a reference implementation showing the minimal changes needed
to add log monitoring to monitor_module.py's handle_command() function.

Copy the relevant sections into monitor_module.py as needed.
"""

import sys
from typing import List

from aipass.prax.apps.modules.logger import system_logger as logger

# Import monitoring components
from aipass.prax.apps.handlers.monitoring import (
    start_log_watcher,        # NEW: Log watcher integration
    stop_log_watcher,         # NEW: Log watcher cleanup
    is_log_watcher_active,    # NEW: Status check
    MonitoringQueue,
    MonitoringEvent,
    print_event,
    FilterState,
    should_display_event,
)

# Global state
_log_observer = None
_event_queue = None


def handle_command(command: str, args: List[str]) -> bool:
    """
    Example handle_command with log watcher integration

    This shows the minimal changes to add real-time log monitoring
    to the existing monitor_module.py structure.
    """
    if command != 'monitor':
        return False

    global _log_observer, _event_queue

    logger.info(f"Starting unified monitoring (args: {args})")
    logger.info("PRAX Mission Control - Unified Monitoring")

    # Initialize event queue
    _event_queue = MonitoringQueue()
    logger.info("Event queue initialized")

    # Start log watcher - NEW INTEGRATION
    try:
        _log_observer = start_log_watcher(_event_queue)
        logger.info("Log watcher started")
        logger.info("Monitoring: system_logs/*.log")
    except Exception as e:
        logger.error(f"Failed to start log watcher: {e}")
        return False

    logger.info("Monitoring active - type 'quit' to exit")

    # Initialize filter state
    filter_state = FilterState()

    # Parse branch filters from args
    if args:
        branches = args[0].split(',') if args[0] != 'all' else []
        if branches:
            filter_state.watched_branches = {b.strip().upper() for b in branches}
            logger.info(f"Filtering branches: {', '.join(filter_state.watched_branches)}")

    try:
        # Main event loop
        while True:
            # Dequeue next event (with timeout to allow Ctrl+C)
            event = _event_queue.dequeue(timeout=0.5) if _event_queue else None

            if event:
                # Apply filters
                if should_display_event(event.event_type, event.branch, event.level, filter_state):

                    # Handle command separator events
                    if event.event_type == 'command':
                        logger.info(f"Command: {event.message}")

                    # Handle log events
                    elif event.event_type == 'log':
                        # Format timestamp
                        timestamp = event.timestamp.strftime('%H:%M:%S')

                        # Branch column (right-aligned, fixed width)
                        branch_col = f"[{event.branch:>8}]"

                        # Display event via logger
                        logger.info(f"{timestamp} {branch_col} {event.message}")

            # Check for keyboard input (simplified - use proper input handling)
            # TODO: Add interactive command handling here

    except KeyboardInterrupt:
        logger.info("Stopping monitoring...")

    finally:
        # Cleanup
        if _log_observer:
            stop_log_watcher()
            logger.info("Log watcher stopped")

        if _event_queue:
            _event_queue.stop()
            logger.info("Event queue stopped")

    logger.info("Monitoring stopped")

    return True


def example_with_interactive_commands():
    """
    Example showing interactive command handling

    This is a more complete version with command input handling.
    Requires threading to read both events and keyboard input.
    """
    import threading
    import select

    def input_handler(running_flag):
        """Thread for reading keyboard input"""
        while running_flag[0]:
            # Use select for non-blocking input on Unix
            if select.select([sys.stdin], [], [], 0.5)[0]:
                try:
                    user_input = sys.stdin.readline().strip()

                    if user_input in ['quit', 'exit']:
                        running_flag[0] = False
                    elif user_input == 'help':
                        logger.info("Commands: help, status, quit")
                    elif user_input == 'status':
                        logger.info(f"Log watcher: {'active' if is_log_watcher_active() else 'inactive'}")
                        logger.info(f"Queue size: {_event_queue.size() if _event_queue else 0}")

                except Exception:
                    pass

    # Running flag for threads
    running = [True]

    # Start input handler thread
    input_thread = threading.Thread(target=input_handler, args=(running,))
    input_thread.daemon = True
    input_thread.start()

    # Main event loop
    while running[0]:
        event = _event_queue.dequeue(timeout=0.5) if _event_queue else None
        if event:
            # Display event (same as above)
            pass


# Example of filter adjustment
def example_filter_adjustment():
    """Show how to dynamically adjust filters"""

    filter_state = FilterState()

    # Watch specific branches
    filter_state.watched_branches = {'SEED', 'FLOW', 'PRAX'}

    # Apply filter
    event = MonitoringEvent(
        priority=1,
        event_type='log',
        branch='SEED',
        level='error',
        message='ERROR: Something went wrong'
    )

    if should_display_event(event.event_type, event.branch, event.level, filter_state):
        logger.info("Event passed filters")


if __name__ == '__main__':
    logger.info("Monitor Module Integration Examples")
    logger.info("This file shows examples of integrating log_watcher.py")
    logger.info("into monitor_module.py's handle_command() function.")
    logger.info("Key changes:")
    logger.info("  1. Import start_log_watcher, stop_log_watcher")
    logger.info("  2. Initialize MonitoringQueue")
    logger.info("  3. Start log watcher with queue")
    logger.info("  4. Main loop dequeues and displays events")
    logger.info("  5. Cleanup on exit")
    logger.info("See code above for full implementation details.")
