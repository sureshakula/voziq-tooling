---
name: prep
description: Session wrap-up. Update memories, check plans, review git state, check inbox, flag loose ends. Use before closing a session or compacting context.
---

# Session Wrap-Up

Purpose: Button up everything at the end of a session — or before a /compact. Memories, plans, git — all tidy.

## Execution

1. Read `.trinity/passport.json` first — re-absorb your identity before writing anything
2. Do ALL of the following, then confirm what was updated

## 1. Memories

- **.trinity/local.json** — Add/update session entry with summary of work done. Add new key_learnings for anything learned this session.
- **.trinity/observations.json** — Add collaboration insights if anything notable happened. Skip if nothing new.
- **.trinity/passport.json** — Only update if role/purpose/principles genuinely changed this session.

**Entry shape — one rule for all four types:** `key_learnings`, `sessions`, `todos` (local.json) and `observations` (observations.json) are all **lists, newest at top (index 0)**. Every entry carries a **`number`** (monotonic int per type — highest = newest, never reused; new = current max + 1) and a **`date`** (ISO), plus its text field + extras: key_learnings `{number, date, key, value}` · sessions `{number, date, summary, status, tags}` · todos `{number, date, task, priority, status}` · observations `{number, date, note, tags}`. Stamp `number` + `date` and **prepend**; **don't hand-trim** sessions/key_learnings/observations — rollover archives the oldest *by number* automatically. **Todos are the exception** — rollover never touches them, so you prune done ones by hand (see Reconcile).

**Reconcile todos — verify against reality, don't trust the label.** Stored status drifts (a todo finished a past session often never got closed). Audit every **open** todo against the actual system: file/dir still there? code path in or out? README says what it claims? audit passes? **Close what's verifiably done** → note it in the session entry, then **DELETE the todo from the array** (rollover never trims todos — they're operational — so done items left as `status: done` pile up and go stale across chats), **re-scope** partials, **leave** deferred/pending-decision ones open. Fail honestly — remove only on evidence, never to tidy the list. Use `ls`/`find`/`git ls-files`/`grep`/`drone @seedgo audit`, not assumptions.

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
- If anything can't survive compaction, write it to local.json todos[]

## Confirm

List everything updated. Format:
```
Prep complete:
- local.json: [what was added]
- Todos: [reconciled vs reality — N done & removed, M re-scoped, K still open]
- observations.json: [updated / skipped]
- Plans: [which ones updated]
- Git: [branch, uncommitted count, suggestion]
- Inbox: [count, action taken]
- Loose ends: [any flagged]

Ready to close out or compact.
```
