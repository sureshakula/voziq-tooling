# Drone Module Recon
**Date:** 2026-03-06

## Summary
Command routing orchestrator. Fundamentally sound and working. LOW path debt.

## Structure
```
drone/
├── apps/
│   ├── drone.py              # Main entry point (router orchestrator, v1.0.0)
│   ├── handlers/
│   │   ├── executor.py       # Safe subprocess execution (no shell=True)
│   │   └── exceptions.py     # Custom exception hierarchy
│   ├── modules/
│   │   ├── config.py         # Registry path discovery (walk-up pattern)
│   │   ├── discovery.py      # Branch/command discovery
│   │   ├── module_registry.py # Internal module registry (drone, seedgo)
│   │   ├── resolver.py       # Symbolic name resolution
│   │   └── router.py         # Command routing logic
│   └── plugins/              # Empty
├── cli.py                    # CLI entry point (pyproject.toml wired)
├── drone_adapter.py          # Self-routing bridge (drone @drone)
├── __init__.py               # Public API
└── tests/
```

## Commands
```
drone                          # Introspection
drone --help / --version       # Help/version
drone systems                  # List all registered branches
drone @target command [args]   # Route to branch or module
```

## Registry Discovery (config.py)
1. Explicit set via set_registry_path()
2. AIPASS_REGISTRY env var
3. Walk-up from drone package location
4. Walk-up from CWD
5. Fallback: ~/.aipass/AIPASS_REGISTRY.json

## Internal Module Registry
```python
_MODULE_REGISTRY = {
    "drone": "aipass.drone.drone_adapter",
    "seedgo": "aipass.seedgo.drone_adapter"
}
```

## Path Debt
- cli.py:1 — hardcoded shebang
- tests/conftest.py:1 — hardcoded shebang
- config.py fallback: `Path.home() / ".aipass" / "AIPASS_REGISTRY.json"` (acceptable)

## Working
- CLI entry, registry discovery, branch listing, module introspection
- Self-routing, help discovery, safe subprocess execution
- All imports use correct `from aipass.drone...` namespace

## Broken
- Hardcoded shebangs
- No .trinity directory
- README incomplete
