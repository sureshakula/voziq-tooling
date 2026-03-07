# SPAWN

**Purpose:** Agent creation and template management. Creates new agents from templates, replaces placeholders, and registers them.
**Module:** `aipass.spawn`
**Created:** 2026-03-05

---

## Overview

### What I Do
- Create new agent directories from the bundled template
- Replace all `{{PLACEHOLDER}}` patterns with branch-specific values
- Register new agents in `AIPASS_REGISTRY.json`
- Regenerate `.template_registry.json` with fresh file hashes
- Validate no unreplaced placeholders remain

### Usage

```python
from aipass.spawn import spawn_agent

result = spawn_agent(
    "/path/to/new/agent",
    role="Data Analyst",
    purpose="Process incoming reports",
    traits="Precise, thorough"
)

# result dict includes: success, branch_name, path, files_copied, validation_issues
```

---

## Architecture

```
spawn/
├── __init__.py              # Public API (exports spawn_agent)
├── apps/
│   ├── spawn.py             # Entry point (CLI)
│   ├── modules/
│   │   └── core.py          # Orchestrator — coordinates all steps
│   └── handlers/
│       ├── file_ops.py      # Template copy, path renaming
│       ├── metadata.py      # Branch name extraction, profile detection
│       ├── placeholders.py  # {{PLACEHOLDER}} replacement engine
│       └── registry.py      # AIPASS_REGISTRY.json CRUD
├── templates/
│   ├── agent.template/      # Source template for new agents
│   └── agent_mock_branch/   # Reference implementation
└── tests/
    └── test_spawn.py        # 13 tests covering all components
```

---

## Spawn Workflow

1. **Resolve** — Extract branch name from target path, validate path doesn't exist
2. **Copy** — Recursive copy of `agent.template/` to target (skips `__pycache__`, `.gitkeep`)
3. **Rename** — Replace `{{BRANCH}}` in directory and file names
4. **Replace** — Substitute all `{{PLACEHOLDER}}` patterns in file contents
5. **Registry** — Regenerate `.template_registry.json`, register in `AIPASS_REGISTRY.json`
6. **Validate** — Scan for any remaining `{{...}}` patterns

---

## Integration Points

### Depends On
- `aipass.prax` — Logging via `system_logger`
- `aipass.cli` — Console output and headers
- Python stdlib (`pathlib`, `json`, `shutil`, `hashlib`, `re`)

### Provides To
- All modules — agent creation service and lifecycle setup
- Registry: Reads/writes `AIPASS_REGISTRY.json`

---

*Last Updated: 2026-03-07*
