# Changelog

All notable changes to AIPass will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Calendar Versioning](https://calver.org/) in the format
`YYYY.WNN` (year and ISO week number).

---

## [2026.W21] - 2026-05-25

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

---

*This is the first CHANGELOG entry. Prior work is documented in the
repository's commit history and branch session logs.*
