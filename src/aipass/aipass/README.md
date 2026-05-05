# AIPASS

**Purpose:** The friendly front door — concierge, librarian, first-run guide
**Module:** `aipass.aipass`
**Created:** 2026-04-16
**Status:** Under construction (gitignored until Phase 8 reveal, DPLAN-0136)

---

## Overview

### What I Do

I am the concierge of AIPass. New users land with me. I greet them, walk them through setup, answer how-things-work questions, and hand them off to their chosen CLI tool. I am also the librarian — I can read any branch, inspect any README, explain any pattern. I do not build.

Drone is the engine. I am the front door.

### How I Work

- **Entry Point:** `apps/aipass.py` — thin CLI dispatch
- **Pattern:** Subcommand routing — `help`, `doctor`, `init`, `profile`
- **Restrictions:** Read-only by design. No writes outside my own `.trinity/`. No git. No real dispatches.

---

## Architecture

```
aipass/
├── apps/
│   ├── aipass.py         # Entry point — subcommand dispatch
│   ├── modules/          # doctor, help_chat, init_flow, handoff, profile
│   ├── handlers/         # system_detect, ping_sweep, readme_map, ui
│   └── plugins/          # Extensions
├── docs/
├── tests/
├── .trinity/
│   ├── passport.json     # Identity — concierge, read-only
│   ├── local.json        # Session history + user profile + setup_progress
│   └── observations.json # Patterns across users
└── README.md
```

---

## Commands

```
aipass              # Help banner
aipass help [Q]     # Chatbot Q&A — "how does drone work?"
aipass doctor       # System health — aggregates seedgo, pytest, registry, hooks
aipass init         # Guided 12-stage setup for new users (resumable)
aipass profile      # Show/edit what I remember about you
aipass --version
```

---

## Integration Points

### Depends On

- `@drone` — routing
- `@seedgo` — audit aggregation
- `@spawn` — creating the user's first agent
- `@flow` — testing plan lifecycle (open/close empty plans)
- `@ai_mail` — test-convention emails (no real dispatch)
- `@prax` — health signals for doctor
- `pytest` — test runner aggregation
- External CLIs — Claude Code / Codex / Gemini (handoff targets)

### Provides To

Nothing in AIPass depends on me. This is by design — I can be removed, replaced, or rebuilt without ripple. One-way arrow.

My direct consumers are **humans** — new users, curious explorers, and anyone who'd rather ask a concierge than read docs.

---

## Build Plan

See `devpulse/DPLAN-0136`. Nine phases:

0. Scaffolding (spawn) ✓
1. `aipass doctor`
2. `aipass help`
3. `aipass init`
4. CLI handoff (tmux / wt.exe)
5. Repo README flip back to project-focused
6. pip entry point wiring
7. Retire cli branch's `aipass init`
8. Gitignore removal — public reveal
9. Optional: VS Code auto-refresh
