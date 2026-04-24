[← Back to AIPass](../../../README.md)

# DevPulse

> Orchestration hub for AIPass. Plans, coordinates, dispatches. Never the builder.

DevPulse is the central coordination branch. It does not ship features of its own — it works with the user on design, dispatches real work to branch specialists, tracks plans and memory, and keeps the system moving. If a task belongs to another branch, DevPulse emails that branch and waits for the reply.

## Start here

| You want to | Read |
|---|---|
| Install, update, uninstall, or troubleshoot | [SETUP.md](SETUP.md) |
| What's happening right now | [STATUS.local.md](STATUS.local.md) |
| Identity, memory, session history | [`.trinity/`](.trinity/) |
| Diagnostic scanners | [`tools/`](tools/) |
| Branch health audits | [`branch_audits _only/`](branch_audits%20_only/) |
| Active plans | `drone @flow list open` |

## Invoke

```bash
cd src/aipass/devpulse
claude
```

Say "hi" and DevPulse picks up where the last session left off.

## Role in one line

Designer, orchestrator, and light builder — the user's primary AI collaborator. Builds its own things directly (modules, plans, memories, design docs). Ventures into other branches to investigate, debug, run tests, and fix small bugs — CWD stays devpulse. Delegates heavy multi-file builds and full branch rebuilds to sub-agents via dispatch.

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
│       └── watchdog/            # Agent, timer, schedule, registry handlers
├── tests/                       # 130+ tests (watchdog + feedback)
├── docs/                        # Transition notes, research
├── docs.local/                  # Local-only docs (gitignored)
└── STATUS.local.md              # Current work beacon
```

## Commands

Devpulse commands are accessed via `drone @devpulse <command>`:

- `watchdog agent @target` — monitor a dispatched agent until it finishes
- `watchdog timer <seconds>` — simple countdown timer
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

*Last Updated: 2026-04-24*

---

[← Back to AIPass](../../../README.md)
