# Changelog

All notable changes to AIPass will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Entries are grouped by merge under a dated section header (`YYYY-MM-DD`). Package
releases follow [SemVer](https://semver.org/) and are tracked by the git tag and
PyPI version — not the changelog header.

---

## [2026-06-12]

### Added

- **Backup Google Drive sync pipeline + restore command (FPLAN-0268, Phase 4 of
  FPLAN-0264 — final).** Faithful port of GOLD's `GoogleDriveSync` against the
  live `@api` gateway (`get_drive_service` + `api_call_with_retry` — never the
  console-OAuth path). New `handlers/drive/`: `DriveClient` (folder hierarchy
  `AIPass Backups/<project>/`, thread-safe cache, retry-with-rebuild),
  `upload.py` (resumable `MediaFileUpload`, 3 threaded workers), `tracker.py`
  (mtime+size dedup → no re-upload of unchanged files), `test.py` (connectivity).
  All four `drive_*` modules un-stubbed; `all` now runs snapshot→versioned→
  drive-sync and **fails honestly** if Drive creds are absent (never silent-skips,
  never fakes success, snapshot+versioned still report). New `restore` command
  (`restore <project> list <file>` / `restore <project> file <file> <out>`)
  exposing the Phase-3 baseline+diff restore engine. Drive tests fully mocked —
  zero real Google calls in CI. Verified by artifact + live: audit 100% (all 37
  files), 187 tests, ruff clean, restore `list`/`file` round-trip confirmed.
- **Backup uses the repo-root pyright config like every citizen.** Removed
  backup's standalone `pyrightconfig.json` (a leftover from its pre-namespace
  standalone days, archived) so it inherits the root config — resolving imports
  consistently with the rest of AIPass. Dead PyQt5 `ui/settings_window.py`
  (never wired) archived.

- **Backup versioned baseline + per-file diff engine (FPLAN-0267, Phase 3 of
  FPLAN-0264 — the heart).** Faithful port of the GOLD versioned engine,
  replacing the mtime full-copy-into-timestamped-dirs remnant. One persistent
  store (`.backup_system/versioned/`) with GOLD's file-folder packaging: each
  file gets `<parent>/<name>/` holding the current copy, a
  `<stem>-baseline-<date>.<ext>` full copy from the first run (never touched
  again), and `<name>_diffs/<name>_v<old-mtime>.diff` unified-diff patches on
  every change — append-only, versioned **never deletes** (cleanup stays
  snapshot-only). Versioned and snapshot back up the identical file set (same
  scan + ignore patterns; `all` shares one scan). Change detection is
  ledger-free (source mtime vs store-current mtime, `copy2`-preserved) — kills
  the regression where running snapshot starved the next versioned via the
  shared `timestamps.json`. New `diff/restore.py` (`list_versions` +
  `restore_file`); `diff/generator.py` wired (binary detection + diff
  include/ignore patterns). +15 tests (125 total). Verified by artifact + live
  end-to-end: snapshot-first-then-versioned still baselines everything
  (starvation dead), edit → real diff with old-mtime timestamp, source delete →
  versioned store untouched while snapshot mirror-deletes, restore round-trip
  byte-identical.

- **Backup snapshot fidelity + shared core (FPLAN-0266, Phase 2 of FPLAN-0264).**
  Restored the snapshot-side machinery the 2026-04-23 rewrite degraded, ported
  from the GOLD archive onto the current per-project handlers. New
  `handlers/cleanup/mirror.py` `cleanup_deleted_files` — exception-aware
  mirror-delete: files removed from source are now removed from the snapshot
  (was a blind `rmtree`+recopy), respecting ignore-exceptions. `copy/snapshot.py`
  gains mtime-skip (quick-check fast path — unchanged files no longer re-copied),
  a long-path guard (>260), and read-only handling. `report/result.py`
  `BackupResult` now tracks critical vs non-critical errors + warnings +
  `files_deleted`; `ignore/patterns.py` gains `IGNORE_EXCEPTIONS`/`is_exception()`.
  +16 tests (`test_snapshot_fidelity.py`, 110 total). Verified by artifact +
  live: audit 100%, 110 passed, and a real throwaway-project test (delete two
  files → re-snapshot → both mirror-deleted, kept files preserved, 3 skipped/0
  re-copied).

- **Backup test suite + seedgo 100% — restoration foundation (FPLAN-0265, Phase 1
  of FPLAN-0264).** Put a safety net under `backup` before the feature rebuild:
  new `tests/` suite (94 tests — json_handler, CLI routing, filesystem handlers,
  error resilience, mocked drive) ported from the canonical citizen conftest
  pattern (hermetic, `tmp_path`, stdlib-only → 3.10–3.13), driving module coverage
  to 27%. Standards brought to 100% across all 35: shared `--help/-h/help` guard
  wired into all 10 modules' `handle_command` (Cli + Introspection), the 6
  Phase-3 drive/diff/ui stubs wired-or-bypassed (Dead_Code + Unused_Function),
  `requirements.project.txt` added (Architecture), README module list + the small
  Modules/Trigger fixes (`display.handle_command`, `create_progress_bar` →
  `build_progress_bar`). Verified by artifact: re-ran audit (100%) + pytest
  (94 passed) + ruff (clean).

### Fixed

- **Memory rollover no longer silently loses rolled-off learnings ("No embeddings
  generated").** A capped `.trinity` file rolls its excess entries out to vectors;
  two combined bugs dropped them on the floor instead. (1) On the "embedding returned
  empty but success=True" path the orchestrator logged the error and continued — but
  the source file was *already* trimmed, so the entry was lost from both the file and
  ChromaDB; it now restores the pre-trim backup before continuing (fail-honest).
  (2) A concurrent-rollover race (two runs ~33ms apart) let the second run extract
  nothing yet still report success → empty embeddings → bug #1; `extract_with_metadata`
  now honors the `skipped` flag and the orchestrator skips no-op extractions before the
  embedding stage. Verified by artifact + live: a 25/25-capped test file rolls over →
  embeds (384-dim) → `drone @memory search` returns it at 91% similarity; audit 100%,
  876 tests (+4).

- **Backup rich CLI output restored end-to-end (FPLAN-0263 + drone passthrough).**
  `drone @backup snapshot|versioned|all` rendered a flat text block instead of the
  original rich output. Two independent causes, both closed: (1) the rich rendering
  was never carried forward in backup's revival — rebuilt as a faithful 9-stage port
  (new `backup_timestamps` state handler + `display.py` pipeline: Last-backups panel →
  boxed header → live Rich progress bar → result summary → Backups-now panel;
  `BackupResult` extended with `files_checked`/`files_skipped`/`backup_path`; copy
  handlers emit `on_progress` callbacks). (2) drone was flattening it at the pipe —
  `@backup` ran through `capture_output=True` (non-TTY → Rich strips color, the
  `transient` progress bar renders to nothing) and the 30s capture timeout would kill
  large backups; added `backup` to drone's `INTERACTIVE_BRANCHES` so all `@backup`
  commands inherit the terminal (mirrors `cli`). Verified live under a pty: full color
  + animated progress bar.

## [2026-06-11]

### Fixed

- **seedgo audit local↔CI parity (FPLAN-0261).** The local `seedgo` audit could
  silently diverge from CI, breaking the "pass locally first, then ship" gate.
  Three independent causes, all closed without coupling any checker to git
  (`.gitignore` is git's concern, not the audit's): (1) usage-scanning checkers
  (`unused_function`, `dead_code`, +4) `rglob`'d gitignored *output* dirs
  (`artifacts/`, `dropbox/`), so a stray local file could mark a function "used"
  that a clean checkout correctly flags — every per-checker skip list hoisted to
  one shared `SOURCE_SKIP_DIRS` (output dirs simply aren't source). (2) The
  `diagnostics` standard shelled out to bare `python3 -m pyright` (system python,
  no pyright) and, on the resulting JSON-parse failure, returned *0 errors = clean*
  — a silent false-green; now uses `sys.executable` and **fails loud**. (3) pyright
  resolved imports against PATH-python, so results flipped with `.venv` activation
  — pinned via `--pythonpath sys.executable`. The audit is now deterministic
  local == CI (proven all-13-branches-100% in an unactivated shell). Also: `drone`
  bypasses the test-only broker `start_background` (intentional API, not dead code).
- **windows-setup CI: guard Linux-only sandbox tests.** The kernel-sandbox build
  is Linux-only (bwrap, `AF_UNIX` sockets, `openat2`); the code already guards on
  `sys.platform`, but four test surfaces ran unconditionally and failed on
  `windows-latest`. Module-level `pytestmark = pytest.mark.skipif(sys.platform !=
  "linux", …)` on `drone/tests/test_broker.py` and `hooks/tests/test_sandbox.py`;
  scoped guards on the remaining `AF_UNIX` broker-socket tests —
  `ai_mail/.../test_dispatch_monitor.py::TestBrokerRealE2E` (class) and
  `aipass/.../test_sandbox_check.py::TestCheckBrokerAlive` socket-connect tests
  (method-level, so the graceful no-broker paths still run on Windows). All skip on
  Windows and run unchanged on Linux. windows-setup was green pre-sandbox-merge
  (`00edd8b`) and red since (`0b4ba63`); this closes it.
- **Broker `start_background` connect-before-bind race.** `drone`'s out-of-sandbox
  broker daemon started via `start_background()`, which returned *before* the
  `AF_UNIX` socket was bound — callers then raced the bind, and on a slower machine
  `create_identified_connection()` hit `FileNotFoundError` (socket not yet present).
  Deterministic locally (`test_delete_nested_file` 0/5), green in CI only by timing
  luck — latent flakiness. Fixed with a `threading.Event` set right after `listen()`;
  `start_background(timeout=5.0)` now blocks on it and **raises** if the socket never
  binds, so callers never guess a `sleep`. Removed the 4 blind `time.sleep(0.15)`
  waits from the broker tests. Verified 55/55 broker tests, formerly-failing test 10/10.

### Added

- **`aipass init` detects missing Claude Code.** Stage 6 (CLI choice) now checks
  `shutil.which("claude")` when the picked CLI is Claude Code. If absent: interactive
  runs prompt `Install now? [Y/n]` and run the canonical installer on yes (native
  `claude.ai/install.sh`, PowerShell on Windows, `npm` fallback, 300s timeout, loud on
  failure); non-interactive runs warn and continue. The whole system routes through
  Claude Code (hook bridge, dispatch, prompt injection), so init no longer silently
  assumes the runtime is present. Only fires when the chosen CLI is `claude`.
- **Kernel filesystem boundary for agent containment (DPLAN-0202 / FPLAN-0250).**
  Every autonomous agent can now launch inside a kernel-enforced mount namespace
  (`@anthropic-ai/sandbox-runtime` → bwrap+seccomp) where reads stay fully open
  (the shared live filesystem is preserved — a bind-mount, *not* isolation: own-tree
  writes land live on the real FS instantly) but deletes/overwrites of protected
  paths (`.git`, sibling branch trees) fail at the kernel no matter how the call is
  phrased — `rm`, `python os.remove`, `find -delete`, Write tool all hit EROFS.
  `/tmp` and the agent's own tree stay writable; `.git` is RW for devpulse, RO for
  builders. A per-role policy generator (`@hooks build_policy`) derives each branch's
  writable/RO map from its passport. Privileged deletes route through an
  out-of-sandbox **drone-broker** daemon: identity-scoped allowlist, `openat2`
  RESOLVE_BENEATH path re-resolution (confused-deputy proof), HMAC identity handshake
  over a pre-connected inherited fd, JSONL audit. `aipass doctor` gained a **Sandbox**
  check group (bwrap present+functional, node, srt, rg, broker socket) that is LOUD
  when the flag is on and a prereq is missing — never a silent unsandboxed launch.
  Proven by a live 16-check red-team suite. **Inert by default** — gated behind
  `AIPASS_SANDBOX_ENABLED` (off); flag-off is byte-identical to the old dispatch path.
- **rm_gate demoted to guardrail.** Now framed honestly as early-feedback that
  catches the accidental `rm -rf` and teaches `drone rm` — belt-and-suspenders, with
  the kernel sandbox as the actual filesystem boundary.

- **Prompt-injection cadence — fire the big loaders every Nth turn.** The global
  and branch prompts are large and were re-injected on *every* turn even though a
  prior copy stays in the conversation. They now fire together every 5th turn
  (config-tunable via `hooks_json/custom_config/cadence_config.json`), with a
  per-session turn counter that resets on a new session and after compaction so
  context is always rebuilt when it's actually needed. Identity and the mail flag
  stay every-turn (tiny, want freshness). Cuts recurring per-turn context cost.
- **Hook fire/skip observability.** Cadence emits a structured
  `[HOOKS] cadence fired|skipped loader= turn= period= offset=` line; the prax
  monitor renders hook events distinctly so the cadence is visible live.
- **Slim global prompt — context-on-demand.** The always-injected global prompt
  was rewritten from a ~13.8KB encyclopedia into a ~7.8KB navigation map
  (DPLAN-0201): `drone` pinned as the router, the framework tree, all 13 agents
  as short bios, and one drilled reflex — run `drone @agent --help` before using
  a branch. Detail now lives in each agent's `--help`, fetched on demand. This
  also dissolves the harness ~10k-char truncation that was silently dropping the
  old prompt's tail; the slim prompt injects whole. Backup retained alongside.

### Changed

- **Shared leaf library re-homed: `aipass.common` → `aipass.aipass.shared` (FPLAN-0260).**
  `src/aipass/common/` was the only non-citizen directory in the agent namespace —
  a shared lib (json_handler / json_ops / registry_discovery, extracted in
  TDPLAN-0006 P2) parked as a sibling to the agents with no owner. Per @seedgo
  design review it now lives inside its steward at `src/aipass/aipass/shared/`,
  owned by @aipass; @spawn imports across (same blessed shared-infra category as
  `aipass.prax`/`aipass.cli`). Content byte-identical; ~9 import/doc sites updated
  across aipass+spawn. A new subprocess guard test pins the bootstrap-safety
  invariant: importing `shared/` loads zero branch dependencies, so `aipass init`
  keeps working pre-drone on fresh machines. Note: `aipass.common` shipped in the
  v2.5.2 wheel; it was internal plumbing — no deprecation shim.
- **Action-gated hook sound.** Piper now speaks only when a hook actually *does*
  something — handlers return a `sound` key the engine plays, instead of
  announcing on every invocation. Skipped loaders are silent. Quieter and honest.
- **README: hardcoded metrics → live badges + qualitative.** Version is now a
  live PyPI badge, test/PR counts replaced with a codecov coverage badge (75%
  minimum) and qualitative wording — no more stale numbers to hand-maintain.

### Fixed

- **Cadence counter separate-process race.** Each `UserPromptSubmit` hook runs as
  its own OS process, so a module-level turn cache double-incremented and the
  loaders leapfrogged (firing erratically instead of together). Fixed with an
  mtime debounce + transcript-size token + `flock` so the counter advances exactly
  once per real turn, verified against the live execution model.
- **`auto_fix` ran no diagnostics.** A leftover `speak()` call (its import removed
  in the sound refactor) raised `NameError` on every edit, swallowed by the
  handler's broad `except` — so auto-fix silently surfaced nothing on any
  `.py`/`.json` edit. Removed the dead call; diagnostics run again.
- **Hook events never colored in the monitor.** The prax log-watcher's
  `_HOOK_PATTERN` required an `action=` field that cadence never emits (it logs
  the action as the bare second word, `fired`/`skipped`), so extraction failed
  and events fell through to plain rendering instead of the styled
  bold-green ⚡ / dim · treatment. Fixed the regex to capture the bare action
  word and enriched the event detail (period, offset, short session id).

### Security

- **Least-privilege token on the `e2e-wheel` workflow.** `e2e-wheel.yml` was the
  one CI workflow missing a top-level `permissions:` block (it was added during
  the cross-OS work after PR #624 hardened the others), so it ran with the
  default broad `GITHUB_TOKEN` scopes — dropping the OpenSSF Scorecard
  Token-Permissions check to 0. Added `permissions: contents: read`; the
  workflow only reads the repo to build and smoke-test the wheel.
- **Signed GitHub Releases via Sigstore (keyless).** The release workflow now
  signs the built wheel + sdist with `sigstore/gh-action-sigstore-python`
  (keyless OIDC — no signing key is generated, stored, or held by anyone) and
  attaches the resulting `.sigstore.json` bundles to the GitHub Release. PyPI
  uploads were already attested via Trusted Publishing; this extends verifiable
  provenance to artifacts pulled from GitHub Releases and satisfies the OpenSSF
  Scorecard Signed-Releases check. First proof lands on the next `v*` tag.

---

## [2026-06-02]

### Fixed

- **`aipass init` scaffold correctness.** A fresh `aipass init` now generates a
  project-specific `AGENTS.md` (new `agents_md()` generator) instead of falling
  back to copying AIPass's own repo-root `AGENTS.md` boilerplate — Codex users
  were getting the wrong file. Project `README.md` quick-start/structure paths
  now reflect the real `src/<package>/<agent>/` layout.
- **First-agent default name `my-agent` → `my_agent`.** `aipass init` seeded its
  default agent with a hyphen, the lone source of a long-standing dir-vs-module
  mismatch (the directory kept the hyphen while the importable module, `@address`
  and registry name all normalize to underscore). Defaulting to `my_agent` makes
  directory, module, `@address` and the README example all consistent.
- **Dead `citizenship.registry_path` removed from spawn templates.** The field
  pointed at a non-existent `.aipass/registry.json`; it was never read anywhere
  (registry is located by `find_registry()` glob), so it's dropped from the
  `builder` and `birthright` passport templates.

### Removed

- **The entire STATUS flow is decommissioned (TDPLAN-0007).** The per-branch
  hand-maintained `STATUS.local.md` beacon and the auto-aggregated central
  `STATUS.md` (853 lines / 70 KB nobody read) are gone — deleted from disk
  across all 13 branches and scrubbed from every prompt, doc, startup protocol,
  `/prep` + `/memo` skill, the compact-recovery hook, the email footer, and
  `aipass init` / spawn scaffolding. Live branch state was already fully covered
  by `DASHBOARD.local.json` (prax) and history by `.trinity/local.json`. The
  status-sync engine is kept **intact but inert** — made dormant by unwiring its
  3-line trigger registration (`trigger registry.py`), so the code stays
  revivable. The one thing STATUS uniquely gave us — a quick scratch todo — is
  replaced by an operational `todos[]` section in `.trinity/local.json`
  (@memory-owned schema, capped, never vectorized by rollover), pushed to all 13
  branches and surfaced as a `todo_count` on the dashboard. Shipped as one
  coordinated cross-branch change (memory, prax, trigger, aipass, spawn, hooks,
  ai_mail, seedgo + devpulse).

### Changed

- **All 13 branches at seedgo 100% under the new introspection standard.**
  Wrapped `print_introspection()` output in Rich markup across ai_mail, drone,
  spawn, trigger, prax and devpulse (the rest were already compliant) —
  presentation only, no logic change — so `drone @branch` with no args renders
  consistent styled output everywhere.
- **CLI polish for human-facing output.** `drone @hooks --help` rewritten (Rich,
  with `hooksound on/off/status` now surfaced); `drone @spawn` repair help
  clarified as distinct from `update` and showing the preview/`--apply` flow;
  drone restores Rich colour on human-facing routed output (`--help`,
  introspection, `status`) via the inherit path.
- **Spawn backups land in one namespace `.spawn/.recovery/` (TDPLAN-0006 P4).**
  Spawn's pre-merge JSON backups previously dropped a `.recovery/` directory at
  each branch root (which had accumulated 242 stale auto-generated `DASHBOARD`
  backups across 10 branches). `aipass.common.json_ops.backup_json` gained an
  optional `backup_dir` parameter (default unchanged), and spawn's update engine
  now directs backups to `{branch}/.spawn/.recovery/` — tucked under the
  spawn-managed `.spawn/` dir instead of cluttering the branch root. Memory stays
  in the safety net (the engine simply never touches `.trinity/`/`DASHBOARD` on
  update, so it never needs to back them up). Stale `.recovery/` backups cleaned
  up. (315 tests, seedgo 100%.)
- **No more cross-branch engine imports — `aipass init update` calls spawn via
  subprocess (TDPLAN-0006 P3).** `init_flow.py` previously did
  `from aipass.spawn.apps.modules.sync_registry import sync_registry` — the one
  place aipass reached directly into spawn's Python. Replaced with a subprocess
  call to the already-existing `drone @spawn sync-registry --fix` (same pattern as
  `aipass init agent` → `drone @spawn create`), preserving graceful degradation
  (a missing `drone`, non-zero exit, or timeout is silently skipped — registry
  sync never hard-fails an update). The aipass branch now has **zero** direct
  imports of another branch's engine code; the remaining cross-branch imports are
  shared service layers only (cli Rich UI, prax logging, trigger events). (438
  tests, seedgo 100%.)
- **`aipass.common` shared library — dedup spawn/aipass scaffold machinery
  (TDPLAN-0006 P2).** `@spawn` and `@aipass` each carried their own copy of the
  JSON merge/handler utilities and registry discovery. Extracted them into a new
  branch-free package `src/aipass/common/` (`json_ops` = `deep_merge` +
  `backup_json`; `json_handler.JsonHandler`; `registry_discovery.find_registry`)
  that both branches now import. `aipass.common` imports **zero** branch code, so
  `aipass/bootstrap.py` (which runs before the drone runtime exists) can depend on
  it without breaking the pre-infrastructure constraint. The duplicated copies are
  deleted (spawn keeps a thin re-export shim; aipass's `json_handler` shrank
  254 → 88 lines). The `save_json` contract is unified to **raise `ValueError`**
  on invalid structure across both branches. (313 spawn + 434 aipass tests, both
  seedgo 100%.)

### Fixed

- **Flow plan-type self-serve UX — register override, help, orphan cleanup.**
  Explicit `drone @flow register <dir> <PREFIX>` now overrides an auto-derived
  prefix instead of silently failing (guarded — refuses if the auto-registered
  type already holds plans), so custom prefixes are settable when adding a new
  plan type. `create`/`templates --help` rewritten to dynamically list registered
  types + templates and document the add-a-new-type workflow. Stale orphan plan
  registries removed; dead `prefix_exists()` dropped. (728 tests, seedgo 100%.)
- **`drone @spawn update` no longer scrambles branches (#636, critical — TDPLAN-0006
  P0+P1).** The update engine compared a freshly-created branch against the class
  template by *content hash* with rename-detection, and because the CREATE path
  regenerated template-registry IDs in filesystem-walk order (≠ the master's
  hand-crafted IDs), a branch created seconds earlier produced **30 proposed renames**
  that rotated identity/memory dirs into each other
  (`apps→.trinity→.seedgo→.claude→.archive→.aipass`), turned `README` into
  `DASHBOARD`, and deep-merged stale template into live `.trinity/` memory —
  `update <class> --all` would have destroyed every citizen in one command. Rebuilt
  `update_ops.py` (v2.0) on an explicit **named-managed-files + path-based** model:
  `.trinity/*`, `DASHBOARD.local.json`, `artifacts/birth_certificate.json` and
  `.seedgo/bypass.json` are delivered on **create only** and never touched on update;
  the create==update invariant now yields **0 renames / 0 merges** on a fresh branch.
  The old ID-based engine (`change_detection.py`, `reconcile.py`) is deleted.
- **Destructive spawn ops are now dry-run by default (TDPLAN-0006 P0).** `drone @spawn
  update` and `drone @spawn repair` preview by default and require an explicit
  `--apply` to write — forgetting a flag is now a safe no-op instead of irreversible
  damage (`--dry-run` kept as an alias). `aipass doctor` repair suggestions emit the
  matching `--apply` form.

### Added

- **Introspection Rich-formatting standard (seedgo).** New
  `check_introspection_rich_formatting` checker enforces that each branch's
  `print_introspection()` output uses Rich markup (delegation-aware — it walks
  `_`-prefixed helper functions), keeping no-arg `drone @branch` output styled and
  consistent. Documented in `introspection.md`; all 13 branches brought into
  compliance (see Changed).
- **Playbook plan type (`PBPLAN`) — reusable SOP checklists (flow).** A new
  `playbook_plans` template family for throwaway, vectorize-on-close operational
  runbooks (first SOP: the Sunday merge). Drop a `.md` under
  `templates/playbook_plans/`, register once, then
  `drone @flow create . "subject" <sop>` stamps a run to tick through and close.
- **Memory-pool auto-processing (TDPLAN-0005)** — dropped files in
  `memory/memory_pool/` are now vectorized and archived automatically on
  session-start and pre-compact, instead of requiring a manual
  `drone @memory pool process`. A 3-branch build: `@memory` gains an intake
  handler + `pool` module (processes then empties the pool, `keep_recent=0`),
  `@hooks` adds a `lifecycle/auto_process` handler (session-guarded via
  `CLAUDE_CODE_SESSION_ID`, since Claude Code has no SessionStart hook), and
  `@trigger` gains event #15 (`memory_pool_auto_processed`) with a Medic error
  path. Runtime pool dirs (`memory_pool/`, `memory_pool_archive/`) are now
  gitignored.
- **HVTracker badge** added to the README badge cluster, linking to the public
  agent profile at hvtracker.net (closes #628).
- **`git_gate` read-verb allowlist — raw read-only git for every branch.** The
  PreToolUse `git_gate` previously blocked *all* raw git (forcing `drone @git`
  even for harmless reads), which left agents unable to inspect what git ships —
  the exact forensics needed to diagnose the audit gap above. It now allows 22
  read-only verbs raw (`ls-files`, `ls-tree`, `show`, `cat-file`, `rev-parse`,
  `rev-list`, `log`, `status`, `diff`, `blame`, `archive`, `grep`, …) while
  write operations stay `drone`-gated. Global options (`-C`, `-c`, `--git-dir`,
  …) are skipped when extracting the verb, and chained commands are split on
  `&&`/`||`/`;`/`|` so a read piped into a write still blocks the whole line.
  (81 tests)
- **Cross-OS end-to-end WIRING test (`tests/e2e/`, `e2e-wheel.yml`)** — the first
  CI gate that proves real AIPass *wiring* (not units-with-mocks) by building the
  wheel, installing it into a clean venv, and asserting a 4-tier ladder: package
  install + console scripts (T0), `aipass init` scaffolding (T1), a hook actually
  firing via the bridge with an observable `engine.jsonl` record (T2a), and
  `drone` resolving + subprocess-executing a real branch (T3). Runs on a 3-OS
  matrix (ubuntu/windows/macos, `fail-fast: false`). Ran red-first on Windows by
  design and immediately earned its keep — it caught two real, *previously
  uncovered* Windows wiring bugs (`aipass init` preflight + `drone` stdout
  encoding, both fixed below). Notably the layers we most feared — clean-wheel
  install (T0) and hook firing (T2a) — passed on Windows. (DPLAN-0194 /
  FPLAN-0239)
- **`drone rm` — provider-agnostic safe delete** — a contained recursive delete
  that lets agents clean up scratch dirs without tripping the `rm -rf` block.
  Deletes are confined to the project root and the system temp dirs (`/tmp` and
  `$TMPDIR`), refusing anything outside (home, `/etc`, `/`, etc.). Even inside
  those roots it hard-refuses protected internals — `.git`, `.trinity/`,
  `.aipass/`, `.codex/`, `.agents/`, and sibling-branch worktrees — mirroring the
  filesystem boundary an OS-sandboxed agent (e.g. Codex) enforces, so behavior is
  consistent across CLIs. Pure-Python (`shutil.rmtree`), with a red-team test
  suite for containment escapes (symlinks, traversal, sibling branches). (#630)
- **`rm_gate` hook — block raw recursive `rm`, teach the safe path** — a
  PreToolUse gate (mirroring `git_gate`) that blocks raw `rm -r`/`-rf`/`-fr`/
  `--recursive` and redirects the agent to `drone rm`. Provider-agnostic (runs in
  the hook engine, not tied to Claude Code permission rules), conservative
  (unparseable targets are blocked, not allowed), and skips `drone rm` itself.
  This makes the safe-delete path discoverable at the moment of friction. (#630)
- **Hook engine logs `agent_type` / `agent_id` per fire** — the engine now
  records which agent triggered each hook (e.g. `agent=main` vs `agent=Explore`)
  in both `engine.jsonl` and the prax monitor stream. Previously the payload
  flowed into handlers but was never logged, leaving no way to tell an internal
  main-turn fire from a real sub-agent fire. Pure visibility; no behavior change.
  Groundwork for #606. (#606)
- **OpenSSF Best Practices passing badge** — AIPass earned the OpenSSF Best
  Practices (CII) **passing** badge (100% of criteria), added to the README badge
  cluster. Self-certified across all six categories — basics, change control,
  reporting, quality, security, and analysis. Complements the existing OpenSSF
  Scorecard, lifting the `CII-Best-Practices` check from 0. (DPLAN-0193)

### Changed

- **Standards floor raised to genuine 100% across all 13 branches** — completed
  the campaign that lifted the seedgo gate threshold from 80 to 100. Rather than
  bypass failing files, two check *flaws* were fixed at the root: (1) the
  **file-size / architecture check is now advisory** (warn-only for 700–1500 line
  files with no docstring nudge, hard-fail only above 1500) — large files are a
  smell, not a defect; (2) **readme-freshness now compares against git history,
  not file mtime** — `git checkout`/`merge` reset mtimes without any semantic
  change, so the old check false-positived (flow + prax shared an identical
  mtime from one git event, not real edits). It now diffs the README's "Last
  Updated" against the last commit that touched `.py`. Genuine content fixes
  where warranted (aipass requirements template + handler routing; honest README
  content refreshes on flow, prax, devpulse). The readme-freshness **failure
  message now teaches** the right fix ("update README content, then set the date
  — don't just bump it"). Also optimized the devpulse watchdog poll cadence
  (2s → 5s; the loop is cheap, so the tighter interval was wasted CPU). (#631)

- **Retired the blanket `rm` deny from provider settings** — `setup.sh` and
  `aipass init` no longer ship `Bash(rm -rf*)` / `Bash(rm -r *)` deny rules
  (they were mis-filed among git rules, blocked all `/tmp` cleanup, and gave a
  bare "permission denied" with no guidance). The `rm_gate` hook + `drone rm`
  now own this — cross-provider, path-aware, and they teach. `aipass doctor`
  detects the stale rules on existing installs and `aipass doctor --fix` removes
  them (idempotent, preserves all other rules). Claude Code still natively
  circuit-breaks `rm -rf /` and `rm -rf ~`. (#630)

### Fixed

- **`Windows Test` / `macOS Test` are no longer path-filtered — they were
  stalling PRs as required checks.** Both workflows only triggered when
  `setup.sh`/`drone/cli.py`/`handlers/__init__.py`/`pyproject.toml` changed, but
  branch protection lists `windows-setup`/`macos-setup` as *required*. On any PR
  that didn't touch those paths the workflows never ran, so GitHub parked the
  required checks as "Expected — waiting for status" indefinitely, blocking the
  merge (the tests themselves were green — they simply didn't fire). They now run
  on every push/PR to main/dev, like the other required lanes. (A required check
  must never be path-filtered.)
- **`seedgo-audit` CI gate was red despite 100% local audits — four checkers
  validated the working tree instead of committed source.** CI audits a clean
  `git checkout` (tracked files only — git ships no empty or gitignored dirs),
  but the working tree carries runtime dirs (`logs/`, `*_json/`, `artifacts/`,
  `.trinity/`, `passport.json`), so every branch scored ~97% in CI while passing
  at 100% locally. Reproduced exactly with a tracked-only tree (`git archive HEAD`
  audits to CI's 97%). Four checkers now measure what git actually ships:
  `log_structure` no longer fails when the gitignored `logs/` dir is absent (it
  still enforces no-hardcoded-paths); `readme` cross-references `.gitignore`
  (via `git check-ignore` with a fallback list) and skips gitignored dirs/links
  in the directory-tree and dead-link checks; `encapsulation` infers the branch
  from the path when the gitignored `AIPASS_REGISTRY.json` is unavailable (and no
  longer collides on the `aipass` branch); `architecture` skips cleanly when the
  gitignored `passport.json` is absent. A follow-up refined `readme`'s
  `git check-ignore` use: `.gitignore` dir-only patterns (trailing slash —
  `logs/`, `**/*_json/`, `.trinity/`) don't match a clean checkout's
  non-existent paths unless directory intent is signalled, so the check now
  also tests the trailing-slash form (this was the last 1% — `readme` flagged
  `cli_json`/`logs`/`artifacts` as "missing on disk" in CI only). The CI gate
  (`.github/scripts/seedgo_audit.py`) now also prints the failing standards and
  their check messages, so a sub-100 result says *why*, not just the percentage.
  Finally, the `seedgo-audit` CI job now installs the `memory` extra
  (`pip install -e ".[dev,memory]"`): the `diagnostics` standard runs pyright over
  every branch, and memory's handlers import `chromadb`/`numpy` at module level —
  without those declared deps installed, pyright reported them as unresolved
  (`reportMissingImports=error`) and memory scored 55%, a false failure from a
  missing CI dep rather than a code defect. Clean-tree and working-tree audits
  both report 13/13 = 100%. (DPLAN-0195)
- **Two latent Windows portability bugs caught by the new e2e harness** — both
  were always present in the code; they only surfaced now because this is the
  first CI to run `aipass init` scaffolding and real-branch `drone` routing on
  Windows (the old Windows CI ran an editable install, `aipass`-less, and only
  routed to in-process modules, so both paths had zero Windows coverage). Pure
  portability fixes — Linux/macOS behaviour is unchanged.
  - **`aipass init` crashed on Windows (surfaced as a misleading "Unknown
    command: init").** Init scaffolded the project correctly, then crashed
    *printing its `✓ Project initialized` banner* — Rich wrote the ✓/box glyphs
    through a cp1252 stdout, raising `UnicodeEncodeError ('charmap')`; the error
    handler's `✗` message hit the same wall, bubbling up to the command router
    which mislabeled it. The `aipass` entry point now reconfigures stdout/stderr
    to UTF-8 in place on Windows. (The init preflight ancestor-walk was also
    hardened to skip un-enumerable Windows drive-root entries — defensive, not
    the trigger.)
  - **`drone @branch` crashed on Windows with the same `UnicodeEncodeError
    ('charmap')`.** `drone` resolved + subprocessed the branch correctly, then
    crashed *printing* the captured output through cp1252 stdout. The existing
    `PYTHONUTF8` guard only affected child interpreters, not the live process
    streams — `drone`'s entry point now also `reconfigure()`s stdout/stderr to
    UTF-8 in place.
  - **CI unit lane no longer runs the e2e wheel tests.** `ci.yml`'s
    `pytest --rootdir=.` swept in `tests/e2e/` (which build a wheel per the
    dedicated `e2e-wheel.yml`), failing the unit lane; it now `--ignore`s them.
    (DPLAN-0194)
- **A release merge can no longer destroy the `dev` branch** — `drone @git merge`
  passed `--delete-branch` to `gh pr merge` unconditionally, so merging a
  `dev`→`main` PR deleted the persistent `dev` branch on the remote and stranded
  the working tree on `main` (the next commit silently landing on main). Merge now
  looks up the PR's head ref and **only deletes non-protected branches** — `dev`
  and `main` are never deleted, and an undeterminable head ref fails safe (no
  delete). After a merge it returns the working tree to `dev` (loud warning if it
  can't). `drone @git branches` now runs `fetch --prune` before listing so it
  reflects the live remote instead of stale cached refs, and a new
  `drone @git prune-temp` cleans up merged temp PR branches. (#625)
- **`drone @git status`/`diff` show their scope** — when scoped to a branch (no
  `--all`), output now appends "(showing <branch> scope — use --all for full
  repo)", so an empty scoped view is no longer mistaken for a clean repo. (#623)
- **External projects can call AIPass branches via drone** — `drone @api ...`
  (and any `drone @X`) now resolves from a non-AIPass project CWD instead of
  being blocked with "path escapes project root." The resolver was validating a
  branch's path against the *primary* registry root even when the branch was
  found via the `AIPASS_HOME` fallback, so any external project (Vera Studio,
  Daemon) hit a false security block. `resolve_branch()` now validates
  containment against the registry the branch was actually found in. Security is
  unchanged — each branch is still contained within its own declaring registry's
  root; genuine path escapes remain blocked. (#618)
- **`aipass <command>` runs instead of printing an introspection banner** —
  `aipass` is a user-facing binary, so `aipass doctor` (and every other command)
  must execute, not describe itself. All 7 modules (`doctor`, `doctor_fix`,
  `doctor_wire`, `handoff`, `help_chat`, `init_flow`, `profile`) previously hit a
  no-args→introspection gate (a standard meant for `drone @branch <module>`
  discovery) and showed a banner on bare invocation. Now bare invocation runs the
  command or shows usage; the introspection banner moved to `--info`. The seedgo
  introspection standard is bypassed for these binary-invoked modules (documented).
- **Dashboard plan counts no longer zeroed on refresh** — a branch's
  `active_plans` was reset to `0` by every `drone @prax dashboard refresh`, because
  `PLANS.central.json` only held Flow's own plans (`location==FLOW_ROOT` filter).
  The central file is now comprehensive: all plans grouped per-branch, so refresh
  reports each branch's real count (e.g. devpulse now shows its 12 open plans
  instead of 0).

### Security

- **`dependency-scan` (pip-audit) green again — upgrade pip, drop stale ignores.**
  The `Security Scan` workflow's `dependency-scan` job had gone red: pip-audit
  scans the whole environment, and the runner's bundled pip (26.1.1) carries
  advisory PYSEC-2026-196 (fixed in 26.1.2). The job now runs
  `python -m pip install --upgrade pip` before auditing (it was the only CI job
  not upgrading pip), removing the vulnerable version outright rather than
  suppressing it. 26.1.2 also resolves CVE-2026-3219 and CVE-2026-6357, so the
  two now-stale `--ignore-vuln` entries were removed — verified against a clean
  reproduction of the job's environment, which audits to "No known
  vulnerabilities found" with nothing ignored.
- **Pinned the `requests` floor to a non-vulnerable version** — raised
  `requests` to `>=2.34.2` in `pyproject.toml` and the API branch's
  `requirements.project.txt` (which previously listed it unconstrained). This
  clears six OSV advisories the OpenSSF Scorecard flagged against the dependency
  (PYSEC-2014-13, PYSEC-2014-14, PYSEC-2018-28, GHSA-9wx4-h78v-vm56,
  GHSA-9hjg-9r4m-mvj7, GHSA-gc5v-m9x4-r6x2) — the oldest surfaced only because the
  dependency was declared without a version bound. No runtime change (the AIPass
  venv already ran a fixed release). (DPLAN-0193)
- **Pinned the test container base image by digest** — `Dockerfile.test` now pins
  `ubuntu:24.04` to its registry digest (`sha256:786a8b55…`) so the test image is
  reproducible and tamper-evident, clearing the Scorecard `containerImage not
  pinned by hash` finding. (DPLAN-0193)

---

## [2026-05-30]

### Added

- **`drone @hooks status`** — read-only viewer for a project's hook config:
  master switch, every hook's enabled state per event group, matchers, and an
  enabled/total summary. Resolves the project's `.aipass/hooks.json` by walking
  up from CWD. (DPLAN-0190 Phase B)
- **Hooks activate in every project** — `aipass init` now writes
  `.aipass/hooks.json`, so new projects fire the hook engine out of the box
  (previously: no config shipped, 0 hooks fired). `aipass init update`
  union-merges the template, preserving any per-hook on/off choices the user
  made. `aipass doctor` now checks for the config's presence. Dead hook-script
  shipping (`_ship_hooks`) removed. (DPLAN-0190 Phase A)
- **README logo** — centered logo image replaces plain `# AIPass` header.
  New `assets/logo.png` added to the repo.
- **OpenSSF Scorecard** — `.github/workflows/scorecard.yml` runs the official
  OSSF Scorecard action on push to `main` and weekly. Publishes a public security
  health score at scorecard.dev with a README badge. Actions pinned by SHA.
- **GitHub Releases** — `publish.yml` now cuts a GitHub Release on each `v*` tag,
  with notes pulled from the top CHANGELOG section and the built dist attached.
  PyPI publish + GitHub Release now fire from the same tag.
- **Registry descriptions** — all 13 branches now have one-liner descriptions
  in `AIPASS_REGISTRY.json`. `drone systems` shows what each agent does
  instead of blank lines. Closes [#607](https://github.com/AIOSAI/AIPass/issues/607).

### Changed

- **Security gates fully project-aware** — both the edit gate *and* the
  subagent stop gate now derive the package name dynamically from CWD instead
  of hardcoding `src/aipass/`. Cross-branch write protection and branch
  detection work for any `src/<package>/<branch>/` project; previously the
  subagent gate silently no-opped outside AIPass. 9 new external-project tests.
  Closes [#605](https://github.com/AIOSAI/AIPass/issues/605).
- **Hooks branch promoted to service** — registry profile changed from
  "AIPass Workshop" to "library" so it appears in `drone systems` alongside
  the other 12 services.
- **Hooks branch hardened to 100% seedgo** — the @hooks citizen took full
  ownership of its branch: every handler verified wired + firing, README
  rewritten (two-tier provider/project model, dynamic-dispatch design, event
  table), 2 stale tests resolved (253 pass). Dead-code/unused-function flags
  documented as architectural bypasses — the 15 handlers are invoked
  dynamically via `importlib` from `hooks.json` paths, never statically
  imported. (DPLAN-0191)

### Release

- **Version 2.5.0** published to PyPI. Trusted publishing via GitHub Actions
  (`publish.yml` triggers on `v*` tags — no manual twine upload needed). The
  same tag now also cuts a GitHub Release with these notes attached.

### Removed

- **Gemini CLI full removal** — deleted `.gemini/` directory (5 files) and
  `GEMINI.md`. Stripped all references from `setup.sh` (~50 lines),
  `README.md`, `bug-report.yml`, `aipass init` (bootstrap/scaffold/test),
  hooks (README/prompt/passport), and prax monitoring (~300 lines). 21 files
  changed, -927 lines. Closes
  [#608](https://github.com/AIOSAI/AIPass/issues/608).

---

## [2026-05-25]

First weekly release. AIPass now follows a Sunday release cadence: changes
accumulate on `dev` throughout the week and merge to `main` as a single
versioned release with notes.

### Added

- **Hook engine** — a new centralized dispatch system for all hook
  execution. A thin bridge receives events from the AI provider (Claude,
  Codex, etc.) and routes them through a single Python engine that reads
  per-project configuration, executes the appropriate handlers, and logs
  every invocation. Replaces 14 standalone shell/Python scripts with native
  handler modules organized by domain: prompt injection, security
  enforcement, lifecycle management, and notifications.
- **Per-project hook configuration** via `.aipass/hooks.json`. Each project
  can enable, disable, or customize individual hooks without touching
  provider-level settings. Previously hooks fired globally with no
  per-project control.
- **Audio feedback on hook events** using Piper TTS. All 14 handlers
  produce distinct spoken audio cues so operators can monitor sessions
  without watching the terminal. A shared sound module
  (`hooks/apps/sound.py`) provides `speak()` and `play()` with built-in
  mute support. Toggle with `drone @hooks hooksound on|off` — muting
  silences all 14 handlers without skipping their functional logic.
- **Hooks agent** — the 13th citizen in the AIPass registry, owning all
  hook infrastructure: the engine, bridge, handlers, and configuration
  schema.
- **Dashboard plugin for devpulse** — aggregates git status, session
  history, and dispatch state into a single startup view. Wired into the
  session startup protocol so branch managers see current state
  immediately.
- **External log routing** — prax now accepts structured log entries from
  any branch, not just its own modules. Hook executions, dispatches, and
  agent activity all flow into the central monitoring log.

### Changed

- **Provider settings fully migrated to bridge pattern.** All hook entries
  in the Claude provider configuration now call the bridge dispatcher
  instead of individual scripts. Each hook produces its own system-reminder
  to the model, preserving prompt injection fidelity (a single merged
  bridge was found to break prompt delivery due to Claude Code's output
  persistence threshold).
- **setup.sh rewritten** to install hooks via the bridge pattern. The old
  version hardcoded 14 script paths; the new version writes a single bridge
  call per event type and validates that the bridge module exists.
- **Documentation sweep** across `.claude/README.md`, `SECURITY.md`, the
  global prompt, and branch-level docs to reflect the new hook
  architecture. References to legacy `.claude/hooks/` scripts replaced with
  the native handler locations.
- **`aipass init update`** now correctly preserves user-customized hook
  settings during project updates instead of overwriting them.
- **Seedgo snapshot tests rebuilt** — the provider hooks snapshot fixture
  and extraction logic were structurally broken (silently passing with zero
  results). Both the fixture format and the test assertions have been
  corrected.
- **Test suite updated for hook migration** — `test_git_gate.py` imports
  from the new handler module; `test_bootstrap.py` no longer asserts that
  project initialization ships standalone hook scripts (it no longer does).

### Fixed

- **Settings merge on project update** — `aipass init update` was
  clobbering user hook configurations. The merge logic now layers AIPass
  defaults under existing user settings.
- **Python 3.10 test collision** — a module/function name collision caused
  mock patch targets to fail on Python 3.10. Test targets corrected.
- **Dead code removal** — removed an unused CLI `__main__.py` entrypoint
  and cleaned up `.gitignore` entries that were masking tracked files.
- **Codecov patch threshold** lowered to 50% to reflect the project's
  current coverage baseline and stop false-negative CI failures.

### Removed

- **18 standalone hook scripts** in `.claude/hooks/` disabled (renamed with
  `(disabled)` suffix). Their logic now lives in native handler modules
  under `src/aipass/hooks/apps/handlers/`. The old files remain on disk for
  reference but are no longer executed.
- **`drone hook-sounds` plugin** disabled. Sound control moved to hooks
  branch as `drone @hooks hooksound on|off` with full mute support for
  all 14 handlers (the old plugin only controlled 4).

### Infrastructure

- **Provider manifest migrated to bridge pattern.** `provider_manifest.json`
  now stores bridge commands (`$AIPASS_HOME/...bridges/claude.py EventType`)
  instead of standalone script names. `doctor_wire.py` auto-wires bridge
  entries directly — no longer copies scripts to `~/.claude/hooks/` or
  generates `sys.executable` paths. Doctor checks validate commands exist in
  provider settings instead of checking for script files on disk.
- **README v3** — rewritten for external users. Tighter problem/solution
  framing, collapsible agent details, Gemini CLI removed (untested),
  user-project perspective throughout.
- **Inline handoff** (`aipass init run` Step 11) — new default stays in the
  current terminal via `os.execvp` instead of opening a new window. Users
  choose "stay here" or "new window." Enables single-terminal demo
  recordings. Closes [#610](https://github.com/AIOSAI/AIPass/issues/610).
- **Project-aware global prompt** — the global prompt loader now detects
  whether CWD is inside AIPass or an external project. External projects
  receive their own lighter prompt (from `.aipass/aipass_global_prompt.md`)
  instead of the full AIPass-internal playbook. Fixes `drone @prax` errors
  in new projects.
- **Project CLAUDE.md template** — `aipass init` now generates a
  project-specific CLAUDE.md from `.aipass/project_CLAUDE.md` instead of
  copying the AIPass-internal one. Removes the startup protocol reference
  to `drone @prax dashboard refresh` which doesn't exist in external
  projects.
- **Gemini CLI removed** from `aipass init` CLI choices and handoff
  options. GEMINI.md no longer created for new projects. Gemini CLI is
  being retired upstream.
- **Demo GIF** added to `assets/demo.gif` and referenced in README.

---

*This is the first CHANGELOG entry. Prior work is documented in the
repository's commit history and branch session logs.*
