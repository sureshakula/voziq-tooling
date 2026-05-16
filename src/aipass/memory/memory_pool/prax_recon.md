# Prax Module Recon
**Date:** 2026-03-06

## Summary
Logging and monitoring system. **Import works** (lazy init). 15 Path.home() hits, 4 at import-time. 71 Python files.

## Public API
```python
from aipass.prax import logger  # SystemLogger instance
logger.info("message")  # Auto-routes to calling module's log file
```

## Structure
```
prax/
├── __init__.py               # Exports: system_logger as logger
├── apps/
│   ├── prax.py               # Entry point (202 lines)
│   ├── modules/
│   │   ├── logger.py         # SystemLogger class (268 lines) - THE public API
│   │   ├── init_module.py    # Initialize logging
│   │   ├── shutdown_module.py
│   │   ├── monitor_module.py # Mission Control (595 lines)
│   │   ├── status_module.py  # System status display
│   │   └── 5 more modules
│   ├── handlers/             # 52 files
│   │   ├── logging/          # 12 files - setup, direct, terminal, rotation
│   │   ├── monitoring/       # 14 files - events, telegram, branch detection
│   │   ├── discovery/        # 3 files - module scanning
│   │   ├── registry/         # 7 files - AIPASS registry
│   │   ├── config/           # 2 files - load.py (CRITICAL)
│   │   ├── json/             # 5 files
│   │   └── watcher/, dashboard/
└── tests/
```

## Path.home() Debt: 15 instances
**Import-time (CRITICAL):**
- config/load.py:51 — `SYSTEM_LOGS_DIR = Path.home() / "system_logs"` + mkdir at line 55
- log_watchdog.py:44 — SYSTEM_LOGS_DIR at import time
- agent_status_writer.py:45 — AIPASS_REGISTRY at import time [stale: was BRANCH_REGISTRY]
- registry/reader.py:34 — AIPASS_REGISTRY_PATH at import time [stale: was BRANCH_REGISTRY_PATH]

**Function-level:**
- monitoring/branch_detector.py:58, 191
- monitoring/telegram_command_bot.py:68 (module-level)
- monitor_module.py:161, 597
- logging/setup.py:125, direct.py:144

## Key Finding
`from aipass.prax import logger` **works** because logger.py uses lazy init. But deeper imports into handlers (config/load.py) crash due to Path.home() mkdir at import time.

## Note
- Circular dependency with CLI properly handled (logger doesn't import CLI)
- File watcher has try/except for inotify limit (graceful degradation)
- `logger.info('test')` produces no visible terminal output (may need config check)
