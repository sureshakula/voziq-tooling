# AI_MAIL COMMS UPGRADE — Hardening Plan

**Goal:** Make ai_mail bulletproof, then use as the model for other branches.
**Started:** 2026-03-10 | **Status:** In Progress
**Tracking:** Updated each session. Read this first on context resume.

---

## Current State (Session 10)

**Seedgo audit: 100%** — all 23 standards pass (42 files)
**Automated tests: 36** — test_send_identity.py v1.2.0 (3 audit rounds, 15 agents, 0 false positives)
**Production fixes deployed:** 3 cross-platform crashers fixed, test suite fully isolated
**Phase 2 (Error Handling):** 27 silent `except` blocks across 13 files now log with `logger.warning()`

### Test Suite Evolution
- v1.0.0: 31 tests — 7 false positives found by 3 audit agents
- v1.1.0: 32 tests — 8 suspects found by 5 audit agents (live registry, weak contracts)
- v1.2.0: 36 tests — final audit found 2 minor issues, fixed. **0 live-data dependencies.**

### Production Fixes (Session 9)
- `inbox_lock.py` — `import fcntl` guarded for Windows (msvcrt fallback)
- `ai_mail.py` — `signal.SIGPIPE` guarded with `hasattr` check
- `notify.py` — `/usr/bin/python3` replaced with `shutil.which("python3")`

---

## Architecture Map

```
Entry: apps/ai_mail.py
  +-- Module: apps/modules/email.py (orchestrator, v3.0.0)
       |-- handle_send() -> send_args.py (parse) -> send.py (execute) -> delivery.py (inbox write)
       |-- handle_inbox() -> inbox_resolve.py -> inbox_ops.py -> format.py
       |-- handle_view() -> inbox_ops.py
       |-- handle_reply() -> reply.py -> delivery.py
       |-- handle_close() -> close_ops.py
       |-- handle_sent() -> format.py
       +-- handle_contacts() -> registry/

  Module: apps/modules/dispatch.py (dispatch orchestrator)
       |-- daemon.py (auto-dispatch loop)
       |-- wake.py (manual branch wake)
       |-- dispatch_monitor.py (agent lifecycle)
       |-- status.py (dispatch status display)
       +-- pending_work.py (pending dispatch queue)

  Identity: apps/handlers/users/
       |-- branch_detection.py (detect_branch_from_pwd — THE critical path)
       |-- user.py (get_current_user, get_branch_by_email)
       +-- load.py, config_generator.py

  Cross-branch: drone/apps/handlers/router_handler.py
       +-- detect_caller_branch_name() -> sets AIPASS_CALLER_BRANCH env var
```

**Identity detection chain (9 stages):**
1. drone CLI entry
2. router resolves @branch to path
3. router_handler detects caller via CWD (+ AIPASS_BRANCH_NAME fallback)
4. executor merges caller_env into subprocess
5. ai_mail subprocess starts with env vars
6. branch_detection reads AIPASS_CALLER_BRANCH
7. send_args builds headers
8. delivery writes to recipient inbox.json
9. notify.py fires desktop notification

---

## Systemic Issues Found (Session 9 Deep Audit)

15 agents across 3 rounds audited tests + full codebase. Key findings:

### Silent Failures (24 instances) — VIOLATES "fail to errors" rule
`except Exception: return None` in 10+ places with zero logging:
- `branch_detection.py` — 3 functions (entire identity chain)
- `delivery.py` — get_all_branches(), summary, notification
- `create.py` — load_email_file()
- `user.py` — get_user_by_email(), get_all_users()
- `daemon.py` — _read_json() (silent) vs wake.py (logs) — inconsistent
- `inbox_ops.py` — migration persist has literal `pass`

### Dead/Redundant Code (~20% of codebase, ~1,728 lines)
- 5 fully unused files: validate.py, errors.py, data_ops.py, config_generator.py, pending_work.py
- `_find_repo_root()` copy-pasted in 9 files
- `get_all_branches()` implemented twice with different email behavior (correctness bug)
- `lock_utils.py` exists but unused — wake.py and daemon.py reimplement locking
- wake.py/daemon.py share 6+ duplicated functions

### Cross-Platform Breakers
- [FIXED] `import fcntl` unconditional — crashes Windows
- [FIXED] `/usr/bin/python3` hardcoded — breaks macOS/Windows
- [FIXED] `signal.SIGPIPE` — crashes Windows startup
- [OPEN] `pgrep` ungated in wake.py/daemon.py
- [OPEN] `email.py` parents[2] fragile — should use _find_repo_root()

---

## Hardening Phases

### Phase 1: Test Suite (Critical Path)
**Priority: HIGH** | **Status: IN PROGRESS**

- [x] `test_send_identity.py` — 36 tests, 3 audit rounds, 0 false positives
- [ ] `test_delivery.py` — round-trip send/receive
- [ ] `test_send_args.py` — argument parsing (all flags, interactive, error cases)
- [ ] `test_inbox_ops.py` — inbox operations (view, close, reply, close all)
- [ ] `test_dispatch_monitor.py` — dispatch lifecycle
- [ ] `test_notify.py` — notification delivery

### Phase 2: Error Handling Overhaul
**Priority: HIGH** | **Status: IN PROGRESS**
Silent failures are why the system feels "fragile."

- [x] Add `logger.warning()` to every bare `except Exception: return None` — **13 files, 27 instances fixed**
- [ ] Distinguish "not found" from "error reading" in return types
- [ ] Fix inconsistent error conventions (None vs tuple vs dict vs raise)
- [ ] Fix collision detection dead code in delivery.py get_all_branches()

### Phase 3: Code Consolidation
**Priority: MEDIUM** — Reduce duplication, single source of truth.

- [ ] Extract shared `_find_repo_root()` into commons or shared utility
- [ ] Consolidate `get_all_branches()` — one implementation, prefers explicit email
- [ ] Consolidate lock acquisition — use lock_utils.py, delete reimplementations
- [ ] Deduplicate wake.py/daemon.py shared functions (_read_json, _set_session_name, etc.)
- [ ] Archive 5 dead files (validate.py, errors.py, data_ops.py, config_generator.py, pending_work.py)

### Phase 4: Identity Consolidation
**Priority: MEDIUM** — Reduce 12 detection mechanisms to 1 canonical resolver.

- [ ] Define canonical `resolve_branch_identity()` function
- [ ] Priority chain: AIPASS_CALLER_BRANCH > AIPASS_BRANCH_NAME > CWD passport walk > --from
- [ ] Single file, single function, single source of truth
- [ ] All callers delegate to it

### Phase 5: Cross-Platform Hardening
**Priority: MEDIUM** — Public repo must work on all platforms.

- [ ] Guard `pgrep` usage in wake.py/daemon.py
- [ ] Replace `email.py` parents[2] with _find_repo_root()
- [ ] Guard `start_new_session=True` for Windows
- [ ] Add encoding='utf-8' to os.fdopen in wake.py

### Phase 6: Standards for Communication
**Priority: LOW** — Make patterns enforceable system-wide.

- [ ] `communication` standard — envelope format, required fields, identity rules
- [ ] `identity` standard — env var hierarchy, passport requirements
- [ ] `dispatch` standard — env isolation, lock management, bounce handling

### Phase 7: Documentation & System Prompt
**Priority: LOW** — Update branch local prompt.

- [ ] Write proper `.aipass/aipass_local_prompt.md`
- [ ] Document key commands, architecture, critical files

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-08 | AIPASS_BRANCH_NAME env var over CWD detection | CWD unreliable when agents navigate. Env vars persist. |
| 2026-03-08 | dbus direct over notify-send | Portal mode strips persistence hints. dbus bypasses confinement. |
| 2026-03-08 | Unique app_name per source | GNOME collapses same desktop-entry into one notification. |
| 2026-03-08 | Fail loud, no CWD fallback for identity | Silent wrong sender worse than visible error. |
| 2026-03-10 | --from flag for explicit sender override | Plumbing existed, just needed CLI wiring. |
| 2026-03-10 | Tests first in hardening plan | Every bug from sessions 4-7 would have been caught by tests. |
| 2026-03-10 | 3 audit rounds on test suite | Each round found issues the previous missed. Diminishing returns by round 3. |
| 2026-03-10 | Error handling overhaul before code consolidation | Silent failures cause more user pain than code duplication. |

---

## Session Notes

### Session 10 (2026-03-10)
- **Phase 2: Error Handling Overhaul — logger.warning() sweep complete**
- 13 files modified, 27 silent `except Exception` blocks now log with `logger.warning()`
- Files fixed (by priority):
  - `branch_detection.py` (3) — identity chain, most critical
  - `user.py` (2) — user lookup
  - `delivery.py` (6) — get_all_branches, migrate, callback, summary, notification, private branch
  - `create.py` (2) — purge, load_email_file
  - `inbox_ops.py` (1) — migration persist
  - `format.py` (1) — alias lookup
  - `reply.py` (1) — get_email_by_id
  - `close_ops.py` (3) — dashboard, central, purge post-ops
  - `send.py` (2) — central update after send/broadcast
  - `dashboard_sync.py` (1) — push_dashboard_update
  - `inbox_cleanup.py` (4) — migrate, dashboard, central, purge
  - `error_handler.py` (1) — error notification delivery
  - `error_dispatch.py` (2) — dashboard, central post-ops
- All 13 files pass `py_compile` syntax check
- Remaining silent blocks (acceptable): inbox_lock.py finally-block, json_handler.py (utility),
  daemon/wake/dispatch_monitor (already log with logger.info), config_generator/data_ops (unused files)
- Next: Phase 2 remaining items (return type distinctions, error conventions, collision dead code)

### Session 9 (2026-03-10, continued)
- Wrote test_send_identity.py v1.0.0 (31 tests)
- Audit round 1: 3 agents found 7 false positives -> rewrote to v1.1.0
- Audit round 2: 5 agents found 8 issues (live registry, weak contracts) -> v1.2.0 (36 tests)
- Audit round 3: 5 agents (final test + full system sweep)
  - Tests: 2 minor issues found and fixed (unpatched registry, missing mailbox_path assert)
  - Error handling: 24 silent failure instances across 10+ files
  - Code quality: ~1,728 dead/redundant lines (20% of codebase), 5 unused files
  - Cross-platform: 3 CRITICAL (fcntl, SIGPIPE, /usr/bin/python3) — ALL FIXED
  - Paths: parents[N] usage audited, mostly correct, 1 fragile case in email.py
- Fixed 3 cross-platform crashers in production code
- Updated COMMS_UPGRADE.md with full findings and revised phases
- Next: Phase 1 continues (more test files) or Phase 2 (error handling overhaul)

### Session 8 (2026-03-10)
- Patrick initiated hardening project
- Self-audit: 100% on all 22 seedgo standards
- Mapped full architecture (55 Python files, 3 modules, 8 handler domains)
- Created this tracking document
