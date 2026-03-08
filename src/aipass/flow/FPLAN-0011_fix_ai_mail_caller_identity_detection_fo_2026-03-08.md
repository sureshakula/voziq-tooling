# FPLAN-0011 - Fix ai_mail caller identity detection for Docker and local

**Created**: 2026-03-08
**Branch**: flow
**Status**: Active
**Type**: Standard Plan

---

## What Are Flow Plans?

Flow Plans (FPLANs) are for **BUILDING** - autonomous construction of systems, features, modules.

**This is NOT for:**
- Research or exploration (use agents directly)
- Quick fixes (just do it)
- Discussion or planning (that happens before creating the FPLAN)

**This IS for:**
- Building features or modules
- Single focused construction tasks
- Sub-plans within a master plan

---

## When to Use This vs Master Plan

| This (Default) | Master Plan |
|----------------|-------------|
| Single focused task | 3+ phases, complex build |
| Self-contained | Roadmap + multiple sub-plans |
| Quick build | Multi-session project |
| One phase of a master | Entire branch/system build |

**Need a master plan?** `drone @flow create "subject" master`

---

## Branch Directory Structure

Use dedicated directories - don't scatter files:

| Directory | Purpose |
|-----------|---------|
| `apps/` | Code (modules/, handlers/) |
| `tests/` | All test files |
| `tools/` | Utility scripts |
| `artifacts/` | Agent outputs |
| `docs/` | Documentation |

---

## Critical: Branch Manager Role

**You are the ORCHESTRATOR, not the builder.**

Your 200k context is precious. Burning it on file reads and code writing risks compaction during autonomous work. Agents have clean context - use them for ALL building.

| You Do (Orchestrator) | Agents Do (Builders) |
|-----------------------|----------------------|
| Create plans | Write code |
| Give instructions | Run tests |
| Review output | Read/modify files |
| Course correct | Research/exploration |
| Update memories | Heavy lifting |
| Send status emails | Single-task execution |

**Pattern:** Instruct agent → Wait for completion → Review output → Next step

---

## Seek Branch Expertise

Don't figure everything out alone. Other branches are domain experts - ask them first.

**Before building anything that touches another branch's domain:**
```bash
ai_mail send @branch "Question: [topic]" "I'm working on X and need guidance on Y. What's the best approach?"
```

**Common examples:**
- Building something with email? Ask @ai_mail how delivery works
- Need routing or @ resolution? Ask @drone
- Unsure about standards? Ask @seedgo for reference code
- Need persistent storage or search? Ask @memory_bank
- Event-driven behavior? Ask @trigger about their event system
- Dashboard integration? Ask @devpulse about update_section()

They have deep memory on their systems. A 1-email question saves you hours of guessing.

---

## Notepad

Keep `notepad.md` in your branch directory as a shared scratchpad during the build. Use it for:
- **Status updates** - Quick progress lines so the user can glance without asking
- **Questions for the user** - Non-urgent questions that can wait for the next check-in
- **Notes to self** - Decisions made, things to revisit, gotchas discovered

Update it as you work - lightweight, not formal. The user checks it when they want to, skips it when busy.

---

## Command Reference

When unsure about syntax, use `--help`:

```bash
# Flow - Plan management
drone @flow create . "subject"         # Create plan (. = current dir)
drone @flow close FPLAN-XXXX           # Close plan
drone @flow list                       # List active plans
drone @flow --help                     # Full help

# Seedgo - Quality gates
drone @seedgo checklist <file>           # 10-point check on file
drone @seedgo audit @branch              # Full branch audit
drone @seedgo --help                     # Full help

# AI_Mail - Status updates
drone @ai_mail send @devpulse "Subject" "Message"
drone @ai_mail --help                  # Full help

# Discovery
drone systems                          # All available modules
drone list @branch                     # Commands for branch
```

---

## Planning Phase

### Goal
ai_mail caller identity detection works in both Docker containers and local environments. When devpulse sends an email via `drone @ai_mail send @spawn "Subject" "Body"`, ai_mail correctly identifies devpulse as the sender — regardless of mount paths.

### Problem
Drone routes commands to ai_mail via subprocess with `cwd=ai_mail_dir`. Drone passes `AIPASS_CALLER_CWD` env var with the original caller's directory. ai_mail's `branch_detection.py` reads this CWD and walks up looking for `.trinity/passport.json`, then matches against the registry.

In Docker: registry paths use container paths (`/home/coder/workspace/AIPass/...`) which are generated fresh. The CWD-to-registry path resolution fails when paths don't match exactly.

### Approach
Two-branch fix — drone and ai_mail cooperate:

**Phase 1 — Drone side** (`src/aipass/drone/apps/modules/router.py`):
- Detect caller branch name from CWD (walk up to find `.trinity/passport.json`, read `identity.name`)
- Pass as `AIPASS_CALLER_BRANCH` env var alongside existing `AIPASS_CALLER_CWD`
- Keep CWD — other branches may need it for different purposes

**Phase 2 — ai_mail side** (`src/aipass/ai_mail/apps/handlers/users/branch_detection.py`):
- Check `AIPASS_CALLER_BRANCH` first — direct name lookup in registry (path-independent)
- Fall back to `AIPASS_CALLER_CWD` path resolution (existing behavior)
- Fall back to `Path.cwd()` (original behavior)

**Phase 3 — Test in Docker**:
- Copy fixed files into `aipass-fresh-test` container
- Run `cd src/aipass/devpulse && drone @ai_mail send @spawn "Test" "Test body"`
- Verify email lands in spawn's inbox
- Verify sender is "@devpulse"

**Phase 4 — Test locally**:
- Run same command from local devpulse
- Verify existing ai_mail functionality still works

### Reference Documents
- `src/aipass/drone/apps/modules/router.py` — lines 57-66, AIPASS_CALLER_CWD
- `src/aipass/drone/apps/handlers/executor.py` — lines 46-50, env merge
- `src/aipass/ai_mail/apps/handlers/users/branch_detection.py` — lines 51-87, detect_branch_from_pwd()
- `src/aipass/ai_mail/apps/handlers/users/user.py` — lines 37-97, get_current_user()

---

## Agent Preparation (Before Deploying)

Agents can't work blind. They need context before they build.

**Your Prep Work (as orchestrator):**
1. [ ] Know where agent will work (branch path, key directories)
2. [ ] Identify files agent needs to reference or modify
3. [ ] Gather any specs, planning docs, or examples to include
4. [ ] Prepare COMPLETE instructions (agents are stateless)

**Agent's First Task (context building):**
- Agent should explore/read relevant files BEFORE writing code
- "First, read X and Y to understand the current structure"
- "Look at Z for the pattern to follow"
- Context-first, build-second

**What Agents DON'T Have:**
- No prior conversation history
- No memory files loaded automatically
- No knowledge of other branches
- Only what you put in their instructions

**Your instructions determine success - be thorough and specific.**

---

## Agent Instructions Template
```
You are working at [BRANCH_PATH].

TASK: [Specific single task]

CONTEXT:
- [What they need to know]
- Reference: [planning docs, existing code to study]
- First, READ the relevant files to understand current structure

DELIVERABLES:
- [Specific file or output expected]
- Tests → tests/
- Reports/logs → artifacts/reports/ or artifacts/logs/

CONSTRAINTS:
- Follow Seedgo standards (3-layer architecture)
- Do NOT modify files outside your task scope
- CROSS-BRANCH: Never modify other branches' files unless explicitly authorized by the user
- 2-ATTEMPT RULE: If something fails twice, note the issue and move on
- Do NOT go down rabbit holes debugging

WHEN COMPLETE:
- Verify code runs without syntax errors
- List files created/modified
- Note any issues encountered (with what was attempted)
```

---

## Execution Log

### 2026-03-08
- [ ] Created FPLAN-0011
- [ ] Agent deployed for: [task]
- [ ] Agent completed: [outcome]
- [ ] Seedgo checklist passed: [file]
- [ ] Memories updated

**Log Pattern:** Task → Agent → Outcome → Quality check → Next

**If production stops (critical blocker):**
```bash
drone @ai_mail send @devpulse "PRODUCTION STOPPED: FPLAN-0011" "Issue: [description]. Attempted: [what was tried]. Awaiting guidance."
```

---

## Notes

[Working notes, issues encountered, decisions made]

---

## Completion Checklist

### Before Closing

- [ ] All goals achieved
- [ ] Agent output reviewed and verified
- [ ] Seedgo checklist on new code: `drone @seedgo checklist <file>`
- [ ] Branch memories updated:
  - [ ] `BRANCH.local.json` - session/work log
  - [ ] `BRANCH.observations.json` - patterns learned (if any)
- [ ] README.md updated (if build changed status/capabilities)
- [ ] Status email sent to @devpulse:
  ```bash
  drone @ai_mail send @devpulse "FPLAN-0011 Complete" "Summary of what was done, any issues, outcomes"
  ```

**Completion Order:** Memories → README → Email (README before email - don't report complete with stale docs)

### Definition of Done
[What specifically defines complete for this plan?]

---

## Close Command

When all boxes checked:
```bash
drone @flow close FPLAN-0011
```
