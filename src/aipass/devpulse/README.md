[← Back to AIPass](../../../README.md)

# DevPulse

> Orchestration hub for AIPass. Plans, coordinates, dispatches, and builds its own modules.

DevPulse is the user's primary AI collaborator. It designs, plans, debugs, and coordinates the 12 branches. Builds its own modules directly (watchdog, feedback, json_handler). Ventures into other branches to investigate, debug, and fix small bugs. Delegates heavy multi-file builds to sub-agents via dispatch.

## Start here

| You want to | Read |
|---|---|
| Install, update, uninstall, or troubleshoot | [SETUP.md](SETUP.md) |
| What's happening right now | [STATUS.local.md](STATUS.local.md) |
| Identity, memory, session history | [`.trinity/`](.trinity/) |
| Diagnostic scanners | [`tools/`](tools/) |
| Active plans | `drone @flow list open` |

## Invoke

```bash
cd src/aipass/devpulse
claude
```

Say "hi" and DevPulse picks up where the last session left off.

## Role in one line

The user's primary AI collaborator — designs, orchestrates, and builds own modules. Delegates heavy multi-file builds to sub-agents via dispatch.

## Architecture

```
src/aipass/devpulse/
├── .trinity/                    # Identity & memory
├── .aipass/                     # Branch prompt
├── .ai_mail.local/              # Mailbox
├── apps/
│   ├── devpulse.py              # Entry point — auto-discovers modules
│   ├── modules/
│   │   ├── feedback.py          # Personal feedback mailbox routing
│   │   └── watchdog.py          # Directed wake system routing
│   └── handlers/
│       ├── feedback/            # Feedback inbox, compose, storage
│       ├── json/                # JSON operation logging (json_handler)
│       └── watchdog/            # Agent, timer, schedule, registry handlers
├── tests/                       # 236 tests (watchdog + feedback + json + devpulse)
├── docs/                        # Transition notes, research
├── docs.local/                  # Local-only docs (gitignored)
└── STATUS.local.md              # Current work beacon
```

## Commands

Devpulse commands are accessed via `drone @devpulse <command>`:

- `watchdog agent @target` — monitor a dispatched agent until it finishes
- `watchdog timer <duration>` — wake after duration (5m, 30s, 2h, 1h30m)
- `watchdog timer start/stop <name>` — named duration tracking
- `watchdog schedule <HH:MM>` — wait until a specific time
- `watchdog status` — show active watchdogs
- `watchdog cancel <id>` — cancel a running watchdog
- `watchdog list` — list all watchdog entries
- `feedback` — inbox summary
- `feedback inbox` — list all feedback messages
- `feedback view <id>` — read a message
- `feedback reply <id> "msg"` — reply to sender
- `feedback send "subject" "body"` — receive feedback from another agent

## Integration Points

### Depends On
drone (routing), prax (logging), cli (display), ai_mail (dispatch), seedgo (audits), flow (plans)

### Provides To
All branches via dispatch orchestration. Watchdog monitoring for any dispatched agent. Feedback channel for cross-project communication.

*Last Updated: 2026-05-15*

---

[← Back to AIPass](../../../README.md)
