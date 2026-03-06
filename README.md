# AIPass

> **Building in public.** This is an active development repo — not a finished product. Modules are being built, tested, and rewired in real time. Some things work, some things don't yet. Follow along, poke around, or fork it and experiment. Contributions welcome once we stabilize.

Orchestration framework for autonomous AI agent ecosystems.

## What is this?

AIPass gives multi-agent systems the infrastructure they usually lack: command routing, symbolic addressing, standards enforcement, workflow management, and inter-agent messaging. Instead of agents hard-coding paths to each other, they use `@branch` names that resolve at runtime. [Trinity Pattern](https://github.com/AIOSAI/Trinity-Pattern) provides the memory layer.

**Status:** Early development. `drone` routing and `seedgo` standards are working. Other modules are being built. Expect breaking changes.

## Quick Start

### From source (recommended for now)

```bash
git clone https://github.com/AIOSAI/AIPass.git
cd AIPass
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Verify it works

```bash
drone --help        # Command router
drone systems       # List all registered modules and branches
```

You should see:

```
Modules (2):
  @drone              Command routing and module discovery
  @seedgo             Standards compliance through pluggable standard packs

Branches (10):
  @ai_mail  @api  @cli  @devpulse  @drone
  @flow  @prax  @seedgo  @spawn  @trigger
```

## Docker (Isolated Testing)

Run AIPass in a fully isolated container with VS Code in the browser:

```bash
cd AIPass
docker build -t aipass-test .
docker run -d -p 8080:8080 --name aipass-vscode aipass-test
```

Open `http://localhost:8080` — you get a full VS Code with AIPass pre-installed. The container clones the repo independently on first boot.

## Core Concepts

### Drone — Command Router

Everything goes through `drone`. It resolves `@branch` names to paths and routes commands.

```bash
drone @seedgo audit aipass    # Route "audit aipass" to the seedgo module
drone @seedgo list            # Route "list" to seedgo
drone @flow status            # Route "status" to flow
drone systems                 # List all registered modules
drone @module --help          # Show help for any module
```

**In Python:**

```python
from aipass.drone.apps.modules.registry import load_registry

registry = load_registry()
# Returns all registered branches with their paths, types, and metadata
```

### Seed Go — Standards Enforcement

> Linters enforce language rules. Seed Go enforces yours.

A plugin-based code standards checker. Define your team's conventions as Python functions and run them like any linter. No API keys. Deterministic.

```bash
drone @seedgo verify          # Check seedgo installation health
drone @seedgo list            # Show installed standard packs
drone @seedgo audit aipass    # Run the aipass standards pack
```

**Write a plugin in 60 seconds:**

```python
# .seedgo/plugins/no_bare_except.py
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
            name="bare-except", passed=False,
            message=f"Bare except: at line {i+1}",
            severity=Severity.WARNING, line=i + 1,
            fix_hint="Use `except Exception:` instead.",
        )
        for i, line in enumerate(lines) if _BARE_EXCEPT.match(line)
    ]
    return CheckResult(
        plugin=PLUGIN_NAME, passed=not violations,
        checks=violations or [CheckItem(
            name="bare-except", passed=True,
            message="No bare excepts found.",
            severity=Severity.WARNING)],
        file_path=file_path,
    )
```

**5 built-in plugins:**

| Plugin | What it checks | Linter equivalent? |
|---|---|---|
| `no-bare-except` | Bare `except:` clauses | ruff E722 (with fix hints) |
| `type-hints-required` | Missing type annotations | mypy (project-configurable) |
| `docstring-coverage` | Missing docstrings | pydocstyle (simpler) |
| `function-length` | Functions exceeding N lines | **None** |
| `file-structure` | Forbidden files in dirs | **None** |

### Symbolic Addressing

Instead of hard-coding agent paths, resolve them by `@name`:

```python
from aipass.drone.apps.modules.resolver import resolve_branch
from aipass.drone.apps.modules.registry import load_registry

# Resolve @name to path
path = resolve_branch("@drone")  # Returns the drone module path

# Load the full registry
registry = load_registry()
# Returns all registered branches with their paths, types, and metadata
```

## Architecture

All modules follow a 3-layer pattern:

```
src/aipass/<module>/
├── apps/
│   ├── branch.py      # Entry point (what drone calls)
│   ├── modules/       # Business logic
│   └── handlers/      # Implementation details
```

**10 modules:** drone, seedgo, flow, ai_mail, prax, cli, api, spawn, trigger, devpulse

| Module | Purpose | Status |
|--------|---------|--------|
| `drone` | Command routing, `@branch` resolution | Working |
| `seedgo` | Standards enforcement, plugin system | Working |
| `flow` | Workflow/plan management | Building |
| `ai_mail` | Inter-agent messaging | Building |
| `prax` | Real-time monitoring | Building |
| `cli` | Display formatting | Building |
| `api` | External API access | Building |
| `spawn` | Agent lifecycle management | Building |
| `trigger` | Event-driven automation | Building |
| `devpulse` | Dev notes and status tracking | Building |

## Configuration

**Registry location** (default: `AIPASS_REGISTRY.json` in repo root):

```bash
export AIPASS_REGISTRY_PATH=/custom/path/to/registry.json
```

**Seed Go config** (default: `.seedgo/` in project root):

```bash
seedgo init          # Create .seedgo/ config directory
seedgo check         # Run all enabled plugins
seedgo list          # Show available plugins
```

## Requirements

- Python 3.10+
- No external API keys required
- Dependencies: `rich` (terminal formatting)

## License

MIT
