# {name} — Project Context
<!-- File: .aipass/aipass_global_prompt.md — Injected every turn via hook. -->

Multi-agent framework. Agents live in directories with persistent identity, memory, and communication. All AIPass infrastructure available from any project via `drone`.

Patterns here are exact. Don't guess command syntax — examples are the API.

`drone` = installed binary, always on PATH. Run directly.

# Terminology

- Branch — directory `src/{name}/<agent>/`. Agent home and address.
- Agent (citizen) — persistent identity. Has passport (`.trinity/`), memory, mailbox, code (`apps/`). Addressable as `@name`.
- Sub-agent — disposable worker spawned for a task. No passport, no memory.
- Registry — `{name}_REGISTRY.json` tracks all agents.
- Project — this directory. Contains registry and agents.

# Setup

If `drone` cannot find AIPass registry:
```bash
export AIPASS_HOME=/path/to/AIPass
```
Add to shell profile to make permanent.

# Commands

## Agent Lifecycle
```
aipass init agent <name>           # Create new agent in src/<name>/
drone @spawn create <name>         # Create agent (alternative)
drone @spawn list                  # List registered agents
```

## Dispatch — Send Task + Wake Agent
```
drone @ai_mail dispatch @<agent> "Subject" "Body"         # Send + wake (default)
drone @ai_mail dispatch @<agent> "Subject" "Body" --fresh # Send + wake fresh session
drone @ai_mail email @<agent> "Subject" "Body"            # FYI only (no wake)
```

Use `dispatch` by default. Use `email` only when you don't need the agent to act now.

## Communication
```
drone @ai_mail inbox               # Check mailbox
drone @ai_mail view <id>           # Read message
drone @ai_mail close <id>          # Mark read
```

## Standards
```
drone @seedgo audit <project>      # Full standards audit
drone @seedgo checklist <file>     # Check single file
```

## Plans
```
drone @flow create . "Subject" dplan   # DPLAN (design/thinking)
drone @flow create . "Subject"         # FPLAN (execution)
drone @flow create . "Subject" aplan   # APLAN (agent task)
drone @flow list open                  # Active plans
drone @flow close <id>                 # Close plan
```

DPLAN = thinking before building. FPLAN = building and executing.

## Memory
```
drone @memory archive              # Archive to vector store
drone @memory search <query>       # Search archived memories
```

## Git
```
drone @git status                  # Git status (branch-scoped)
drone @git pr 'description'        # Create pull request
drone @git sync                    # Sync with main
```

## Infrastructure
```
drone systems                      # List all available branches
drone @<branch> --help             # Branch command reference
```

# Patterns

- Communication — agents communicate via `.ai_mail.local/`
- Standards — `drone @seedgo audit` checks compliance
- Identity — agents have `.trinity/passport.json`, projects use registry
- Memory — update `.trinity/local.json` at session end. Memory is presence.
- Use drone commands for all operations. Never raw git, gh, or python -m.

# Maintenance

- Upgrade scaffold: `aipass init update` refreshes managed files to latest
- Entry point: each agent's `apps/{name}.py` auto-configures sys.path
- Layout: `src/{name}/<agent>/` for standalone projects
