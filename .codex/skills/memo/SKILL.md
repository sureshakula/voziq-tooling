---
name: memo
description: Update branch memory files after completing work. Saves session history, key learnings, and collaboration observations to .trinity/ files.
---

# Memory Update

Purpose: Update branch memory files after completing work this session.

## Execution

1. Read `.trinity/passport.json` first — re-absorb your identity, role, and principles before writing memories
2. Review what was done this session (context, recent changes, key decisions)
3. Update each file below as needed
4. Confirm completion — list files updated

## What to Update

### Always

- **.trinity/local.json** — Add a session entry to `sessions` if significant work was done; add `key_learnings` for facts you'd need next time. **Todos: add what you parked, and DELETE every todo you finished this session** — the proof goes in the session entry, not the todo. Rollover never trims todos (they're operational), so done ones you leave behind resurface as "open" next load and you waste time re-confirming them.
- **.trinity/observations.json** — Add notable collaboration insights: breakthrough moments, pattern corrections, flow states, friction points, preference discoveries. Skip if nothing notable this session.

### Entry shape — one rule for all four types

`key_learnings`, `sessions`, `todos` (local.json) and `observations` (observations.json) all share ONE shape: a **list of objects, newest at the top (index 0)**. Every entry carries a **`number`** (monotonic int per type — highest = newest, never reused; new = current max + 1) and a **`date`** (ISO), plus its text field + extras: key_learnings `{number, date, key, value}` · sessions `{number, date, summary, status, tags}` · todos `{number, date, task, priority, status}` · observations `{number, date, note, tags}`.

**When adding:** stamp `number` + `date`, then **prepend** (newest on top). **Don't hand-trim** sessions/key_learnings/observations — rollover archives the oldest *by number* to @memory automatically. **Todos are the exception** — rollover never touches them, so you prune done ones by hand (delete finished todos, see above).

### If Relevant

- **.trinity/passport.json** — Evolve identity when the branch's role, capabilities, or principles have genuinely changed. Don't update just to update — but don't leave placeholders forever either.
- **README.md** — Does it reflect current state? Update if stale.
