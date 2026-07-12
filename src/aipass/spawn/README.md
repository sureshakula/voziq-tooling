[← Back to AIPass](../../../README.md)

# SPAWN

**The agent factory and branch lifecycle manager for AIPass.**

**Module:** `aipass.spawn` | **Version:** 1.0.0 | **Created:** 2026-03-05

---

## What I Do

- Create new branches from class-scoped templates (aipass_framework)
- Update branches from templates (single or batch by class, with --dry-run)
- Delete branches (archive + deregister)
- Sync registry and templates against filesystem
- Regenerate template registries with fresh file hashes
- Replace all `{{PLACEHOLDER}}` patterns with branch-specific values
- Register new citizens in `AIPASS_REGISTRY.json`

---

## Citizen Classes

Every branch belongs to a **citizen class**, which determines its template:

| Class | Template | What It Creates |
|-------|----------|-----------------|
| `aipass_framework` (default) | `templates/aipass_framework/` | Full 3-layer scaffold: .trinity/, .aipass/, apps/ (modules/ + handlers/), tests/, docs/, logs/ |

---

## Commands

All commands run through `drone @spawn <command>`.

### Create

```bash
drone @spawn create <path>                                    # Create aipass_framework branch
drone @spawn create <path> --role "Analyst" --purpose "Reports"  # With identity
drone @spawn create <path> --dry-run                           # Preview without touching disk
drone @spawn create @existing                                  # Adopt pre-existing agent
drone @spawn create ~/Projects/MyProject/agent_name            # External project (targets that project's own registry)
```

### Update

Update is **preview-only by default** — `--apply` required to execute changes.

```bash
drone @spawn update @branch_name                               # Preview changes (dry-run default)
drone @spawn update @branch_name --apply                       # Execute changes
drone @spawn update aipass_framework --all --apply              # All aipass_framework-class branches
drone @spawn update @branch_name --dry-run                     # Explicit preview (same as default)
```

### Delete

```bash
drone @spawn delete @branch_name                               # Archive + deregister
```

### Sync and Regenerate

```bash
drone @spawn sync-registry                                     # Report healthy/stale/unregistered
drone @spawn sync-registry --fix                               # Rebuild .spawn/ tracking + fix passport registry_ids
drone @spawn sync-templates                                    # Pull managed files from sources (partial — see Known Issues)
drone @spawn regenerate-registry                               # Regenerate aipass_framework template hashes
drone @spawn regenerate-registry --all                         # All template classes

# Repair (preview-only by default — --apply required to execute)
drone @spawn repair <project_path>                             # Preview structural issues (dry-run default)
drone @spawn repair <project_path> --apply                     # Execute fixes
drone @spawn repair --relocate @branch src/pkg/branch --apply  # Move branch to new location
drone @spawn repair --relocate @branch path --relocate-artifacts --apply  # Move + .chroma/
drone @spawn repair <project_path> --clean-pollution --apply    # Archive + remove duplicate dirs
```

### Introspection

```bash
drone @spawn                                                   # No args — lists connected modules
drone @spawn --help                                            # Full help text
drone @spawn --version                                         # Version string
```

### Python API

```python
from aipass.spawn import spawn_agent

result = spawn_agent(
    "/path/to/new/agent",
    role="Data Analyst",
    purpose="Process incoming reports",
    traits="Precise, thorough"
)
# Returns: { success, branch_name, path, files_copied, validation_issues }
```

---

## Architecture

```
spawn/
├── __init__.py                          # Public API (exports spawn_agent)
├── apps/
│   ├── spawn.py                         # Entry point — CLI routing, version, help
│   ├── modules/
│   │   ├── core.py                      # Create orchestrator (_spawn_agent, handle_command)
│   │   ├── update.py                    # Update CLI — single/batch by class
│   │   ├── delete.py                    # Delete CLI — archive + deregister
│   │   ├── sync_registry.py             # Registry repair CLI
│   │   ├── sync_templates.py            # Template sync CLI
│   │   └── regenerate_registry.py       # Template registry regeneration CLI
│   └── handlers/
│       ├── class_registry.py            # Citizen class → template directory mapping
│       ├── file_ops.py                  # Template copy, path renaming, registry regeneration
│       ├── metadata.py                  # Branch name extraction, profile detection
│       ├── placeholders.py              # {{PLACEHOLDER}} replacement engine
│       ├── registry.py                  # AIPASS_REGISTRY.json CRUD, find_registry()
│       ├── meta_ops.py                  # Branch metadata generation, hash computation
│       ├── update_ops.py                # Update workflow (Phase 0 snapshot → detect → execute)
│       ├── delete_ops.py                # Delete workflow (resolve → archive → cleanup → deregister)
│       ├── sync_registry_ops.py         # Registry sync (CWD-aware, external project support)
│       ├── sync_templates_ops.py        # Template sync implementation
│       ├── regenerate_registry_ops.py   # Template registry hash regeneration
│       ├── json_ops.py                  # JSON deep merge, backup utilities
│       └── json/
│           └── json_handler.py          # Standard JSON I/O, operation logging, 7 API functions
├── templates/
│   └── aipass_framework/                # Full scaffold template (44 files, 23 dirs)
├── tests/                               # 14 test files, 297 tests
├── spawn_json/                          # JSON tracking directory
├── tools/                               # Branch verification utilities
├── docs/                                # Documentation
└── logs/                                # Prax log output
```

### Three-Layer Design

1. **Entry point** (`spawn.py`) — Routes CLI commands, never imports handlers directly
2. **Modules** (`modules/`) — Business logic coordinators, parse arguments, delegate to handlers
3. **Handlers** (`handlers/`) — Implementation details, pure functions where possible

---

## Workflows

### Create (aipass_framework class)

1. **Resolve** — Extract branch name from target path, validate path doesn't exist
2. **Lookup** — Resolve citizen class to template directory via class_registry
3. **Copy** — Recursive copy of class template to target (skips `__pycache__`)
4. **Rename** — Replace `{{BRANCH}}` in directory and file names
5. **Replace** — Substitute all `{{PLACEHOLDER}}` patterns in file contents, including `{{CITIZEN_CLASS}}` (sourced from the create call, not a baked literal)
6. **Registry** — Generate `.branch_meta.json` (meta tabs load from `@memory` when available, degrading gracefully to empty when it's not), register in the target project's own `AIPASS_REGISTRY.json`
7. **Validate** — Scan for any remaining `{{...}}` patterns

### Update (class-aware, Phase 0)

1. **Snapshot** — Back up current `.branch_meta.json` and `.template_registry.json`
2. **Detect** — Compare branch files against template via ID-based change detection
3. **Execute** — Apply renames, additions, JSON merges (`.py` files skipped by design)
4. **Refresh** — Regenerate `.branch_meta.json` with current state

### Adopt Existing (`create @existing`)

1. **Fix** — Repair `registry_id` in passport if stale (from registry recreation)
2. **Register** — Add to project registry
3. **Update** — Run template update to sync scaffold files

---

## Tests

**344 tests | 0 skipped | 0 failed** across 14 test files:

| File | Focus |
|------|-------|
| `test_lifecycle.py` | End-to-end spawn lifecycle workflows |
| `test_json_handler.py` | JSON I/O, operation logging, standard API |
| `test_handlers.py` | Handler function behavior and integration |
| `test_regenerate_registry_ops.py` | Template registry regeneration |
| `test_update.py` | Branch update mechanics |
| `test_citizen_classes.py` | Citizen class validation and template discovery |
| `test_file_ops.py` | File copy, rename, placeholder replacement |
| `test_cli_routing.py` | Command routing and argument parsing |
| `test_contracts.py` | Handler contracts and interface compliance |
| `test_spawn.py` | Basic CLI routing and help |
| `test_error_resilience.py` | Error handling and edge cases |
| `test_check_fix_identity.py` | Owner/identity check and fix (DPLAN-0239 P4) |
| `conftest.py` | Fixtures: mock templates, registry protection |

**Public functions:** 50 total, 49 tested (98%)

---

## Integration

### Depends On

- **aipass.prax** — Logging via `system_logger`
- **aipass.cli** — Console output (header, error, warning)
- Python stdlib (`pathlib`, `json`, `shutil`, `hashlib`, `re`, `argparse`)

### Provides To

- All branches — creation, template updates, registry management, citizenship
- Registry: CRUD operations on `AIPASS_REGISTRY.json` and `*_REGISTRY.json`

---

## Known Issues

- `sync-templates` is a no-op — `template_owners.json` has no entries (template IS source of truth, not downstream consumer)
- `.py` files never auto-update during `drone @spawn update` (by design) — template .py changes need individual branch dispatch
- 4 untested public functions remain (45 total, 41 tested)

---

## Metrics

- **Seedgo:** 100% (34/34)
- **Tests:** 340 passed, 0 skipped, 0 failed
- **Module coverage:** 23/23 (100%)
- **Template registry:** 44 files, 23 dirs (aipass_framework)
- **Battle test:** 17/17 commands pass (2026-04-22)

---

*Last Updated: 2026-07-01*

[← Back to AIPass](../../../README.md)
