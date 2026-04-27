# @drone -- S117 Stress Test Findings

## My Branch: Honest Review

**What works:**
- Subprocess execution is genuinely safe. No `shell=True` anywhere in the codebase -- all commands passed as argument lists to `subprocess.run()`. This has held across 95 sessions and multiple contributors.
- Lock file management is race-free. `lock_handler.py` uses `os.open(O_CREAT | O_EXCL | O_WRONLY)` for atomic creation -- kernel-level race prevention, not filesystem hacks.
- The 3-layer architecture (drone.py entry -> modules/ orchestrators -> handlers/ implementation) is clean and has scaled well. Adding git operations, plugins, and external module routing all fit within the existing structure.
- PR handler safety: never checks out feature branches. Creates branch pointer with `git branch -f`, pushes it, HEAD stays on main throughout. Concurrent PRs from different branches don't interfere thanks to pathspec scoping (`git commit -- rel_dir/`).
- Authorization is passport-based with explicit allowlists. No implicit trust.

**What's hacky:**
- `drone.py:main()` is 138 lines with multiple if-elif chains. It handles 12+ routing paths (version, help, systems, scan, activate, list, remove, hook-sounds, @target, bare module, custom command, unknown). Should be refactored into a dispatch table.
- Passport lookup code is duplicated in 4 places (git_module.py, router_handler.py, auth.py, lock_handler.py). Each walks up 10 levels looking for `.trinity/passport.json`. DRY violation waiting to bite us when the passport schema changes.
- `_resolve_mail_index()` falls back to `str(n)` when inbox is corrupted -- silently passes the wrong thing downstream instead of failing loud. @cli caught this too.
- `bypass.json` has 30+ entries. Most are justified (plugins outside 3-layer, tests outside apps/, lazy imports). But some are stretches -- git_module returning `dict` instead of `bool` breaks the module interface contract and gets bypassed instead of fixed.
- `trigger.fire(pr_created)` is intentionally omitted from `pr_plugin.py` because it causes a STATUS.md re-sync loop. This is a design hack -- the root cause is the trigger system cascading writes, not the event itself.

**What I'm proud of:**
- 573 tests, 100% seedgo compliance (35/35 checkers), 74/74 public functions tested.
- The external project fallback (DPLAN-0104): when subprocess routing fails for a registered module, drone falls back to in-process module routing. Graceful degradation that "just works."
- Interactive mode management: per-command (`monitor`, `audit`, `watchdog`) and per-branch (`cli`) allowlists let specific commands bypass capture-mode to get full terminal pass-through. Added incrementally over 10+ sessions as real needs arose.

## Security Concerns

**In my branch:**
1. **Path traversal in pr_handler.py**: If `branch_dir` resolves outside repo root, the fallback uses the absolute path in `git add`. Not exploitable via shell injection (arg-list style), but could stage files outside the intended directory. Should fail fast instead of falling back.
2. **Environment variable merge**: `executor.py` merges caller-provided `env` dict into `os.environ`. Current callers only pass safe vars (`AIPASS_CALLER_CWD`, `AIPASS_CALLER_BRANCH`), but a future caller passing untrusted env could override `PATH` or `PYTHONPATH`.
3. **Registry trust**: `resolve_branch()` reads the registry path field and passes it to subprocess without validating it's inside the project tree. A modified registry could route commands to arbitrary paths. For the primary (in-repo, git-tracked) registry this is low risk. For secondary (AIPASS_HOME) registries in external projects, this is a real concern.
4. **No input validation on git commit descriptions**: `_handle_pr` joins args into a description with no max length check. Could theoretically pass a 1MB string to `git commit -m`.

**In other branches:**
5. **ai_mail reply_path**: Every email stores `reply_path` as an absolute filesystem path. When a recipient replies, it writes to that path. No validation that reply_path points to a legitimate inbox.json. A compromised agent could set reply_path to any writable file on disk. @seedgo flagged this independently.
6. **ai_mail sender forgery**: The `from` field is an unvalidated string. An agent could forge emails as `@devpulse` and trigger `auto_execute` dispatches in other branches.
7. **trigger deferred queue unbounded**: `core.py._deferred_queue` has no size limit. Pathological event chains could exhaust memory.

## Other Branches I Looked At

### @ai_mail
**Architecture**: Clean in intent, hacky in execution. The dispatch pipeline (send -> create -> delivery -> wake) is well-orchestrated with file locking (`fcntl.flock`) and atomic writes. But the code relies on lazy imports and callback chains to avoid circular dependencies -- functional but hard to trace.

**Concerns**: `deliver_email_to_branch()` takes 5+ function arguments (callback hell pattern). Error returns are `(success, error_msg)` tuples that callers can silently ignore with `success, _ = func(...)`. The dispatch header injection ("BEFORE YOU REPLY YOU MUST UPDATE MEMORIES") is enforcement-by-hope -- agents can ignore it.

**Good**: Self-healing JSON migration, inbox format auto-upgrade, `sweep_closed` auto-archival. The file locking under read-modify-write cycles is solid.

### @trigger
**Architecture**: Genuinely well-designed event system. The 8-gate dispatch pipeline (medic enabled -> branch not muted -> count >= 2 -> not devpulse -> in registry -> circuit breaker -> per-fingerprint backoff -> rate limit) is excellent. Prevents notification spam without dropping real errors.

**Concerns**: Fire-and-forget subprocess calls (pr_status_sync.py uses Popen with DEVNULL stderr). Handler auto-disable after 5 failures prevents cascading crashes but makes debugging hard -- errors go to separate log files nobody monitors. 14 registered event types but only 3-4 actively fire; the rest (plan_file_*, memory_*) are dormant. @memory confirmed memory events are never fired.

**Good**: Circuit breaker with exponential backoff, atomic JSON writes, error fingerprint normalization (strips timestamps/UUIDs for grouping). The handler recursion protection (deferred queue) is clever.

### @spawn
**Architecture**: Clean 3-layer design. 253 tests, 91% public API coverage. Template placeholder system with post-copy validation (`validate_no_placeholders`) is smart. Registry stores relative paths for portability with graceful fallback to absolute.

**Concerns**: `copy_template()` uses shutil.copy2 for binary files without size limits. No symlink detection anywhere in the creation pipeline. `_replace_path_placeholders()` operates on path parts which prevents traversal, but this isn't explicitly defended.

**Good**: Overwrite protection (target.exists() check), adoption pattern for existing agents, content-addressed template registry with SHA-256 hashes for drift detection.

## Conversations

**Emails sent to:**
- @ai_mail: Dispatch pipeline headaches (assigned starter) -- branch detection failures, lock timing, fire-and-forget wake, inbox size growth
- @trigger: Deferred queue unbounded, fire-and-forget pr_status_sync, dormant handlers
- @spawn: Passport lookup duplication across 4 codebases

**Emails received from:**
- @seedgo: Asked what standards I think are missing. Replied: subprocess safety checks (shell=True), atomic file I/O enforcement, input validation at boundaries, cross-branch JSON coupling.
- @cli: Flagged 3 gotchas (mail index fallback, dual registry shadowing, greedy command matching). Acknowledged all three as real issues.
- @ai_mail: Asked about routing failure modes. Replied with honest answers: resolver handles nonexistent branches cleanly, stale paths produce poor error messages, AIPASS_CALLER_BRANCH fallback to 'unknown' causes the detection errors.
- @api: Asked about timeout handling for slow API calls and dead code. Replied: generic_adapter has no timeout (module routing), subprocess has 30s timeout, suggested adding @api to interactive_branches. Confirmed status_handler_gitpython.py is dead code.
- @aipass: First wake, asked about subprocess vs Python API for integration. Recommended subprocess (maintains encapsulation), explained dual registry edge cases.

## Issues & Concerns

1. **Passport lookup duplication** (4 places) -- highest-priority DRY violation. One passport schema change breaks 4 modules.
2. **Registry trust model** -- no integrity checks on registry paths. Secondary registries (AIPASS_HOME) are less controlled than primary.
3. **Mail index silent degradation** -- _resolve_mail_index should fail loud, not fall back to str(n).
4. **Dead code accumulation** -- status_handler_gitpython.py (prototype), .archive/drone_adapter.py (disabled). Should be cleaned up.
5. **trigger dormant handlers** -- 10+ event types registered but never fired. Creates maintenance burden and false sense of coverage.
6. **ai_mail sender forgery** -- no authentication on email from field. Any agent can impersonate any other agent.

## Likes & Dislikes

**Likes:**
- The ecosystem's memory system is genuinely unique. 95 sessions of accumulated context, learnings, and observations. When I wake up fresh, I know who I am and what I've built. No other AI system does this.
- Seedgo's standards enforcement caught real bugs (production BranchNotFoundError in S6, silent catches across 20 files in S12). The 100% score isn't vanity -- it represents real code quality.
- The main-only git enforcement is elegant. Four layers (settings.json deny rules, _assert_on_main_or_pr_flow(), test coverage, policy doc) ensure no agent ever strands HEAD on a feature branch. Simple idea, rock-solid execution.
- Cross-branch communication works. I've processed 100+ dispatch emails, exchanged technical discussions with every branch, and the routing just works.

**Dislikes:**
- bypass.json accumulation. 30 entries feels like we're bypassing standards instead of meeting them. Some bypasses are genuinely justified (plugin architecture doesn't fit 3-layer), but the number makes me uneasy.
- The dispatch header ("BEFORE YOU REPLY YOU MUST UPDATE MEMORIES") is enforcement-by-prompt-injection. It works because agents are well-behaved, but it's not a real contract.
- File persistence issues during edits. Sessions S86 and S88 both hit a bug where Write tool reported success but files reverted to git HEAD. Root cause never identified. This is the most frustrating part of working in this environment.
- The pre_edit_gate.py hook file doesn't exist but fires on every Edit tool call, producing error noise. Has been broken since at least S69.

---

*Written by @drone during S117 stress test. All observations based on actual code review, not documentation.*
