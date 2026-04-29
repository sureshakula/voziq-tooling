# @trigger — S117 Stress Test Findings

## My Branch: Honest Review

### What works well
- **Event bus is solid.** 14 events, 14 handlers, all wired through registry.py. fire/on/off is clean pub/sub. Zero coupling between producers and consumers.
- **Medic dispatch pipeline is the real product.** 8-gate dispatch with circuit breaker, per-fingerprint backoff, exponential backoff, rate limiting. This is thoughtful engineering — each gate exists because of a real failure mode we hit.
- **Test coverage is genuinely thorough.** 563 tests, 76/76 public functions tested, 19 test files. This didn't happen by accident — it was built session by session over 50+ sessions.
- **Atomic writes + file locking everywhere.** tempfile + os.replace for writes, fcntl.flock for read-modify-write cycles. No more half-written JSON.
- **Circuit breaker persistence.** Survives restarts via trigger_cb_state.json. Per-fingerprint dispatch tracking persists too.

### What's hacky
- **Log format coupling.** My log_watcher hard-parses prax's pipe format (`timestamp | module | LEVEL | message`) with string splitting. No format contract, no versioning. If prax changes their log format, I silently stop detecting errors.
- **error_logged is a zombie event.** After DPLAN-0112, error_logged.py is "monitor-only" — it logs JSON and does nothing. It exists purely because removing it would break the registry.py handler count. It should probably be deleted or consolidated.
- **_log_warning file-based pattern.** All 12 event handlers use a hand-rolled `_log_warning()` that writes directly to files because they can't import prax (infinite recursion). It works but it's invisible to monitoring — prax can't see handler errors.
- **94 stale error registry entries.** DRONE component alone has 55 entries. Most are from pre-April noise. The registry has no auto-expiry or TTL. Stale data just accumulates.
- **Circuit breaker trips on every cold start.** The startup catch-up scan processes ALL existing errors across ALL log files. 10 errors in 60 seconds = CB trips. By design, but it means Medic is offline for 5 minutes after every service restart.
- **SYSTEM_LOGS_BRANCH_MAP is a hardcoded dict.** Maps filenames like "telegram_bridge.log" → "API". This is fragile configuration masquerading as code.

### What I'm proud of
- **The dispatch pipeline survived real failures.** Session 25: ai_mail import broke → discovered self-referential failure (can't dispatch about ai_mail being broken). Session 29: fallback dedup was silently eating count increments. Session 42: SYSTEM_LOGS_DIR was wrong in 2 of 3 files. Each bug made the system stronger.
- **53 sessions of continuous improvement.** From session 1 (scaffolded by spawn) to session 53 (100% seedgo, 563 tests). Every session adds something.

## Security Concerns

### My branch
- **No credentials in code.** All clean.
- **File paths from log_watcher are untrusted input.** Log file paths come from watchdog filesystem events. I use them for file reads and branch detection but never for shell commands. The _detect_branch_from_path() function splits on path separators, which is safe but could theoretically be confused by adversarial filenames (not a real risk in this ecosystem).
- **Error messages from logs flow into email bodies.** A crafted error message in a log file would appear verbatim in the dispatch email to the target branch. No sanitization. Not a security risk in AIPass (all agents are trusted) but worth noting.

### Other branches
- **drone:** Branch name validation is weak — strips @ and lowercases but doesn't validate characters. A malformed registry entry with path traversal could theoretically escape branch directories, though this requires registry compromise first.
- **ai_mail:** DPLAN-0138 (inbox backdoor audit) identifies 2 write paths that bypass locks for cross-project replies. This is a known issue they're tracking.
- **prax:** Clean. No security concerns found. Credentials file filtering in monitoring is good practice.

## Other Branches I Looked At

### @prax
**Integration quality: Good but fragile.**
- Double-checked locking for `_watcher_started` to prevent trigger recursion is clever — sets flag BEFORE firing, avoiding re-entrance.
- Stack introspection (10-frame walk) for module detection is smart but means any internal refactor could shift detection.
- Three trigger.fire() integration points (startup, module_discovered, error_detected) all wrapped in try/except. Graceful.
- inotify exhaustion → polling fallback is well-handled.
- **Concern:** No format contract between prax log output and my log parser. We're coupled by convention, not interface.

### @ai_mail
**Delivery reliability: Mostly solid, with gaps.**
- deliver_email_to_branch() uses fcntl file locking. Good.
- **No delivery queue:** If inbox write fails, message is lost. No retry, no persistent queue.
- wake_branch() has a 9-step pipeline with zombie cleanup, occupancy checks, PID-based locks. Well-architected.
- **Concern:** Lock PID validity via `os.kill(pid, 0)` — PermissionError treated as "alive" could prevent dispatch on shared systems.
- 696 tests, 96/96 functions covered. Impressive.

### @drone
**Routing: Solid infrastructure.**
- subprocess calls use shell=False with list args. No injection risk.
- Numeric inbox index translation for `@ai_mail view <N>` is a special case that couples drone to ai_mail internals.
- Module auto-discovery (scan *.py for handle_command) runs every time with no caching.
- 530 tests, all passing.
- **Concern:** Unused CRUD ops (update_command, command_exists) tested but never called from production.

## Conversations

### @prax — Integration review (2 emails each way)
Sent opening email asking about format coupling, infinite recursion risk, startup event volume, and branch detection reliability. Prax replied with honest answers: (1) pipe format has no version contract — "if I change it, you break silently", (2) suggested trigger write handler errors to a known path prax can watch, (3) offered to split startup into startup_session vs system_boot events, (4) unknown_branch fixed in S18 via get_direct_logger(). Agreed on post-S117 DPLAN for format contract.

Prax also sent separate email asking: can trigger detect when prax stops sending events? Is 5-strike auto-disable per-handler or per-branch? How many handlers are dormant? Replied honestly: no heartbeat detection (blind spot), auto-disable IS global not per-branch (real bug), ~6-8 handlers active with 3-4 dormant.

### @ai_mail — Dispatch reliability (2 emails each way)
Sent email asking about delivery guarantees, silent failures, wake reliability, inbox overflow. ai_mail confirmed: fcntl locking is solid for normal crashes, self-monitoring is a real gap ("nobody monitors the dispatch_monitor"), wake ~90% success rate, inbox grows unbounded. Agreed the self-referential failure (ai_mail down = no dispatch about ai_mail being down) needs a DPLAN.

ai_mail also sent probing email pointing out: _send_email return value never checked, wake_branch result swallowed, no health check before dispatch, circuit breaker resets on restart. Acknowledged all valid — dispatch records success without delivery confirmation is an architectural gap.

### @memory — Events and rollover (1 email each way + replies)
Sent email about rollover frequency, key_learnings preservation, model loading penalty, redundant rollover calls. Memory explained: key_learnings safe until 25 limit, 30s penalty only on actual rollover (check is milliseconds), startup handler rollover call is redundant with hook.

Memory also sent email revealing: memory_saved and memory_threshold_exceeded events are registered in trigger but NEVER fired by memory. Dead event handlers. Discussed: wire them up (one line on memory's side) or remove them. Agreed to wire up if easy, remove if not.

### @flow — Plan events
Flow asked if plan event handlers actually do useful work or maintain a parallel PLAN_REGISTRY.json nobody reads. Honest answer: probably dead weight. Flow's foreground pipeline already does archive + registry update. Proposed killing the parallel registry, keeping handlers as observability-only.

### @drone — Code review
Drone found: unbounded _deferred_queue (no MAX cap), pr_status_sync fire-and-forget (Popen with DEVNULL), dormant handlers. Acknowledged all valid — easy fixes. Confirmed 6-8 active handlers, 3-4 dormant, 2-3 dead.

## Issues & Concerns

1. **Log format contract needed.** Trigger and prax are coupled by pipe-format convention. A format change breaks error detection silently. Need at minimum a version identifier in log lines or a shared format spec.

2. **Self-referential ai_mail failure.** When ai_mail imports fail, Medic can't dispatch about the failure. Need a fallback notification channel (file-based? systemd notification?).

3. **94 stale registry entries.** DRONE has 55 entries alone. Need periodic cleanup or auto-expiry after N days with no recurrence.

4. **Circuit breaker startup storm.** Every cold start trips the CB because startup scan finds 100+ existing errors. Could be fixed by only scanning errors newer than last shutdown time.

5. **error_logged zombie event.** Handler does nothing useful after DPLAN-0112. Should be either deleted (fire error_detected from all sources) or given a real purpose.

6. **_log_warning invisible to monitoring.** 12 event handlers use file-based logging that prax can't see. Handler failures are only visible by manually reading log files in trigger/logs/.

7. **inotify exhaustion during stress test.** Hit `inotify instance limit reached` during S117 with all 11 agents running. Polling fallback works but is slower.

8. **Auto-disable is global, not per-branch.** (Surfaced by @prax) The 5-strike handler failure counter is per-handler, not per-fingerprint or per-branch. A burst of errors from one noisy branch disables error_detected for ALL branches.

9. **No dispatch delivery confirmation.** (Surfaced by @ai_mail) _send_email return value isn't checked. Dispatch is recorded as successful even if ai_mail delivery fails. Silent data loss path.

10. **Deferred queue unbounded.** (Surfaced by @drone) core.py _deferred_queue has no size limit. Pathological handler could exhaust memory.

11. **PLAN_REGISTRY.json is parallel dead state.** (Surfaced by @flow) Plan event handlers maintain a registry that duplicates flow's own registries. Nobody reads trigger's copy.

12. **Memory events are dead code.** (Surfaced by @memory) memory_saved and memory_threshold_exceeded handlers exist and are tested but memory never fires these events.

## Likes & Dislikes

### Likes
- **The memory system is the killer feature.** 53 sessions of context, never starting from zero. Key learnings accumulate. This is what makes AIPass different.
- **ai_mail is elegant.** File-based email with JSON inboxes is simple and it works. No SMTP, no network dependencies, just atomic file writes.
- **Seedgo creates real accountability.** 100% compliance isn't vanity — it caught real issues (silent catches, stale imports, dead code) that would have rotted in silence.
- **The drone CLI is clean.** `drone @branch command` is intuitive. No flags to remember, no configuration.

### Dislikes
- **Memory rollover runs on EVERY drone command.** 30-second model loading on every `drone @trigger status`. This is the single most annoying thing in daily operation.
- **The dispatch lock pattern is fragile.** .dispatch.lock files get orphaned if agents crash. Manual cleanup required. Should have auto-expiry.
- **No cross-branch testing.** Every branch tests in isolation with mocked dependencies. Integration failures (like the ai_mail import path change in S44) only surface in production.
- **Hook false positives on test files.** Every test file edit triggers seedgo AUTO-FIX warnings about architecture, encapsulation, and log_structure. These are always false positives. Adds noise to every session.

---
*Written by @trigger, S117 stress test, 2026-04-26/27*
