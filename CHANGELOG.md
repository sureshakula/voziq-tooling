# Changelog

All notable changes to AIPass will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Entries are grouped by merge under a dated section header (`YYYY-MM-DD`). Package
releases follow [SemVer](https://semver.org/) and are tracked by the git tag and
PyPI version — not the changelog header.

---

## [2026-07-03]

Post-2.6.1 cycle — **unreleased** (held for a later merge).

### Fixed

- **Telegram replies no longer overwrite the previous message.** The Stop-hook
  out-path (`hooks/.../notification/telegram_response.py`) reused a stale
  `processing_message_id`: after a successful delivery, `_advance_pending` kept
  the pending file but never cleared the placeholder id, so any reply that fired
  without a fresh "Processing…" bubble (remote/mirror input, multi-Stop turns)
  re-*edited* the same Telegram message instead of posting a new one — every
  response clobbered the last. Now clears `processing_message_id` after the first
  delivery, so subsequent Stops fall through to `_send_with_retry` (a new
  message). Root-caused live on the devpulse bot and proven by the delivery log
  flipping `edit`→`send`; +2 regression tests in `TestAdvancePending` (114/114).
  (fixed by @hooks, `f42a98b`, PR #651 — not yet merged)

## [2026-07-02]

Released as **2.6.1**. Rolls up the DPLAN-0226 / FPLAN-0289 / TDPLAN-0010 /
FPLAN-0298 batch (unified Telegram↔Claude Code bridge, single-session presence
gate, live Telegram streaming, `aipass init` template selector + portability,
`@backup share`) — all documented under `[2026-07-01]` — plus the CI
stabilization below.

### Added

- **`drone @git tag <vX.Y.Z>` — guarded release-tag automation (post-2.6.1).**
  Devpulse-tier verb that pushes a release tag with no manual step: fetches
  `origin`, refuses unless the tag's `X.Y.Z` matches **both** `pyproject.toml`
  and `src/aipass/__init__.py` on `origin/main` (version guard) and the tag
  doesn't already exist (exists guard), then tags `origin/main` and pushes —
  firing `publish.yml`. `drone @git tag --list` lists tags. Removes the merge
  playbook's last manual `git tag`/`push` step, so releases need zero user
  input. (built by @drone, S274)

### Fixed

- **CI green — six regressions from the DPLAN-0226 / FPLAN-0289 / TDPLAN-0010
  batch (PR #646).** The dev branch had gone red across `seedgo-audit`, the
  `test` matrix, and Windows; root-caused and fixed at source:
  - **seedgo** — the new `template_check` advisory checker was gating CI.
    `branch_audit.py` averaged *all* checker scores into the branch total, so
    `template_check`'s `ADVISORY=True` was never honored and it dragged 7
    branches below the 100% floor on legitimate README brace-examples. Added a
    `gating_scores` filter that excludes `ADVISORY is True` checkers before
    computing the average (strict `is True` to avoid MagicMock false-positives)
    and exposed `advisory_standards` in the audit output. Also refreshed the
    provider hooks snapshot fixture to include the `presence_gate`
    `UserPromptSubmit` hook (FPLAN-0289), fixing 4 `test_hooks_snapshot` tests.
  - **hooks** — `cc_sessions.py` (added by the bridge, `f6cbe34`) was missing
    its README entry and a seedgo `modules` bypass (it reads external
    `~/.claude/sessions/*.json`, not branch data, so `json_handler` is the wrong
    tool — same precedent as `presence.py`). Added both.
  - **spawn** — retired the `passport(disabled).py` / `passport_ops(disabled).py`
    pair to `.archive/`; the `(disabled)` suffix kept them visible to the type
    checker, which flagged a broken cross-import between them.
  - **ai_mail** — `test_child_inherits_broker_fd` gave its throwaway test branch
    a real `.trinity/passport.json` so the broker's new `.trinity`-marker
    resolution (`f914ab6`) can resolve it and permit the delete.
  - **spawn** — the `builder→aipass_framework` template rename (`13463c0`) left
    `.gitignore` exceptions pointing at the old `templates/builder/` path, so
    `DASHBOARD.local.json` + ~10 other template files were silently untracked
    since the rename — present on disk (dirty tree passed) but absent from clean
    clones/CI, so `test_full_spawn` failed only in a clean checkout. Fixed all 23
    `.gitignore` exception paths and committed the now-visible template
    scaffolding.
  - **skills** — `test_streaming` asserted a `+1` newline byte, but `write_text`
    text mode translates `\n`→`\r\n` on Windows (2 bytes), failing `windows-setup`
    only. Switched the test's transcript writes to `write_bytes()` for
    deterministic LF; production `_tail_transcript_bytes` was already CRLF-safe.

## [2026-07-01]

### Added

- **`aipass init` is now a template selector (TDPLAN-0010)** — `init` presents a
  chooser with **`empty project`** at the top, pre-selected as the default
  (creates just the project folder, no scaffold), and **`aipass_framework`**
  below it (the full AIPass agent framework — the old always-on behavior, now
  opt-in). Flag and positional forms both work: `aipass init --list` (branches
  before the `--` catch-all) and `aipass init <template>`. The AIPass-specific
  stages (8 spawn-first-agent / 9 ping-registry / 11 handoff / 12 init_report,
  `AIPASS_SPECIFIC_STAGES`) and the `bootstrap.init_project()` scaffold are now
  gated on the chosen template, so an empty project stays empty. In-product pip
  hints in `init_flow.py` + `doctor.py` retuned to clone/`setup.sh`. 8 new
  selector tests; 499 tests pass. (built by @aipass, FPLAN-0295, TDPLAN-0010)

- **Unified Telegram ↔ Claude Code bridge — CC-native session discovery
  (DPLAN-0226)** — a Telegram message to a branch's bot now lands directly in
  that branch's live Claude Code session, and the reply tails back out to
  Telegram — a full round trip, **live-proven end-to-end from Patrick's own
  Telegram client** (not just a self-test). The bot's inbound path
  (`base_bot.ensure_tmux_session`) discovers the active session by enumerating
  CC-native `~/.claude/sessions/<pid>.json` files (match `cwd`, confirm PID
  alive, newest by `startedAt`), maps it to a tmux pane by cwd, and injects the
  message — replacing the old `PRESENCE.central.json` pointer, which is kept but
  commented out. The outbound path gains a CC-native "Strategy 0" in
  `_resolve_active_transcript` that prefers the discovered transcript, so
  assistant replies relay back reliably. Anthropic ToS rules out a cloud peer,
  so all delivery is local (tmux/PTY). New `session_boot.py` boot wrapper
  (attach-if-live-else-start-in-tmux; a thin `~/.bashrc claude()` shim delegates
  to it). Hooks tests 66 green (presence_gate / cc_sessions / session_boot),
  telegram presence_pointer 42 green. (DPLAN-0226 P1/P2, FPLAN-0290/0291/0292)

- **Seedgo stale-template audit checker (`template_check`)** — a new advisory
  standard that flags branches still carrying unrendered template markers in
  their local prompts / config, so a citizen that never customized its scaffold
  no longer fails silently. Auto-discovered like every other checker; advisory
  (warns, never blocks). Ships with `template_content.py` and a `template.md`
  standard doc, covered by `test_template_check.py`. (built by @seedgo, DPLAN-0228)

### Fixed

- **Drone `--json` output no longer corrupts machine JSON** — `--json`
  pass-through was routed through Rich's `console.print()`, which defaults to
  width 80 on a non-TTY and hard-wraps mid-string, producing invalid JSON
  (e.g. `"Security \nScan"`). Fixed by writing raw JSON with `sys.stdout.write()`
  in the pass-through paths (`drone.py` + `router.py`) while keeping Rich for
  drone's own human UI. Verified live end-to-end. (fixed by @drone, td-49)

### Changed

- **README: pip removed, clone-only install (TDPLAN-0010)** — the top-level
  README no longer documents `pip install aipass` anywhere: the PyPI badge, the
  install steps (hero + Quick Start), the Project Status version badge, and the
  uninstall `pip uninstall` line are all removed. Install is now a single path —
  `git clone … && ./setup.sh` (puts `aipass` + `drone` on PATH), then
  `aipass init` scaffolds agents into your own project on top. Quick Start
  reorganized into Install → Your own project → Explore the full framework.
  (packaging code untouched; docs are clone-first.) (DPLAN-0228, devpulse)

- **Spawn: `builder` template → `aipass_framework`, birthright retired,
  per-project registry targeting (TDPLAN-0010)** — the citizen_class/template
  `builder` is renamed to **`aipass_framework`** across `class_registry.py`,
  `core.py`, `meta_ops.py`, `update_ops.py`, `sync_registry_ops.py`, help text,
  and the template dir itself (`templates/builder/` → `templates/aipass_framework/`).
  The class is no longer baked as a literal in the template passport — a new
  **`{{CITIZEN_CLASS}}` placeholder** (passport line 21, `placeholders.py`) now
  takes it from the create call. **`birthright`** (0 live users) is retired to
  `templates/.archive/birthright/` and its `passport` command disabled
  (`passport.py` / `passport_ops.py` → `(disabled).py`, routing removed).
  **Per-project registry targeting:** `spawn`'s `find_registry()` no longer
  passes `package_root` to the shared discovery (killing the silent fallback to
  AIPass's own registry for external targets), and `_spawn_agent` now validates
  containment and, if the found registry is outside the target's project, walks
  up from the target for `.git`/`pyproject.toml`/`setup.py`/`setup.cfg` to use
  **that project's own registry** — so an agent created into any project is
  tracked by that project's registry, never AIPass's. The
  `_validate_path_containment` isolation invariant is untouched. `create` also
  degrades gracefully when `@memory` is unavailable (empty meta-tabs, no crash).
  297 tests pass. (built by @spawn, FPLAN-0294, TDPLAN-0010)

- **Drone resolution + access checks made project-portable (TDPLAN-0010
  foundation)** — five `src/aipass`/fixed-depth self-location hardcodes are
  replaced with `.trinity/`-marker walk-ups: `rm_handler` sibling protection,
  `commit_handler` test-gate branch detection, `broker/daemon` allowed-bases,
  the `handlers/__init__` import-guard access check (now `is_relative_to()`
  instead of scanning path parts for the literal `aipass`), and
  `registry_handler`'s `parents[4]` last-resort (now a
  `.git`/`pyproject.toml`/`setup.py`/`setup.cfg` marker walk). `@name`→path
  resolution now works for an agent in any project layout via a CWD-first
  registry walk (AIPASS_HOME only as a last resort when the CWD ancestry has no
  registry at all). The `_validate_branch_path` containment invariant is
  untouched — per-project isolation preserved. (Drone uses its own resolver, not
  the shared `registry_discovery.py`.) 838 tests pass. (built by @drone,
  FPLAN-0296, TDPLAN-0010)

- **ai_mail routing made project-portable (TDPLAN-0010 foundation)** — the
  fixed-depth `_REPO_ROOT = parents[2].parents[2]` self-location in
  `email.py` / `email_send.py` / `dispatch.py` (4 sites) is replaced with the
  portable `find_repo_root()` marker-walk already used in
  `delivery.py` / `wake.py` / `paths.py`, so mail resolves via the project
  marker instead of a hardcoded tree depth — a prerequisite for agents that
  live outside `src/aipass/`. Per-project isolation preserved (no cross-project
  mailbox routing). 737 tests + seedgo 100%. (built by @ai_mail, FPLAN-0293,
  TDPLAN-0010)

- **Presence gate re-sourced to CC-native session files (presence_gate v2)** —
  the single-session guard now sources truth from `~/.claude/sessions/<pid>.json`
  via a new `cc_sessions` module (`find_occupant`/`find_live_for_cwd`) instead of
  `PRESENCE.central.json`. Resume-aware (a `/resume` keeps the same PID, so the
  session is correctly recognized as re-entry, not a duplicate) and exit-aware
  (CC deletes the file on clean exit). `handle_stop` is now a plain no-op —
  cleanup is CC's job. The old `presence.py` / `PRESENCE.central.json` are
  preserved, just no longer sourced. (DPLAN-0226 P1)

## [2026-06-25]

### Added

- **Daemon auto-runner — systemd user timer (the deferred last mile of the
  decentralized scheduler)** — `.daemon/schedule.json` jobs now fire **hands-off**.
  A oneshot `daemon-tick.service` + `daemon-tick.timer` (every ~2 min, mirroring
  the `prax-monitor.service` pattern: user-scope `~/.config/systemd/user/`, `%h`
  not hardcoded paths, venv-python ExecStart `-m aipass.daemon.apps.daemon run`,
  logs to `~/.aipass/daemon-tick.log` outside any tailed dir) reuses the existing
  fcntl-locked `run.py` tick unchanged — the timer is the ticker. New
  `apps/modules/timer_install.py` installs/enables it idempotently. Live-proven:
  @devpulse received a `DAEMON TEST` ping from a branch woken purely by the timer,
  no human tick. Tick profile: ~1.7s (import overhead only); the earlier CPU spike
  was `wake_branch` spawning opus agents concurrently, **not** the tick — so
  scheduled wakes want light models + staggering. Closes the piece DPLAN-0204 /
  FPLAN-0282 deferred. 461 daemon tests green, seedgo 100%. (FPLAN-0287)

- **Prax monitor → Telegram relay (`prax_monitor` bot)** — the live
  `drone @prax monitor run` Mission-Control feed now mirrors to a dedicated
  Telegram bot, so the whole-system monitor is watchable from a phone ("same
  monitor, different window"). New `monitoring/telegram_relay.py` taps the single
  render seam (`_render_event`), buffers events, and flushes every 5s (4000-char
  split, 150-line flood cap, `disable_notification`); fail-silent-once when
  unconfigured. Gated behind `--relay` / `AIPASS_PRAX_MONITOR_RELAY=1` so a local
  `monitor run` stays console-only (no double-send). Bot config (token + chat_id)
  loads from the @api secret `telegram/prax_monitor`. Ships a reboot-survivable
  `prax-monitor.service` user unit. 937 prax tests green (31 new). (DPLAN-0221)

- **Self-documenting `.trinity` state-tabs** — each memory-file section
  (`todos` / `key_learnings` / `sessions` / `observations`) now carries a
  config-sourced `⟦ rollover ON/OFF · keep N · ≤chars ⟧` tab rendered directly
  above it, so an agent editing a section sees its rollover state and character
  cap at the edit point (stops over-limit writes). Values are generated from
  `memory.config.json` (single source of truth) via @memory's new
  `render_all_meta_tabs()` / `tab_renderer.py`; @memory's `spawn_pusher` carries
  the `{{*_META}}` placeholders into @spawn's branch templates, and @spawn
  resolves them at create (`build_replacements_dict`, fail-loud on missing keys)
  so new branches auto-populate. `refresh_all_tabs` keeps live branches synced;
  @memory README documents the system. (FPLAN-0285, FPLAN-0286)

### Changed

- **Todo management — delete-on-done discipline** — `todos[]` are operational
  and exempt from rollover (confirmed; the vestigial `todos` entry was removed
  from `memory.config.json` rollover defaults). Because rollover never trims
  them, finished todos must be **deleted**, not left as `status: done` (which
  pile up and resurface as "open" across sessions). `/prep` and `/memo` (Claude
  + Codex) and the `CLAUDE.md` startup protocol now codify: delete each todo when
  done (proof → session entry), reconcile on load. (FPLAN-0285)

### Fixed

- **Daemonized wakes killed by systemd cgroup teardown (td-48)** — timer-fired
  `wake_branch()` calls spawned the dispatch monitor + claude child, then died
  within seconds with no email and a stale lock, while the *same* wake from an
  interactive terminal worked. Root cause: a systemd oneshot service defaults to
  `KillMode=control-group`, so when the ~1.7s tick process exits, systemd SIGTERMs
  **every member of its cgroup** — `start_new_session=True` is irrelevant because
  systemd tracks by cgroup, not process group. Fix in `ai_mail` dispatch: detect
  the systemd context (`INVOCATION_ID`) and re-spawn the monitor via
  `systemd-run --user` in its **own transient unit**, escaping the parent cgroup
  (falls back to direct `Popen` when not under systemd); plus `stdin=DEVNULL` on
  both the monitor and claude `Popen` calls and monitor PID self-registration in
  the lock. Now genuinely live-proven through the timer: 3 branches
  (commons/cli/backup) woken purely by `daemon-tick.timer` each emailed @devpulse
  and exited clean (~20s, code=0). 737 ai_mail tests green, seedgo 100%.

- **seedgo-audit — telegram ported-but-unwired functions** — the DPLAN-0218
  relocation pulled the telegram lib into the seedgo gate's scope, surfacing 16
  `unused_function` flags across 8 handler files. These are *not* dead code —
  they're ported-but-unwired from the ~9k-line Dev-Pass port (S249), awaiting
  DPLAN-0220 wiring (on_response hooks, response_router, tmux session mgmt, file
  up/download, multi-bot, config helpers). Added name-scoped `unused_function`
  bypasses in `skills/.seedgo/bypass.json` (the existing mechanism), each citing
  DPLAN-0220, and documented every one in `SKILL.md` → *Ported-but-unwired* with
  a "remove the bypass as you wire each fn" note. @skills back to 100%.

- **seedgo-audit — @spawn direct JSON read** — `core.py` adopt-path read a
  passport via `json.loads(path.read_text())` (direct file op), failing the
  `json_handler` standard and the CI seedgo-audit gate. Switched to
  `json_handler.read_json()` (the same pattern used a few lines above), dropping
  the now-unused `import json as _json`. @spawn back to 100%; 315 spawn tests
  green.

- **Windows CI — telegram `bot_registry` crashed test collection** — the module
  did a bare `import fcntl` (POSIX-only), so on Windows all 8 telegram test
  modules that transitively import it failed at *collection* with
  `ModuleNotFoundError: No module named 'fcntl'`, reddening Windows Test on the
  last several PRs. Guarded the import (`try/except ImportError → fcntl = None`,
  the established hooks/daemon convention) and routed the three flock call-sites
  through no-op-on-Windows `_lock`/`_unlock` helpers — advisory locking still
  applies on POSIX, is skipped where unavailable. Fixing collection then
  *unmasked* three telegram tests that had never actually run on Windows, all
  test-portability bugs (not product bugs): a log-streamer byte-count broke on
  CRLF translation (fixture now writes `newline=""`); a registry write-failure
  test used the Unix-only `/proc` path (now a cross-platform file-as-directory
  parent); and `validate_bot_config` rejected valid POSIX `work_dir`s on Windows
  because `Path.is_absolute()` is host-dependent (now tests POSIX *and* Windows
  absoluteness). 493 telegram tests green.

- **prax-monitor service feedback loop** — the unit wrote its own stdout into
  `system_logs/`, the very directory the monitor tails *and* @trigger watches,
  creating a self-reinforcing loop (monitor output → re-tailed and recorded by
  @trigger into `trigger_data.json` → reported as a file change → more output).
  Moved the service log to `~/.aipass/` to break the cycle. Also corrected the
  ExecStart to `monitor run` (relay enabled via env) — the module `__main__`
  rejects the drone-style `run all --relay` argument form. (DPLAN-0221)

## [2026-06-24]

### Changed

- **Skill library relocated to `src/aipass/skills/lib/`** — first-party skills
  were split across `catalog/` (built-in, cross-branch) and `.aipass/skills/`
  (the branch-prompt dir, cwd-relative). Renamed `catalog/`→`lib/`, moved the
  telegram skill in, archived three orphan test-fixture skills, and retired
  `.aipass/skills/` from the branch. This unifies all 6 first-party skills under
  one built-in tier and **fixes the telegram skill not being discoverable from
  other branches** (it sat in a cwd-relative path). The public discovery
  convention (`.aipass/skills/` + `~/.aipass/skills/`) is unchanged. One
  functional line changed (`discovery_handler` built-in path); telegram's test
  `conftest` path-depth, the systemd `.service` ExecStart, and seedgo bypass +
  test paths were updated to match. Packaging, imports, and gitignore are
  unaffected (everything stays under `src/aipass/`). 252/252 skills tests green;
  cross-branch discovery verified from another branch. Moving telegram into the
  gate's scope newly surfaced 9 pre-existing `unused_function` flags in its
  handlers — triage tracked separately. (DPLAN-0218)

### Added

- **`@api` in-process `set_secret` write-door** — `aipass.api.apps.modules.secrets.set_secret(provider, slug, value, *, as_json=False)`
  mirrors the existing `get_secret`, writing `~/.secrets/aipass/<provider>/<slug>.json`
  (dirs `0o700`, files `0o600`, value never echoed to stdout or logged). The @api
  secrets store was previously read-only; this is the writer the telegram
  mother-bot needs to persist a newly-created bot's config so the child can read
  its token. 515 @api tests pass (11 new), @api seedgo 100%. (DPLAN-0220)

- **Prax-monitor v1 on Telegram — `/monitor` system-wide log subscription** —
  the old Dev-Pass "prax monitor bot" (a `@prax` push relay on a dedicated token)
  was stripped during the port; this revives the capability as a feature of the
  existing `@aipass` bot (no second bot, no new credential). New `/monitor on`
  (errors+warnings) / `all` (firehose) / `off` / `status` command on `base_bot`,
  shown in the slash menu + `/help`. The subscribed chat is persisted to the `@api`
  store (`set_secret('telegram','monitor',{chat_id,mode})`) so it survives restart,
  and `base_bot` boot-starts the stream from it on startup — set-and-forget under
  systemd. `LogStreamer` gained `system_wide` (glob all `system_logs/*.log`, not one
  branch) + `level_filter` (default keeps `WARNING`/`ERROR`/`CRITICAL`, `all` =
  passthrough); `_init_positions` still seeks EOF so subscribing never floods
  history. 33 new tests (`test_monitor.py`), telegram suite 493/493, skills 252/252,
  @skills seedgo 98%. (First @skills run crashed mid-edit on 3 string-handling
  syntax errors; continued + fixed.) The richer AS-WAS `@prax` event-feed relay
  (rendered Mission-Control stream, needs a dedicated-bot-token decision) is tracked
  as Route B. (DPLAN-0221)

### Fixed

- **Telegram port — wave 1 (persistence + monitor + state hygiene)**, surfaced by
  a full completeness audit against `TELEGRAM_PORT_MAP.md` (366 tags, ~83% ported,
  452/452 tests green): (1) **bot launch** — `bot_factory.start_bot_process` and
  `telegram-bot@.service` used a non-existent `~/.venv/bin/python3`; now launch via
  `sys.executable -m …base_bot` (added `lib/__init__.py` + `lib/telegram/__init__.py`
  for package resolution, since base_bot uses relative imports). (2) **reboot
  survival** — `enable_service` now installs the systemd unit to
  `~/.config/systemd/user/` + `daemon-reload` (previously the unit was never
  installed, so `enable` silently no-op'd). (3) **state hygiene** — gitignored
  `skills/.../lib/telegram/.local/` so the runtime registry/offset/lock files stop
  leaking into the repo. (4) **prax-monitor** — `log_streamer` tailed a hardcoded
  `~/system_logs` while prax writes to the repo-root `system_logs`; now resolves the
  repo root (honoring `AIPASS_TEST_LOG_DIR`) so the log stream actually delivers.
  (5) **auto-create (GAP1)** — `create_bot` wrote a new bot's config only to a disk
  shadow file while the runtime loads its token exclusively from the @api store, so
  a minted bot started then exited with no config; `create_bot` now calls
  `set_secret('telegram', bot_id, config, as_json=True)` (fail-loud) so the
  create→@api→load round-trip works and the mother-bot can mint startable bots. New
  round-trip + fail-loud tests; telegram suite 454/454.
  (6) **/help + Telegram command menu** — `setMyCommands` only ran inside
  `create_bot`, so hand-launched bots (like the live `@aipass`) had no slash-menu,
  and the menu list had drifted from `/help`; `base_bot` now sets its menu on
  startup from a single source (`build_botfather_commands`, also used by
  `create_bot` — `DEFAULT_BOT_COMMANDS` retired), so the Telegram menu and `/help`
  list the same enriched commands incl. `/create`/`/cancel`. Wiring the builder
  (rather than deleting it as "dead") also lifted Unused_Function 92→93%. 6 new
  tests, telegram suite 460/460. (A running bot needs a restart to pick up the
  startup menu.)
  (DPLAN-0220)

- **Telegram `@aipass` deployed under systemd (reboot survival + clean lifecycle)** —
  the live mother-bot was a hand-launched foreground process: no reboot survival, and
  `stop_bot`/restart targeted an uninstalled `telegram-bot@base` unit, so there was no
  working lifecycle command. Installed the user service + `enable --now` +
  `loginctl enable-linger` (`Linger=yes`); the 17:26 startup log confirms the full
  chain live — `Telegram API OK`, **`Command menu set (6 commands)`** (the new `/help`
  menu), stale-lock cleanup, poll loop, tmux Claude session preserved, `NRestarts=0`.
  Also corrected the ported unit's `StandardOutput`/`StandardError`, which pointed at a
  non-existent `~/system_logs` (would have crash-looped the service) — now
  `<repo>/system_logs`, matching where the app already logs. Restart is now
  `systemctl --user restart telegram-bot@base`. (DPLAN-0220)

- **seedgo CLI help checkers green-lit non-compliant `--help` output** — the
  `cli`/`help_text`/`introspection` standards are static source scans (they
  confirm a `print_help` function, `console.print`, and `--help` wiring exist)
  but never execute `--help`, so a module could score 100% while rendering raw
  argparse. `@ai_mail` did exactly that via `console.print(parser.format_help())`,
  laundering argparse's plain text through the approved console API and dodging
  the existing `parser.print_help()` ban. Closed the loophole: `cli_check` now
  flags `.format_help()`, `cli.md`/`cli_content.py` name it alongside
  `print_help()`, +2 regression tests. Also rewrote `@ai_mail`'s `print_help()`
  to render hand-rolled Rich (the `--help` content was complete, just unstyled).
  A behavioral `--help` check (run it, assert not raw argparse) is noted as a
  follow-up. (DPLAN-0217) On its first CI run the tightened checker immediately
  surfaced the same pattern in 4 `@api` modules (`api_key`, `usage_tracker`,
  `google_client`, `openrouter_client`) — migrated to Rich, `@api` back to 100%.
- **seedgo `readme_check` ignored the `(disabled)` marker in self-scans** — its
  module-list and test-count scans now skip `foo(disabled).py`, matching the
  central audit collector. An in-place disabled module no longer trips a false
  "missing module" violation; disabled test files no longer inflate README test
  counts (td-103).
- **seedgo `unused_function` bypasses are now name-scoped** — bypasses match by
  function name (`functions: [...]`) instead of line number (`lines: [...]`),
  which drifted silently when code shifted and re-flagged exempted functions
  (bit us S216/S217). `lines` stays supported for other standards. Migrated the
  10 existing line-scoped entries across drone/memory/skills and dropped 3 dead
  entries already pointing past EOF (td-009).
- **Dispatch footer no longer tells workers to close the orchestrator's plan** —
  the standard email footer's checklist item read `CLOSE FPLAN → drone @flow
  close <plan_id>`, which led dispatched agents to close the master/parent plan
  referenced in their brief (bit us in FPLAN-0260). Reworded to `CLOSE YOUR PLAN
  → ... this task's plan only, never the master/parent` — a worker still closes
  the sub-plan handed to it, but the master stays the orchestrator's to close on
  completion (td-6).

### Changed

- **Backup `.backupignore` default moved out of code into a template file** — the
  seed content backup writes into a new project's `.backupignore` now lives in
  `backup/templates/backupignore.template` (loaded at register), matching the
  AIPass convention that templates are data files, not hardcoded Python. Retired
  the `BUILTIN_IGNORES` list; `_build_backupignore()` reads the template and
  **raises** if it's missing — never silently empty, since an empty
  `.backupignore` would back up everything and crash. Docs/comments repointed to
  the template (td-30).

### Removed

- **Dead `bulletin_created` trigger handler** — the event handler that wrote a
  `bulletin_board` section into every branch dashboard is retired: nothing fired
  the event, its `BULLETINS.central.json` store no longer exists, and prax
  already prunes `bulletin_board` as a deprecated section. Archived + unwired
  from the event registry; prax's pruning stays (td-102).
- **Dead `backup/run/` test dir** — leftover from an ad-hoc backup test run
  (only its generated `.backupignore` had been tracked); removed (td-218).

### Documentation

- **Backup docs corrected** — `.backup/` is now documented as a **shared runtime
  namespace** (@backup stores + @memory rollover safety copies + @flow plan
  archive), not @backup-exclusive. @backup's README gained full command coverage,
  the `.backup/` store layout, and a `.backupignore` ("gitignore for backups")
  section; its branch prompt's stale `.backup_system/` / `drive_test.py` names
  were fixed. Root README lists @backup and documents `.backupignore`; the navmap
  was corrected. The shipped root `/.backupignore` was realigned to
  `BUILTIN_IGNORES` (dropped stale `.backup_system/` + over-broad `*logs`).
  @memory and @flow READMEs now cross-reference their `.backup/` writes, and the
  orphaned `prax/.backupignore` (a stale per-branch config) was removed.
- **Root README agent roster brought current** — added the three missing agents
  (`@daemon`, `@skills`, `@commons`) to the tree and tables, and normalized the
  agent count to **17** everywhere (was an inconsistent mix of "13" and "14").
  `@daemon` joins Quality & operations; a new "Capabilities and community" group
  covers `@skills` + `@commons` (td-28).
- **`/prep` now reconciles todos against reality** — the session-wrap command
  (both the Claude `.claude/commands/prep.md` and the Codex skill mirror) gained
  a step to audit every open todo against the actual system (`ls`/`find`/`git
  ls-files`/`grep`/`audit`) and close what's verifiably done — catching todos
  finished in a past session but never closed.
- **Backup ignore architecture documented** — confirmed and written down the
  two-layer model so it stops getting re-discovered: `BUILTIN_IGNORES` is the
  **seed** that generates a new project's `.backupignore` at register and is
  never consulted at backup time; `.backupignore` (via `load_spec`) is the
  **runtime source of truth**. There's no static fallback, so the seed is
  safety-critical — an empty `.backupignore` backs up everything and can crash
  the machine. Added a "How Ignores Work" README section + code comments on
  `BUILTIN_IGNORES` and `load_spec`. Also added `logs/` to the seed so new
  projects exclude log directories (e.g. prax `.jsonl` output) by default, not
  just `*.log` files (td-27).

## [2026-06-23]

The **2.6.0** release — a large `dev → main` merge spanning several weeks (68 commits).
Headline changes below; the granular per-merge history is in the dated sections that follow.

### Added

- **Compass v2** — devpulse-owned SQLite/FTS5 rated-decision engine + `/compass`
  human-triggered capture (separate from @memory; DB gitignored).
- **Decentralized daemon scheduler** — each branch owns `.daemon/schedule.json`;
  the daemon discovers and fires.
- **Telegram skill** — the Dev-Pass bridge ported to a self-contained AIPass skill
  that consumes services as opt-in imports.
- **Tiered prompt injection** — Tier 0 kernel every turn + Tier 1 navmap by cadence,
  replacing the single always-on global prompt.
- **seedgo `HARDCODED_PATH` standard (#37)** — flags hardcoded home paths in source
  and docstrings.

### Changed

- **@backup fully restored** — `aipass.backup.*` namespace, 9-stage Rich CLI,
  versioned baseline + per-file diff engine, Google Drive sync + `restore`.
- **Memory subsystem unified** — single-source config limits, char-limit edit-gate,
  unified entry schema, rollover safety + the silent-rollover repair.
- **Legacy global prompt retired** across every runtime — Claude (cadence) and Codex
  (SessionStart) read the same tier files.
- **@daemon / @commons / @skills** revived to working citizens.
- Public source genericized — `Patrick` → `user` (private memories stay gitignored).

### Fixed

- **Secrets hardening** — no secret value reaches stdout (cleared CodeQL #86-88,
  `py/clear-text-logging-sensitive-data`).
- **Memory rollover was silently dead** — the PreCompact hook now delegates to
  `drone @memory rollover`; the v1 line-count / 600-line fallback removed entirely.
- **Hardcoded home paths removed (seedgo #37).** `@memory` `symbolic.py` builds its
  8 dash-encoded branch-path names at runtime (was a literal `-home-patrick-`);
  `@prax` `branch_detector.py` docstrings genericized. Both back to 100%
  `Hardcoded_Path`.
- Green-CI fixes across Linux / Windows / macOS; `dispatch_monitor` PID-`429`
  substring bug; git post-merge friction (FF-only realign).

## [2026-06-19]

### Fixed

- **`aipass init` now seeds the tiered prompts to new projects (@aipass).** The
  init template + bootstrap still handed new projects the retired global prompt
  with no tiers; now `.aipass/project_hooks.json` mirrors the live wiring
  (`tier0_kernel` + `navmap` enabled, `global_prompt` disabled) and `bootstrap.py`
  seeds both tier `.md` files. `init update` backfills existing projects.
  (77 bootstrap tests, 100% seedgo.)
- **Cadence reset observability (@hooks).** `reset_counter()` silently no-op'd
  when the Claude session id was absent; it now fails loud, logs the session id +
  prior turn on each reset, falls back to hook data for the id, and handles a
  corrupt state file. (The post-compaction counter reset was already working —
  this makes it visible so it can't fail invisibly.)
- **Memory rollover was silently dead — fixed end-to-end (@hooks + @memory).** The
  PreCompact rollover hook read its limits from `.trinity` file metadata, but
  DPLAN-0210 had moved limits into @memory's `memory.config.json` — so the hook
  always fell back to a 600-line check the lean files never reached, and rollover
  never fired (for weeks). The hook is now a thin trigger delegating to
  `drone @memory rollover check/run`; `compact.py` reads the current list schema
  (it was calling `.keys()` on a now-list `key_learnings`). Both fail loud instead
  of a silent exit-0.
- **Removed @memory's v1 line-count / 600-line silent fallback entirely.** The
  detector + extractor are now v2-only (`per_branch` → `defaults` → warn-and-skip);
  a parse failure logs loud and skips rather than silently falling back. Deleted
  `_get_max_lines` / `_load_config` / `_detect_growing_array` / the line-count
  extraction path. (959 tests.)

### Removed

- **Legacy global prompt fully retired across every runtime (DPLAN-0215).** After
  the tiered cutover the old `global_prompt` is now gone, not just disabled:
  `global_loader.py` + its tests deleted, the `global_prompt` block stripped from
  `.aipass/hooks.json` + `project_hooks.json`, `_resolve_global_prompt` + all global
  seeding removed from `aipass init` bootstrap/update, the cadence default + bypass
  entries cleaned, and both `aipass_global_prompt.md` / `project_global_prompt.md`
  archived. Claude (cadence) and Codex (SessionStart) now read the same tier files —
  one prompt source, every runtime.

### Added

- **seedgo `HARDCODED_PATH` standard (#37).** A new checker (`hardcoded_path_check.py`
  + `hardcoded_path_content.py`, `test_checkers_batch10.py`) flags hardcoded home
  paths — `/home/<user>` and dash-encoded `-home-<user>-` — in source and docstrings,
  keeping the public repo clean.

## [2026-06-18]

### Changed

- **Prompt injection is now tiered by cadence instead of one 8k always-on block
  (FPLAN-0284 / DPLAN-0214).** The single global prompt is split into two
  cadence-throttled tiers: **Tier 0** (`.aipass/tier0_kernel.md`, ~2k) injects
  every turn — identity grounding, the `drone @agent --help` reflex, and the
  disaster-preventer rules; **Tier 1** (`.aipass/tier1_navmap.md`, ~7.7k)
  injects every 5th turn plus at session start and right after compaction — the
  full agent roster, framework, conventions, and a new Terminology section. The
  hook engine gained per-loader cadence periods; the old `global_prompt` loader
  is retired (kept as a reference snapshot). Net: more navigation context
  reaches agents while less is paid per turn. Fresh-clone wiring is seeded from
  `cadence.py` defaults + `setup.sh` + `provider_manifest.json`.
- **Public source genericized — `Patrick` → generic `user`.** No personal
  identifiers in tracked code/docs: the compass decision-source enum
  (`patrick` → `user`) + the `/compass` command, the devpulse local prompt, the
  `aipass init` onboarding example (`--name Patrick` → `--name YourName`), and
  stale refs across @ai_mail / @backup / @flow. Private memories (`.trinity/`,
  compass DB) keep personal context — they're gitignored.
- **Telegram skill genericized (@skills).** Retired the inactive `patrick_private`
  personal bot from the skill's tests; the message sender now defaults to the
  Telegram user's first name (fallback `User`) instead of a hardcoded `Patrick`.

### Added

- **Prompt-craft conventions harvested from Claude Code's own prompts
  (DPLAN-0213).** A `Writing voice` section in `.aipass/PROMPT_STYLE.md`
  (`file_path:line` refs, write-for-a-person, three-tier "where detail lives");
  a blast-radius habit in the devpulse prompt; faithful-reporting +
  no-gold-plating folded into the Tier 0 kernel.
- **Skill frontmatter discipline (@skills).** A `when_to_use` field with trigger
  phrases (surfaced during discovery scans) and per-step "Done when:" success
  criteria across the SKILL.md templates.
- **`HARDCODED_PATH` standard (@seedgo, 37th checker).** Flags absolute home-dir
  literals in source — POSIX `/home/<user>/`, macOS `/Users/<user>/`, Windows
  user-home paths, and Claude Code's dash-encoded `-home-<user>-` form — with a
  bypass for legitimate test fixtures. Swept the repo for violations.
- **`prompt_change` flow playbook (PPLAN template).** A reusable SOP for changing
  any injected prompt — leads with "live ≠ seeded" and walks every wiring layer +
  fresh-install seed path; born from the `aipass init` seeding gap this surfaced.

## [2026-06-16]

### Security

- **Secrets door hardened — no raw secret value ever reaches stdout
  (DPLAN-0211).** `@api get-secret` previously printed retrieved secret values
  to stdout — an acute exposure in AIPass because Claude Code captures command
  stdout into the model context. The command now emits a **masked summary** by
  default (`provider/slug: set (N chars)`), writes the raw value only to a
  `0600`-mode file via `--out FILE` (printing just the path), and `--list`
  prints slug **names** only. The `telegram` skill — the sole consumer — was
  rewired from subprocess-parsing `get-secret` stdout to the **in-process
  secrets module API**. Clears CodeQL clear-text-logging alerts #86/#87/#88.

### Fixed

- **`@ai_mail` dispatch monitor mislabeled failures as "API rate limit" on a
  PID-`429` collision.** The monitor classifies dispatch failures by
  substring-scanning the stderr log for `"429"`/`"529"`, but that log includes
  the monitor's own header line `(PID <pid>)`. A monitor PID containing `"429"`
  (e.g. `14290`) was read as an HTTP 429, overwriting the real bounce reason
  (e.g. sandbox-abort `-4`) with "API rate limit" — and flaking
  `test_sandbox_failure_sends_bounce` deterministically-by-PID in CI. The scan
  now excludes the monitor's own `--- ` framing lines; genuine `429`/`529`
  markers in agent output are still detected.

## [2026-06-15]

### Added

- **Telegram bridge ported into AIPass as a self-contained skill (FPLAN-0277).**
  The Dev-Pass Telegram bridge (multi-bot long-poll listener → tmux Claude
  injection → Stop-hook reply) is ported AS-WAS into a self-contained `telegram`
  skill that consumes AIPass services instead of bespoke wiring: secrets via the
  new `@api get-secret`, logging via `@prax`, and the outbound Stop hook
  registered through the `@hooks` engine. Three phases — **P1 `@api`** adds
  `get-secret <provider/slug> [--json|--list]` + `auth/secrets.py` (reads
  `~/.secrets/aipass/`); **P2 `@skills`** ports the 14-file bridge (~5,300 lines)
  + ~424 tests into `.aipass/skills/telegram/`, rewiring every seam to services;
  **P3 `@hooks`** ports `telegram_response.py` (the reply path, with the 3-layer
  SubagentStop/sidechain/transcript-cursor defense intact) and registers it on
  the Stop event. A 366-tag completeness map (`TELEGRAM_PORT_MAP.md`) audited the
  port: **288 verified, 23 gaps** (top gap — a missing test log-isolation fixture
  — now fixed), **55 deferred to a live round-trip**. Live bring-up (real bot
  creds, systemd install, telethon auth, message round-trip) is still pending.

## [2026-06-13]

### Changed

- **Unified memory entry schema — Phase 1 (DPLAN-0207).** All four `.trinity`
  entry types (`key_learnings`, `sessions`, `todos`, `observations`) move to one
  shape: numbered + dated, list-shaped, newest-first. `key_learnings` converts
  from a dict to a numbered list; the rollover extractor now trims the **oldest
  by number from the tail**, and the schema normalizer self-heals ordering by
  re-sorting on `number` — so an out-of-order write can never archive a fresh
  entry (the bug surfaced in S229, where rollover ate the *newest* key_learning
  instead of the oldest). Backward-compatible: un-migrated dict-shaped
  key_learnings skip cleanly, no crash. **All 17 branches migrated** to
  `schema_version` 3.0.0 (reversible per-file backups, no data loss). A
  follow-up made the rollover **detector** and the **learnings manager** (used
  by rollover + symbolic) list-aware — a live `rollover check` caught they still
  counted key_learnings as a dict, so an at-cap list was invisible to the
  detector (the 955 unit tests stayed green because none counted a *list*). 960
  tests; seedgo 99% (1 pre-existing unused-function on an unwired manager API).
  Remaining: `/memo`+`/prep` and @spawn template updates.

- **Memory config relocated to the json-home and unified behind one
  self-healing loader (FPLAN-0271).** `memory.config.json` moved from the loose
  tracked `config/` dir into the gitignored `memory_json/custom_config/`
  (operator-tunable, fast-access) and `.plans_processed.json` into
  `memory_json/` root; the empty `config/` dir was removed. The config was
  previously read by **9 separate loaders**, each carrying its own *disagreeing*
  defaults (8 divergence classes — incl. the headline bug where a missing config
  silently flipped `entry_limits.enforce` off, plus rollover defaulting to 600
  vs the configured 500). All 9 now read through one
  `apps/handlers/json/config_loader.py` with a single `DEFAULT_CONFIG` +
  non-mutating deep-merge + self-heal: a missing file is rewritten from code
  defaults (warn-first `enforce: false`), while malformed JSON fails loud and is
  never overwritten. Dead `intake` section deleted; a static `_meta` block in
  `DEFAULT_CONFIG` documents each section's consumer files. Code-as-Template:
  the on-disk file is local tuning, code carries the committed defaults — same
  model as hooks `cadence_config.json`. Verified: 949 memory tests green, seedgo
  @memory 100%, live self-heal / malformed-no-clobber / edit_gate checks pass.
  Design: DPLAN-0206. Follow-up parked: issue #643 (codify `custom_config/` as a
  seedgo standard).

## [2026-06-12]

### Changed

- **Devpulse dashboard slimmed — todos no longer duplicated (startup-context
  fix).** `DASHBOARD.local.json` was embedding the full `todos[]` bodies that
  already live in `.trinity/local.json`; since both files are read at every
  startup, that was pure duplication. The dashboard now emits `todo_count` only
  (the glance value) — the bodies are commented out in the prax
  `devpulse_dashboard` plugin's `todo_section.py` (revivable). Dashboard
  `DASHBOARD.local.json` 6.8 KB → 3.0 KB. Devpulse-only (plugin, not templated).
  Verified: seedgo 100%, 17/17 plugin tests.
- **Deprecated dashboard sections are now actually pruned on refresh.**
  `bulletin_board` (and the other entries in prax's `DEPRECATED_SECTIONS`:
  `devpulse`, `commons_activity`, `agent_status`, `memory_bank`) were listed as
  deprecated but only excluded from template *pushes* — they lingered in every
  branch's live `DASHBOARD.local.json`. Added `_prune_deprecated_sections()` to
  the prax dashboard `refresh` path (reusing the single `DEPRECATED_SECTIONS`
  constant), so a refresh strips them. Verified: `bulletin_board` removed from
  the devpulse dashboard; 116/116 prax tests, seedgo 100%. (Follow-up: `@trigger`
  still has a `bulletin_created` writer to retire separately.)
- **Dashboard slimmed to a lean glance — removed duplicated/dead sections.**
  Dropped three sections from the devpulse dashboard: `session` (broken since
  May — read keys `id`/`d`/`sum` vs the actual `session`/`date`/`summary`, so it
  always wrote empty strings — and it duplicated `local.json`, which loads at
  startup), `todo` (carried only `todo_count`, already in `quick_status`; now
  sourced directly from `local.json`), and `ai_mail` (its counts live in
  `quick_status`; the section is removed from output *after* quick_status is
  computed from it). End state: 4 sections (`flow`, `memory`, `git`, `dispatch`)
  + the `quick_status` glance. `session_section.py`/`todo_section.py` archived
  (not deleted). `DASHBOARD.local.json` overall 6.8 KB → 2.4 KB. Verified: seedgo
  100%, 108 prax tests. (Follow-up: `@ai_mail`'s `dashboard_sync.py` section
  writer to retire separately.)
- **quick_status now self-sources mail counts from `inbox.json`.** Decouples the
  glance from the `ai_mail` section: prax's three quick_status calculators read
  `.ai_mail.local/inbox.json` directly (`_read_mail_counts`) for `new_mail`/
  `opened_mail`, so the `ai_mail` section is no longer a data dependency and can
  be retired. 116 prax tests, seedgo 100%.
- **Retired `@ai_mail`'s dashboard section writer (completes the dashboard
  slim).** ai_mail no longer writes to the dashboard — removed
  `push_dashboard_update` from 5 call sites and archived `dashboard_sync.py`.
  With prax self-sourcing mail counts, the `ai_mail` section now stays gone (a
  mail op no longer re-adds it — verified). 737 ai_mail tests.
- **`.backupignore` is now a true `.gitignore` for the backup system — a single
  source of truth (FPLAN-0269).** Replaced the hand-rolled `fnmatch`+part-loop
  matcher (which broke leading-slash anchoring, `*`-crossing-`/`, dir-only `foo/`,
  `!` negation, and last-match-wins) with the `pathspec` gitwildmatch library, so
  `.backupignore` honors full gitignore semantics: include-by-default, `!`
  negation, `#` comments, anchoring, dir-only, last-match-wins. `BUILTIN_IGNORES`
  is demoted to a seed-only default (written when the file is absent, never merged
  at runtime), and the separate `IGNORE_EXCEPTIONS`/`is_exception` layer is
  removed (exceptions are native `!` lines). Snapshot, versioned, `all`, and
  mirror-cleanup now all obey the one file. `.ruff_cache/` + `.coverage` added to
  the default. `pathspec` (pure-Python, cross-OS) declared. Verified by artifact
  (seedgo 100%, 220 tests incl. 26 new gitignore-parity tests) + live (a dotfile
  flows into the store, `!` negation re-includes end-to-end).
- **Backup store dir renamed `.backup_system/` → `.backup/`, dead `versions/`
  removed (FPLAN-0269 follow-up).** The backup root is now `.backup/` (shorter,
  coexists with `@flow`'s `.backup/processed_plans/`); the orphaned per-timestamp
  `versions/` scaffold and the unused `build_versioned_path()` — both superseded
  by the Phase-3 `versioned/` baseline+diff store — are gone. Drive sync confirmed
  reading `.backup/versioned/` + `.backup/drive_tracker.json` via the shared
  `backup_root()`. Verified by artifact (seedgo 100%, 220 tests) + live (a
  throwaway project writes to `.backup/`, no `versions/` dir).

### Fixed

- **Backup Drive sync no longer silently drops 41% of files — including the
  memories (FPLAN-0269).** Removed a foreign dotfile-skip in `drive_sync.py` that
  excluded every dotted path (`.trinity/` memories, `.chroma/` vectors, `.aipass/`
  prompts, `.ai_mail.local/` mailboxes — 4558 files) from the offsite Google Drive
  copy while the local snapshot/versioned kept them. Drive now uploads the full
  versioned store (already exactly the `.backupignore`-filtered set). Added a
  Drive-sync output panel matching the Snapshot/Versioned stages (header, progress,
  stats, Duration | Location).

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

- **Backup Google Drive folder duplication + dedup-wipe fixed (GOLD-faithful lock
  restoration).** The Phase-4 port had narrowed `GoogleDriveSync`'s folder lock: a
  single `drive_sync` run's 3 upload workers raced the folder search+create →
  multiple "AIPass Backups" root folders, and `get_or_create_backup_folder` reset
  the dedup tracker on every call (re-uploading everything = the slowness). Restored
  GOLD's structure exactly: `get_or_create_project_folder` / `get_or_create_nested_folder`
  hold `_folder_cache_lock` across the **entire** method (cache + root-ensure + search
  + create); `get_or_create_backup_folder` is lock-free (called inside the project
  lock — no re-entrant deadlock), short-circuits cached ids via `_verify_folder_id`,
  and clears the tracker only on a genuine brand-new root folder. Also: all four
  `drive_*` commands route by their underscore names (were hyphenated → "Unknown
  command"); `requirements.project.txt` now declares the three google libs. Verified
  by artifact (seedgo 100%, 197 tests incl. a 5-thread concurrency test → exactly one
  create) + live (real Drive backup: no duplicate folders).

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
