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

## Seed Go

> Linters enforce language rules. Seed Go enforces yours.

A portable, plugin-based code standards checker. Define your team's conventions
as simple Python functions — function length limits, docstring coverage, file
structure rules — and run them like any other linter. Zero external dependencies.
No API keys. Deterministic results.

### Quick Start

```bash
# Install
pip install aipass[seedgo]

# Initialize config in your project
seedgo init

# Run all enabled plugins
seedgo check

# List available plugins
seedgo list
```

### Write a Plugin in 60 Seconds

```python
# .seedgo/plugins/my_plugin.py
import re
from seedgo import CheckResult, CheckItem, Severity

PLUGIN_NAME = "no-bare-except"
PLUGIN_DESCRIPTION = "Flag bare except: clauses."
FILE_TYPES = ["*.py"]

_BARE_EXCEPT = re.compile(r"^\s*except\s*:\s*(#.*)?$")

def check(file_path: str, config: dict | None = None) -> CheckResult:
    lines = open(file_path).readlines()
    violations = [
        CheckItem(
            name="bare-except",
            passed=False,
            message=f"Bare except: at line {i+1}",
            severity=Severity.WARNING,
            line=i + 1,
            fix_hint="Use `except Exception:` instead.",
        )
        for i, line in enumerate(lines)
        if _BARE_EXCEPT.match(line)
    ]
    return CheckResult(
        plugin=PLUGIN_NAME,
        passed=not violations,
        checks=violations or [CheckItem(name="bare-except", passed=True,
                                        message="No bare excepts found.",
                                        severity=Severity.WARNING)],
        file_path=file_path,
    )
```

### Starter Plugins (5 Built-in)

| Plugin | What it checks | Linter equivalent? |
|---|---|---|
| `no-bare-except` | Bare `except:` clauses | ruff E722 (but with fix hints) |
| `type-hints-required` | Missing type annotations | mypy (but project-configurable) |
| `docstring-coverage` | Missing module/function docstrings | pydocstyle (but simpler) |
| `function-length` | Functions exceeding N lines | **No linter equivalent** |
| `file-structure` | Forbidden files in root/dirs | **No linter equivalent** |

Two of the five check things no standard linter can enforce.

### vs. Pre-Commit

Seed Go is complementary to pre-commit, not a replacement. Run it as a hook:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: seedgo
      name: Seed Go standards check
      entry: seedgo check
      language: system
      pass_filenames: false
```

Or standalone in CI:

```bash
seedgo check --format github  # GitHub Actions annotations
seedgo check --format json    # machine-readable output
```

### Honest About What It Is

- Deterministic checks — same input always produces same output
- No AI in the validation loop — no API keys, no network calls
- Plugin contract is stable: `check(file_path, config) -> CheckResult`
- Scores are weighted: errors block (weight 1.0), warnings degrade (0.5),
  info is reported only (0.0). Threshold is configurable (default: 75/100).

## License

MIT
