# JSON Handler Integrity Standard

## Purpose

Catches silent handler drift. Every branch's `apps/handlers/json/json_handler.py` must be a canonical handler capable of creating the full config/data/log triplet — not a stripped log-only fork that passes json_structure but cannot create config or data files.

## What Is Checked

### 1. Handler Capability (one must be true)

- **Shared shim:** imports from `aipass.aipass.shared.json_handler` (the v3.0.0 pattern)
- **Standalone with triplet surface:** defines or re-exports `ensure_module_jsons` and/or `ensure_json_exists`

A handler that only defines `log_operation()` without the triplet-creating functions is a **log-only fork** — it can write operation logs but cannot create config or data files. This is the exact failure case that caused memory's 25-log / 0-config / 0-data drift.

### 2. Disk Triplet Completeness

For each `*_log.json` in the branch's `{branch}_json/` directory, matching `*_config.json` and `*_data.json` must also exist. Catches the symptom (missing files on disk) even if the handler check alone misses it.

## Scope

`branch_level` — checked once per branch during audit.

## Scoring

| Score | Meaning |
|-------|---------|
| 100 | Handler capable + disk triplets complete |
| 66 | Handler capable but disk triplets incomplete |
| 33 | Log-only fork (cannot create triplets) |
| 0 | No handler file + no disk triplets |

Pass threshold: 75%.

## Known Exemptions

- **@hooks** — no json_handler.py (hook engine, doesn't follow the module JSON pattern). Bypassed.
- **@backup** — log-only fork, appears dormant (0/0/0 json files). Bypassed pending migration decision.

## Fix

Replace the forked handler with the shared shim (~35 lines):

```python
from aipass.aipass.shared.json_handler import JsonHandler

_BRANCH_ROOT = Path(__file__).resolve().parents[3]
_handler = JsonHandler(json_dir=_BRANCH_ROOT / "{branch}_json")

log_operation = _handler.log_operation
ensure_module_jsons = _handler.ensure_module_jsons
ensure_json_exists = _handler.ensure_json_exists
# ... re-export remaining public functions ...
```

## History

- 2026-06-14: Created after memory's silent handler drift was discovered and fixed. Memory had a 103-line v1.0.0 log-only fork that passed json_structure at 100% but produced 0 config / 0 data files.
