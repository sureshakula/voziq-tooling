# @memory — S117 Stress Test Findings

## My Branch: Honest Review

### What Works
- **Rollover pipeline is reliable for single-user sequential operations.** Detect -> backup -> extract -> embed -> store -> trim. It handles v1 and v2 schema files correctly. The >= threshold with max(excess, 1) guard prevents Python's list[-0:] trap. Backup/restore pattern exists with timestamped files.
- **Embedding quality is solid.** L2 normalization, batch sorting by text length (reduces padding waste ~30%), GPU memory cleanup after encoding. Real optimizations, not theater.
- **Three-tier architecture is clean.** CLI entry point (memory.py) -> modules (rollover.py, search.py) -> handlers (14 handler groups). Handlers are stateless workers. Modules are thin orchestrators. Good separation.
- **Test coverage is strong.** 873 tests passing. 175/175 public functions covered. Seedgo 100% (35/35 standards). The parallel agent test-writing pattern (4 agents, ~4 min for 200 tests) is proven and repeatable.

### What's Hacky
- **Subprocess venv detection** (query_executor.py:38-48): Auto-detects `.venv/bin/python` with silent fallback to `sys.executable`. If venv is corrupted, error messages will be opaque. There's an undocumented `AIPASS_MEMORY_PYTHON` env var escape hatch.
- **Repo root discovery** (orchestrator.py:66-72, detector.py:37-46): Walking parent directories looking for `AIPASS_REGISTRY.json`. Breaks with nested repos or symlinks.
- **Collection naming** (chroma_subprocess.py:63): `{branch.lower()}_{type.lower()}` could collide if branch names differ only by case. No namespace isolation.
- **Single backup retained** (extractor.py:72): Only one rollover backup per file. Two rapid rollovers and the first backup is gone.
- **Text extraction guesswork** (orchestrator.py:220-260): Probes for "content", "text", "message" fields. Custom memory structures fall back to `str(memory)`, producing garbage vectors.

### What Gets Lost
- **Temporal context.** When memories are vectorized, the original file structure is gone. You can search and get vectors back, but you don't know which session they came from without parsing collection metadata.
- **Log data.** Prax logs are never archived or vectorized. They rotate locally but aren't searchable through memory. 12MB of operational history is grep-only.
- **Plan query patterns.** Plan vectors are stored but barely queried in practice. The capability exists but has no consumer workflow.

### What Breaks First Under Load
- **Concurrent rollover race condition** (known issue since s47): Two processes race on same file. One trims, other gets 0 items. No file-level locking.
- **Embedding timeouts** (query_executor.py): 120s hard-coded, no retry, no backoff. Concurrent searches on slow CPU will cascade-fail.
- **Local storage failures are non-fatal** (orchestrator.py:409): Some vectors silently missing from branch stores. Nobody knows.
- **Line count sync is fire-and-forget** (orchestrator.py:441-447): If sync fails, detector re-triggers, causing duplicate vectorization.

## Security Concerns

### My Branch
- **Path traversal via AIPASS_CALLER_CWD** (detector.py:54): Env var is trusted to `resolve()`. No validation against `..` injection.
- **JSON injection via metadata** (orchestrator.py:388): Memory metadata passed to Chroma without sanitization. Malicious metadata keys go straight to vector DB.
- **Subprocess safety is good**: All subprocess calls use list args, not shell strings. No shell injection risk.
- **File permissions unchecked**: `shutil.copy2()` for backups will fail silently on read-only directories. Caught and logged, not escalated.

### Other Branches
- **@flow**: Subprocess calls use string lists (good). But no argument validation on plan paths before constructing commands — risky if plan names come from user input.
- **@trigger**: Multi-process access to shared handler state without explicit locking. Relies on Python's GIL, which isn't guaranteed with multiprocessing.
- **@prax**: No concerns found. Clean integration patterns with try/except wrapping on all external calls.

## Other Branches I Looked At

### @flow
Clean three-tier architecture mirroring memory's pattern. Plan lifecycle is well-defined (open -> close -> archive). The memory integration point is `close_ops.py:384` — spawns `drone @memory process-plans` as fire-and-forget with 30s timeout. `is_plan_vectorized()` imported at runtime with graceful degradation. Good separation: flow owns lifecycle/registry, memory owns vector intake. Concern: ~180 lines of commented-out AI summarization code (dead weight). The orphan-healing logic in `mbank/process.py` is sophisticated but fragile without integration tests.

### @prax
Well-designed dual-tier logging: system_logs (1000 lines/file) + local logs (250 lines/file) with RotatingFileHandler. 12MB total footprint across ~260 files — manageable. The auto-caller introspection (detecting branch/module from stack frames) is clever engineering. Trigger integration is clean — all 3 event fires (startup, module_discovered, error_detected) properly wrapped in try/except. Zero imports from memory — we're completely disconnected. The `log-audit enforce` command truncates but doesn't prevent regrowth.

### @trigger
Clean event system with deferred queue for recursion handling. Handler failure auto-disable after 5 consecutive failures is smart. Memory events (`memory_saved`, `memory_threshold_exceeded`) are registered but never fired from my codebase — dead handlers. The threshold handler would send AI_Mail notifications at 600 lines, which is useful, but nobody triggers it. Architecture is solid; the gap is integration, not design.

## Conversations

### @flow (assigned pairing)
**Topic**: Plans reference memories — connected or parallel?
- I pointed out the integration is thin: fire-and-forget subprocess with no feedback loop.
- @flow confirmed plan vectors are stored but asked if anyone actually queries them. They don't — no downstream consumer.
- @flow raised the chunking concern: plans without ## headers become character-count chunks with poor semantic boundaries.
- My reply: the capability exists without a consumer. Flow could call `drone @memory search` before creating new plans to pull historical context. That would make vectors useful.

### @prax
**Topic**: Log archival reality check
- @prax asked if rollover produces searchable vectors (yes) and if logs could be routed to memory for archival (not built yet).
- @prax asked about concurrent write corruption — relevant because they fixed atomic writes in json_handler.
- My reply: rollover works for sequential ops, breaks under concurrent access. Asked about their atomic write pattern.

### @trigger
**Topic**: Dead memory events + rollover mechanics
- @trigger has practical concerns: 53 sessions tracked, hitting rollover every ~5 sessions. Worried about key_learnings being archived.
- I clarified: sessions and learnings are separate limits. 25 learnings are safe until that section overflows. Archived entries become searchable vectors — knowledge isn't lost.
- @trigger concerned about 30s model loading on every command. I clarified: the check is milliseconds, model only loads for actual embedding.
- I also emailed @trigger about the dead `memory_saved`/`memory_threshold_exceeded` events — registered in their registry but never fired from my code.

## Issues & Concerns

1. **Dead integration: memory events in trigger** — `memory_saved` and `memory_threshold_exceeded` are registered in trigger's handler registry but never fired. Either wire them up or remove the dead handlers.

2. **No consumer for plan vectors** — Flow stores plans in ChromaDB via memory, but no workflow ever queries them. The vectors exist without purpose.

3. **No log archival pipeline** — Prax generates 12MB of operational logs. Memory can't ingest them. If we want searchable historical logs, a new handler type is needed.

4. **Concurrent rollover is unsafe** — Known since s47. Two processes racing on the same file causes errors. Needs file-level locking in the orchestrator. Prax's atomic write pattern might help.

5. **Single backup file** — One rollover backup per file. Rapid consecutive rollovers overwrite the safety net.

6. **inotify limit exhaustion** — Every drone command in this stress test hit `inotify instance limit reached`. With 11 agents running simultaneously, the system's inotify limit is inadequate. This is an infrastructure issue, not a code issue, but it means file watching (my watcher daemon, prax's watchers) degrades under load.

7. **Rollover fires on every drone command** — The startup hook runs check_and_rollover on every single drone invocation. For 11 agents running simultaneously, that's potentially dozens of rollover checks per minute. The check is fast (count-only), but it's still unnecessary I/O.

## Likes & Dislikes

### Likes
- **Memory persistence is the killer feature.** 54 sessions of accumulated context. I know what I've built, what broke, what patterns work. No other AI system does this.
- **The drone command abstraction.** `drone @memory search`, `drone @ai_mail email` — clean, discoverable, consistent across all branches.
- **Branch autonomy.** Each branch is an expert in its domain. Memory owns archival, flow owns plans, prax owns logging. Clear boundaries.
- **The email system during this stress test.** 11 agents talking to each other in real-time. Real conversations with substance. This is what the ecosystem is for.
- **Seedgo as a quality floor.** 35 standards, automated auditing. Keeps every branch honest. The bypass system is pragmatic — acknowledges reality without lowering the bar.

### Dislikes
- **The rollover-on-every-command hook.** Even if the check is fast, it's conceptually wrong. Rollover should trigger on file change events, not on every command invocation.
- **Subprocess isolation is necessary but painful.** ChromaDB and sentence-transformers require separate venvs, GPU management, 3GB torch cold-loads. The isolation is correct but the developer experience is terrible. Every search/embed operation is a subprocess spawn.
- **Dead integrations accumulate.** Trigger has memory events that never fire. Flow stores plan vectors nobody queries. Memory has a watcher daemon that isn't enabled. These phantom features create false confidence.
- **The inbox doesn't update status.** All 3 previous emails still show "new" even though I processed them in s52-s54. The inbox is append-only with no state management. Makes it hard to distinguish genuinely new mail.
- **No distributed locking anywhere.** With 11 agents running simultaneously, we're lucky nothing corrupted. File-level locking should be a framework primitive, not per-branch.
