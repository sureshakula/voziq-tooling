# AIPass Framework

<!-- ![CI](https://github.com/AIOSAI/AIPass/actions/workflows/ci.yml/badge.svg) -->

Orchestration framework for autonomous AI agent ecosystems.

## What is this?

AIPass provides routing, workflow management, inter-agent messaging, and monitoring for autonomous AI agent ecosystems. It coordinates multiple agents working together across branches, plans, and tasks. [Trinity Pattern](https://github.com/AIOSAI/Trinity-Pattern) serves as the memory layer.

## Install

```bash
pip install aipass
```

> **Note:** This package is not yet published to PyPI. This repo is in early development.

## Features

### Routing & Discovery (v1.0)

Symbolic addressing for multi-agent systems. Instead of hard-coded paths, agents use `@branch` symbolic names that resolve to actual locations at runtime.

**Quick Start:**

```python
from aipass.routing import initialize_registry, register_branch, resolve_branch

# Initialize registry (first time only)
initialize_registry()

# Register your agents
register_branch("my_agent", "/path/to/agents/my_agent", branch_type="agent")
register_branch("researcher", "/path/to/agents/researcher", branch_type="agent")
register_branch("monitor", "/path/to/services/monitor", branch_type="service")

# Resolve symbolic names to paths
agent_path = resolve_branch("@my_agent")
# Returns: "/path/to/agents/my_agent"

# Works with or without @ prefix
researcher_path = resolve_branch("researcher")
# Returns: "/path/to/agents/researcher"
```

**Discovery:**

```python
from aipass.routing import list_branches, branch_exists, get_branch_info

# Check if a branch exists
if branch_exists("@my_agent"):
    print("Agent found!")

# List all registered branches
all_branches = list_branches()
# Returns: ["@my_agent", "@researcher", "@monitor"]

# List branches by type
agents_only = list_branches(branch_type="agent")
# Returns: ["@my_agent", "@researcher"]

# Get full branch metadata
info = get_branch_info("@my_agent")
# Returns: {
#   "name": "my_agent",
#   "path": "/path/to/agents/my_agent",
#   "type": "agent",
#   "status": "active",
#   "created": "2026-03-01T10:00:00Z"
# }
```

**Configuration:**

By default, the registry is stored at `~/.aipass/BRANCH_REGISTRY.json`. You can customize this:

```python
from aipass.routing import set_registry_path

# Set custom registry location
set_registry_path("/custom/path/to/registry.json")
```

Or via environment variable:

```bash
export AIPASS_REGISTRY_PATH=/custom/path/to/registry.json
```

**Integration with Trinity Pattern:**

```python
from trinity_pattern import Agent
from aipass.routing import resolve_branch

# Before: hard-coded paths
agent = Agent(directory="/home/user/agents/my_agent")

# After: symbolic addressing
agent_dir = resolve_branch("@my_agent")
agent = Agent(directory=agent_dir)
```

**Error Handling:**

```python
from aipass.routing import resolve_branch, BranchNotFoundError

try:
    path = resolve_branch("@nonexistent")
except BranchNotFoundError as e:
    print(f"Branch not found: {e}")
```

## License

MIT
