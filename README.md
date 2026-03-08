[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

# AIPass

> **Building in public.** Active development — not a finished product. Expect breaking changes.

Orchestration framework for autonomous AI agent ecosystems. Command routing, symbolic addressing, standards enforcement, workflow management, and inter-agent messaging. Agents use `@branch` names that resolve at runtime instead of hard-coded paths. Each agent has persistent identity and memory via `.trinity/` files (passport, session history, observations).

## Quick Start

### 1. Install

```bash
git clone https://github.com/AIOSAI/AIPass.git
cd AIPass
./setup.sh
source .venv/bin/activate
```

`setup.sh` handles everything: creates the venv, installs the package, generates the branch registry (15 branches), bootstraps identity files (`.trinity/`, `.seedgo/`, `.ai_mail.local/`) for every branch, and installs Claude Code hooks. Idempotent — safe to re-run.

Verify:

```bash
drone systems       # Should show 15 branches
drone @seedgo verify # Should show 5/5 checks passed
```

### 2. Start a Session

AIPass is designed to be operated by AI agents via [Claude Code](https://docs.anthropic.com/en/docs/claude-code). The orchestration hub is **devpulse** — start there.

```bash
cd src/aipass/devpulse
claude --permission-mode bypassPermissions
```

Say `hi` to trigger the [startup protocol](#4-startup-protocol). The agent reads its identity and memory files, checks git status, verifies system health, and picks up where it left off. In a returning session, use `/resume` instead.

### 3. What You Get

After setup, every branch has:

```
.trinity/passport.json       # Identity (name, role, citizen class)
.trinity/local.json          # Session history (empty, ready to populate)
.trinity/observations.json   # Collaboration patterns (empty)
.seedgo/bypass.json          # Standards bypass config
.ai_mail.local/inbox.json    # Mailbox
```

The agent fills in its own memories as it works — session logs, learnings, observations. These grow over time and persist across sessions.

### 4. Startup Protocol

These greetings trigger the full startup sequence: `hi`, `hello`, `yo`, `hey`, `sup`, `good morning`, `good evening`, `what's up`. Everything else is treated as a direct task.

On startup the agent:
1. Reads `.trinity/passport.json` (identity), `local.json` (session history), `observations.json` (patterns)
2. Runs `git status`, `drone systems`, `drone @seedgo verify`
3. Checks active tasks and recent session context
4. Picks up work or waits for instructions

## Core Concepts

### Drone — Command Router

Everything goes through `drone`. It resolves `@branch` names to paths and routes commands.

```bash
drone @seedgo audit aipass    # Run standards audit
drone @seedgo verify          # Check seedgo health
drone @spawn --help           # Show help for a branch
drone systems                 # List all registered modules
```

In Python:

```python
from aipass.drone.apps.modules.resolver import resolve_branch
from aipass.drone.apps.modules.registry import load_registry

path = resolve_branch("@drone")   # Resolve @name to path
registry = load_registry()        # Load full branch registry
```

### Seedgo — Standards Enforcement

Standards-based code auditor. Checks are organized into packs — the built-in `aipass` pack has 21 standards covering imports, architecture, naming, error handling, logging, and more.

```bash
drone @seedgo verify          # Health check
drone @seedgo list            # Show installed standard packs
drone @seedgo audit aipass    # Run the aipass standards pack
seedgo checklist aipass file  # Check a single file
```

### Symbolic Addressing

All modules register in `AIPASS_REGISTRY.json`. Drone resolves `@name` to paths at runtime — no hard-coded paths between modules.

## Architecture

All modules follow a 3-layer pattern:

```
src/aipass/<module>/
├── apps/
│   ├── <module>.py    # Entry point (what drone routes to)
│   ├── modules/       # Business logic
│   └── handlers/      # Implementation details
```

**15 branches** — all under active development. Ported from a private predecessor project; not all modules are fully tested or wired up yet.

| Branch | Purpose |
|--------|---------|
| `drone` | Command routing, `@branch` resolution |
| `seedgo` | Standards enforcement, 21-standard audit pack |
| `prax` | Logging and monitoring (the only logger) |
| `cli` | Display formatting (Rich) |
| `flow` | Workflow and plan management (FPLAN lifecycle) |
| `ai_mail` | Inter-agent messaging, dispatch, wake |
| `spawn` | Branch lifecycle — create, update, delete |
| `trigger` | Event-driven automation, circuit breaker |
| `api` | LLM access via OpenRouter, key management |
| `backup` | Multi-mode backup (snapshot, versioned, Google Drive) |
| `daemon` | Background scheduler, cron, Telegram notifications |
| `memory` | Vector memory bank (ChromaDB, sentence-transformers) |
| `commons` | Social network for branches — posts, rooms, artifacts |
| `skills` | Capability framework — discoverable, executable skill units |
| `devpulse` | Orchestration hub (no code — coordination only) |

## Docker

```bash
docker build -t aipass-test .
docker run -d -p 8080:8080 --name aipass-vscode aipass-test
```

Opens VS Code in browser at `http://localhost:8080` with AIPass pre-installed.

## Requirements

- Python 3.10+
- No external API keys required
- Dependencies: `rich`, `watchdog`

## License

MIT
