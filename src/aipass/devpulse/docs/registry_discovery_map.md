# Registry Discovery Map — FPLAN-0029 Phase 1

## Primary Implementations (5)

| File | Function | Strategy |
|------|----------|----------|
| `src/aipass/spawn/apps/handlers/registry.py:34-79` | `find_registry(start_path)` | Env var → project markers (.git/pyproject.toml) → walk-up → cwd fallback |
| `src/aipass/drone/apps/handlers/registry_handler.py:36-61` | `find_registry()` | Walk-up from __file__ → walk-up from cwd → parents[4] fallback |
| `src/aipass/drone/apps/handlers/registry_handler.py:64-81` | `get_registry_path()` | Global override → env var → find_registry() |
| `src/commons/apps/handlers/database/db.py:343-378` | `_find_branch_registry()` | Env var AIPASS_ROOT → walk-up (10 limit) → ~/.aipass/ fallback |
| `src/commons/apps/handlers/identity/identity_ops.py:33-67` | `_find_branch_registry_path()` | Same as db.py |

## Local Reimplementations (23+)

All do walk-up from `__file__` looking for `AIPASS_REGISTRY.json`:

### ai_mail (4 files)
- `apps/handlers/users/branch_detection.py:26-38`
- `apps/handlers/registry/read.py:31-41`
- `apps/handlers/email/format.py:21-31`
- `apps/handlers/dispatch/daemon.py:36-55`

### memory (3 files)
- `apps/handlers/dashboard_push.py:44-54`
- `apps/handlers/monitor/detector.py:36-83`
- `apps/handlers/monitor/memory_watcher.py:363-385`

### prax (2 files)
- `apps/handlers/registry/reader.py:24-39`
- `apps/handlers/dashboard/agent_status_writer.py:33-44`

### seedgo (3 files)
- `apps/handlers/audit/discovery.py:54-62`
- `apps/handlers/diagnostics/discovery.py:21-29`
- `apps/handlers/readme/readme_ops.py:29-37`

### + 11 more across other branches

## Hardcoded String Count
100+ references to `"AIPASS_REGISTRY.json"` across codebase.

## Phase 1 Plan
1. Create `commons.registry.find_registry()` — one function, glob for `*_REGISTRY.json`
2. All 23+ modules import from commons
3. Drone/spawn wrappers call commons internally
4. Test: temp dir with TEST_REGISTRY.json → drone systems finds it
