# =================== AIPass ====================
# Name: INTEGRATION_EXAMPLE.py
# Description: Example: File Watcher Integration with monitor_module.py
# Version: 1.0.0
# Created: 2026-03-09
# Modified: 2026-03-09
# =============================================

"""
Example: File Watcher Integration with monitor_module.py

This shows how to integrate the file watcher with the monitoring module.
This code would go in monitor_module.py's handle_command() function.
"""

import sys

from aipass.prax.apps.modules.logger import system_logger as logger

from aipass.prax.apps.handlers.monitoring import (
    start_file_watcher,
    stop_file_watcher,
    is_file_watcher_running,
    get_file_watcher_stats,
    FileWatcherManager,
    MonitoringEvent,
    global_queue,
    print_event,
)


def example_monitor_with_file_watcher(branch_filter=None):
    """
    Example monitoring loop with file watcher integration

    Args:
        branch_filter: Optional list of branches to watch (e.g., ['PRAX', 'CLI'])
                      None = watch all branches (may hit inotify limits)
    """
    logger.info("Starting PRAX Monitor with File Watcher")
    logger.info("=" * 60)

    # Start file watcher
    if branch_filter:
        logger.info(f"Starting file watcher for branches: {', '.join(branch_filter)}")
        watcher = FileWatcherManager(branch_filter=branch_filter)
        success = watcher.start()
    else:
        logger.info("Starting file watcher for all branches")
        success = start_file_watcher()

    if not success:
        logger.error("Failed to start file watcher")
        return

    # Show stats
    stats = get_file_watcher_stats()
    logger.info(f"Watching {stats['branches_watched']} branches:")
    for branch in stats['branch_names']:
        logger.info(f"  - {branch}")

    logger.info("Monitoring active - press Ctrl+C to stop")
    logger.info("-" * 60)

    try:
        # Main monitoring loop
        while True:
            # Get next event from queue (blocks for 0.5 seconds)
            event = global_queue.dequeue(timeout=0.5)

            if event:
                # Handle different event types
                if event.event_type == 'file':
                    # File change event
                    print_event(event.event_type, event.branch, event.message, event.level)

                elif event.event_type == 'log':
                    # Log event (from log monitor - future)
                    print_event(event.event_type, event.branch, event.message, event.level)

                elif event.event_type == 'module':
                    # Module execution event (from module tracker)
                    print_event(event.event_type, event.branch, event.message, event.level)

                # You can also handle events directly:
                # logger.info(f"[{event.branch}] {event.action}: {event.message}")

    except KeyboardInterrupt:
        logger.info("-" * 60)
        logger.info("Stopping monitor...")

    finally:
        # Cleanup
        stop_file_watcher()
        logger.info("File watcher stopped")
        logger.info("Monitor stopped")


def example_filtered_monitoring():
    """
    Example: Monitor only PRAX and CLI branches

    Recommended approach to avoid inotify limits
    """
    example_monitor_with_file_watcher(branch_filter=['PRAX', 'CLI'])


def example_all_branches_monitoring():
    """
    Example: Monitor all branches

    WARNING: May hit inotify limits on systems with many branches
    """
    example_monitor_with_file_watcher(branch_filter=None)


def example_custom_event_handling():
    """
    Example: Custom event handling logic
    """
    logger.info("Custom Event Handling Example")
    logger.info("=" * 60)

    # Start watcher for specific branches
    watcher = FileWatcherManager(branch_filter=['PRAX'])
    watcher.start()

    logger.info("Watching PRAX branch for 30 seconds...")
    logger.info("Try modifying a file in src/aipass/prax/")

    import time
    start_time = time.time()
    event_count = 0

    try:
        while time.time() - start_time < 30:
            event = global_queue.dequeue(timeout=0.5)

            if event:
                event_count += 1

                # Custom handling based on action
                if event.action == 'created':
                    logger.info(f"NEW FILE: {event.message}")
                    logger.info(f"   Branch: {event.branch}")
                    logger.info(f"   Time: {event.timestamp}")

                elif event.action == 'modified':
                    logger.info(f"MODIFIED: {event.message}")

                elif event.action == 'deleted':
                    logger.info(f"DELETED: {event.message}")

                elif event.action == 'moved':
                    logger.info(f"MOVED: {event.message}")

    except KeyboardInterrupt:
        logger.info("Stopping...")

    finally:
        watcher.stop()
        logger.info(f"Captured {event_count} events in total")


# For integration into monitor_module.py's handle_command():
"""
def handle_command(command: str, args: List[str]) -> bool:
    if command != 'monitor':
        return False

    # Parse branch filter from args
    branch_filter = None
    if args:
        branch_arg = args[0]
        if branch_arg.lower() != 'all':
            branch_filter = [b.strip().upper() for b in branch_arg.split(',')]

    # Start file watcher
    if branch_filter:
        watcher = FileWatcherManager(branch_filter=branch_filter)
        watcher.start()
    else:
        start_file_watcher()

    # Main monitoring loop
    try:
        while True:
            event = global_queue.dequeue(timeout=0.5)
            if event:
                print_event(event)
    except KeyboardInterrupt:
        pass
    finally:
        stop_file_watcher()

    return True
"""


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == 'custom':
            example_custom_event_handling()
        elif sys.argv[1] == 'all':
            example_all_branches_monitoring()
        else:
            # Parse branch list
            branches = [b.strip().upper() for b in sys.argv[1].split(',')]
            example_monitor_with_file_watcher(branch_filter=branches)
    else:
        # Default: monitor PRAX only
        logger.info("Usage:")
        logger.info("  python3 INTEGRATION_EXAMPLE.py                 # Monitor PRAX only")
        logger.info("  python3 INTEGRATION_EXAMPLE.py PRAX,CLI        # Monitor specific branches")
        logger.info("  python3 INTEGRATION_EXAMPLE.py all             # Monitor all branches (may fail)")
        logger.info("  python3 INTEGRATION_EXAMPLE.py custom          # Custom event handling demo")
        logger.info("Running default: PRAX only")
        example_monitor_with_file_watcher(branch_filter=['PRAX'])
