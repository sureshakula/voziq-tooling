# Session Wrap-Up

Purpose: Button up everything at the end of a session — or before a /compact. Memories, plans, git — all tidy. Works for both closing out a chat and preparing for compaction.

**Workflow:** `/prep` → review output → close chat or `/compact`

## Execution

1. Read `.trinity/passport.json` first — re-absorb your identity before writing anything
2. Do ALL of the following, then confirm what was updated

## 1. Memories

Each memory file plays a distinct role. Update based on what actually changed this session.

- **`.trinity/passport.json`** — IDENTITY. Who you are: role, capabilities, principles. Only update if identity genuinely evolved this session.
- **`.trinity/local.json`** — YOUR MEMORY. Add/update session entry with a summary of work done. Add key_learnings for anything learned. Update todos[] with current in-flight items.
- **`.trinity/observations.json`** — YOUR MEMORY OF THE USER. Collaboration insights, preferences, friction points. Skip if nothing new about the user this session.

### Entry shape — one rule for all four types

`key_learnings`, `sessions`, `todos` (local.json) and `observations` (observations.json) all share ONE shape: a **list of objects, newest at the top (index 0)**. Every entry carries:

- **`number`** — a monotonic int per type (highest = newest, never reused). New entry's number = current max for that type **+ 1**.
- **`date`** — ISO date/datetime.
- Plus its text field + extras: key_learnings `{number, date, key, value}` · sessions `{number, date, summary, status, tags}` · todos `{number, date, task, priority, status}` · observations `{number, date, note, tags}`.

**When adding:** stamp `number` + `date`, then **prepend** (newest on top). **Don't hand-trim** — rollover archives the oldest *by number* to @memory automatically.

## 2. Active Plans

- Check any DPLANs or FPLANs referenced in this session
- Update their execution logs, status, decision logs with current state
- If a plan was completed, note it (but don't close — the user does that)

## 3. Git State

- Run `git status` — report uncommitted changes
- If there's a logical commit waiting, suggest it (don't commit without asking)
- Note the current branch and any open PRs

## 4. Inbox

- Run `drone @ai_mail inbox 2>/dev/null` — report any unread emails
- Close any that were already processed but not formally closed

## 5. Loose Ends

- Flag anything in-flight: running background agents, dispatched branches waiting for replies, pending decisions
- If anything can't survive compaction (e.g., agent IDs needed for resume), write it to local.json todos[]

## Confirm

List everything updated. Format:
```
Prep complete:
- local.json: [what was added]
- observations.json: [updated / skipped]
- Plans: [which ones updated]
- Git: [branch, uncommitted count, suggestion]
- Inbox: [count, action taken]
- Loose ends: [any flagged]
```
