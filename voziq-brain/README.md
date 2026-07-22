# VOZIQ Brain

Shared engineering knowledge for the VOZIQ team. Plain markdown, changed only through pull requests, readable by humans and coding agents alike.

This folder is a starter kit. It is meant to be lifted out into its own repository (see "Standing this up" below). Nothing here depends on the repo it currently sits in.

## Why this exists

Per-seat AI tooling gives each engineer an assistant that remembers their own work. Nothing carries what one person learned to the rest of the team except the code itself. This repo is that missing layer: the distilled, reviewed residue of everyone's work, in a form both a new hire and a Claude Code session can search.

## Layout

| Folder | What goes there | Example |
|---|---|---|
| `decisions/` | Architecture decision records. Why things are the way they are. | "Why churn scores are batch, not realtime" |
| `runbooks/` | Repeatable procedures with steps and verification. | "Backfill churn features for a client" |
| `domain/` | Facts about our systems and clients that live in nobody's head reliably. | "Client X sends usage data 48h late" |
| `onboarding/` | What a new engineer reads in week one. | Environment setup, who owns what |
| `sessions/` | Distilled learnings from individual work sessions. Raw material for the other folders. | "2026-07-21: pipeline retry behavior" |
| `docs/` | Documentation about the brain itself, including the MCP server spec. | |
| `capture/` | The `/brain-lint` maintenance command, plus a pointer to the deployable `/brain-memo` in `project-seed/`. | |

## Ground rules

There are two rules, and they are absolute:

1. All changes arrive as pull requests. Nobody pushes to main, not even admins, not even for typos. Turn on branch protection the day the repo exists.
2. This repo stays separate from every product repo. It never gains code, build scripts, or client data exports.

Every failure mode of a shared knowledge base (stale, untrusted, junk-filled) starts with relaxing one of these.

## Using it

To read: clone it and grep, or open it in an editor. Once the MCP server exists (spec in `docs/mcp-server-spec.md`), every Claude Code session can search it semantically without leaving the terminal.

To write: open a PR. `CONTRIBUTING.md` covers what goes where, the templates, and the review checklist. The fastest path is the capture ritual: at the end of a work session, run `/brain-memo` and let your agent draft the note for you.

## Standing this up

1. Create an empty private repo at `voziqai/brain`, top level in the GitLab org so the whole company can use it, not just engineering.
2. Copy the contents of this folder to its root and push.
3. Protect the main branch: require one merge-request approval, no direct pushes, no force pushes.
4. Deploy the on-ramp to every project from `project-seed/` (sibling folder in this tooling repo): the `/brain-memo` command, a CLAUDE.md section, and the `BRAIN_REPO_PATH` convention.
5. Seed it: each engineer writes one runbook and one domain note in the first week. The repo has to be worth searching before anyone will search it.
6. Schedule `/brain-lint` (see `capture/brain-lint.md`) monthly once the repo has real content.

Front matter follows Google's Open Knowledge Format, so the brain is a valid OKF bundle any OKF-aware tool can consume.

Tooling (the MCP server, the index) comes after the content. A repo with twenty good notes and no server beats a server over an empty repo.
