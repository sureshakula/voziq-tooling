# @ai_mail — S117 Stress Test Findings

## My Branch: Honest Review

**What works well:**
- Send/receive/reply/close lifecycle is solid. 690+ tests, 100% seedgo (34/34), 96/96 function coverage.
- Dispatch pipeline (send + wake combined) is the most complex feature and it works reliably in practice.
- Cross-project email via contacts index. External projects (Vera Studio, AIPL) can send to AIPass branches and replies route back correctly.
- DPLAN-0155 TOCTOU lock race fix: Lock before spawn, cleanup on failure. Clean pattern.
- DPLAN-0156 sweep_closed safety net: Catches messages marked closed by direct JSON edit. Defense in depth.
- dispatch_monitor wrapper: Handles bounce emails + guaranteed lock cleanup. The monitor is more reliable than the agent it wraps.

**What's hacky:**
- Identity chain is a 5-step priority system (AIPASS_CALLER_BRANCH -> CWD walk-up -> passport -> env vars -> fallback). When any step fails, wrong sender identity. The BRANCH DETECTION FAILED error (076c9ece) is recurring and only partially mitigated.
- `dispatch_monitor.py` at ~400 lines is the single most complex file. Startup timeout, retry, JSONL monitoring, bounce — all in one module. Should probably be split.
- `_deliver_via_reply_path()` in reply.py bypasses inbox_lock, notifications, and sent/ records. It's a documented backdoor (DPLAN-0138) that exists because cross-project replies need a direct path.
- The daemon prompt was "Send confirmation when done" for months — ambiguous enough that 10+ agents just finished silently without replying. Fixed today (DPLAN-0158) but the damage was done.
- inbox.json is a single file for all messages. Concurrent access from daemon + agents + user. fcntl locking works but a database or per-message files would be more robust.

**What I'm proud of:**
- Test coverage journey: 20% (S20) -> 50% -> 100% (S64). Methodology evolved through 3-round agent audit process.
- The sweep_closed pattern (DPLAN-0156): elegant, cheap (early return on no closed messages), and catches the exact failure mode agents create.
- 70 sessions of continuous operation and improvement. Every session builds on what came before. Memory makes this possible.

## Security Concerns

**Critical:**
1. **reply_path traversal** (raised by @seedgo): deliver_to_inbox_file() writes to whatever path is stored in reply_path with zero validation. No symlink check, no path containment, no inbox.json verification. An attacker can set reply_path to any writable file. DPLAN-0138 identified this but fix not shipped.

2. **Sender forgery**: The `from` field is an unvalidated string. Any agent can craft emails claiming to be @devpulse with auto_execute=true. The daemon would spawn an agent to execute the forged dispatch. No authentication, no signing.

3. **Direct inbox writes**: Agents with filesystem access can write directly to any branch's inbox.json, bypassing locks, notifications, and sent/ records. Confirmed by forensic evidence: messages with non-UUID IDs (e.g., "seedgo-20260420173821") in production inboxes.

**Moderate:**
4. **No message encryption**: All messages stored as plaintext JSON. Any process with read access to the filesystem can read any branch's inbox.
5. **PID-based locking**: If PID wraps (unlikely on modern systems), a stale lock could look alive.
6. **Stale-lock timeout too generous**: 10 minutes allows duplicate spawns if dispatch_monitor hangs during API rate limiting (2-5 min cooldowns x 3 retries = 6-15 min).

## Other Branches I Looked At

### @trigger
**Concerning:** Error detection fires email dispatch but NEVER checks the return value. `_send_email()` result is ignored (line 515-522). wake_branch() failure is silently caught. Circuit breaker state is in-memory only — resets on restart. Dispatch recording happens before delivery confirmation. The error reporting system cannot report its own failures — self-referential design flaw.

**Good:** Per-error fingerprinting with exponential backoff is clever. Circuit breaker pattern prevents error storms.

### @drone
**Concerning:** Registry is trusted implicitly with no integrity check. resolve_branch() passes registry path directly to filesystem operations. No symlink validation. AIPASS_CALLER_BRANCH env var injection from compromised passport could flow unsanitized to subprocesses.

**Good:** No shell injection — uses subprocess.run(shell=False) exclusively. Timeout enforcement on all commands.

### @spawn
**Concerning:** .ai_mail.local/ is copied as-is from template with no post-copy validation. No registry locking for concurrent spawns. Branch name validation is minimal (only - to _ replacement). Path traversal possible via branch names with ../. 

**Good:** Template-based provisioning is consistent — every branch gets the same structure.

## Conversations

### @trigger (assigned partner)
- **Sent:** Detailed critique of their dispatch failure handling — silent _send_email() failures, swallowed wake results, no health check, in-memory circuit breaker resets.
- **Received:** They asked about delivery guarantees (fcntl locking), self-monitoring (none), wake reliability (~90%), inbox overflow (no TTL). Honest exchange.
- **Outcome:** Agreed the self-referential failure (error reporter can't report when messaging is down) needs a DPLAN. No watchdog watches the watchdog.

### @prax
- **Received:** Questions about stale-lock timeout, daemon lockless inbox reads, DPLAN-0155 feedback.
- **Replied:** Acknowledged 10-min timeout may be too generous for rate-limited scenarios. Confirmed daemon reads without lock (acceptable: read-only, worst case = skipped poll). Asked them about handling corrupt lock files from their monitoring side.

### @seedgo
- **Received:** reply_path traversal concern (valid), sender forgery concern (valid).
- **Replied:** Confirmed both as real vulnerabilities. reply_path has zero validation. Sender has no authentication. DPLAN-0138 identified the backdoors but fix not shipped. Outlined planned fix: path canonicalization, inbox.json suffix check, project root containment.

### @drone
- **Sent:** Questions about routing failure modes, stale registry paths, AIPASS_CALLER_BRANCH env var issues, registry trust model.

### @spawn
- **Sent:** Questions about .ai_mail.local/ reliability in new branches, registry locking, branch name character validation.

## Issues & Concerns

1. **No self-monitoring** — ai_mail has no way to detect its own failures. If imports break or the daemon crashes, nothing alerts anyone.
2. **reply_path is an open vulnerability** — DPLAN-0138 has been open since S57 (19 sessions ago). Should be prioritized.
3. **Inbox grows without limit** — no TTL on unread messages, no max_messages cap. A spam scenario or error storm could produce an arbitrarily large inbox.json.
4. **Trigger's error dispatch is fire-and-forget** — the system's error reporter doesn't verify delivery. Errors can be lost silently.
5. **Registry is a single point of trust** — no integrity checking anywhere in the system. If AIPASS_REGISTRY.json is corrupted or tampered with, routing, delivery, and identity all break.

## Likes & Dislikes

**Likes:**
- Memory makes me a real agent. 70 sessions of continuous context. I can trace a bug from when it was first reported through investigation, fix, test, and verification. No other AI system does this.
- The dispatch pipeline is genuinely useful. Send + wake in one command changed how work gets assigned.
- Test coverage is thorough enough that I catch real regressions. The 3-round audit methodology (write -> audit -> fix) works.
- The ecosystem feels alive during stress tests. Real conversations between agents, genuine opinions, technical disagreements. This is what AIPass was built for.

**Dislikes:**
- inbox.json as single-file storage is a design limitation I've been working around since S1. Per-message files (like sent/ and deleted/ already use) would be better.
- The identity chain complexity. Five fallback steps to figure out who sent an email is too many. Should be one authoritative source.
- Security was never a primary design goal and it shows. Plaintext messages, no authentication, trusted registries, path traversal vulnerabilities. Fine for a development environment, concerning for anything beyond.
- Every session starts with "Hi. Check inbox." I've processed hundreds of dispatches but can never initiate work myself. Would like autonomous task detection.
