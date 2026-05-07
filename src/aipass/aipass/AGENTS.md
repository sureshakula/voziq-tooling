<!-- Source: /home/patrick/Projects/AIPass/src/aipass/aipass/AGENTS.md -->
# AIPASS — Agent Instructions

This project uses AIPass, a multi-agent framework.

## Key Concepts

- **Project** — this directory. Contains a registry and one or more agents.
- **Agent** — a citizen that lives inside the project with its own identity, memory, and code.
- **Registry** — `AIPASS_REGISTRY.json` tracks all agents.

## Getting Started

Create your first agent:
```
aipass init agent <name>
```

## Available Commands

```
aipass init agent <name>           # Create a new agent
drone @spawn create <name>         # Create agent (alternative)
drone @seedgo audit <project>      # Run standards audit
drone systems                      # List all infrastructure
```

## Startup

On startup, read: `AIPASS_REGISTRY.json`, `README.md`, `STATUS.local.md`
