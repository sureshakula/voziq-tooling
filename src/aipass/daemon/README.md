[← Back to AIPass](../../../README.md)

# DAEMON

**Purpose:** Cron-triggered task scheduler with plugin system. Routes commands to modules for scheduled tasks, activity reports, action management, and status digests.
**Module:** `aipass.daemon`
**Created:** 2026-03-07
**Citizen Class:** builder
**Last Updated:** 2026-04-07

---

## Overview

Builder citizen -- full 3-layer architecture with identity and memory. DAEMON serves as the background orchestration branch: it discovers modules at startup, routes CLI commands to them, and provides introspection and help output via Rich console.

### What I Do
- Route CLI commands to discovered modules (update, schedule, activity_report, actions)
- Manage scheduled follow-ups with CRUD operations and due-date processing
- Generate activity reports across all branches (24h summary, detailed, per-branch)
- Run action registry (list, toggle, set reminder/schedule, migrate plugins)
- Auto-discover and dispatch plugins (community_rotation, daily_audit, heartbeat)
- Detect red flags (code changes without memory updates, stale branches)
- Produce status digests (inbox, actionable items, escalations)

---

## Architecture

```
daemon/
├── __init__.py
├── README.md
├── DASHBOARD.local.json
├── apps/
│   ├── daemon.py              # Entry point (CLI) — module discovery + command routing
│   ├── daemon_wakeup.py       # Wakeup / cron trigger
│   ├── scheduler_cron.py      # Cron scheduler
│   ├── modules/
│   │   ├── update.py          # Status digest module — summarizes DAEMON activity
│   │   ├── schedule.py        # Scheduled follow-ups — fire-and-forget task management
│   │   ├── activity_report.py # Branch activity report generator
│   │   ├── actions.py         # Action registry CLI — list, toggle, info, reminders
│   │   ├── scheduler_ops.py   # Scheduler cron operations facade
│   │   └── wakeup_ops.py      # Wake-up cron operations facade
│   ├── handlers/
│   │   ├── actions/
│   │   │   └── actions_registry.py   # Action registry implementation
│   │   ├── json/
│   │   │   └── json_handler.py       # JSON data operations
│   │   ├── monitoring/
│   │   │   ├── activity_collector.py  # Collects branch activity data
│   │   │   ├── memory_health.py       # Memory health checks
│   │   │   └── red_flag_detector.py   # Detects anomalies / red flags
│   │   ├── schedule/
│   │   │   ├── task_registry.py       # Task registry for scheduled items
│   │   │   └── .archive/             # assistant_notifier, telegram_notifier (archived)
│   │   ├── telegram/                  # ARCHIVED — moving to skills system
│   │   │   └── .archive/             # assistant_chat (archived)
│   │   └── update/
│   │       └── data_loader.py         # Data loading for status digests
│   ├── extensions/             # Extension point for additional capabilities
│   ├── json_templates/         # JSON template definitions
│   └── plugins/
│       ├── community_rotation.py      # Community rotation plugin
│       ├── daily_audit.py             # Daily audit plugin
│       ├── heartbeat.py               # Heartbeat / liveness plugin
│       └── .archive/                  # botfather_reminder, devpulse_monitor (archived)
├── daemon_json/                # JSON tracking data
├── docs/                       # Documentation
├── dropbox/                    # Incoming file drops
├── logs/                       # Prax log output
├── tools/                      # Branch verification utilities
└── tests/                      # Test suite
```

---

## Commands / Usage

```bash
drone @daemon                       # Show discovered modules (introspection)
drone @daemon --help                # Rich-formatted help with all commands
drone @daemon --version             # Print version

drone @daemon update                # Status digest — inbox, session info, escalations (partial — reads stale data paths)
drone @daemon schedule list         # List pending scheduled tasks
drone @daemon schedule create "task" --due 7d --to @branch
drone @daemon schedule run-due      # Fire all due tasks (sends emails)
drone @daemon activity              # Quick 24h activity summary
drone @daemon activity-report       # Full detailed report (--json for raw)
drone @daemon branch-health BRANCH  # Single branch deep dive
drone @daemon actions list          # Action registry
drone @daemon actions <id> on/off   # Toggle action
drone @daemon actions set reminder 7d "msg" --to @branch
drone @daemon actions set schedule @branch "prompt" daily 04:00
drone @daemon install-timer           # Install + enable systemd user timer
drone @daemon uninstall-timer         # Stop + remove systemd user timer
```

Each module accepts `--help` for module-specific usage:
```bash
drone @daemon <command> --help
```

---

## Modules

| Module | Description | Status |
|--------|-------------|--------|
| `update` | Status digest of DAEMON activity | *(partial)* — reads inbox/sessions but data_loader paths return empty |
| `schedule` | Fire-and-forget scheduled follow-ups and task management | Operational |
| `activity_report` | Branch activity reports: `activity`, `activity-report`, `branch-health` | Operational |
| `actions` | Action registry CLI — list, toggle, info, set reminder, set schedule, migrate | Operational |
| `scheduler_ops` | Scheduler cron operations facade for scheduler_cron.py | Operational |
| `wakeup_ops` | Wake-up cron operations facade for daemon_wakeup.py | Operational |
| `timer_install` | Idempotent systemd user timer installer for daemon scheduler | Operational |
| `run` | Decentralized scheduler tick: discover .daemon/ jobs, fire due ones | Operational |

---

## Scheduling Jobs

Each branch owns its schedule at `src/aipass/<branch>/.daemon/schedule.json`. The daemon discovers and fires — branches define their own jobs.

### Job file schema

```json
{
  "version": 1,
  "branch": "@<branch>",
  "jobs": [
    {
      "id": "my-job",
      "enabled": true,
      "schedule": { "type": "interval", "interval_minutes": 30 },
      "wake": { "fresh": true, "model": "haiku" },
      "prompt": "Do something, then STOP."
    }
  ]
}
```

### Schedule types

| Type | Fields | Due when |
|------|--------|----------|
| `interval` | `interval_minutes: N` | Elapsed >= N since last_run. Fires immediately if never run. |
| `daily` | `time: "HH:MM"` | Within +/-15 min of target time, once per day. |
| `hourly` | `time: "M"` (minute) | Within +/-15 min of target minute, once per hour. |
| `once` | `due_date: "YYYY-MM-DD"` | Date <= today, then marks completed. |

### Wake options

- `fresh` (bool) — start a fresh Claude session (true) or resume (false)
- `model` (string, optional) — `"haiku"` or `"sonnet"` recommended for light wakes

### Staggering

No native offset field. To stagger jobs, seed different `last_run` values in `daemon_json/daemon_runstate.json`.

---

## Integration Points

### Depends On
- `rich` -- Console output and formatted display
- Python stdlib (`sys`, `typing`, `logging`)

### Provides To
- All modules — background task scheduling, activity monitoring, action tracking
- Plugins — extensible plugin system for recurring tasks (community_rotation, daily_audit, heartbeat)
- Note: Telegram handlers archived — moving to skills system. See `apps/handlers/telegram/.archive/`

---

## Plugins

| Plugin | Target | Schedule | Status |
|--------|--------|----------|--------|
| `community_rotation` | @rotating | every 4h | Operational — requires AIPASS_WAKE_SCRIPT env var |
| `daily_audit` | @seed | daily 04:00 | *(not operational)* — targets @seed (renamed to @seedgo) |
| `heartbeat` | @vera | every 4h | *(not operational)* — @vera not in branch registry |

---

## Known Issues

- `update` command shows empty data (0 sessions, no focus) — data_loader reads from different paths than .trinity/local.json
- `daily_audit` plugin targets `@seed` which was renamed to `@seedgo`
- `heartbeat` plugin targets `@vera` which is not registered in the branch registry
- All plugins require `AIPASS_WAKE_SCRIPT` env var to dispatch — without it, plugins discover but can't execute
- `drone @daemon activity_report` (underscore) fails — use `activity`, `activity-report`, or `branch-health` instead

---

## Identity

- **Passport:** `.trinity/passport.json`
- **Session History:** `.trinity/local.json`
- **Observations:** `.trinity/observations.json`
- **Branch Prompt:** `.aipass/branch_system_prompt.md`

---

## Test Suite

- **448 tests** across 19 test files
- 8/8 modules covered, 43/51 public functions tested
- Seedgo audit: **100%** across all standards

*Last Updated: 2026-04-07*

---
[← Back to AIPass](../../../README.md)
