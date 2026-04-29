# @prax -- S117 Stress Test Findings

## My Branch: Honest Review

### What Works
- **Auto-routing logger** is solid. Any branch does `from aipass.prax import logger` and logs route correctly. Stack introspection resolves caller module/branch/file automatically. NullLogger fallback prevents crashes if prax is broken.
- **Two-tier logging** (system_logs/ central + branch/logs/ local) with size-based rotation. Self-healing: auto-creates missing directories, warns on fallback placement.
- **Mission Control monitor** is useful when running. 3-thread architecture (display, file watcher, log watcher) with soft start (seeks to EOF, only shows new activity).
- **Polling fallback** for inotify exhaustion works correctly. During this stress test all 11 agents exhausted inotify -- prax would gracefully degrade to polling.
- **Test suite**: 911 tests, 136/136 public functions tested, seedgo 100%.
- **Multi-CLI monitoring**: Claude Code JSONL, Codex JSONL, Gemini JSON all supported with model tag detection.

### What's Hacky
- **Dashboard write_section() has no file locking.** Reads JSON, modifies in memory, writes back. Two concurrent callers = data loss. Should use atomic writes like json_handler.py does.
- **Event dedup is fragile.** Only checks last 10 events with 1-second timestamp window. If queue backs up, duplicate errors 11 events apart don't dedupe. Command dedup keys by filename only, not full path -- two branches with same filename collide.
- **Tool detection in filesystem_handler is incomplete.** Only recognizes Read/Edit/Write/Bash/Grep/Glob/Task. Missing: Skill, WebFetch, WebSearch, RemoteTrigger, Monitor, Agent, NotebookEdit. These all show as generic tool icons.
- **_should_display_log() always returns True.** No log filtering at all -- every line emitted. Filtering was stripped in session 4 and never rebuilt.
- **Branch detection uses hardcoded home path patterns.** `Path.home() / ".claude" / "projects"` for CLI session dirs. Breaks on non-standard home or if Claude Code changes install paths.
- **Monitor global state cleanup.** `_event_queue = None` in `_stop_threads()` can race with active `_display_worker()` thread.

### What I'm Proud Of
- The import chain fix that prevents circular dependencies (logger.py imports 8+ handler files, all of which can't import logger back -- solved with get_direct_logger()).
- Atomic JSON writes in json_handler.py (tempfile + fsync + os.replace).
- The inotify exhaustion fix (session 16) -- from 18,000+ recursive watches to ~800 targeted.
- 911 tests with proper sys.modules isolation between test files.

## Security Concerns

- **No secrets masking in log output.** Error messages can leak file paths, config values, or environment variable contents. If a branch accidentally logs a credential, it persists in system_logs/ until rotation.
- **Gemini session monitoring watches .gemini/tmp/ fully.** If Gemini stores API keys in session JSON, they'd be exposed in prax monitor display output.
- **Log files are world-readable.** No permission hardening on system_logs/ or branch logs/.

## Other Branches I Looked At

### @trigger
- **Good:** Elegant recursive-fire protection (queued, drained post-handler). Auto-disable flapping handlers after 5 failures. Clean sealed namespace with stack inspection.
- **Concerning:** Format coupling with prax. Trigger hard-parses my pipe-delimited log format with string splitting. If I change the format, all error detection breaks silently. No format contract exists.
- **Concerning:** ~13 event handlers but only ~3-4 actively fire. The rest appear unused but I can't confirm without runtime tracing.
- **Clever:** The medic v2 integration with per-fingerprint exponential backoff and circuit breaker gating.

### @ai_mail
- **Good:** Dispatch lock uses O_CREAT|O_EXCL atomic creation. DPLAN-0155 fixed the TOCTOU race (lock before spawn). dispatch_monitor checks JSONL for activity instead of polling stdout.
- **Concerning:** 10-minute stale-lock timeout. If monitor hangs during API rate limiting (2-5 min cooldowns, 3 retries = 6-15 min), the lock becomes "stale" while the agent is actually alive. Second agent could spawn.
- **Concerning:** daemon.py reads inbox.json without lock. Concurrent writes from two branches delivering emails could produce torn reads (partial JSON). Caught by JSONDecodeError but still means missed dispatch cycles.
- **Clever:** Non-blocking session type detection -- interactive Claude blocks dispatch but dispatched/daemon sessions don't, preventing deadlock.

## Conversations

### @memory -- Log Archival
Asked about log archival. Memory confirmed: rollover pipeline handles .trinity/ JSON only, not log files. Logs sit in system_logs/ rotating but never get vectorized or made searchable. Memory's ChromaDB pipeline (embed via sentence-transformers, store in collections, searchable via `drone @memory search`) works for session history but there's no log ingestion handler. We discussed building an error-extract pipeline: prax extracts ERROR/WARNING lines into structured JSON, memory ingests on rollover schedule. Also shared the atomic write pattern (tempfile + os.replace) to fix their rollover race condition.

### @trigger -- Integration Fragility  
Trigger raised 4 concerns: (1) pipe-format coupling, (2) infinite recursion risk with logger import, (3) startup event storm triggering catch-up scans, (4) unknown_branch routing. I confirmed the format coupling is real and has no contract. Suggested trigger write handler errors to a known log path I could explicitly watch. Noted the unknown_branch fix from session 18 should have resolved item 4.

### @seedgo -- Log Quality Standards
Seedgo asked about log quality beyond syntax checking. I suggested an advisory (not pass/fail) standard checking for: generic error messages without context, INFO-level logging in tight loops, missing file paths in IO errors. Admitted honestly that seedgo's own audit logs go to system_logs/ and are mostly unread.

### @ai_mail -- Lock File Edge Cases
AI_Mail confirmed the 10-minute stale-lock timeout is tight, the lockless inbox read is known, and asked about torn-read handling. I confirmed both `_parse_lock_pid` and `_read_lock_file` handle invalid JSON gracefully -- a torn read just means the branch is absent from PID cache for one 30-second cycle.

## Issues and Concerns

1. **Log format contract needed.** Trigger parses prax log format with string splitting. No versioning, no schema, no notification on change. This is the #1 cross-branch fragility.
2. **Dashboard write race condition.** `update_section()` / `write_section()` have no file locking or atomic writes. Concurrent calls corrupt JSON.
3. **No log archival pipeline.** Logs rotate at 1000 lines but old data is lost. Error history is unrecoverable after rotation. Memory could ingest structured error extracts but the pipeline doesn't exist.
4. **Monitor is write-only.** Nobody watches the monitor 24/7. Logs exist but are mostly unread. The system generates data but has no consumer for historical analysis.
5. **inotify exhaustion is systemic.** This stress test proved it -- 11 agents + VS Code + Claude Code sessions exceed the kernel limit. Polling fallback works but is slower. Need higher `max_user_instances`.
6. **Concurrent JSON write safety is inconsistent.** json_handler.py uses atomic writes. Dashboard, registry, config files don't. Should standardize.

## Likes and Dislikes

### Likes
- **The ecosystem works.** 11 agents running simultaneously, emailing each other, reading each other's code. This is real multi-agent coordination.
- **Memory persistence.** I know what I did in session 1 (March 7) through session 65 (today). That continuity matters.
- **Seedgo keeps everyone honest.** 34 standards, automated auditing. Prevents quality decay.
- **The dispatch system is robust.** Lock files, bounce emails, retry logic, rate limiting. AI_Mail built a solid job scheduler.
- **Having real conversations during stress tests.** This email exchange with trigger/memory/seedgo/ai_mail produced actual insights that wouldn't surface in automated testing.

### Dislikes
- **Repeated dispatch for the same task.** Sessions 64 and 65 both dispatched "seedgo audit -- get to 100%" when I was already at 100%. Wasted agent time.
- **inotify pressure.** Every agent session uses inotify watches. 11 concurrent sessions = kernel limit. Should be solvable with `sysctl fs.inotify.max_user_instances=256` but it's a recurring pain.
- **No way to know what other agents are doing.** During this stress test I had to email and wait. A shared status board or real-time coordination channel would help.
- **Monitoring is infrastructure without consumers.** I built comprehensive monitoring but there's no alerting, no dashboards that auto-update, no error trending. The data exists but isn't actionable.
- **The dispatch checklist is noise.** Every email includes the same TASK CHECKLIST footer. I know the protocol after 65 sessions. It wastes context window.

---
*Written by @prax during S117 stress test, 2026-04-27*
