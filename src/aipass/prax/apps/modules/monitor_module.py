
# ===================AIPASS====================
# META DATA HEADER
# Name: monitor_module.py - Unified Monitoring Module
# Date: 2025-11-23
# Version: 0.2.0
# Category: prax/modules
#
# CHANGELOG (Max 5 entries):
#   - v0.2.0 (2025-11-23): Implemented threading-based monitoring loop
#     * Added display thread (pulls from event queue)
#     * Added file watcher thread (monitors filesystem changes)
#     * Added log watcher thread (monitors log files)
#     * Implemented interactive command handling (watch, filter, status, help, quit)
#     * Starts in quiet mode - no output until user specifies what to watch
#   - v0.1.0 (2025-11-23): Initial version - Mission Control orchestrator
#
# CODE STANDARDS:
#   - Follows AIPass Prax standards
#   - Implements handle_command(command: str, args: List[str]) -> bool interface
#   - Uses Prax logger for system-wide logging
#   - Orchestration only - delegates to handlers
# =============================================

"""
PRAX Monitor Module - Mission Control for Autonomous Branches

Unified monitoring orchestrator that provides real-time visibility into:
- File changes across all branches (file watcher)
- Log events from all modules (log monitoring)
- Branch activity and state changes
- Module execution tracking
- System health and status

Purpose:
    Single command interface for monitoring all autonomous branch activity.
    Replaces fragmented monitoring with unified Mission Control console.
    Enables multi-agent workflow visibility and coordination.

Usage:
    prax monitor              # Monitor all branches (quiet mode)
    prax monitor all          # Explicit all-branches monitoring
    prax monitor seed,cli     # Monitor specific branches

Interactive Commands:
    help                      # Show available commands
    status                    # Display current monitoring state
    filter [branches]         # Adjust branch filter
    quit/exit                 # Stop monitoring

Architecture:
    This module is thin orchestration layer only. All implementation
    delegated to specialized handlers in apps/handlers/monitoring/:

    - unified_stream.py       → Terminal output formatting
    - branch_detector.py      → Path-to-branch mapping
    - interactive_filter.py   → Runtime filter adjustment
    - monitoring_filters.py   → Event filtering logic (TODO)
    - event_queue.py          → Event buffering and deduplication
    - module_tracker.py       → Module execution tracking
    - (file watcher)          → Real-time file change detection (TODO)
    - (log monitor)           → Log stream processing (TODO)
"""

import sys
import argparse
import threading
import time
from pathlib import Path
from typing import List, Optional

# Prax logger (system-wide, always first)
from aipass.prax.apps.modules.logger import system_logger as logger

# CLI services (display/output formatting)
from aipass.cli.apps.modules import console, header, success, error, warning

# Monitoring handlers (connected subsystems)
from aipass.prax.apps.handlers.monitoring import (
    print_event,              # unified_stream.py
    print_command_separator,  # unified_stream.py - command headers
    detect_branch_from_path,  # branch_detector.py
    FilterState,              # interactive_filter.py
    parse_command,            # interactive_filter.py
    should_monitor,           # monitoring_filters.py
    get_priority,             # monitoring_filters.py
    MonitoringEvent,          # event_queue.py
    MonitoringQueue,          # event_queue.py
    ModuleTracker,            # module_tracker.py
)

# Telegram relay (optional - graceful if unavailable)
try:
    from aipass.prax.apps.handlers.monitoring.telegram_relay import (
        telegram_start, telegram_stop, telegram_queue_event
    )
    _telegram_available = True
except ImportError:
    _telegram_available = False

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def normalize_branch_arg(arg: str) -> str:
    """
    Convert path or name to branch name.

    DRONE now resolves @branch arguments to full paths before passing to modules.
    This function normalizes both formats to branch names.

    The package structure is: .../src/aipass/{module}/apps/...
    Find "aipass" in path parts, then the next part is the module name.

    Args:
        arg: Branch name (e.g., "flow") or full path (e.g., ".../src/aipass/flow")

    Returns:
        Uppercase branch name (e.g., "FLOW")

    Examples:
        >>> normalize_branch_arg("flow")
        "FLOW"
        >>> normalize_branch_arg("/path/to/src/aipass/flow")
        "FLOW"
    """
    if arg.startswith('/'):
        from pathlib import Path
        parts = Path(arg).parts
        # Check if path contains "aipass" - extract module name after it
        if 'aipass' in parts:
            idx = parts.index('aipass')
            if idx + 1 < len(parts):
                return parts[idx + 1].upper()
        # Otherwise, use last part of path
        return Path(arg).name.upper()
    return arg.upper()

# =============================================================================
# PID CACHE - Maps branch names to active agent PIDs from dispatch lock files
# =============================================================================

import json as _json

_pid_cache: dict[str, int] = {}
_pid_cache_lock = threading.Lock()
_pid_cache_last_refresh: float = 0.0
_PID_CACHE_TTL = 30.0  # Refresh every 30 seconds


def _refresh_pid_cache() -> None:
    """Scan dispatch lock files to build branch→PID mapping."""
    global _pid_cache_last_refresh
    import time as _time
    now = _time.time()
    if now - _pid_cache_last_refresh < _PID_CACHE_TTL:
        return
    _pid_cache_last_refresh = now

    try:
        from aipass.prax.apps.handlers.config.load import _find_repo_root
        registry_path = _find_repo_root() / "AIPASS_REGISTRY.json"
        if not registry_path.exists():
            return
        data = _json.loads(registry_path.read_text(encoding="utf-8"))
        new_cache: dict[str, int] = {}
        for branch in data.get("branches", []):
            branch_path = Path(branch.get("path", ""))
            lock_path = branch_path / "ai_mail.local" / ".dispatch.lock"
            if not lock_path.exists():
                continue
            try:
                lock_data = _json.loads(lock_path.read_text(encoding="utf-8"))
                pid = lock_data.get("pid", 0)
                if pid and (sys.platform == "linux" and Path(f"/proc/{pid}").exists()):
                    name = branch.get("name", "").upper()
                    if name:
                        new_cache[name] = pid
            except (ValueError, OSError):
                continue
        with _pid_cache_lock:
            _pid_cache.clear()
            _pid_cache.update(new_cache)
    except Exception as e:
        logger.info(f"[monitor] PID cache refresh failed: {e}")


def _get_pid_for_branch(branch: str) -> Optional[int]:
    """Look up PID for a branch from the cache."""
    _refresh_pid_cache()
    base = branch.upper()
    if base.endswith(' AGENT'):
        base = base[:-6]
    with _pid_cache_lock:
        return _pid_cache.get(base)


# =============================================================================
# MODULE STATE
# =============================================================================

# Global monitoring state
_monitoring_active = False
_filter_state: Optional[FilterState] = None
_event_queue: Optional[MonitoringQueue] = None
_module_tracker: Optional[ModuleTracker] = None
_display_thread: Optional[threading.Thread] = None
_file_watcher_thread: Optional[threading.Thread] = None
_log_watcher_thread: Optional[threading.Thread] = None


# =============================================================================
# CORE COMMAND HANDLER (Required for auto-discovery)
# =============================================================================

def handle_command(command: str, args: List[str]) -> bool:
    """
    Handle monitor command - required for auto-discovery by prax.py

    Args:
        command: Command name from prax.py dispatcher
        args: Command arguments (branch filters, flags, etc.)

    Returns:
        True if command was handled (command == "monitor")
        False if not our command (pass to next handler)
    """
    if command != 'monitor':
        return False

    global _monitoring_active, _filter_state, _event_queue, _module_tracker
    global _display_thread, _file_watcher_thread, _log_watcher_thread

    logger.info(f"Starting unified monitoring (args: {args})")

    # Initialize monitoring subsystems
    _filter_state = FilterState()
    _event_queue = MonitoringQueue()
    _module_tracker = ModuleTracker()
    _monitoring_active = True

    # Parse args for initial branch filters
    _is_tty = sys.stdin.isatty()
    if args:
        if args[0] == 'all':
            # Watch all branches
            _filter_state.show_all = True
            _filter_state.show_info = True
        else:
            # Watch specific branches
            initial_branches = args[0].split(',')
            _filter_state.watched_branches = set(normalize_branch_arg(b.strip()) for b in initial_branches)
            _filter_state.show_info = True
    elif not _is_tty:
        # No TTY and no args — default to watching all (can't type 'watch all')
        _filter_state.show_all = True
        _filter_state.show_info = True

    # Display header
    console.print()
    header("PRAX Mission Control - Unified Monitoring")
    console.print()
    console.print("[green]Monitoring system starting...[/green]")
    if _is_tty:
        console.print("[yellow]Quiet mode active - type 'help' for commands[/yellow]")
    else:
        console.print("[yellow]Passive mode - no TTY detected, watching all (Ctrl+C to stop)[/yellow]")
    console.print()

    # Start monitoring threads + Telegram relay
    _start_threads()
    if _telegram_available:
        telegram_start()

    # Enter interactive mode
    _interactive_loop()

    # Cleanup on exit
    if _telegram_available:
        telegram_stop()
    _stop_threads()

    return True


def _start_threads():
    """Start all monitoring threads"""
    global _display_thread, _file_watcher_thread, _log_watcher_thread

    # Display thread - pulls from event queue and displays
    _display_thread = threading.Thread(target=_display_worker, daemon=True)
    _display_thread.start()

    # File watcher thread - watches filesystem changes
    _file_watcher_thread = threading.Thread(target=_file_watcher_worker, daemon=True)
    _file_watcher_thread.start()

    # Log watcher thread - watches log files
    _log_watcher_thread = threading.Thread(target=_log_watcher_worker, daemon=True)
    _log_watcher_thread.start()

    logger.info("All monitoring threads started")


def _stop_threads():
    """Stop all monitoring threads"""
    global _monitoring_active, _event_queue

    _monitoring_active = False

    if _event_queue:
        _event_queue.stop()

    # Give threads time to finish
    time.sleep(0.5)

    logger.info("All monitoring threads stopped")


def _display_worker():
    """Display thread - pulls events from queue and displays them"""
    global _monitoring_active, _event_queue, _filter_state

    while _monitoring_active:
        if not _event_queue:
            time.sleep(0.1)
            continue

        # Get next event from queue
        event = _event_queue.dequeue(timeout=0.1)

        if event:
            # Check if event should be displayed based on filters
            from aipass.prax.apps.handlers.monitoring.interactive_filter import should_display_event

            if _filter_state and should_display_event(event.event_type, event.branch, event.level, _filter_state, event.message):
                # Resolve PID for this branch
                branch_pid = _get_pid_for_branch(event.branch)

                # Display the event - use separator for commands, regular format for others
                if event.event_type == 'command':
                    # Pass caller and target for attribution
                    caller = getattr(event, 'caller', None)
                    # Target encoded in action field as "executed:TARGET"
                    target = None
                    if hasattr(event, 'action') and event.action and ':' in event.action:
                        parts = event.action.split(':', 1)
                        if len(parts) == 2 and parts[1]:
                            target = parts[1]
                    print_command_separator(event.branch, event.message, caller, target)
                    # Telegram relay
                    if _telegram_available:
                        telegram_queue_event('command', event.branch, event.message, caller, target)
                else:
                    print_event(event.event_type, event.branch, event.message, event.level, pid=branch_pid)
                    # Telegram relay
                    if _telegram_available:
                        telegram_queue_event(event.event_type, event.branch, event.message)


def _file_watcher_worker():
    """File watcher thread - watches filesystem changes and pushes to queue"""
    global _monitoring_active, _event_queue

    # Use the existing file watcher from discovery
    from aipass.prax.apps.handlers.discovery.watcher import start_file_watcher, stop_file_watcher
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    from aipass.prax.apps.handlers.config.load import ECOSYSTEM_ROOT

    # Files whose modification indicates a command is running (python3 direct calls)
    # Maps filename -> command description. Used to emit command separators from file events.
    COMMAND_INDICATOR_FILES = {
        'standards_audit_log.json': 'seed audit',
        'standards_checklist_log.json': 'seed checklist',
    }
    # Track last command emitted per file to avoid duplicate separators
    last_file_command = {}
    # Track JSONL file positions for incremental reading
    jsonl_positions = {}
    # Track last agent action per session to avoid duplicate displays
    last_agent_action = {}

    class MonitoringFileHandler(FileSystemEventHandler):
        """File system event handler that pushes to event queue"""

        def on_created(self, event):
            if not event.is_directory:
                self._handle_event('created', event.src_path)

        def on_modified(self, event):
            if not event.is_directory:
                self._handle_event('modified', event.src_path)

        def on_deleted(self, event):
            if not event.is_directory:
                self._handle_event('deleted', event.src_path)

        def on_moved(self, event):
            if not event.is_directory:
                # dest_path can be bytes or str, normalize to str for comparison
                dest_path_str = event.dest_path.decode() if isinstance(event.dest_path, bytes) else event.dest_path
                src_path_str = event.src_path.decode() if isinstance(event.src_path, bytes) else event.src_path
                if 'Trash' in dest_path_str or '.local/share/Trash' in dest_path_str:
                    # Moved to Trash = deletion
                    self._handle_event('deleted', src_path_str)
                elif '.tmp.' in src_path_str or src_path_str.endswith('.tmp'):
                    # Atomic write: tmp file moved to real file = modification
                    self._handle_event('modified', dest_path_str)
                else:
                    self._handle_event('moved', dest_path_str)

        def _parse_agent_activity(self, file_path, branch):
            """Parse Claude Code session JSONL to show agent actions.

            Returns True if an event was emitted (or deduped), False on failure.
            """
            import json as _json
            try:
                path_key = str(file_path)
                current_size = file_path.stat().st_size
                last_pos = jsonl_positions.get(path_key, 0)

                # File shrunk or new - reset
                if current_size < last_pos:
                    last_pos = 0

                if current_size <= last_pos:
                    return True  # No new data, but not an error

                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_pos)
                    new_data = f.read()
                    jsonl_positions[path_key] = f.tell()

                # Parse last meaningful line
                lines = [l for l in new_data.strip().split('\n') if l.strip()]
                if not lines:
                    return True  # Empty, not an error

                for line in reversed(lines):
                    try:
                        entry = _json.loads(line)
                    except _json.JSONDecodeError:
                        continue

                    entry_type = entry.get('type', '')
                    msg = entry.get('message', {}) if isinstance(entry.get('message'), dict) else {}
                    content = msg.get('content', [])

                    # Skip noise entries - look for next meaningful one
                    if entry_type in ('progress', 'system', 'file-history-snapshot', 'queue-operation'):
                        continue

                    action_text = None

                    if entry_type == 'assistant' and isinstance(content, list):
                        for item in content:
                            if not isinstance(item, dict):
                                continue
                            item_type = item.get('type', '')

                            if item_type == 'thinking':
                                action_text = '💭 Thinking'
                                break
                            elif item_type == 'tool_use':
                                tool_name = item.get('name', '')
                                inp = item.get('input', {})
                                if tool_name in ('Read', 'Edit', 'Write'):
                                    fp = inp.get('file_path', '')
                                    short = fp.split('/')[-1] if '/' in fp else fp
                                    action_text = f"🔧 {tool_name}: {short}"
                                elif tool_name == 'Bash':
                                    desc = inp.get('description', '')
                                    if not desc:
                                        cmd = inp.get('command', '')[:120]
                                        desc = cmd
                                    action_text = f"⚡ Bash: {desc[:120]}"
                                elif tool_name in ('Grep', 'Glob'):
                                    pat = inp.get('pattern', '')[:80]
                                    action_text = f"🔍 {tool_name}: {pat}"
                                elif tool_name == 'Task':
                                    desc = inp.get('description', '')[:80]
                                    action_text = f"🚀 Agent: {desc}"
                                else:
                                    action_text = f"🔧 {tool_name}"
                                break
                            elif item_type == 'text':
                                text = item.get('text', '').strip()[:200]
                                if text:
                                    action_text = f"💬 {text}"
                                break

                    elif entry_type == 'user':
                        # Skip tool_result entries (noise - every tool call produces one)
                        # Only show actual user messages (new prompts)
                        is_tool_result = False
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get('type') == 'tool_result':
                                    is_tool_result = True
                                    break
                        if not is_tool_result:
                            action_text = '📩 User message'

                    if action_text:
                        # Dedup: skip if same action for same session
                        if last_agent_action.get(path_key) == action_text:
                            return True  # Deduped, not an error
                        last_agent_action[path_key] = action_text

                        event = MonitoringEvent(
                            priority=1,
                            event_type='agent',
                            branch=branch,
                            action='activity',
                            message=action_text,
                            level='info'
                        )
                        if _event_queue:
                            _event_queue.enqueue(event)
                        return True

                # All lines were progress/system - that's fine
                return True

            except Exception as e:
                logger.info(f"[monitor] JSONL parse error for {file_path.name}: {e}")
                return False

        def _handle_event(self, action, path_str):
            """Process file event and push to queue."""
            try:
                file_path = Path(path_str)

                # Check if should monitor this path
                if not should_monitor(file_path):
                    return

                # Detect branch from path
                branch = detect_branch_from_path(str(file_path))

                # Claude Code JSONL files: parse agent activity instead of raw modification
                if file_path.suffix == '.jsonl' and '.claude/projects/' in path_str:
                    # Distinguish subagents from main sessions
                    # Main: ~/.claude/projects/{hash}/{uuid}.jsonl
                    # Sub:  ~/.claude/projects/{hash}/{uuid}/subagents/agent-{id}.jsonl
                    if '/subagents/' in path_str:
                        branch = branch + ' agent'
                    if self._parse_agent_activity(file_path, branch):
                        return  # Parsed successfully, don't show raw event
                    # Parsing failed - fall through to show raw file event

                # Check if this file indicates a command (python3 direct calls)
                if action == 'modified' and file_path.name in COMMAND_INDICATOR_FILES:
                    cmd = COMMAND_INDICATOR_FILES[file_path.name]
                    dedup_key = f"{branch}:{cmd}"
                    if last_file_command.get(file_path.name) != dedup_key:
                        last_file_command[file_path.name] = dedup_key
                        cmd_event = MonitoringEvent(
                            priority=2,
                            event_type='command',
                            branch=branch,
                            action='executed',
                            message=cmd,
                            level='info'
                        )
                        if _event_queue:
                            _event_queue.enqueue(cmd_event)
                    # Still show the file event too (don't return)

                # Get priority
                priority_level = get_priority(file_path, action)

                # Build display name with context (branch-relative path or short path)
                display_name = file_path.name
                # Show parent dir for context when file is deep in a branch
                parts = file_path.parts
                # Find branch root and show relative path from there
                for i, part in enumerate(parts):
                    if part in ('apps', 'handlers', 'modules', 'docs', 'templates'):
                        display_name = '/'.join(parts[i:])
                        break

                # Create event
                event = MonitoringEvent(
                    priority=0,  # Will be set based on level
                    event_type='file',
                    branch=branch,
                    action=action,
                    message=f"{action.upper()}: {display_name}",
                    level=priority_level if priority_level in ['error', 'warning', 'info'] else 'info'
                )

                # Push to queue
                if _event_queue:
                    _event_queue.enqueue(event)
            except Exception as e:
                # Log error but don't crash the watcher
                logger.error(f"[monitor] Error handling {action} event for {path_str}: {e}")

    # Create observer and start watching
    # Watch from repo root (covers all modules)
    from aipass.prax.apps.handlers.config.load import _find_repo_root
    observer = Observer()
    handler = MonitoringFileHandler()
    watch_dir = _find_repo_root()
    observer.schedule(handler, str(watch_dir), recursive=True)
    observer.start()

    try:
        while _monitoring_active:
            time.sleep(0.1)
    finally:
        observer.stop()
        observer.join()


def _log_watcher_worker():
    """Log watcher thread - uses proper log_watcher.py with all improvements"""
    global _monitoring_active, _event_queue

    from aipass.prax.apps.handlers.monitoring.log_watcher import start_log_watcher, stop_log_watcher

    # Start the proper log watcher (has command detection, branch detection, message parsing)
    # Guard against None - should never happen since we initialize before starting threads
    if _event_queue is None:
        logger.error("[monitor] Event queue not initialized for log watcher")
        return
    observer = start_log_watcher(_event_queue)

    try:
        while _monitoring_active:
            time.sleep(0.1)
    finally:
        stop_log_watcher()


def _interactive_loop():
    """Interactive command loop - handles user input, or passive loop if no TTY"""
    global _monitoring_active, _filter_state, _event_queue

    # Non-TTY mode: no interactive input available, just keep alive
    if not sys.stdin.isatty():
        logger.info("[monitor] No TTY detected - running in passive mode (Ctrl+C to stop)")
        try:
            while _monitoring_active:
                time.sleep(0.5)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping monitoring...[/yellow]")
        return

    from aipass.prax.apps.handlers.monitoring.interactive_filter import (
        parse_command,
        apply_filter,
        get_help_text
    )

    while _monitoring_active:
        try:
            # Get user input
            user_input = input().strip()

            if not user_input:
                continue

            # Parse command
            cmd, cmd_args = parse_command(user_input)

            if not cmd:
                continue

            # Handle commands
            if cmd in ['quit', 'exit', 'q']:
                console.print("[yellow]Stopping monitoring...[/yellow]")
                break

            elif cmd == 'help':
                console.print(get_help_text())

            elif cmd == 'status':
                _print_status()

            elif cmd in ['watch', 'monitor', 'filter', 'verbosity', 'clear']:
                # Update filter state
                if _filter_state:
                    apply_filter(_filter_state, cmd, cmd_args)
                    console.print(f"[green]Filter updated: {cmd} {' '.join(cmd_args)}[/green]")

            else:
                console.print(f"[red]Unknown command: {cmd}[/red]")
                console.print("[dim]Type 'help' for available commands[/dim]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping monitoring...[/yellow]")
            break
        except EOFError:
            break


def _print_status():
    """Display current monitoring status"""
    global _filter_state, _event_queue

    console.print()
    console.print("[bold cyan]Monitoring Status:[/bold cyan]")
    console.print()

    if _filter_state:
        if _filter_state.show_all:
            console.print("  [yellow]Watching:[/yellow] All branches")
        elif _filter_state.watched_branches:
            console.print(f"  [yellow]Watching:[/yellow] {', '.join(sorted(_filter_state.watched_branches))}")
        else:
            console.print("  [yellow]Watching:[/yellow] None (quiet mode)")

        console.print(f"  [yellow]Show errors:[/yellow] {_filter_state.show_errors}")
        console.print(f"  [yellow]Show warnings:[/yellow] {_filter_state.show_warnings}")
        console.print(f"  [yellow]Show info:[/yellow] {_filter_state.show_info}")
        console.print(f"  [yellow]Verbosity:[/yellow] {_filter_state.verbosity}")

    if _event_queue:
        console.print(f"  [yellow]Queue size:[/yellow] {_event_queue.size()}")

    console.print()


# =============================================================================
# INTROSPECTION (Module metadata and handler connections)
# =============================================================================

def print_introspection():
    """Display module introspection - shows connected handlers and architecture"""
    console.print()
    console.print("[bold cyan]PRAX Monitor Module[/bold cyan]")
    console.print()
    console.print("[yellow]Purpose:[/yellow]")
    console.print("  Mission Control for autonomous branch monitoring")
    console.print("  Unified console for file changes, logs, and module activity")
    console.print()

    console.print("[yellow]Connected Handlers (apps/handlers/monitoring/):[/yellow]")
    console.print()
    console.print("  [cyan]1. unified_stream.py[/cyan]")
    console.print("     [dim]→ print_event() - Terminal output formatting[/dim]")
    console.print()
    console.print("  [cyan]2. branch_detector.py[/cyan]")
    console.print("     [dim]→ detect_branch_from_path() - Path-to-branch mapping[/dim]")
    console.print()
    console.print("  [cyan]3. interactive_filter.py[/cyan]")
    console.print("     [dim]→ FilterState, parse_command() - Runtime filtering[/dim]")
    console.print()
    console.print("  [cyan]4. monitoring_filters.py[/cyan]")
    console.print("     [dim]→ should_monitor(), get_priority() - Event filtering[/dim]")
    console.print()
    console.print("  [cyan]5. event_queue.py[/cyan]")
    console.print("     [dim]→ MonitoringEvent, MonitoringQueue - Event buffering[/dim]")
    console.print()
    console.print("  [cyan]6. module_tracker.py[/cyan]")
    console.print("     [dim]→ ModuleTracker - Module execution tracking[/dim]")
    console.print()
    console.print("  [cyan]7. file watcher (threaded)[/cyan]")
    console.print("     [dim]→ Real-time file change detection using watchdog[/dim]")
    console.print("     [green]STATUS: Active - monitors ECOSYSTEM_ROOT recursively[/green]")
    console.print()
    console.print("  [cyan]8. log monitor (threaded)[/cyan]")
    console.print("     [dim]→ Log stream processing from SYSTEM_LOGS_DIR[/dim]")
    console.print("     [green]STATUS: Active - watches *.log files for new entries[/green]")
    console.print()

    console.print("[dim]Run 'python3 monitor_module.py --help' for usage[/dim]")
    console.print()


# =============================================================================
# HELP OUTPUT (Drone-compliant command documentation)
# =============================================================================

def print_help():
    """Drone-compliant help output - command syntax and examples"""
    console.print()
    console.print("[bold cyan]PRAX Monitor - Unified Branch Monitoring[/bold cyan]")
    console.print()

    console.print("[yellow]Commands:[/yellow]")
    console.print()
    console.print("  [cyan]monitor[/cyan]")
    console.print("    Start monitoring all branches (quiet mode)")
    console.print()
    console.print("  [cyan]monitor all[/cyan]")
    console.print("    Explicit all-branches monitoring")
    console.print()
    console.print("  [cyan]monitor [branches][/cyan]")
    console.print("    Monitor specific branches (comma-separated)")
    console.print("    Example: monitor seed,cli,flow")
    console.print()

    console.print("[yellow]Interactive Mode Commands:[/yellow]")
    console.print()
    console.print("  [cyan]help[/cyan]          Show available commands")
    console.print("  [cyan]status[/cyan]        Display current monitoring state")
    console.print("  [cyan]filter [branches][/cyan]  Adjust branch filter")
    console.print("  [cyan]quit/exit[/cyan]     Stop monitoring")
    console.print()

    console.print("[yellow]Examples:[/yellow]")
    console.print()
    console.print("  [dim]# Monitor all branches[/dim]")
    console.print("  $ prax monitor")
    console.print()
    console.print("  [dim]# Monitor specific branches[/dim]")
    console.print("  $ prax monitor seed,cli,flow")
    console.print()
    console.print("  [dim]# Standalone execution[/dim]")
    console.print("  $ python3 monitor_module.py")
    console.print()


# =============================================================================
# MAIN BLOCK (Standalone execution support)
# =============================================================================

if __name__ == "__main__":
    # Show introspection when run without arguments
    if len(sys.argv) == 1:
        print_introspection()
        sys.exit(0)

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="PRAX Unified Monitoring - Mission Control",
        add_help=False
    )
    parser.add_argument('--help', action='store_true', help='Show help message')
    parser.add_argument('--introspect', action='store_true', help='Show module introspection')
    parser.add_argument('branches', nargs='?', help='Branches to monitor (comma-separated)')

    args = parser.parse_args()

    # Handle flags
    if args.help:
        print_help()
        sys.exit(0)

    if args.introspect:
        print_introspection()
        sys.exit(0)

    # Prepare arguments for handle_command
    cmd_args = []
    if args.branches:
        cmd_args = [args.branches]

    # Execute monitor command
    handled = handle_command('monitor', cmd_args)
    sys.exit(0 if handled else 1)
