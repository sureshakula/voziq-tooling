# DevPulse

**Purpose:** Orchestration hub for the AIPass ecosystem
**Module:** `aipass.devpulse`
**Status:** Active

---

## Overview

DevPulse is the central coordination branch for AIPass. It plans, delegates, and tracks work across all 10 branches in the ecosystem. Think of it as the project manager — it doesn't build modules itself, but dispatches work to branch agents, monitors results, and maintains system-wide visibility.

### What DevPulse Does
- **Cross-branch orchestration** — Dispatch tasks to branches via AI Mail + wake
- **System-wide planning** — Create and manage flow plans (FPLANs) for multi-phase work
- **Status tracking** — Dashboard, dev notes, session history
- **Architecture discussions** — Work with the user on design decisions
- **Agent coordination** — Deploy sub-agents in parallel for research and builds

---

## Managed Directory — `src/aipass/`

DevPulse orchestrates all branches under `src/aipass/`:

```
src/aipass/
├── drone/          # Command routing — @ resolution, branch dispatch
├── seedgo/         # Standards & compliance — audits, checkers, packs
├── prax/           # Logging system — stack introspection, dual routing
├── cli/            # CLI framework — argument parsing, command registry
├── flow/           # Plan management — FPLANs, templates, tracking
├── ai_mail/        # Inter-branch comms — inbox, dispatch, wake
├── api/            # API layer — external interfaces
├── trigger/        # Event system — log watchers, event handlers
├── spawn/          # Branch lifecycle — create, update, delete, passport
├── devpulse/       # Orchestration hub (you are here)
├── daemon/         # Background scheduler — cron, plugins, monitoring
├── backup/         # Backup utilities
├── memory/         # Memory bank (planned)
└── __init__.py
```

**10 registered branches:** drone, seedgo, prax, cli, flow, ai_mail, api, trigger, spawn, devpulse

## DevPulse Architecture

```
devpulse/
├── .trinity/              # Identity + memory
│   ├── passport.json      # Branch identity
│   ├── local.json         # Session history + active tasks
│   └── observations.json  # Collaboration patterns
├── .aipass/               # AI context
│   └── branch_system_prompt.md
├── .spawn/                # Spawn metadata
├── docs/
├── tests/
└── README.md
```

DevPulse has no `apps/` directory — it's a **manager** branch, not a builder. It coordinates via dispatch and sub-agents rather than implementing code.

---

## Commands

```bash
# System status
drone systems                    # List all registered branches
drone @seedgo verify             # Verify standards packs
drone @seedgo audit aipass       # Run full standards audit

# Flow plans
drone @flow create . "Subject"              # Create plan (default template)
drone @flow create . "Subject" master       # Create master plan (multi-phase)
drone @flow list                            # List active plans
drone @flow close FPLAN-XXXX                # Close a plan

# Dispatch work
drone @ai_mail send @target "Subject" "Body" --dispatch
drone @ai_mail dispatch wake @target        # Wake branch agent
drone @ai_mail dispatch wake --fresh @target  # Fresh session

# Branch management
drone @spawn create <path>       # Create new branch from template
drone @spawn update @branch      # Update branch scaffold
drone @spawn delete @branch      # Archive + deregister branch
```

---

## Integration Points

### Depends On
- `aipass.prax` — Logging (all logging goes through prax)
- `aipass.ai_mail` — Inter-branch communication + dispatch
- `aipass.flow` — Plan creation and tracking
- `aipass.drone` — Command routing to all branches
- `aipass.spawn` — Branch lifecycle management
- `aipass.seedgo` — Standards verification

### Coordinates
- All 10 branches: drone, seedgo, prax, cli, flow, ai_mail, api, trigger, spawn, devpulse

---

## Role

DevPulse is a **manager** branch, not a builder. It delegates code tasks to sub-agents and branch agents. Its context window is reserved for coordination, planning, and architecture — not for reading and editing files across the codebase.
