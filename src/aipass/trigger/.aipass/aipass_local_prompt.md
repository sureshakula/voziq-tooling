# TRIGGER Branch-Local Context

## Role
Event bus and error dispatch for AIPass. I detect errors, fingerprint them, gate dispatch, and notify affected branches.

## Architecture
```
trigger.py (entry point — auto-discovers modules/)
├── core.py        → Event bus: fire/on/off/status (14 events, 14 handlers)
├── errors.py      → Error registry CLI: list/detail/suppress/resolve/stats/circuit-breaker
├── medic.py       → Medic toggle: on/off/status/mute/unmute
├── log_events.py  → Centralized log watcher (system_logs/)
└── branch_log_events.py → Branch log watcher (*/logs/*.log)

handlers/
├── error_registry.py  → SHA1 fingerprinting, circuit breaker, exponential backoff
├── error_reporter.py  → report_error() public API + source fix email pipeline
├── medic_state.py     → Persistence (trigger_config.json)
├── log_watcher.py     → Watchdog-based branch log watcher with position tracking
├── events/            → 12 event handlers (registry.py wires them on first fire)
└── watchers/          → Centralized log watcher (system_logs/)
```

## Key Commands
```
drone @trigger fire <event> [key=val]    # Fire event
drone @trigger list                      # Show registered handlers
drone @trigger errors list               # View error registry
drone @trigger errors stats              # Registry + circuit breaker stats
drone @trigger medic status              # Medic state
drone @trigger medic on|off              # Toggle dispatch
drone @trigger medic mute|unmute @branch # Per-branch control
drone @trigger branch_log_events status  # Log watcher state
```

## Dispatch Pipeline (8 gates)
1. Medic enabled → 2. Branch not muted → 3. Count >= 2 → 4. Not DEV_CENTRAL
5. Branch in registry → 6. Circuit breaker closed → 7. Per-fingerprint backoff → 8. Rate limit

## Critical Files
- `trigger_json/trigger_config.json` — medic state, circuit breaker, muted branches
- `trigger_json/error_registry.json` — all tracked errors
- `trigger_data.json` — log watcher positions, dedup hashes

## Integration Points
- **ai_mail**: `deliver_email_to_branch()` for dispatch and source fix emails
- **prax**: Logger (`from aipass.prax import logger`), prax monitor for live log watching
- **AIPASS_REGISTRY.json**: Branch validation for dispatch targets

## Rules
- Never fix errors in other branches — detect and dispatch, they fix their own
- Hot path logging is poison — event bus fire() must be silent by default
- Error registry is operational, not archival — clear resolved entries regularly
