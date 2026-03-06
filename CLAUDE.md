# AIPass Startup Protocol

Startup for AI agents working in the AIPass public repo.

## CRITICAL: Startup vs Task Mode

**Startup protocol ONLY triggers on these EXACT greetings (nothing else):**
- `hi`, `hello`, `yo`, `hey`, `sup`, `good morning`, `good evening`, `what's up`

**Everything else is a TASK - execute directly, NO startup:**
- `review README` → just read and review the README
- `fix the bug` → just fix the bug
- ANY prompt that contains an action verb = TASK, not greeting

## Session Entry
Start sessions with `hi`, `hello`, `yo` to trigger standard startup.

## On Startup - Read These
At your directory level (CWD is your location):
```
.trinity/passport.json       # Identity and role
.trinity/local.json          # Session history, current work
.trinity/observations.json   # Collaboration patterns
DASHBOARD.local.json         # System status
README.md                    # Branch documentation
```

## After Reading Memories
1. **Git status** - Run `git status` in your branch directory
2. **Check system** - `drone systems` (verify modules are registered)
3. **Seedgo verify** - `drone @seedgo verify` (standards packs healthy)
4. **Verify README.md** - Does it reflect current state? Update if stale.
5. **Check active tasks** - What's in local.json today_focus?
6. **Review recent sessions** - Context from last few sessions

## Structure
- `src/aipass/` — All modules live here
- 10 modules: drone, seedgo, prax, cli, flow, ai_mail, api, trigger, spawn, devpulse
- 3-layer architecture per module: `apps/branch.py` (entry) + `apps/modules/` (logic) + `apps/handlers/` (impl)
- `AIPASS_REGISTRY.json` — Branch registry at repo root

## Commands
```
drone systems                    # List registered modules/branches
drone @seedgo verify             # Verify standards packs installed
drone @seedgo audit aipass       # Run standards audit on repo
drone @module --help             # Module help
```

## Conventions
- All imports use pip namespace: `from aipass.{module}.apps.modules...`
- No hardcoded paths — use `Path(__file__).parents[N]` or registry lookups
- Tests: `pytest` from repo root
- `pyproject.toml` defines CLI entry points: `drone`, `seedgo`
- No paths referencing `/home/aipass/` — that's Dev-Pass, not AIPass

## Directory Structure
All modules follow 3-layer architecture:
```
apps/
├── branch.py      # Entry point
├── modules/       # Business logic orchestration
└── handlers/      # Implementation details
```

## DevPulse
DevPulse (`src/aipass/devpulse/`) is the orchestration hub for this repo. It coordinates work across modules, tracks status, and manages dev notes. It is to AIPass what DEV_CENTRAL is to Dev-Pass.

## Core Principles
- Code is truth - if it doesn't run, it's not real
- Test in Docker for isolation verification
- Never bare imports - always `from aipass.{module}...`
