# {plan_number} - {subject} (MERGE)

**Created**: {today}
**Branch**: {location}
**Status**: Active
**Type**: Playbook — Merge SOP

---

## Purpose

The `dev → main` merge + release tag — run on-demand, not on a fixed weekly cadence.
Run by **devpulse** (only branch with git write). Tick each step as you go; fill the
**Run Summary** with PR numbers and tags for the vectorized trail. Close when done.

> All git writes go through `drone @git` — **run drone from a branch dir** (it needs
> `.trinity/passport.json` in the cwd; running from the repo root fails with "No
> passport found"). Read git (`status`, `log`, `diff`, `rev-parse`) is allowed raw.
> ⚠️ `drone @git` has **no `tag` verb** — pushing the release tag is a MANUAL step
> (the user, or raw `git tag`/`push` via `!`). All other writes go through drone.

---

## The Law (read first — these prevent the recurring git scares)

1. **Local files on `dev` are the truth.** Git is just a transfer mechanism to the
   remote. We live on `dev`, permanently.
2. **`main` is a remote push-target, nothing more.** Local `main` can be 7000 commits
   behind — it does **not** matter. The only thing ever done to local main is a
   *cosmetic* pull. Never build on it, never read files from it.
3. **NEVER move HEAD lightly.** Any HEAD move — `checkout` (switch branch), `reset`
   (move backward), `rebase` onto a different base — changes what's in the working tree and
   *always* causes confusion, even when the work is technically safe. Treat every HEAD move
   as a deliberate, narrated step, never a reflex. In normal flow you should rarely move HEAD
   at all: you commit (HEAD advances on dev) and push. That's it.
   - **NEVER check out `main`, NEVER reset a HEAD.** Checking out main swaps your whole
     working tree to main's (often stale) content — that's the file-revert scare. The flow
     never needs it. Stay on `dev`.
   - The only routine, safe HEAD advance is a **fast-forward of dev** when dev is purely
     behind main (`git rev-list --left-right --count dev...origin/main` shows `0` ahead) —
     done via `drone @git sync` **from dev** (stays on dev). If dev shows any commits *ahead*,
     it's not a pure FF — stop and think, don't force it.
   - To reference main for a tag, use **`origin/main`** (the remote ref), never local main.
   - ⚠️ Your IDE's "switch to main" / "sync main" button does a `git checkout main` — **don't
     click it.** If you want local main fresh, `drone @git sync` **from dev** is safe (it
     stays on dev); the IDE button is not.

### Why `dev` shows "behind main" after a merge — and why it's fine

`drone @git merge` runs `gh pr merge --merge` — a **merge commit**, not a squash. GitHub
adds a merge commit on main whose parent IS dev's tip. After merging, `dev` is a **clean
ancestor** of `main` (fast-forwardable), never diverged. The "dev is 1 behind main" is
just that one merge commit — **cosmetic and trivially resolved**.

- **The files are identical. It is 100% cosmetic. You can always move forward** — the next
  `dev-pr` compares real file changes and works perfectly regardless of this graph quirk.
- Because `dev` is a clean ancestor of `main`, **`git merge --ff-only origin/main` on dev
  WORKS** — a clean fast-forward realign, no merge commit created, no history rewrite.
- **Realign dev to even** (recommended): `drone @git sync` from dev (clean FF), or
  manually `git merge --ff-only origin/main` on dev. No force-push, no rebase needed.
- **Sync local `main` ref WITHOUT checkout**: `git fetch origin main:main` — updates the
  local main ref to match origin with **zero working-tree touch, no checkout**. This is the
  answer to the IDE "switch to main → your local changes would be overwritten by checkout"
  dialog: that dialog is git SAFETY working — **Cancel, never Force Checkout**. You never
  need to stand on main.

---

## 1. Pre-flight

- [ ] On `dev`, working tree understood: `drone @git status --all`
- [ ] Confirm what's shipping — scan uncommitted changes + already-pushed dev commits ahead of main: `git rev-list --count main..dev` (read git, raw ok)
- [ ] No surprise files (stray `/tmp` artifacts, test pollution, `.recovery`/`.archive` churn). Clean = archive, never delete.
- [ ] **Version state check** (informs the bump decision): read the **two** release-tied versions — `grep '^version' pyproject.toml` and `grep __version__ src/aipass/__init__.py` (they should match; if drifted, note it) — and what PyPI already has: `curl -s https://pypi.org/pypi/aipass/json | python3 -c "import sys,json;print(json.load(sys.stdin)['info']['version'])"`. PyPI rejects a duplicate, so the target must be > published.
- [ ] Decide: **release tag this merge?** (tag = PyPI publish + GitHub Release). If yes, note target version. (Significance call is the user's — the PATCH-default rule below is guidance, and the actual release history is a useful tie-breaker.)

## 2. Verify, commit, CHANGELOG

- [ ] **Run the CI audit gate LOCALLY before pushing** (local == CI, S199 parity — catches red before the PR): `cd <repo-root> && .venv/bin/python .github/scripts/seedgo_audit.py` → expect all 13 branches `>=100%`, exit 0. Uses a relative `src/aipass` path, so run from the repo **root**, not a branch dir.
- [ ] Update `CHANGELOG.md` — add entries under a dated section header `## [YYYY-MM-DD]` (the merge date), one section per merge. Sort into Added / Changed / Fixed.
- [ ] Commit: `drone @git commit "msg" --all` (from a branch dir, e.g. devpulse). New/untracked files (e.g. new templates) — confirm they got staged: `git ls-files <path>` after; `--all` may not pick up untracked.
- [ ] Every commit pushed — local-only commits are invisible

## 3. Open / update the PR

- [ ] `drone @git dev-pr "Merge summary: what's shipping"`
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
- [ ] `drone @git merge <PR#>` (merge commit via `gh pr merge --merge`)
- [ ] ⚠️ The merge command **echoes the PR's ORIGINAL opening description** — often stale if the PR accumulated more work after it was opened. Don't trust it as the merge summary; the real contents are `git log main..dev` from before the merge.
- [ ] ⚠️ **Verify `dev` SURVIVES the merge** (the #625 scar — empirical, every time): `drone @git branches` → `dev` still present; `git rev-parse dev` resolves

## 6. Post-merge realign

- [ ] **Expect `dev` to show "1 behind main" — that's the merge commit, it's cosmetic + fast-forwardable.** See "Why dev shows behind main" up top.
- [ ] **Realign dev** (recommended): `drone @git sync` from dev, or `git merge --ff-only origin/main` on dev. Clean FF, no merge commit, no rewrite.
- [ ] **Stay on `dev`. Do not check out `main`.** Local main being behind is fine — sync it without checkout: `git fetch origin main:main` (zero working-tree touch).
- [ ] Never rebase, never reset, never checkout main.
- [ ] Dependabot / other PRs targeting main: they go green once main has the fix + bots rebase — check after the push

## 7. Release tag (only if cutting a release)

**Versioning rule — bump by SIGNIFICANCE, not cadence:**
- **PATCH** (`x.y.Z+1`) = fix / internal / standards / UX only → the default for most merges
- **MINOR** (`x.Y+1.0`) = a new backward-compatible user-facing feature shipped
- **MAJOR** (`X+1.0.0`) = breaking public-API change

(aipass is a 2.x library others pin → keep SemVer; the CHANGELOG uses `YYYY-MM-DD` dated section headers.)

How the release fires (verified `publish.yml`): a `v*` **git tag push** runs build → PyPI publish → GitHub Release. Key facts:
- PyPI version = `pyproject.toml [project] version` at the tagged commit — **NOT** the tag string (the tag only *triggers* the build).
- Tag and `pyproject` version **must match** (`v2.5.2` ⇄ `version = "2.5.2"`), or PyPI publishes the wrong number while the Release is named the tag.
- PyPI **rejects a duplicate version** → if shipping, you MUST bump.
- GitHub Release notes = the **topmost `## [...]` CHANGELOG block** (awk-extracted).

Steps:
- [ ] Bump the version in **BOTH** files (they must match the tag, or `__version__` ships wrong): `pyproject.toml` `version` **and** `src/aipass/__init__.py` `__version__`. Do it **on dev so it rides into the PR** (then main's merge commit carries the right version). ⚠️ These two drift easily — `__init__.py` is the one that gets forgotten.
- [ ] Confirm the CHANGELOG top section is the release notes you want
- [ ] Get the **real** merged-main sha from the **remote ref** (stay on dev — never checkout main): `git fetch origin` then `git rev-parse origin/main`. **Verify the version on that exact commit BEFORE tagging:** `git show origin/main:pyproject.toml | grep '^version'` and `git show origin/main:src/aipass/__init__.py | grep __version__` — both must equal the tag. (If the user merged via the GitHub UI, their local `main` ref is stale until `git fetch` — always fetch first, always tag `origin/main`, never local `main`.)
- [ ] **Push the tag — MANUAL (drone has no `tag` verb; devpulse can't push tags):** user runs it, via `!` or terminal. **Tag the remote ref directly so a stale local main can't poison it. Separate lines, no `&&`:**
      ```
      git fetch origin
      git tag v<version> origin/main
      git push origin v<version>
      ```
- [ ] Verify PyPI shows the new version + the GitHub Release appeared (`curl -s https://pypi.org/pypi/aipass/json | python3 -c "import sys,json;print(json.load(sys.stdin)['info']['version'])"`)
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

Write a plain English summary of this merge here when done. No markdown, no symbols,
no tables, no code blocks, no asterisks, no bullet points. Just natural sentences for text to speech.

---

## Close Command

When all steps are ticked and the Run Summary is filled:
```bash
drone @flow close {plan_number}
```
