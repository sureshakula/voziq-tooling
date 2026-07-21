---
title: Brain repo conventions
date: 2026-07-21
author: suresh
tags: [meta, process]
status: accepted
---

# 0001: Brain repo conventions

## Context

VOZIQ engineers are adopting per-seat AI coding agents. Each agent remembers its own engineer's work, but nothing carries knowledge across the team except code and tribal memory. We need a shared knowledge layer that both humans and agents can read and write, that fits the team's existing review habits, and that doesn't become a compliance problem in a business that handles subscriber data.

## Decision

Team knowledge lives in a dedicated git repo of plain markdown. All changes arrive as pull requests reviewed by a human. The repo contains no code, no client data exports, and no end-customer PII; client-specific facts use client short codes.

## Alternatives we rejected

- A wiki (Confluence, Notion): agents can't easily read or write it, there's no review gate, and content rots invisibly.
- Shared agent memory files synced between machines: no review gate means junk and sensitive data spread silently, and merge semantics for memory files are unsolved.
- Direct writes with post-hoc cleanup: every knowledge base we've seen die, died this way.

## Consequences

Contributing costs a PR, which is friction; the `/brain-memo` capture command exists to keep that cost near two minutes. Review is the quality and confidentiality gate, so reviewers carry real responsibility. Git history gives us audit and rollback for free. Because everything is plain files, the future MCP server is an index over the repo, not a system of record, and can be rebuilt from scratch at any time.
