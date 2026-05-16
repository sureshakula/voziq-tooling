# Trigger Module Recon
**Date:** 2026-03-06

## Summary
Event orchestration hub with error management. 34 Python files. Operational but 1 hardcoded path + many Path.home() hits.

## Structure
```
trigger/
├── apps/
│   ├── trigger.py            # Entry point (auto-discovery)
│   ├── config.py             # TRIGGER_ROOT, AIPASS_PKG_ROOT
│   ├── modules/
│   │   ├── core.py           # Event bus (Trigger class: fire/on/off)
│   │   ├── errors.py         # Error registry management
│   │   ├── medic.py          # Medic toggle (on/off/mute/unmute)
│   │   ├── branch_log_events.py  # Branch log watcher
│   │   └── log_events.py    # System log watcher
│   ├── handlers/
│   │   ├── error_registry.py # Fingerprinting, circuit breaker, rate limiting
│   │   ├── medic_state.py    # Medic config persistence
│   │   ├── log_watcher.py    # Log monitoring
│   │   ├── watchers/         # Watchdog file monitoring
│   │   ├── events/           # 12 event handlers
│   │   │   ├── registry.py   # Central handler registration
│   │   │   ├── error_detected.py  # Medic v2 error dispatch
│   │   │   ├── error_logged.py    # DEPRECATED legacy handler
│   │   │   └── startup, cli, memory, plan_file, bulletin, warning
│   │   └── json/
├── trigger_json/
│   └── trigger_data.json     # Error catchup state (MODIFIED, unstaged)
└── tests/                    # Empty
```

## Key Features
- **Event Bus:** Deferred queue prevents recursion during nested events
- **Medic v2:** Circuit breaker (closed/open/half_open) + exponential backoff per error fingerprint
- **Error Registry:** SHA1 fingerprinting, dedup, rate limiting, dispatch gating
- **Auto-healing:** Dispatches fix-it emails via AI_Mail when errors detected

## Commands
```
drone @trigger errors list|detail|suppress|resolve|stats|circuit-breaker
drone @trigger medic on|off|status|mute|unmute
```

## Path Debt
- **CRITICAL:** `plan_file.py:42` — `ECOSYSTEM_ROOT = Path("/home/aipass")` (hardcoded)
- **HIGH:** 8+ event handlers use `AIPASS_HOME = Path.home()` at module level
- Shebang debt across all files

## Modified File
`trigger_data.json` — error catchup state with 7 processed hashes, indicates active error processing from Dev-Pass side

## Notes
- Inotify exhaustion issue documented and resolved (lazy-start disabled)
- error_logged.py DEPRECATED but kept for backward compat
- Handlers can't import Prax logger directly (causes event recursion) — use get_direct_logger()
