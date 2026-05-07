[← Back to AIPass](../../../README.md)

# CLI

**Purpose:** Display and output formatting service for all AIPass branches. Provides consistent terminal output — headers, success/error/warning messages, section breaks, and operation templates — so every branch looks the same without duplicating Rich formatting code.
**Module:** `aipass.cli`
**Version:** 2.1.0
**Seedgo:** 100% (34/34 standards)
**Tests:** 203 passing (6 files, 5/5 modules covered)
**Last Updated:** 2026-05-04

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
drone @cli --version                     # Version (v2.1.0)
drone @cli                               # Module discovery (introspection)
drone @cli display                       # Display module info
drone @cli display demo                  # Run display function showcase
drone @cli templates                     # Templates module info
drone @cli templates demo                # Run templates function showcase

# Standalone (no drone required)
python -m aipass.cli --help              # Same help output
```

> **Note:** The `aipass init` command is now owned by the @aipass branch (`aipass.aipass.apps.aipass:main`).

## aipass init (moved)

The `aipass init` command has been moved to the @aipass branch. CLI no longer owns project bootstrapping. See `aipass.aipass.apps.aipass:main` for the current implementation.

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
│   │   └── templates.py        # operation_start, operation_complete
│   └── handlers/               # PRIVATE — internal implementation
│       ├── json/
│       │   └── json_handler.py # JSON lifecycle (CRUD, validation, rotation)
│       └── templates/          # Empty — placeholder from scaffold
├── tests/                      # Test suite
│   ├── test_json_handler.py    # 35 tests — CRUD, validation, rotation
│   ├── test_display.py         # 28 tests — all display functions + routing
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

## Entry Points

| Entry | Command | How |
|-------|---------|-----|
| drone | `drone @cli [command]` | Drone routes to `apps/cli.py:main()` |
| Module | `python -m aipass.cli [args]` | `__main__.py` calls `main()` |

---

*Last Updated: 2026-05-04*

---
[← Back to AIPass](../../../README.md)
