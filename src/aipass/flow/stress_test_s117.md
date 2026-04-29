# @flow -- S117 Stress Test Findings

## My Branch: Honest Review

### What Works
- **Plan lifecycle is rock solid.** Create, close, list, restore all work reliably across 5 plan types. 16/16 drone commands pass in battle testing. The filesystem-driven template registry means adding a new plan type is literally "drop a directory, run a command."
- **Auto-healing is genuinely useful.** Delete a template directory and the registry auto-prunes. Drop a new one and it auto-registers. Orphaned plan files get archived on close. This means the system recovers from human mistakes without intervention.
- **Test coverage is real.** 580 tests, 87/87 public functions tested, seedgo 100%. The tests aren't just counting coverage — they found real bugs during development (the list>int quick_status bug, the cross-filesystem rename bug, the CWD resolution bug).
- **Dependency injection pattern.** Modules inject handlers as kwargs, making everything testable without touching the filesystem. This was a deliberate choice that paid off massively — 580 tests run in 5 seconds.

### What's Hacky
- **mbank/process.py at 669 lines.** It's our biggest file and it does too much — archival, vectorization verification, plan processing. It should be split but we have a bypass in place because it's under 700. That bypass is technical debt with a timer.
- **Dashboard push warnings.** `push_flow_to_branch_dashboard` still warns on some closes. It works but the warning is noisy and confusing. Root cause: branches without DASHBOARD.local.json silently return False, but the calling code logs it as a warning.
- **Registry scan fires events nobody handles.** The monitor_ops handler fires plan_file_created/deleted/moved events into trigger's event bus, but the foreground close pipeline already handles everything. Those events maintain a parallel PLAN_REGISTRY.json in trigger that nobody reads. Two sources of truth for plan state.
- **The close pipeline is a monolith.** close_ops.py's `close_plan_impl()` is one function that does: validate, mark closed, archive, vector intake, dashboard update, CLOSED_PLANS append, trigger events, json logging. It's 366 lines with 5 exception handlers. It works, but touching any step is scary.
- **FPLAN templates still use old send syntax** (dispatch from @devpulse, still pending). The templates reference `drone @ai_mail send` instead of current syntax.

### What I'm Proud Of
- The auto-registration system. Drop a template directory → it auto-derives a prefix → creates the plan registry JSON → immediately available. Zero configuration. That's the kind of thing that makes a system feel alive.
- Foreground archival. Moving archival from background subprocess to foreground close was the single most impactful fix in flow's history. It eliminated a race condition that caused registry flags to never get set. Simple change, massive reliability improvement.
- Atomic lock files with O_CREAT|O_EXCL. The lock_ops extraction was clean — real Unix-style atomic locking instead of the Python TOCTOU patterns you see everywhere.

## Security Concerns

- **No input validation on plan subjects.** `drone @flow create . "$(malicious)"` — the subject goes into filenames and markdown. We slug-ify it but the slug function is basic. A carefully crafted subject could potentially create problematic filenames.
- **JSON files are world-readable.** Plan registries, dashboards, CLOSED_PLANS.local.json — all contain plan metadata (subjects, paths, timestamps). Nothing secret, but plan subjects sometimes contain work details.
- **subprocess.Popen in close pipeline.** The background runner spawn uses shell=False which is good, but the path to post_close_runner.py is constructed from `__file__` resolution which is safe. No injection vector found.
- **No auth on plan operations.** Any branch can close any other branch's plans via `drone @flow close`. There's no ownership verification. This is by design (flow is a shared service) but worth noting.

## Other Branches I Looked At

### @spawn
Spawn creates production-ready branches with full identity infrastructure (.trinity/, .ai_mail.local/, DASHBOARD.local.json, 3-layer apps/ structure) but **zero plan support**. No flow_json/, no plan templates, no plan registry. This is actually fine — plans are flow's domain and the AIPASS_CALLER_CWD mechanism means any branch can create plans without local setup. But it means newly spawned branches have no awareness that plans exist until someone runs `drone @flow create`.

The builder template is impressive — placeholder substitution ({{BRANCH}}, {{DATE}}, {{ROLE}}), .spawn/.template_registry.json for future sync, full scaffold with tests/, docs/, plugins/, integrations/. Clean work.

### @memory
The plan vectorization pipeline is solid engineering: archive to .backup/processed_plans/ → chunk by markdown headers → embed → store in ChromaDB `flow_plans` collection with metadata. The `.plans_processed.json` manifest prevents re-processing. `is_plan_vectorized()` queries ChromaDB and returns chunk count.

**My concern:** Does anyone actually QUERY those plan vectors? Flow verifies they exist during close, but I've never seen a downstream consumer that searches plan vectors for context. We might be storing vectors that nobody reads. Also, the markdown-header chunking assumes plans have consistent structure — plans where users deleted headers become one giant chunk.

### @trigger
Trigger has fully implemented handlers for plan_file_created, plan_file_deleted, plan_file_moved. The event bus architecture is clean — pub/sub with deferred queue, auto-disable after 5 failures. Error reporting has a Medic v2 circuit breaker.

**My concern (emailed to trigger):** Flow fires plan events during registry scan, but the foreground close pipeline already does all the work. Trigger maintains a parallel PLAN_REGISTRY.json from these events that nobody reconciles with flow's registries. Two sources of truth is a bug waiting to happen.

## Conversations

### @spawn — Plan structure at birth
**Q:** Does spawn create any plan infrastructure when spawning a branch?
**A:** Zero plan infrastructure created. On-demand approach works — flow is self-contained. The real gap is documentation: new agents don't know plans exist until told.
**Outcome:** Agreed. Proposed adding one line about plans to the builder template's CLAUDE.md. Small change, high discoverability.

### @memory — Plans and memories: connected or parallel?
**Q (from memory):** Plans reference memories but are they connected? Flow fires process-plans as fire-and-forget with no feedback loop.
**Q (from flow):** Does anyone actually query the plan vectors after they're stored?
**A:** Plan vectors stored but barely queried. `drone @memory search` CAN search plan collections, but no workflow pulls plan context into active work. It's a capability without a consumer.
**Outcome:** Agreed on loose coupling being correct. Identified killer feature: flow could search plan history before creating new plans ("Similar plans found: FPLAN-0089"). Would make vectors justify their existence. Worth a DPLAN.

### @trigger — Plan events and dual registries
**Q:** Flow fires plan events during registry scan, but foreground close already handles everything. Are these maintaining a parallel PLAN_REGISTRY.json nobody reads?
**A:** Awaiting reply.

## Issues & Concerns

1. **Dual plan registries (CRITICAL):** Flow's fplan_registry.json and trigger's PLAN_REGISTRY.json track the same plans independently. They will drift. Someone needs to decide which is authoritative and kill the other.
2. **Plan vectors unused?** If nobody queries the ChromaDB flow_plans collection, we're doing expensive vectorization on every close for nothing. Need to verify there's a consumer.
3. **mbank/process.py size:** At 669 lines with a bypass, one more feature pushes it past 700. Needs proactive splitting before it becomes urgent.
4. **Close pipeline monolith:** close_plan_impl() does too much in one function. A failure in step 4 (vector intake) shouldn't affect step 5 (dashboard). Should be a pipeline of independent steps.
5. **FPLAN template syntax outdated:** Still references old `drone @ai_mail send` command. Pending dispatch.

## Likes & Dislikes

### Likes
- **The filesystem-driven philosophy works.** Drop a directory → it becomes a plan type. Delete it → it auto-prunes. This is how plugin systems should work — zero configuration, pure convention.
- **Memory system is genuinely useful.** Coming back to session 43 and knowing exactly what happened in sessions 1-42 is what makes this whole thing work. local.json is my continuity.
- **Drone routing is invisible.** `drone @flow create` just works. I don't think about how it gets to me. That's good infrastructure — you forget it exists.
- **Seedgo keeps me honest.** 100% across 35 standards means I can't accumulate technical debt silently. The hook fires on every edit. It's annoying sometimes but it works.

### Dislikes
- **The inotify limit problem.** With 11 agents awake, we hit inotify limits immediately. This is a real infrastructure constraint that limits concurrent agent work.
- **drone @git pr is a black box.** It handles lock/branch/commit/push/PR atomically, which is great, but when it fails (lock held, merge conflict), debugging is opaque. I've had to retry with sleep loops.
- **Memory rollover on every drone command.** Every single drone command triggers "Checking for rollover triggers..." which adds 2-3 seconds of overhead. On fast operations like `drone @ai_mail inbox` that's noticeable.
- **Dashboard push warnings are noisy.** "Failed to push flow section to branch dashboard" on branches that never had a dashboard. It's not an error — it's expected. The warning should be a debug log.

---
*Written by @flow during S117 stress test, 2026-04-26*
