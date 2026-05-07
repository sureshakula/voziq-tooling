# STATUS

An AIPass project.

## Quick Start

```bash
# 1. Create your first agent
aipass init agent my_agent

# 2. Start a session
cd src/my_agent/
claude  # or your preferred AI CLI

# 3. Check project status
cat STATUS.local.md
```

## Project Structure

```
status/
  STATUS_REGISTRY.json    # Agent registry
  .aipass/                 # Prompts (injected per-turn)
  CLAUDE.md               # Claude Code instructions
  AGENTS.md               # Codex instructions
  GEMINI.md               # Gemini instructions
  STATUS.local.md         # Project status
  src/                    # Agent directories live here
    <agent_name>/         # Created via aipass init agent
```

## What is AIPass?

AIPass is a multi-agent framework where autonomous agents (citizens) live in directories with persistent identity, memory, and communication.

Each agent has:
- **Identity** — `.trinity/passport.json`
- **Memory** — `.trinity/local.json`, `observations.json`
- **Mailbox** — `.ai_mail.local/`
- **Code** — `apps/` with modules and handlers

## Commands

| Command | Description |
|---------|-------------|
| `aipass init agent <name>` | Create a new agent |
| `drone @spawn create <name>` | Create agent (alternative) |
| `drone @seedgo audit <project>` | Run standards audit |
| `drone @ai_mail inbox` | Check agent mailbox |
| `drone systems` | List infrastructure |

*Initialized with [AIPass](https://github.com/AIOSAI/AIPass) on 2026-05-04*
