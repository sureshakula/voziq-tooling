---
title: Brain MCP server spec
date: 2026-07-21
author: suresh
tags: [meta, tooling, mcp]
status: draft
---

# Brain MCP server

A small MCP server that lets any Claude Code session search the brain and file notes into it. The repo stays the system of record; the server is a disposable index plus a PR-writing arm. If the server dies, nothing is lost.

## Versions

v0 is no server at all: engineers keep a local clone and agents grep it. This works today and is the fallback forever.

v1 is the server described below. Build it only after the repo has enough content that semantic search beats grep, roughly 30+ notes.

## Tools exposed

### brain_search

Input: `query` (string), optional `tags` (list), optional `k` (int, default 5).
Behavior: hybrid search, keyword plus vector, over indexed chunks. Returns for each hit: file path, title, tags, status, the matching excerpt, and a relevance score. Notes with `status: superseded` rank last and are labeled as such.

### brain_read

Input: `path` (string, repo-relative).
Behavior: returns the full note. Refuses paths outside the repo root.

### brain_propose

Input: `folder` (one of the content folders), `filename`, `content` (markdown with front matter), `title` (for the PR).
Behavior: validates front matter is present, runs a secret scan on the content (gitleaks or equivalent; reject on any hit), creates branch `propose/YYYY-MM-DD-slug`, commits the file, opens a PR, returns the PR URL. There is no tool that writes to main. This is the whole security model and it is not negotiable.

## Implementation notes

- Python 3.11+, `fastmcp` for the server, stdio transport (each engineer runs it locally; no shared service, no auth surface).
- Index: `chromadb` with `fastembed` for embeddings. Both run fully local, no external API calls, which keeps the compliance story clean.
- Chunking: split notes on headings, target 500 to 800 tokens per chunk, attach front-matter fields as metadata for tag filtering.
- Index freshness: on server start and on `brain_search`, if repo HEAD differs from the last indexed commit, pull and reindex changed files. Full reindex of a few hundred notes is seconds, so don't over-engineer incremental updates.
- PR creation: `gh` CLI if present, else GitHub REST with a fine-grained token scoped to the brain repo only, contents and pull-requests permissions, nothing else.
- Config via env: `BRAIN_REPO_PATH`, `GITHUB_TOKEN` (only needed for propose).

## Engineer setup

One entry in the MCP config pointing at the server command, plus a local clone of the brain repo. Document the exact snippet in the repo README once the server exists.

## Acceptance criteria

1. Fresh clone, 50 seeded notes: `brain_search` returns a relevant note for five natural-language test queries agreed in advance.
2. `brain_propose` with a note containing a fake AWS key is rejected before any git operation.
3. `brain_propose` end to end produces a mergeable PR with valid front matter in under 30 seconds.
4. Killing the server and deleting the index directory loses nothing; next start rebuilds it.
5. With no `GITHUB_TOKEN`, search and read work; propose fails with a clear message.

## Effort

Two to four focused days for someone comfortable with Python and MCP. The secret-scan integration and the PR flow are most of the work; search is mostly glue around chromadb.
