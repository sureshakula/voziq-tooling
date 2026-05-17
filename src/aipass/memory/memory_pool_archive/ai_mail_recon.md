# AI Mail Module Recon
**Date:** 2026-03-06

## Summary
Inter-agent communication system. Well-architected but CRITICAL path debt (34 Path.home() hits).

## Structure
```
ai_mail/
├── apps/
│   ├── ai_mail.py            # Entry point (auto-discovers modules)
│   ├── modules/
│   │   ├── email.py          # Email workflow: send, inbox, view, reply, close, contacts
│   │   ├── dispatch.py       # Agent spawn: dispatch status, daemon, wake
│   │   └── branch_ping.py    # Memory health: ping, status, registry, thresholds
│   ├── handlers/
│   │   ├── email/            # delivery, inbox, format, lock_utils, purge, dashboard_sync
│   │   ├── dispatch/         # daemon, wake, status, pending_work
│   │   ├── registry/         # read, update, validate
│   │   ├── users/            # user detection, config, branch_detection
│   │   ├── persistence/      # json_ops, logging
│   │   ├── monitoring/       # errors, memory health
│   │   ├── central_writer/   # System-wide stats aggregation
│   │   ├── json/             # json_handler.py
│   │   └── json_utils/       # DUPLICATE json_handler.py
│   ├── plugins/
│   └── json_templates/
└── tests/                    # Empty (conftest.py only)
```

## Path.home() Debt: 34 instances (CRITICAL)
Key offenders:
- email.py:43 — `AIPASS_ROOT = Path.home() / "aipass_core"` [stale: aipass_core]
- central_writer.py:54-57 — 4 instances (AI_CENTRAL_DIR [stale: now ai_mail], AIPASS_REGISTRY [stale: was BRANCH_REGISTRY])
- dispatch/daemon.py — 4 instances
- dispatch/wake.py — 3 instances
- email/delivery.py:71 — hardcoded `Path("/home/aipass/BRANCH_REGISTRY.json")` [stale: now AIPASS_REGISTRY.json]
- registry/read.py:41 — hardcoded `Path("/home/aipass/BRANCH_REGISTRY.json")` [stale: now AIPASS_REGISTRY.json]
- 20+ files with hardcoded shebangs

## Integration Points
- Depends on: prax (logger), cli (console), trigger (events), spawn (agent spawning)
- Provides: inter-agent email, dispatch daemon, dashboard updates

## Working
- Email creation, formatting, send/inbox/reply/close workflows
- Dispatch system, daemon spawning, wake command
- Registry integration, branch detection
- Dashboard sync

## Broken
- 34 Path.home() instances block portability
- No .trinity files
- No tests
- Duplicate json handlers (json/ AND json_utils/)
- Hardcoded /home/aipass in delivery.py and registry/read.py
