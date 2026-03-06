# SEEDGO

**Purpose:** Standards compliance platform with pluggable standard packs
**Module:** `aipass.seedgo`
**Created:** 2026-03-05
**Last Updated:** 2026-03-05

---

## Overview

### What I Do
Seedgo audits code against configurable standard packs. Ships with the `aipass` pack (20 standards). Routes commands to packs — each pack is self-contained with its own handlers, modules, and manifests.

### How I Work
- **Entry Point:** `apps/seedgo.py`
- **Pattern:** Pack router — discovers packs, dispatches audit/verify/checklist commands

---

## Architecture

```
seedgo/
├── apps/
│   ├── seedgo.py                  # Entry point + pack router
│   ├── modules/
│   │   └── seedgo_verify.py       # Self-check module
│   ├── handlers/
│   ├── plugins/
│   └── standards/
│       └── aipass/                 # Built-in standard pack
│           ├── pack.json           # Pack manifest (20 standards)
│           ├── pack_entry.py       # Pack entry point
│           ├── handlers/           # Standard check implementations
│           └── modules/            # Standard orchestrators
├── tests/
└── README.md
```

---

## Commands

```
seedgo --help              # Show packs and usage
seedgo list                # Show installed standard packs
seedgo verify              # Self-check (5 checks)
seedgo audit <pack>        # Run full standards audit
seedgo checklist <pack> <file>  # Check single file
```

---

## Standard Packs

### aipass (built-in)
20 standards for AIPass framework modules: imports, architecture, naming, CLI, handlers, modules, documentation, error handling, testing, encapsulation, triggers, logging, permissions, META, README, JSON structure, type checking, CLI flags.

Custom packs can be added to `apps/standards/` — each needs a `pack.json` manifest and `pack_entry.py`.

---

## Integration Points

### Depends On
- `aipass.cli` — display formatting (Rich)
- `aipass.prax` — logging

### Provides To
- All modules — standards auditing and compliance checking
