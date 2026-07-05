# CLI — Branch Prompt
<!-- File: src/aipass/cli/.aipass/aipass_local_prompt.md — Injected every prompt when in cli directory. -->

Shared Rich display and formatting service for all AIPass branches. Provides consistent terminal output — headers, success/error/warning messages, section breaks, operation templates — so every branch renders the same without duplicating formatting code.

# Commands

```
drone @cli --help              # Full help + architecture overview
drone @cli                     # Module discovery (introspection)
drone @cli display demo        # Display function showcase
drone @cli templates demo      # Operation template showcase
```

# Public API

10 symbols exported from `apps/modules/__init__.py`:
 - `console`, `err_console` — Rich Console instances (stdout, stderr)
 - `header(title, details=None)` — Bordered section header with optional key-value pairs
 - `success(message, **kwargs)` — Green checkmark with metadata
 - `error(message, suggestion=None)` — Red error with optional suggestion
 - `warning(message, details=None)` — Yellow warning with optional details
 - `fatal(message, suggestion=None)` — Error then `sys.exit(1)`
 - `section(title)` — Visual section separator
 - `operation_start(operation, **details)` — Operation begin header
 - `operation_complete(**summary)` — Completion summary with timing

Import: `from aipass.cli import console, header, success, error, warning, section` (top-level, 6 symbols) or `from aipass.cli.apps.modules import ...` (full set, 10 symbols).

# Architecture

```
cli/
├── __init__.py           # Top-level exports (6 symbols) + cli_entry()
├── apps/
│   ├── cli.py            # Entry point (main, route_command)
│   ├── modules/          # PUBLIC — import from here
│   │   ├── display.py    # header, success, error, warning, fatal, section
│   │   └── templates.py  # operation_start, operation_complete
│   └── handlers/
│       └── json/         # JSON lifecycle (CRUD, validation, rotation)
└── tests/                # 127 tests across 5 files
```

Two-tier design: `apps/modules/` is the public API. `apps/handlers/` is internal — don't import directly. See README for full tree.

# Critical Rules

 - `apps/modules/` must not import `aipass.prax` — circular dependency (prax depends on cli). Bypassed in `.seedgo/bypass.json`.
 - `json_handler.py` must not import prax either — same circular chain. Callers log via prax.
 - Import json_handler as module: `from aipass.cli.apps.handlers.json import json_handler` then `json_handler.log_operation(...)`. Seedgo AST checker matches this exact pattern.
 - `error()` suggestion param must not include "Try:" prefix — `display.py` adds it automatically.
 - `handle_command()` accepts both direct command (`command='init'` from PATH) and prefixed command (`command='aipass'` from drone). Both paths must stay wired.

# Integration Points

 - Depends on: `rich` (formatting), `aipass.prax` (logging, in cli.py only), Python stdlib
 - Provides to: all branches — display functions, operation templates, Rich console access
 - Cannot import in modules/: `aipass.prax` — see bypass rules above

# Entry Points

 - `drone @cli [command]` — routes to `apps/cli.py:main()`
 - `python -m aipass.cli` — `__main__.py` calls `main()`
 - `aipass` on PATH — console_scripts via `cli_entry()` in `__init__.py`
