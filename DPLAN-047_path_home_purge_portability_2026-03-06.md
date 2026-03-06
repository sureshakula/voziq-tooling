# DPLAN-047: Path.home() Purge — AIPass Portability Fix

**Status:** READY
**Created:** 2026-03-06
**Priority:** CRITICAL — blocks all Docker/container testing
**Parent:** MPLAN-001 (AIPass Public Repo Build)
**Triggered by:** Docker container testing revealed `Permission denied: '/home/aipass'` on `drone @seedgo audit aipass`

---

## Problem

Every module in AIPass uses `Path.home()` or hardcoded `/home/aipass` strings to resolve paths at module level (import time). This means:

- **0 of 10 modules** are portable
- **107 module-level bindings** crash on any machine that isn't ours
- A pip user running `from aipass.prax import logger` gets `Permission denied` immediately
- Docker container (the acceptance test) fails on basic commands

### Root Cause

Code was transferred from Dev-Pass (where `/home/aipass` is the fixed root) to AIPass (pip package, root is wherever the user cloned it). The import rewire (FPLAN-0409) fixed `from` statements but didn't touch path resolution.

### The Fix Pattern

```python
# WRONG — Dev-Pass pattern (breaks everywhere else)
SYSTEM_LOGS_DIR = Path.home() / "system_logs"
BRANCH_REGISTRY = Path.home() / "BRANCH_REGISTRY.json"
API_ROOT = Path.home() / "aipass_core" / "api"

# RIGHT — Package-relative (works everywhere)
# Option A: Walk up from __file__ to find repo root
REPO_ROOT = Path(__file__).resolve().parents[N]  # N = depth to repo root

# Option B: Walk-up finder (already used by drone/seedgo)
def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "AIPASS_REGISTRY.json").exists():
            return parent
    return Path.cwd()
```

---

## Scope — Module Debt Count

| Module | Path.home() | Hardcoded /home/aipass | Module-Level | Severity |
|--------|-------------|----------------------|--------------|----------|
| api | 40 | 20 | 33 | CRITICAL |
| ai_mail | 35 | 20 | 22 | CRITICAL |
| prax | 16 | 23 | 9 | CRITICAL |
| flow | 15 | 26 | 6 | HIGH |
| trigger | 8 | 14 | 8 | MEDIUM |
| seedgo | 10 | 66* | 0 | DONE (seed purged) |
| drone | 2 | 0 | 1 | LOW (fallback only) |
| cli | 2 | 11 | 2 | LOW |
| spawn | 2 | 0 | 2 | LOW |
| devpulse | 1 | 0 | 1 | LOW |

*seedgo 66 count is 59 documentation strings + 7 code. Seed already fixed all runtime breakers.

---

## Phase Plan

### Phase 0: Immediate Unblock (DEV_CENTRAL — done)
- [x] AIPASS_REGISTRY.json DEVPULSE absolute path fixed
- [x] README.md fake import paths fixed
- [x] pyproject.toml missing watchdog dependency added
- [x] Seedgo Path.home() purge dispatched to @seed (12 files, AST-verified clean)
- [x] Prax setup.py:125 hardcoded `Path("/home/aipass")` fixed
- [ ] Commit + push all pending changes

### Phase 1: Prax Logger Unblock (dispatch to @prax)
**Goal:** `from aipass.prax import logger` works in container
**Files:** 8 module-level bindings in prax
**Key targets:**
- config/load.py:51 — SYSTEM_LOGS_DIR = Path.home()
- config/load.py:55 — mkdir at import time
- setup.py:125 — branch_logs_dir (FIXED)
- introspection.py:103 — parts.index('aipass') username assumption
- registry/reader.py:34 — BRANCH_REGISTRY_PATH
- dashboard/agent_status_writer.py:45 — BRANCH_REGISTRY
- monitoring/telegram_command_bot.py:68 — AIPASS_HOME cascade
- monitoring/telegram_relay.py:60 — PRAX_MONITOR_CONFIG
- log_watchdog.py:44 — SYSTEM_LOGS_DIR duplicate

**Fix pattern:** Lazy initialization. Don't mkdir at import time. Use repo-relative paths.

### Phase 2: Core Module Purge (parallel dispatch)
**Goal:** drone, cli, spawn, devpulse portable
**These are small** — 1-2 fixes each. Can dispatch in parallel.
- drone config.py:41 — fallback Path.home() (already has walk-up, just remove fallback)
- cli json_handler.py:27 — CLI_ROOT
- spawn verify_branch.py — AIPASS_ROOT
- devpulse verify_branch.py — AIPASS_ROOT

### Phase 3: Heavy Modules (parallel dispatch, larger scope)
**Goal:** flow, trigger, ai_mail, api portable
**These are big** — 6-33 module-level bindings each.

Strategy: Many of these paths reference Dev-Pass infrastructure that doesn't exist in AIPass (MEMORY_BANK, AI_CENTRAL, BRANCH_REGISTRY.json, telegram bots, daemon). Two options per reference:
1. **Rewire to repo-relative** — if the feature exists in AIPass
2. **Guard with try/except or conditional** — if it's a Dev-Pass-only feature
3. **Remove entirely** — if the code shouldn't be in the public repo at all

**Decision needed from Patrick:** Which modules should ship functional vs stub in v1.0?
- api telegram handlers — probably Dev-Pass only (not for pip users)
- ai_mail daemon/dispatch — probably Dev-Pass only
- flow AI_CENTRAL aggregation — probably Dev-Pass only
- trigger event handlers — probably Dev-Pass only

### Phase 4: Docker Verification
**Goal:** Full test suite passes in container
- `pip install -e .` clean
- `drone --help` works
- `drone systems` works
- `drone @seedgo audit aipass` works
- `drone @seedgo verify` works
- `drone @seedgo list` works
- Python imports work: `from aipass.drone import ...`, `from aipass.prax import logger`

---

## Key Decision: What Ships in v1.0?

The massive path debt in api (40), ai_mail (35), flow (15) is because these modules contain Dev-Pass infrastructure code (telegram bots, daemon dispatch, AI_CENTRAL aggregation) that pip users will never use.

**Option A: Fix everything** — rewire all 131 Path.home() calls. Massive effort, most code is dead weight for pip users.

**Option B: Strip Dev-Pass code from public modules** — ship only the pip-relevant parts. Faster, cleaner, but requires deciding what's public vs private per module.

**Option C: Guard at module boundary** — keep all code but wrap Dev-Pass features in `try/import` guards so they don't crash when infrastructure is missing. Middle ground.

**Recommendation:** Option B for v1.0. Ship lean. The telegram bridge, daemon dispatch, and AI_CENTRAL aggregation are Dev-Pass features. Public users need: drone routing, seedgo auditing, prax logging (basic), flow planning (basic), cli formatting.

---

## Container Test Checklist (Acceptance Criteria)

```bash
# In Docker container (clean clone, pip install -e .)
source .venv/bin/activate
pip install -e .

# Core commands
drone --help                    # Must work
drone systems                   # Must show 10 branches
drone @seedgo verify            # Must pass 5/5
drone @seedgo list              # Must show packs
drone @seedgo audit aipass      # Must run without Permission denied

# Python imports
python3 -c "from aipass.drone.apps.modules.registry import load_registry; print(load_registry())"
python3 -c "from aipass.prax import logger; logger.info('test')"
python3 -c "from aipass.cli import console, header; header('test')"
```

---

## Notes

- Shebangs (`#!/home/aipass/.venv/bin/python3`) are cosmetic — don't affect pip imports
- Display strings in seedgo standards checkers are documentation, not runtime
- The walk-up `_find_registry()` pattern is proven — drone and seedgo already use it
- Dev-Pass and AIPass can coexist on same machine (different venvs, different registries)
