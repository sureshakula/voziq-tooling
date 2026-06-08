# {plan_number} - {subject} (SUNDAY MERGE)

**Created**: {today}
**Branch**: {location}
**Status**: Active
**Type**: Playbook — Sunday Merge SOP

---

## Purpose

The weekly `dev → main` merge + release tag. Run by **devpulse** (only branch with git
write). Tick each step as you go; fill the **Run Summary** with PR numbers and tags for
the vectorized trail. Close when done.

> All git writes go through `drone @git` — **run drone from a branch dir** (it needs
> `.trinity/passport.json` in the cwd; running from the repo root fails with "No
> passport found"). Read git (`status`, `log`, `diff`, `rev-parse`) is allowed raw.
> ⚠️ `drone @git` has **no `tag` verb** — pushing the release tag is a MANUAL step
> (Patrick, or raw `git tag`/`push` via `!`). All other writes go through drone.

---

## 1. Pre-flight

- [ ] On `dev`, working tree understood: `drone @git status --all`
- [ ] Confirm what's shipping this week — scan uncommitted changes + already-pushed dev commits ahead of main: `git rev-list --count main..dev` (read git, raw ok)
- [ ] No surprise files (stray `/tmp` artifacts, test pollution, `.recovery`/`.archive` churn). Clean = archive, never delete.
- [ ] Decide: **release tag this week?** (tag = PyPI publish + GitHub Release). If yes, note target version.

## 2. Verify, commit, CHANGELOG

- [ ] **Run the CI audit gate LOCALLY before pushing** (local == CI, S199 parity — catches red before the PR): `cd <repo-root> && .venv/bin/python .github/scripts/seedgo_audit.py` → expect all 13 branches `>=100%`, exit 0. Uses a relative `src/aipass` path, so run from the repo **root**, not a branch dir.
- [ ] Update `CHANGELOG.md` — add entries under the current week's `[YYYY.WNN]` section (don't batch; mostly done as work landed). Sort into Added / Changed / Fixed.
- [ ] Commit: `drone @git commit "msg" --all` (from a branch dir, e.g. devpulse). New/untracked files (e.g. new templates) — confirm they got staged: `git ls-files <path>` after; `--all` may not pick up untracked.
- [ ] Every commit pushed — local-only commits are invisible

## 3. Open / update the PR

- [ ] `drone @git dev-pr "Week summary: what's shipping"`
- [ ] "PR already open" in output = push succeeded onto the existing PR (expected on re-runs)
- [ ] Record the PR number → Run Summary

## 4. Wait for CI green (ALL required checks)

The PR gate (verified against `.github/workflows/`):
- [ ] `ci.yml` → **lint**, **test**, **standards** (= seedgo-audit / the README + 100%-floor check, runs `.github/scripts/seedgo_audit.py`), **coverage**
- [ ] `security.yml` → Security Scan / dependency-scan
- [ ] `e2e-wheel.yml` → 3-OS wheel smoke (path-filtered: fires on `src/**`, `tests/e2e/**`, `pyproject.toml`)
- [ ] `windows-test.yml` / `macos-test.yml` → required checks, run on every PR (must NEVER be path-filtered or they park as "Expected/waiting" forever and block merge)
- [ ] If "all green but can't merge": it's usually post-push mergeability **lag**. Confirm ground truth via the public API (no gh, no gate):
      - `curl -s https://api.github.com/repos/AIOSAI/AIPass/commits/<sha>/check-runs` → all check-runs success (incl. app checks: codecov, CodeQL)
      - `curl -s https://api.github.com/repos/AIOSAI/AIPass/pulls/<n>` → `mergeable_state: clean`

## 5. Merge to main

- [ ] **User's call to merge** — confirm GO
- [ ] `drone @git merge <PR#>` (squash-merge)
- [ ] ⚠️ **Verify `dev` SURVIVES the merge** (the #625 scar — empirical, every time): `drone @git branches` → `dev` still present; `git rev-parse dev` resolves

## 6. Post-merge realign

- [ ] Pull main locally: `drone @git sync`
- [ ] If merged via GitHub UI (bypassing `drone @git merge`), fast-forward dev to main so dev doesn't fall behind / revert main-only commits (e.g. Dependabot): dev is an ancestor → `git merge --ff-only main` is clean (via `drone @git`)
- [ ] Dependabot / other PRs targeting main: they go green once main has the fix + bots rebase — check after the push

## 7. Release tag (only if cutting a release)

**Versioning rule — bump by SIGNIFICANCE, not cadence** (keeps the version from inflating weekly):
- **PATCH** (`x.y.Z+1`) = fix / internal / standards / UX only → the default, most weeks
- **MINOR** (`x.Y+1.0`) = a new backward-compatible user-facing feature shipped
- **MAJOR** (`X+1.0.0`) = breaking public-API change

(aipass is a 2.x library others pin → keep SemVer; the CHANGELOG keeps its `YYYY.WNN` header as a date index.)

How the release fires (verified `publish.yml`): a `v*` **git tag push** runs build → PyPI publish → GitHub Release. Key facts:
- PyPI version = `pyproject.toml [project] version` at the tagged commit — **NOT** the tag string (the tag only *triggers* the build).
- Tag and `pyproject` version **must match** (`v2.5.2` ⇄ `version = "2.5.2"`), or PyPI publishes the wrong number while the Release is named the tag.
- PyPI **rejects a duplicate version** → if shipping, you MUST bump.
- GitHub Release notes = the **topmost `## [...]` CHANGELOG block** (awk-extracted).

Steps:
- [ ] Bump `pyproject.toml` version per the rule above, **on dev so it rides into the PR** (then main's merge commit carries the right version)
- [ ] Confirm the CHANGELOG top section is the release notes you want
- [ ] **Push the tag — MANUAL (drone has no `tag` verb):** Patrick, or raw `git tag v<version> <main-sha>` + `git push origin v<version>` via `!`, on the merged main commit
- [ ] Verify PyPI shows the new version + the GitHub Release appeared
- [ ] Record the tag → Run Summary

## 8. Wrap

- [ ] Update `.trinity/` memories (session log: what merged, PR#, tag)
- [ ] Fill **Run Summary** below (PR numbers, tag, anything that broke)
- [ ] Close this playbook → vectorizes the run

---

## Run Summary

- **Date:** {today}
- **Outcome:** (merged clean / issues / no-merge)
- **PR(s) merged:** #
- **Release tag:** v
- **CI notes:** (any flaky/red checks + how cleared)
- **dev survived merge:** yes / no
- **Issues hit:**
- **Notes for next run:** (refine this SOP — what was missing or wrong?)

---

## Listen (TTS-friendly summary)

Write a plain English summary of this Sunday merge here when done. No markdown, no symbols,
no tables, no code blocks, no asterisks, no bullet points. Just natural sentences for text to speech.

---

## Close Command

When all steps are ticked and the Run Summary is filled:
```bash
drone @flow close {plan_number}
```
