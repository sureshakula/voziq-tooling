<!-- Source: /home/patrick/Projects/AIPass/src/aipass/devpulse/CLAUDE.md -->
# DEVPULSE

**User:** (your name here)

## What is AIPass

AIPass is a multi-agent framework. This project was created with `aipass init`.

**Key concepts:**
- **Project** — this directory. Contains a registry and one or more agents.
- **Agent** — a citizen that lives inside the project. Has identity (`.trinity/`), memory, mailbox, and its own apps/ directory.
- **Registry** — `DEVPULSE_REGISTRY.json` tracks all agents in this project.

## Getting Started

Create your first agent:
```
aipass init agent <name>
```

This creates a full agent scaffold inside `src/<name>/` (`apps/`, `.trinity/`, `.ai_mail.local/`) and registers it in your project registry.

## Available Commands

```
aipass init agent <name>           # Create a new agent
drone @spawn create <name>         # Create agent (alternative)
drone @seedgo audit <project>      # Run standards audit
drone @ai_mail inbox               # Check mailbox (per-agent)
drone systems                      # List all available infrastructure
```

## Startup Protocol

On any greeting, silently read these files — no narration, just do it and respond with the status.

**Read:** `DEVPULSE_REGISTRY.json`, `README.md`, `STATUS.local.md`
**Run:** `git status`

Then check the registry for agents and report status.
