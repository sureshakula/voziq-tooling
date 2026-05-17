# CLI Module Recon
**Date:** 2026-03-06

## Summary
Display/formatting service provider using Rich. Clean public API. LOW path debt.

## Structure
```
cli/
├── apps/
│   ├── cli.py               # Entry point - showroom & help (v0.2.0)
│   ├── modules/
│   │   ├── display.py       # header(), success(), error(), warning(), section() (v0.4.0)
│   │   └── templates.py     # operation_start(), operation_complete() (v0.3.0)
│   ├── handlers/
│   │   ├── json/json_handler.py  # JSON auto-create (PATH.HOME BUG)
│   │   └── templates/       # Empty
│   ├── extensions/           # Stub
│   └── plugins/              # Stub
├── __init__.py               # Exports: console, header, success, error, warning, section, operation_start, operation_complete
├── .seed/bypass.json
└── tests/
```

## Public API
```python
from aipass.cli import console, header, success, error, warning, section
from aipass.cli import operation_start, operation_complete
```

## Path.home() Debt
- `json_handler.py:27-29` — `CLI_ROOT = Path.home() / "aipass_core" / "cli"` (CRITICAL) [stale: aipass_core]
- 8 files with hardcoded shebang `#!/home/aipass/.venv/bin/python3`

## Working
- Display module with Rich integration
- Templates module with operation patterns
- Handler guard system (cross-branch import protection)
- SEED pattern implementation (introspection, help, demo)

## Broken
- json_handler.py Path.home() — wrong paths in container
- No .trinity files
- No .aipass branch prompt
- Extensions/plugins empty
