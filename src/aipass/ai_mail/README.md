# AI_MAIL

**Purpose:** Inter-agent messaging for AIPass. File-based email system that lets agents send, receive, and process messages using `@branch` addresses. No SMTP, no external services — just JSON files and symbolic routing.
**Module:** `aipass.ai_mail`
**Created:** 2025-11-08
**Last Updated:** 2026-03-08

---

**Status:** Building. Core email workflow (send/inbox/reply/close) is functional. Dispatch system is working.

## Commands / Usage

```bash
drone @ai_mail send @target "Subject" "Body"   # Send inter-branch email
drone @ai_mail send @target "Subject" "Body" --dispatch  # Send task dispatch email
drone @ai_mail dispatch wake @target            # Wake a branch
drone @ai_mail dispatch wake --fresh @target    # Fresh wake (no context)
drone @ai_mail inbox                            # Check inbox
drone @ai_mail --help                           # Full help
```

## Email Lifecycle

Messages follow a 3-state model:

```
new → opened → closed
```

- **new** — Delivered to inbox, never viewed
- **opened** — Viewed by recipient, awaiting action
- **closed** — Replied or dismissed, archived automatically

## Dispatch System

The `--dispatch` flag marks emails for autonomous execution. A polling daemon watches inboxes and spawns agents to process dispatch emails automatically.

- Agents are ephemeral (wake, do work, exit)
- Safety limits: max turns per wake, max dispatches per branch per day
- PID-based locking prevents concurrent agents per branch
- Failed agents trigger bounce emails back to sender

## Architecture

Follows the standard AIPass 3-layer pattern:

```
ai_mail/
├── apps/
│   ├── ai_mail.py          # Entry point (auto-discovers modules)
│   ├── modules/
│   │   ├── email.py        # Send, inbox, view, reply, close, contacts
│   │   ├── dispatch.py     # Dispatch status, daemon, wake
│   │   └── branch_ping.py  # Branch health monitoring
│   └── handlers/
│       ├── email/           # Delivery, formatting, inbox ops, purge
│       ├── dispatch/        # Daemon, wake, monitoring
│       ├── registry/        # Branch registry read/update
│       └── users/           # Branch detection, config generation
```

## Integration Points

### Depends On
- `aipass.prax` — Logging via `system_logger`
- `aipass.cli` — Console output and display formatting
- `aipass.drone` — Command routing and `@branch` resolution
- Python stdlib (`pathlib`, `json`, `argparse`, `importlib`)

### Provides To
- All modules — inter-branch messaging (send/receive/reply/close)
- Dispatch system — autonomous task execution via `--dispatch` flag
- Branch contacts — address book for `@branch` routing

---

*Last Updated: 2026-03-08*
