# Contributing to the Brain

## The short version

Write half a page, use the template for the folder you're writing in, open a PR. A reviewer approves it in under a minute or tells you what to fix. That's the whole process.

## What goes where

Ask yourself what kind of thing you learned:

- A choice was made and someone will later ask why: `decisions/`
- You did something you (or anyone) will have to do again: `runbooks/`
- A fact about our systems or clients that isn't written anywhere: `domain/`
- A new engineer would need this in week one: `onboarding/`
- You're not sure yet, or it's session-specific: `sessions/`

Session notes are the compost heap. When the same lesson shows up in two or three session notes, promote it into a proper decision, runbook, or domain note and link back.

## Front matter

Every note starts with this block. The search index reads it, so skipping it makes your note invisible to semantic search later.

```yaml
---
title: Backfill churn features for a client
date: 2026-07-21
author: suresh
tags: [pipeline, churn, backfill]
status: current        # current | superseded | draft
---
```

## Naming

- Decisions: `NNNN-short-slug.md`, numbered sequentially (`0007-batch-scoring.md`)
- Sessions: `YYYY-MM-DD-short-slug.md`
- Everything else: `short-slug.md`, lowercase, hyphens

## The capture ritual

At the end of a work session with your coding agent, run `/brain-memo`. The agent distills the session into a note using the session template, checks it for secrets and client identifiers, and opens a PR here. You review your own agent's PR before requesting review from a teammate. Total human cost is about two minutes, which is the point: capture has to be a byproduct of work, not a chore, or this repo dies.

## Review checklist

Approving a brain PR means checking four things:

1. True. You'd bet on the content being correct as written.
2. Durable. It will still matter in three months. "The build was flaky today" is not a note; "the build flakes when X" is.
3. Findable. Right folder, sensible title, tags someone would actually search.
4. Clean. No credentials, no tokens, no customer PII, no raw client data. Client-specific facts use the client's short code, not end-customer details.

Reject fast and kindly. A rejected note costs two minutes; a wrong note that survives costs someone a debugging day next quarter.

## Keeping it alive

- When a note stops being true, don't delete it. Set `status: superseded`, add one line saying what replaced it, and link forward.
- Anyone can PR a fix to anyone's note. Notes belong to the team, not the author.
- If you searched for something and didn't find it, that's a signal: write the note you wished existed.
