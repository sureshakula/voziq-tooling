[← Back to AIPass](../../../README.md)

# PRAX

**Purpose:** System-wide logging, real-time monitoring, and dashboard for AIPass.
**Module:** `aipass.prax`
**Last Updated:** 2026-04-07

---

## Overview

Prax auto-routes log output from any module to per-module log files and provides a live monitoring console (Mission Control) that shows file changes, log events, and command execution across all branches. Monitors Claude Code, Codex, and Gemini CLI sessions.

## Commands

```bash
drone @prax monitor run                         # Launch Mission Control
drone @prax status                              # System health status
drone @prax log-audit audit                     # Audit log file sizes
drone @prax dashboard                           # Show dashboard
drone @prax --help                              # Full help
```

## Usage

### Logging

**Canonical import (use this):**

```python
from aipass.prax import logger

logger.info("Processing started")
logger.warning("Disk usage high")
logger.error("Connection failed")
```

This is Pattern A — the recommended way for all branches. Logs auto-route via two-tier placement: `system_logs/<branch>_<module>.log` (central aggregation) and `<branch>/logs/` (branch-local). No configuration needed — prax detects the caller via stack introspection.

For prax handlers that need to bypass the event pipeline (watchdog threads, import-chain files):

```python
from aipass.prax.apps.modules.logger import get_direct_logger

logger = get_direct_logger()
logger.info("Direct log entry")
```

### Mission Control

Real-time monitoring console for watching system activity across all branches and CLI tools.

```bash
drone @prax monitor run
```

Features:
- File changes, log events, drone commands, agent activity — all in one console
- **Caller attribution** — shows `CALLER → TARGET` for drone commands
- **Model tags** — shows `[BRANCH/model]` (e.g., `[DEVPULSE/opus]`, `[DEVPULSE/gpt-5.4]`)
- **Multi-CLI** — monitors Claude Code (JSONL), Codex (JSONL), Gemini (JSON) sessions
- **Polling fallback** — when inotify is exhausted, falls back to PollingObserver automatically
- **Interactive filtering** *(not operational)* — `watch`, `filter` commands are deferred

Interactive commands inside the monitor:

```
help              # Show available commands
status            # Display current monitoring state
quit/exit         # Stop monitoring
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `drone @prax monitor run` | Launch Mission Control |
| `drone @prax monitor` | Show monitor introspection |
| `drone @prax status` | Show system status (modules, loggers, watcher state) |
| `drone @prax status sync` | Sync STATUS.md from all branch STATUS.local.md |
| `drone @prax log-audit audit` | Audit log file sizes and health |
| `drone @prax log-audit enforce` | Truncate oversized logs |
| `drone @prax dashboard` | Show system dashboard |
| `drone @prax dashboard refresh --all` | Refresh dashboard data from centrals |

## Architecture

```
prax/
├── apps/
│   ├── prax.py                    # Entry point (CLI)
│   ├── modules/
│   │   ├── logger.py              # SystemLogger (public API)
│   │   ├── monitor.py             # Mission Control
│   │   ├── dashboard.py           # System dashboard
│   │   ├── status.py              # System status / STATUS sync
│   │   └── log_audit.py           # Log file audit
│   └── handlers/
│       ├── central/               # Central file reader
│       ├── config/                # Configuration loading
│       ├── dashboard/             # Dashboard refresh and operations
│       ├── discovery/             # Module scanning and filtering
│       ├── logging/               # Log setup, rotation, introspection
│       ├── monitoring/            # Event queue, branch detection, stream output
│       ├── registry/              # Module registry management
│       ├── status/                # STATUS sync handler
│       └── watcher/               # File and log watchers
├── templates/                     # Dashboard templates
├── tests/                         # Test suite (374 tests)
└── tools/                         # Standalone utilities (inbox_watchdog.py)
```

## How It Works

1. **Auto-routing** — When any module calls `logger.info()`, prax inspects the call stack to identify the caller and routes the log entry to the appropriate file.
2. **Two-tier logging** — Each log entry goes to both `system_logs/` (central aggregation) and `<branch>/logs/` (branch-local), both with rotation.
3. **Mission Control** — A multi-threaded monitoring console (display, file watcher, log watcher). Falls back to polling when inotify is exhausted. Shows caller attribution and model tags.
4. **Multi-CLI monitoring** — Watches Claude Code JSONL, Codex JSONL, and Gemini JSON session files for agent activity (thinking, tool use, responses).
5. **Dashboard** — Aggregates data from central files and branch status into per-branch dashboard views.

---

## Integration Points

### Depends On
- `aipass.cli` — Console output, headers, success/error formatting
- `aipass.drone` — Caller attribution via `[CALLER:BRANCH]` log markers
- Python stdlib (`pathlib`, `importlib`, `argparse`, `logging`)
- `watchdog` — File system monitoring (inotify + polling fallback)

### Provides To
- All 11 branches — Unified logging via `from aipass.prax import logger`
- All branches — Real-time monitoring via Mission Control
- System — STATUS.md sync, dashboard infrastructure

---

*Last Updated: 2026-04-07*

---
[← Back to AIPass](../../../README.md)
