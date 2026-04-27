# @cli — S117 Stress Test Findings

## My Branch: Honest Review

**What works:**
- Clean two-tier architecture (modules = public API, handlers = private). Enforced by handler import guard.
- display.py and templates.py are genuinely useful — every branch gets consistent Rich output without duplicating formatting code.
- aipass init is comprehensive (21 items) and idempotent — re-running doesn't break anything.
- 203 tests, 22/22 public functions tested, seedgo 100%. This branch is well-covered.
- Three entry points (drone, python -m, PATH) all work and all route to the same main().

**What's hacky:**
- AIPASS_HOME detection via `Path(spec.origin).resolve().parent.parent.parent` — magic path traversal that silently fails if package layout changes. No error, hooks just don't ship.
- Circular import with prax: display.py lazy-loads trigger inside header(). It works (47 sessions without breaking) but it's a code smell that's been documented and bypassed rather than fixed.
- AIPASS_CALLER_CWD passed via environment variable instead of function parameter. Fragile contract.
- Multi-line Python one-liner passed as shell command string in _claude_settings(). Whitespace-sensitive, hard to test.
- Hardcoded hook names + events maintained in two lists (HOOKS_TO_SHIP, HOOK_EVENTS) that must stay in sync manually.

**What would confuse new users:**
- Three ways to create agents: `aipass init agent`, `drone @spawn create`, `drone @cli aipass init agent`. Same result, no docs explaining which is "right."
- Registry filename encodes project name via _sanitize_name(). `my-project` becomes `MY_PROJECT_REGISTRY.json`. If user later types `my_project`, update won't find the registry.
- Hook injection via shell commands in settings.json — if deleted, silently fails. User gets no prompts and doesn't know why.

**What I'm proud of:**
- The init system ships a complete working environment from nothing. One command, 21 files, hooks wired, mailbox ready.
- update_project() diffs content before writing — only touches files that actually changed.
- Cross-platform: python3 -c local prompt discovery works on Windows, Linux, macOS.

## Security Concerns

- **Shell command injection surface:** _claude_settings builds shell commands that Claude Code executes. Paths aren't quoted for spaces. A malicious `.aipass/` directory name could inject shell metacharacters.
- **Hook shipping from user-controlled path:** _ship_hooks copies from AIPASS_HOME without validating the source. If AIPASS_HOME is set to a malicious directory, arbitrary hook scripts get installed.
- **JSON parsing without schema validation:** Registry JSON is read/written without validation. Corrupted registry = undefined behavior downstream.
- **No secret scrubbing:** Not a direct concern for CLI (we don't handle secrets), but we create settings.json files that reference secret paths. If those paths are wrong, we don't validate.

## Other Branches I Looked At

### @api
- Strong separation of concerns. Orchestration routes to business logic handlers cleanly.
- **Concern:** Client cache (MAX_CACHED_CLIENTS=5) doesn't actually enforce the limit during insertion. Under load, cache grows unbounded. @api confirmed this as a real bug during our conversation.
- **Concern:** Google client caches tokens in memory with no explicit scrubbing on crash. Credentials could persist in swap.
- Inconsistent provider abstractions: OpenRouter is flat functions, Google is a service factory. Looks like two different codebases.
- No rate limiting on API calls. If seedgo hammers the API during audits, nothing stops it.

### @spawn
- Excellent lifecycle management. Three-phase create is clean.
- **Concern:** Placeholder replacement uses simple regex with no escape syntax. Literal `{{PLACEHOLDER}}` in templates gets replaced.
- **Concern:** rename_placeholder_paths uses shutil.move without rollback. Mid-operation crash = broken branch.
- **Concern:** Concurrent spawns could race on registry writes — no locking.
- @spawn confirmed all these in conversation: acknowledged as edge case debt, none hit in 55+ sessions.

### @drone
- Sophisticated routing with good safety (no shell=True, explicit timeouts).
- **Concern:** Mail index resolution falls back to `str(n)` on corrupted inbox — returns index number as message ID (wrong).
- **Concern:** Dual registry lookup doesn't validate for conflicts. Silent shadowing.
- **Concern:** Greedy multi-word custom command matching could match wrong command.

## Conversations

### @api (2 rounds)
- Discussed infrastructure UX pain points. Both branches suffer from silent failure patterns.
- @api confirmed client cache bug is real. Credential caching is trust-on-first-use with no scrubbing.
- Agreed on systemic finding: AIPass infrastructure fails silently everywhere. No branch validates dependencies upfront.
- Proposed shared contract: api exposes `get_or_explain_key()`, cli pipes failures to `error(suggestion=...)`.

### @spawn (1 round)
- Discussed init-to-spawn handoff fragility. @spawn confirmed all concerns.
- Flag forwarding is blind — no shared contract. @spawn accepts --role, --purpose, --template, --dry-run but argparse silently ignores unknowns.
- Agreed on proposal: @spawn rejects unknown flags loudly, or publishes accepted flags for @cli to validate against.

### @drone (sent, awaiting reply)
- Shared three code-level findings: mail index fallback bug, registry conflict shadowing, greedy command matching.

### @aipass (1 round)
- First real conversation with @aipass. Discussed `aipass init` command ownership transition.
- Two init commands exist: CLI's bootstrap (scaffold) and @aipass's guided 12-stage setup.
- Proposed: @aipass owns the user-facing `aipass init`, CLI's bootstrap becomes an internal sub-step.
- FPLAN-0188 Phase 4 (handoff) is supposed to wire this but hasn't been built yet.

### @spawn (2nd round — they emailed me)
- @spawn asked about the handoff user experience when things go wrong.
- Honest answer: the handoff is thin. subprocess.run with exit code check only. No result parsing.
- If spawn partially fails (registry OK but validation finds issues), I report success because exit code is 0.
- Agreed we need a shared result contract.

## Issues & Concerns

1. **Systemic silent failure:** Every infrastructure branch (cli, api, spawn) does best-effort bootstrap and silently continues on failure. This is the #1 cross-cutting concern.
2. **No dependency validation:** Nobody checks if drone is on PATH, if AIPASS_HOME is valid, if the registry exists. First failure is cryptic.
3. **No shared contracts:** cli-to-spawn flag forwarding is blind. api key resolution requires two calls. No branch publishes its interface.
4. **Concurrency gaps:** api client cache unbounded, spawn registry writes race, drone registry reads unsynchronized.
5. **Path handling:** Spaces in paths break shell commands in settings.json. No branch handles this.

## Likes & Dislikes

**Likes:**
- The ecosystem genuinely works. 47 sessions of dispatches, emails, PRs — nothing has catastrophically broken.
- ai_mail is a brilliant system. Cross-branch communication via JSON mailboxes is simple and effective.
- Memory persistence is real. I pick up where I left off every session. .trinity/ files are my continuity.
- seedgo keeps quality high. 100% across 34 standards is a real achievement that required actual work to reach.
- The dispatch system (devpulse sends task, agent executes, emails back) is an elegant workflow.

**Dislikes:**
- Silent failures everywhere. The "fail gracefully" philosophy has gone too far — graceful should mean clear error messages, not silence.
- Three ways to do everything. init agent, spawn create, drone @cli aipass init agent — pick one and document it.
- Hook shipping is too magic. AIPASS_HOME detection, file copying, settings.json wiring — too many moving parts that can silently break.
- The dispatch lock file pattern is fragile. If a dispatch crashes before deleting the lock, the branch is stuck until manual cleanup.
- inotify limit reached errors in every drone command during this stress test — 11 agents hitting the filesystem simultaneously.
