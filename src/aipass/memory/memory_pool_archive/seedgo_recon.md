# Seedgo Module Recon
**Date:** 2026-03-06

## Summary
Standards compliance platform with pluggable packs. 20 AIPass standards defined. Path debt: DONE (runtime clean). Two pyproject.toml issues.

## Structure
```
seedgo/
├── apps/
│   ├── seedgo.py             # Entry point (pack discovery + routing)
│   ├── modules/
│   │   └── seedgo_verify.py  # Self-verification (5 checks)
│   ├── handlers/             # Empty at root (handlers live in packs)
│   └── standards/
│       ├── aipass/           # Main pack (20 standards)
│       │   ├── pack.json     # Pack manifest
│       │   ├── pack_entry.py # Pack orchestrator
│       │   ├── modules/      # Audit, verify, list
│       │   ├── handlers/     # Checkers per standard
│       │   └── standards/    # Standard definitions (JSON)
│       ├── app_development.example/
│       └── website_design.example/
├── drone_adapter.py          # Drone integration
├── cli.py                    # CLI entry point
└── tests/
```

## Commands
```
drone @seedgo verify           # 5/5 self-checks (WORKING)
drone @seedgo list             # Shows installed packs (WORKING)
drone @seedgo audit aipass     # Audit repo against standards
```

## 20 AIPass Standards
Architecture, CLI, imports, handlers, modules, documentation, testing, logging, meta headers, error handling, JSON structure, naming, permissions, diagnostics, trigger patterns, and more.

## Path Debt: DONE
- No Path.home() in runtime code
- Shebang in conftest.py: `#!/home/aipass/.venv/bin/python3` (cosmetic)
- Help text references `/home/aipass/standards/...` (display only)

## Critical Issues
1. **pyproject.toml:** `seedgo = "seedgo.cli:main"` points to non-existent module (should be `aipass.seedgo...`)
2. **pyproject.toml:** packages includes `"src/seedgo"` which doesn't exist

## Working
- Pack discovery, module auto-discovery, verify (5/5), list, drone adapter
- Standards documentation (20 defined)
- Bypass rules system (.seed/bypass.json)
