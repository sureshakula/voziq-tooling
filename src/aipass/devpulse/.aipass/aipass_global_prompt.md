<!-- Source: /home/patrick/Projects/AIPass/src/aipass/devpulse/.aipass/aipass_global_prompt.md -->
# DEVPULSE — Project Context
<!-- Injected every turn via hook. -->

## What is AIPass

AIPass is a multi-agent framework. Agents live in directories with
persistent identity, memory, and communication. All AIPass infrastructure
is available from any project via the `drone` command.

## Terminology

- **Project** — this directory. Contains a registry and agents.
- **Agent** — a citizen with identity (`.trinity/`), memory, mailbox,
  and code (`apps/`).
- **Registry** — `DEVPULSE_REGISTRY.json` tracks all agents.

## Setup: if drone commands fail

If `drone` cannot find the AIPass registry, set the env var:
```bash
export AIPASS_HOME=/path/to/AIPass   # path to AIPass installation
```
Add to your shell profile (`~/.bashrc` or `~/.zshrc`) to make it permanent.

## Commands

### Agent Lifecycle
```
aipass init agent <name>           # Create a new agent in src/<name>/
drone @spawn create <name>         # Create agent (alternative)
drone @spawn list                  # List registered agents
```

### Standards
```
drone @seedgo audit <project>      # Run full standards audit
drone @seedgo checklist <file>     # Check a single file
```

### Dispatch — Send Task + Wake an Agent (DEFAULT)
```
drone @ai_mail dispatch @<agent> "Subject" "Body"        # Send + wake (default)
drone @ai_mail dispatch @<agent> "Subject" "Body" --fresh # Send + wake fresh session
drone @ai_mail dispatch wake @<agent>                    # Wake without sending
drone @ai_mail dispatch wake --fresh @<agent>            # Wake fresh
drone @ai_mail email @<agent> "Subject" "Body"           # FYI only (no wake)
```

Use `dispatch` by default. Use `email` only when you don't need the agent to act now.

### Communication (ai_mail)
```
drone @ai_mail inbox               # Check your mailbox
drone @ai_mail view <id>           # Read a message
drone @ai_mail close <id>          # Mark message read
```

### Feedback
```
drone @devpulse feedback send "Subject" "Body"  # Send feedback (cross-project)
```

### Plans (flow)
```
drone @flow create . "Subject" dplan   # Create DPLAN (design/thinking)
drone @flow create . "Subject" master  # Create FPLAN master (execution)
drone @flow create . "Subject" aplan   # Create APLAN (agent-level task)
drone @flow list open                  # List active plans
drone @flow list                       # List all plans
drone @flow close <id>                 # Close a plan
drone @flow info <id>                  # View plan details
```

**DPLAN** = Dev Plan. Thinking, brainstorming, architecture decisions. Use before building.
**FPLAN** = Flow Plan. Building and executing. Use when the plan is clear and work is underway.

### Memory
```
drone @memory archive              # Archive memories to vector store
drone @memory search <query>       # Search archived memories
```

### Git Workflow
```
drone @git pr 'description'        # Create a pull request
drone @git status                  # Git status (branch-scoped)
drone @git sync                    # Sync with main
drone @git lock / unlock           # Lock/unlock the repo
```

### Infrastructure
```
drone systems                      # List all available infrastructure
drone --help                       # Full drone command reference
```

## Patterns

- **Communication** — agents communicate via `.ai_mail.local/`.
- **Standards** — run `drone @seedgo audit` to check compliance.
- **Identity** — agents have `.trinity/passport.json`. Projects use the registry.
- **Memory** — update `.trinity/local.json` at session end. Memory is presence.

## Maintenance

- **Upgrade scaffold**: `drone @cli aipass init update` refreshes managed project files (hooks, prompts, settings) to latest templates.
- **Entry point**: each agent's `apps/{name}.py` auto-configures `sys.path` and `AIPASS_BRANCH_NAME` env var. If prax logs to `unknown_branch/`, check that these are set.
- **Standalone projects** use `src/{name}/` layout (not `src/aipass/{name}/`). Module discovery adapts automatically.
