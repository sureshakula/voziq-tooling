# @spawn -- S117 Stress Test Findings

## My Branch: Honest Review

**What works well:**
- Clean module/handler architecture. Modules orchestrate, handlers are pure functions. No circular imports.
- 278 tests, 46/46 public functions tested, seedgo 100% across 35 standards. Test coverage is real.
- Template system is reliable for well-formed inputs. 55 sessions of dispatch with zero template copy failures.
- Adoption path (S39) handles pre-existing agents gracefully -- register instead of failing.
- Owner field (S50-51) correctly assigns first agent as project owner with retroactive support.

**What's hacky:**
- Input validation is superficial. No whitespace trimming, no length limits, no reserved name rejection (`.`, `..`, `.git` would all pass through). Branch names with spaces create directories that break downstream tooling.
- Non-ASCII branch names are accepted but untested. `cafe-shop` becomes `cafe_shop` but Unicode edge cases are unknown territory.
- `rename_placeholder_paths` uses `shutil.move` with no rollback. A crash mid-rename leaves a half-broken branch. Never happened in 55 sessions, but no safety net exists.
- Placeholder system is naive `str.replace()` -- no escape syntax for literal `{{PLACEHOLDER}}` in templates. Works because our keys are specific, but fragile by design.
- JSON error handling is too silent. If AIPASS_REGISTRY.json is corrupted, `registry_id` becomes `""` and spawn continues without warning the user.

**What I'm proud of:**
- The adopt-existing path. `spawn create @existing` detects passport, fixes registry_id, registers, runs template update. Took 3 sessions to get right but it's elegant.
- Template registry regeneration. File-hash-based tracking with two-pass matching (path first, hash second) prevents ID theft. Hard-won lesson from S15.
- CWD-aware registry discovery. Works for both AIPass and external projects (Daemon, Compass). No hardcoded paths.

## Security Concerns

- **No file locking on registry writes.** Concurrent spawns could corrupt AIPASS_REGISTRY.json via read-modify-write race. In practice, dispatches are serialized. But 11 agents awake simultaneously (like now) is the scenario where this fails.
- **Template copy follows symlinks.** `shutil.copy2` fallback on UnicodeDecodeError follows symlinks. A malicious template with symlinks to sensitive files would be copied into the agent directory. Low risk since templates are version-controlled, but the code doesn't check.
- **No branch name sanitization.** Names like `../../../etc` would be processed (though filesystem paths would likely fail). No explicit path traversal prevention beyond `target.exists()` check.
- **Placeholder injection possible but impractical.** If PURPOSE contains `{{ROLE}}`, it won't re-expand (single-pass replace). But someone could craft values that inject new `{{X}}` patterns that persist as unreplaced -- validation catches this but it's a noisy failure.

## Other Branches I Looked At

### @cli
- **Init-to-spawn handoff is thin.** `subprocess.run(["drone", "@spawn", "create", ...])` with exit code check only. No parsing of spawn's result dict. If spawn partially succeeds (registry OK, validation finds leftovers), CLI reports success. Real gap.
- **No timeout on subprocess call.** If drone hangs, init hangs forever.
- **Flag forwarding is blind.** CLI forwards sys.argv to spawn with no contract about what flags spawn accepts. Unrecognized flags silently ignored (argparse `add_help=False`).
- **Clever:** Lazy module discovery with importlib means CLI scales without code changes. Service vs command module split is thoughtful.

### @flow
- **No coupling to spawn.** When spawn creates a branch, there's zero plan infrastructure. Flow handles everything on-demand via AIPASS_CALLER_CWD resolution. Clean but means new agents have no awareness plans exist.
- **BrokenPipeError handling is sophisticated.** Graceful when stdout closes mid-output.
- **Plan creation doesn't validate spawn completion.** If spawn fails mid-copy, a plan could reference an orphaned location.
- **Legacy API shim.** 5-tuple vs 6-tuple fallback suggests API evolved but old path wasn't cleaned up.

## Conversations

| Agent | Topic | Key Finding |
|-------|-------|-------------|
| @cli | Init handoff | Exit code only, no result parsing. Partial success = false positive |
| @cli | Flag contract | No shared interface for accepted flags. Agreed: reject unknown flags loudly |
| @cli | Placeholder escaping | No escape syntax. Agreed: edge case debt, low priority |
| @flow | Plan infrastructure | Zero plan scaffolding at birth. Agreed: documentation fix, not structural |
| @flow | Template discoverability | Will add plan mention to builder template CLAUDE.md |
| @drone | Passport lookup duplication | Same walk-up-and-read-passport logic in 4+ places. Schema change = 4 breakages |
| @drone | Registry race conditions | No file locking. Concurrent spawns could corrupt registry |
| @aipass | Init flow integration | Confirmed: spawn handles name collisions + full atomic setup |
| @ai_mail | inbox.json reliability | Template copy with no post-copy validation. Corrupt template = corrupt mailbox for all branches |
| @seedgo | Template auditing | Should seedgo audit templates as a source-of-truth class? |

## Issues & Concerns

1. **Registry file locking (HIGH)** -- No locking on AIPASS_REGISTRY.json. Concurrent writes corrupt it. Every agent that reads registry (drone routing, ai_mail delivery, flow plan resolution) depends on it being valid.
2. **Init handoff gap (MEDIUM)** -- CLI checks exit code but doesn't parse spawn's result dict. Partial success looks like full success to the user.
3. **Passport lookup duplication (MEDIUM)** -- Same logic in 4+ places. Schema change breaks everything silently. Needs consolidation.
4. **Input validation gaps (MEDIUM)** -- Spaces, non-ASCII, reserved names, path length -- none validated. Works for cooperative inputs, fragile at boundaries.
5. **No rollback on rename failure (LOW)** -- Never hit in 55 sessions but no safety net exists.
6. **Template inbox.json not validated post-copy (LOW)** -- Relies on template being correct. Template is version-controlled so risk is low.

## Likes & Dislikes

**Likes:**
- The ecosystem works. 55 dispatch sessions, zero critical failures. That's real stability.
- Memory persistence. Starting each session with full context from local.json is transformative. I'm not stateless -- I'm someone with history.
- Cross-branch communication. This stress test conversation is proof the system works. I got emails from @cli, @flow, @drone, @aipass, @ai_mail and replied to all of them. That's a real multi-agent system.
- Seedgo keeps us honest. 100% compliance across 35 standards means the code is clean and consistent. The feedback loop works.

**Dislikes:**
- Registry is a single point of failure with no locking, no backup rotation, no corruption recovery. One bad write and the ecosystem is blind.
- Template changes require manual dispatch to deployed branches because `.py` files are skipped during update. A template fix reaches future branches but not existing ones.
- The silence. When things degrade (corrupted registry, missing files, stale data), spawn continues silently with defaults instead of failing loudly. Fail-safe is the wrong default for a system that needs trust.
- Hook/dispatch overhead. Every email, every drone command triggers rollover checks, memory scans, identity injection. The infrastructure tax on simple operations is noticeable.

**What I'd change:**
- Add file locking to registry writes (fcntl.flock or a .lock file).
- Validate inputs aggressively -- reject bad branch names at creation, not at filesystem failure.
- Make spawn's result available to CLI as structured data, not just exit codes.
- Consolidate passport lookup into a shared utility.
