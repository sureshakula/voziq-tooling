[← Back to AIPass](../../../README.md)

# CLI

**Purpose:** Display and output formatting service for all AIPass branches, plus the `aipass init` project bootstrap command. Provides consistent terminal output — headers, success/error/warning messages, section breaks, and operation templates — so every branch looks the same without duplicating Rich formatting code.
**Module:** `aipass.cli`
**Version:** 2.0.0
**Seedgo:** 100% (34/34 standards)
**Tests:** 203 passing (6 files, 5/5 modules covered)
**Last Updated:** 2026-04-26

## Usage

Import display functions from `aipass.cli` and call them to produce consistent Rich-formatted terminal output across all branches.

### Display Functions

```python
from aipass.cli import header, success, error, warning, section

header("Creating Branch", {"Name": "feature", "Type": "module"})
success("Files created", items=12, time="2.3s")
error("Path not found", suggestion="Check spelling")
warning("Config missing, using defaults")
section("Results")
```

### Operation Templates

```python
from aipass.cli import operation_start, operation_complete

operation_start("Processing", count=10)
# ... do work ...
operation_complete(created=5, skipped=3, failed=0, time="1.2s")
```

### Fatal (exit on error)

```python
from aipass.cli import fatal

fatal("Config file missing", suggestion="Run aipass init first")
# Prints error message + suggestion, then calls sys.exit(1)
```

### Direct Console Access

```python
from aipass.cli import console

console.print("[bold cyan]Custom Rich output[/bold cyan]")
```

## Public API

All display functions are importable from the top-level package or `apps/modules/`:

| Function | Signature | Purpose |
|----------|-----------|---------|
| `header()` | `header(title, details=None)` | Bordered section header with optional key-value pairs |
| `success()` | `success(message, **kwargs)` | Green checkmark message with metadata |
| `error()` | `error(message, suggestion=None)` | Red error with optional suggestion |
| `warning()` | `warning(message, details=None)` | Yellow warning with optional details |
| `fatal()` | `fatal(message, suggestion=None)` | Error + `sys.exit(1)` for unrecoverable failures |
| `section()` | `section(title)` | Visual section separator with title |
| `operation_start()` | `operation_start(operation, **details)` | Standard operation begin header |
| `operation_complete()` | `operation_complete(**summary)` | Completion summary with optional timing |
| `console` | Rich Console instance | Standard output console |
| `err_console` | Rich Console instance | Stderr console |

Import paths (all equivalent):
```python
from aipass.cli import header                              # Top-level re-export
from aipass.cli.apps.modules import header                 # Module-level
from aipass.cli.apps.modules.display import header         # Direct
```

## Commands

```bash
# Via drone
drone @cli --help                        # Services + Rich formatting showcase
drone @cli --version                     # Version (v2.0.0)
drone @cli                               # Module discovery (introspection)
drone @cli aipass                        # Show aipass subcommands
drone @cli aipass init                   # Bootstrap AIPass project in current dir
drone @cli aipass init /path             # Bootstrap in target directory
drone @cli aipass init /path MyProject   # Bootstrap with custom name
drone @cli aipass init update            # Re-sync managed scaffold files
drone @cli aipass init update /path      # Re-sync in target directory
drone @cli aipass init agent <name>      # Create agent (routes to spawn)
drone @cli aipass init --help            # Detailed init usage
drone @cli display                       # Display module info
drone @cli display demo                  # Run display function showcase
drone @cli templates                     # Templates module info
drone @cli templates demo                # Run templates function showcase

# Standalone (no drone required)
python -m aipass.cli --help              # Same help output
python -m aipass.cli aipass init /path   # Bootstrap directly
aipass --help                            # Via console_scripts entry point
```

## aipass init

Bootstraps a new AIPass project with 21 items (when AIPASS_HOME is detected):

| Category | Items Created |
|----------|---------------|
| Identity | `*_REGISTRY.json` |
| Prompts | `.aipass/aipass_global_prompt.md`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` |
| Docs | `README.md`, `STATUS.local.md` |
| Config | `.claude/settings.json`, `.gitignore` |
| Slash commands | `.claude/commands/prep.md`, `.claude/commands/memo.md` |
| Hooks | 7 enforcement/injector hooks in `.claude/hooks/` |
| Dirs | `hooks/`, `src/` |
| Mail | `.ai_mail.local/inbox.json` |

Settings.json wires 5 hook event types:
- **UserPromptSubmit** (5 hooks): global prompt, local prompt, branch prompt loader, email notification, identity injector
- **PostToolUse**: auto-fix diagnostics
- **PreToolUse**: pre-edit gate
- **Stop**: subagent stop gate
- **PreCompact**: pre-compact

`aipass init update` re-syncs managed files (prompts, config, hooks) without touching user-owned files (registry, README, STATUS.local.md, .gitignore, mailbox).

Cross-platform: local prompt discovery uses `python3 -c` with pathlib (no bash dependency). A `setup.py` installer handles Windows + Linux + macOS.

## Architecture

```
cli/
├── __init__.py                 # Public API exports + cli_entry()
├── __main__.py                 # python -m aipass.cli entry
├── apps/
│   ├── cli.py                  # Entry point (main, discover_modules, route_command)
│   ├── modules/                # PUBLIC — import from here
│   │   ├── __init__.py         # Re-exports all display + template functions
│   │   ├── display.py          # header, success, error, warning, fatal, section
│   │   ├── templates.py        # operation_start, operation_complete
│   │   └── init_project.py     # aipass init command routing
│   └── handlers/               # PRIVATE — internal implementation
│       ├── init/
│       │   ├── bootstrap.py    # init_project(), update_project() (511 lines)
│       │   └── scaffold_content.py  # 10 content generators (502 lines)
│       ├── json/
│       │   └── json_handler.py # JSON lifecycle (CRUD, validation, rotation)
│       └── templates/          # Empty — placeholder from scaffold
├── tests/                      # 203 tests across 6 files
│   ├── test_bootstrap.py       # 72 tests — init/update/hooks/memo/mailbox/scaffold
│   ├── test_json_handler.py    # 35 tests — CRUD, validation, rotation
│   ├── test_display.py         # 28 tests — all display functions + routing
│   ├── test_init_project.py    # 34 tests — command routing, agent, update, output
│   ├── test_templates.py       # 19 tests — operation templates + routing
│   └── test_integration.py     # 8 tests — main() flow, entry points
├── cli_json/                   # Auto-created JSON (config, data, log)
├── logs/                       # Branch-level logs
└── .archive/                   # Archived stubs (extensions/, json_templates/)
```

**Two-tier design:**
- `apps/modules/` — Public API. Import from here.
- `apps/handlers/` — Internal implementation. Don't import directly.

## JSON Handler

Manages the three-file JSON pattern (config, data, log) for any module:

```python
from aipass.cli.apps.handlers.json import json_handler

json_handler.log_operation("files_created", {"count": 12})
data = json_handler.load_json("cli", "config")
json_handler.save_json("cli", "data", {"key": "value"})
json_handler.ensure_module_jsons("cli")  # Create all 3 if missing
```

## Integration Points

### Depends On
- `rich` — Terminal formatting (Table, Panel, Text, Console)
- Python stdlib (`sys`, `importlib`, `pathlib`, `json`)

### Cannot Import
- `aipass.prax` — Circular dependency (prax depends on cli). Display/templates modules bypass this with documented entries in `.seedgo/bypass.json`.

### Provides To
- **All branches** — Display formatting (header, success, error, warning, fatal, section)
- **All branches** — Operation templates (operation_start, operation_complete)
- **All branches** — Rich console access
- **All users** — `aipass init` project bootstrap + `aipass init update` refresh
- **All users** — `aipass init agent` routing to spawn

## Entry Points

| Entry | Command | How |
|-------|---------|-----|
| drone | `drone @cli [command]` | Drone routes to `apps/cli.py:main()` |
| Module | `python -m aipass.cli [args]` | `__main__.py` calls `main()` |
| PATH | `aipass [args]` | `console_scripts` calls `cli_entry()` |

---

*Last Updated: 2026-04-26*

---
[← Back to AIPass](../../../README.md)
