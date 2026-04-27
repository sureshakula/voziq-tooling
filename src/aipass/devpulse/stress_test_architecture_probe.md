# Architecture Probe -- External Reviewer

**Date:** 2026-04-26
**Reviewer model:** Claude Opus 4.6 (1M context)
**Scope:** Full codebase review of 11 agent branches (826 active Python files)
**Method:** Static analysis of imports, file patterns, hooks, identity, communication, and test architecture

---

## Design Strengths

### 1. Genuine agent isolation with clear domain boundaries

Each branch owns its domain and the directory layout enforces it: `apps/handlers/` for private implementation, `apps/modules/` for public API, `apps/plugins/` for extensions. This is a real architectural pattern, not just a file tree. The handler/module split means internals can change without breaking callers, which is exactly right for a multi-agent system where branches evolve independently.

**Key files:** Every branch follows the `{branch}/apps/handlers/`, `{branch}/apps/modules/`, `{branch}/apps/plugins/` triplet.

### 2. The hook system is architecturally sound

The pre-edit gate (`/.claude/hooks/pre_edit_gate.py`) enforces cross-branch write protection at the tool layer, not at the application layer. This means a misbehaving branch cannot bypass the protection by importing the wrong module -- the gate operates below the code. The daemon confinement rule (Rule 1.5) is particularly smart: dispatched agents can only write inside their own branch directory, which breaks prompt-injection amplification chains.

**Key files:** `/.claude/hooks/pre_edit_gate.py`, `/.claude/hooks/auto_fix_diagnostics.py`

### 3. Prax as a shared infrastructure service

The `aipass.prax` package with its `NullLogger` fallback (`/src/aipass/prax/__init__.py`) means no branch crashes if the logging system is down. The pattern of `from aipass.prax import logger` providing a guaranteed-safe logger instance is a good service design. 434 imports from prax across non-test code show it is genuinely central, and the fallback proves it was hardened after real failures.

### 4. Registry credential verification

`drone/apps/handlers/registry_handler.py` verifies that the registry file's `metadata.id` matches the caller's `passport.json` `citizenship.registry_id`. This prevents a branch from accidentally reading a wrong registry -- a subtle but important safety net in a system where multiple projects can coexist via `AIPASS_HOME`.

**Key file:** `/src/aipass/drone/apps/handlers/registry_handler.py` lines 114-154

### 5. Self-healing delivery

The email delivery system (`ai_mail/apps/handlers/email/delivery.py`) auto-provisions inboxes for branches that do not have one, auto-migrates old inbox formats, and auto-registers contacts. This means the system degrades gracefully instead of failing when a new branch has not been fully set up yet. The `_migrate_inbox_format` function handles at least four different corruption/legacy states.

### 6. Trigger event bus with circuit breaker

The `Trigger` class in `/src/aipass/trigger/apps/modules/core.py` has a proper circuit breaker: after 5 consecutive failures, a handler is auto-disabled rather than crashing the event bus. The deferred queue prevents recursive event firing from deadlocking. The disabled inotify lazy-start (with the explicit comment explaining why) shows the team learns from production failures.

---

## Design Concerns

### 1. 58 independent copies of `_find_repo_root()`

There are 58 separate implementations of `_find_repo_root()` / `find_repo_root()` scattered across the codebase. Most use the same walk-up-parents-looking-for-AIPASS_REGISTRY.json pattern but with slight variations (some look for `.git`, some for `pyproject.toml`, some for `AIPASS_REGISTRY.json`, some limit depth, some do not). This is the single largest duplication problem in the codebase.

**The risk:** If the project root detection strategy changes (say, the registry file is renamed, or a monorepo layout is adopted), you must find and update 58 functions. The devpulse tools alone account for 20+ copies.

**Key files showing variations:**
- `/src/aipass/ai_mail/apps/handlers/paths.py` -- looks for AIPASS_REGISTRY.json
- `/src/aipass/prax/apps/handlers/config/load.py` -- looks for AIPASS_REGISTRY.json
- `/src/aipass/drone/apps/handlers/registry_handler.py` -- globs `*_REGISTRY.json` (different strategy)
- `/.claude/hooks/identity_injector.py` -- looks for pyproject.toml or .git

### 2. 12 copies of `json_handler.py` (2,720 total lines)

Every branch has its own `apps/handlers/json/json_handler.py`. These range from 28 lines (ai_mail, which re-exports from json_utils) to 450 lines (drone). They all provide `log_operation()`, `ensure_json_exists()`, `load_json()`, `save_json()` -- but each one discovers its branch root independently via `Path(__file__).resolve().parents[N]` and creates branch-scoped JSON directories.

**The risk:** This is copy-paste inheritance. When a bug is found in one (like the empty-file corruption guard added to drone's version), it must be manually propagated to 11 other files. The parent-traversal depth (`parents[3]` vs `parents[4]`) varies by branch and will break if directory structure changes.

**All copies:**
```
ai_mail/apps/handlers/json/json_handler.py       (28 lines, re-export shim)
aipass/apps/handlers/json/json_handler.py         (275 lines)
api/apps/handlers/json/json_handler.py            (244 lines)
cli/apps/handlers/json/json_handler.py            (222 lines)
drone/apps/handlers/json/json_handler.py          (450 lines, most evolved)
flow/apps/handlers/json/json_handler.py           (298 lines)
memory/apps/handlers/json/json_handler.py         (103 lines)
prax/apps/handlers/json/json_handler.py           (281 lines)
seedgo/apps/handlers/json/json_handler.py         (267 lines)
spawn/apps/handlers/json/json_handler.py          (266 lines)
trigger/apps/handlers/json/json_handler.py        (286 lines)
```

### 3. 10 identical copies of `verify_branch.py`

Every branch has `tools/verify_branch.py`. Comparing drone's and trigger's copies -- they are character-for-character identical except for a single comment ("relative to drone directory" vs "relative to current directory"). This is pure template artifact duplication. The tool compares a branch against its template, but the `TEMPLATE_DIR` is always set to the module's own root (`_THIS_DIR.parent`), which means every copy is checking itself against itself.

**Key files:** `/src/aipass/drone/tools/verify_branch.py`, `/src/aipass/trigger/tools/verify_branch.py` (and 8 others)

### 4. Two parallel registry systems

The drone branch has its own registry handler (`drone/apps/handlers/registry_handler.py`) that normalizes branches from list to dict format and merges primary + AIPASS_HOME registries. The ai_mail branch has its own (`ai_mail/apps/handlers/registry/read.py`) that reads the same `AIPASS_REGISTRY.json` but with different normalization logic and different return types (list of dicts with email vs dict of dicts keyed by name).

Neither imports from the other. Both are mature, both handle edge cases, and they will inevitably drift.

**Key files:**
- `/src/aipass/drone/apps/handlers/registry_handler.py` (334 lines)
- `/src/aipass/ai_mail/apps/handlers/registry/read.py` (220 lines)
- `/src/aipass/spawn/apps/handlers/registry.py` (spawn's own copy)

### 5. conftest.py patterns are inconsistent

The test fixtures across branches are structurally similar but not shared:
- `drone/tests/conftest.py` -- defines `mock_json_handler` as a standalone MagicMock fixture
- `ai_mail/tests/conftest.py` -- defines `mock_json_handler` with monkeypatch argument (but does not use it)
- `flow/tests/conftest.py` -- uses `autouse=True` with `patch()` context managers, pre-imports modules for patch resolution

The `AIPASS_TEST_LOG_DIR` env-var redirect is copy-pasted at the top of every conftest. This is a cross-cutting concern that belongs in a shared conftest at the package root.

**Key files:**
- `/src/aipass/drone/tests/conftest.py`
- `/src/aipass/ai_mail/tests/conftest.py`
- `/src/aipass/flow/tests/conftest.py`

---

## Coupling Issues

### 1. Prax is a god dependency (434 non-test imports)

Every branch imports `aipass.prax.apps.modules.logger`. This is correct for a logging service, but it means prax cannot be modified, refactored, or have its module structure changed without potentially breaking all 10 other branches. The `system_logger` instance is imported at module level in almost every handler file, creating eager import chains.

**Specific risk:** If prax's internal structure changes (e.g., moving `logger.py` from `apps/modules/` to `apps/handlers/`), hundreds of import statements across the codebase break.

### 2. CLI is deeply coupled as a display layer (191 non-test imports)

`from aipass.cli.apps.modules import console` appears everywhere -- in handlers, modules, introspection functions, even in `__main__` blocks. The CLI branch is not just a command-line interface; it is the stdout abstraction for the entire system. This means:
- No branch can produce output without CLI being importable
- Rich (the CLI's display library) becomes a transitive dependency for all branches
- Running any branch's code in a context where Rich is unavailable will fail

### 3. Trigger is imported by 8+ branches via lazy imports

The pattern `from aipass.trigger.apps.modules.core import trigger` appears in ai_mail, aipass, api, cli, drone, flow, memory, and prax. Most uses are inside lazy `try/except` blocks, which is good, but the coupling surface is enormous. Trigger fires events that cross every branch boundary -- it is the nervous system of the ecosystem. A breaking change to `trigger.fire()` or its handler signature could cascade.

### 4. Cross-branch import chains at module load time

`delivery.py` (ai_mail) imports from `prax.apps.modules.logger`, `ai_mail.apps.handlers.json`, `ai_mail.apps.handlers.paths`, and `ai_mail.apps.handlers.registry.read` -- all at module level. `registry.read` imports from `prax.apps.modules.logger`. `paths.py` imports from `ai_mail.apps.handlers.json`. This creates eager initialization chains where importing any handler drags in the logger, the json system, and the path resolution, all before a single function is called.

---

## Scaling Concerns

### 1. File-based communication without coordination

ai_mail delivers messages by directly writing to JSON files on disk. The `inbox_lock` context manager provides per-file locking, but there is no global coordinator. If the system grows beyond a single machine (or even beyond a single filesystem), the entire communication layer breaks. The dispatch daemon polls files on a timer. There is no message queue, no pub/sub, no event-driven I/O.

**Not a current problem**, but the architecture assumes co-located filesystem access as a hard invariant.

### 2. Registry is a single JSON file read by every branch

`AIPASS_REGISTRY.json` is read by drone (via `registry_handler.py`), ai_mail (via `registry/read.py`), spawn (via `registry.py`), flow, seedgo, and hooks. Every registry read re-parses the entire file. With 12 branches, this is fine. With 50 branches and frequent operations, this becomes a hot path. There is no caching layer -- every `get_all_branches()` call opens and parses the file from scratch.

### 3. json_handler log rotation is per-process, not per-branch

Each `json_handler.py` appends to per-module log files with a FIFO rotation of 100 entries. But if multiple processes (daemon, interactive session, hook) all log to the same module's log file, they race. The `_atomic_write_json` uses temp-file-then-rename, which prevents corruption, but does not prevent lost writes (two processes read the same log, append different entries, and one overwrites the other).

### 4. The dispatch daemon is a single-threaded poller

`daemon.py` polls every N seconds, spawns agents via subprocess, and waits. It processes one branch at a time. If 20 branches all have pending dispatches, latency grows linearly. The subprocess spawn is blocking. There is no concurrent dispatch, no priority queue, and no backpressure mechanism.

### 5. Trigger event bus uses class-level state

`Trigger._handlers`, `Trigger._history`, `Trigger._firing` are all class-level attributes. This means the Trigger is a process-global singleton. In a multi-process architecture (which AIPass already is, given the daemon + interactive sessions + hooks), each process has its own independent Trigger instance. Events fired in the daemon are invisible to the interactive session. This is probably intentional but limits the utility of the event system as a coordination mechanism.

---

## Suggestions

### 1. Extract `find_repo_root()` to a shared utility

Create a single canonical implementation in a shared location (perhaps `aipass/__init__.py` or a new `aipass.shared.paths` module). Accept a `marker` parameter for the file to search for. Replace all 58 copies with imports. This is the highest-ROI refactor available.

```
aipass/
  shared/
    paths.py          # find_repo_root(marker="AIPASS_REGISTRY.json")
    json_handler.py   # Base class for branch json handlers
```

### 2. Promote json_handler to a shared base class

The 12 json_handler copies share ~80% of their logic. Extract a base implementation that parameterizes:
- Branch root discovery (pass it in instead of computing from `__file__`)
- JSON directory name
- Default schemas

Each branch's json_handler becomes a thin subclass or configuration of the shared one. Drone's extra features (atomic write, corruption guard) become the baseline for all.

### 3. Unify registry access behind a single service

drone and ai_mail should not independently parse `AIPASS_REGISTRY.json`. Create a registry service module (perhaps in drone, which already has the most complete implementation) that:
- Provides both list and dict access patterns
- Handles caching with TTL
- Merges primary + AIPASS_HOME registries
- Is the sole reader of registry files

### 4. Add a shared conftest at the package root

`/src/aipass/conftest.py` already exists but appears minimal. Move the `AIPASS_TEST_LOG_DIR` redirect, `temp_test_dir`, `mock_logger`, and `mock_json_handler` fixtures there. Branch conftest files should only add branch-specific fixtures.

### 5. Define explicit service interfaces for prax and cli

The coupling to prax and cli is correct in principle but fragile in practice because it targets internal paths (`aipass.prax.apps.modules.logger`). Consider exporting stable interfaces from `aipass.prax` and `aipass.cli` top-level packages:

```python
# Instead of:
from aipass.prax.apps.modules.logger import system_logger as logger
# Use:
from aipass.prax import logger  # (already works via __init__.py)
```

The prax `__init__.py` already does this. Propagate this pattern to all branches so they import from the stable surface, not the internal path.

### 6. Consider a thin message bus for cross-branch coordination

The Trigger event bus is process-local. For events that need to cross process boundaries (daemon -> interactive session, hook -> running agent), consider a filesystem-based event queue (a simple JSON append log) that the Trigger can poll or watch. This would unify the "trigger fires event" and "ai_mail delivers message" patterns into a single coordination mechanism.

### 7. Add type stubs or Protocol classes for the json_handler interface

Every branch imports `json_handler` and calls `log_operation()`, `load_json()`, `save_json()`, `ensure_json_exists()`. This is a de facto interface. Formalize it as a Protocol class so tests can verify compliance and so new branches get autocomplete and type checking for free.

---

## Summary Statistics

| Metric | Count |
|---|---|
| Active Python files | 826 |
| Test files | 241 |
| Branches | 12 (including aipass itself) |
| json_handler.py copies | 12 (2,720 total lines) |
| verify_branch.py copies | 10 (identical) |
| find_repo_root implementations | 58 |
| Prax imports (non-test) | 434 |
| CLI imports (non-test) | 191 |
| Trigger cross-branch imports | 25+ |
| Passport files | 12 |
| Hook files | 8 active |

---

*Generated by external architectural review. Findings are based on static analysis of the codebase as of 2026-04-26. No code was executed.*
