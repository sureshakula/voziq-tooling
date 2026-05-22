# .claude/hooks/ -- Legacy Hook Scripts (Post-Migration)

> **Migration complete (DPLAN-0184).** All 18 hook scripts in this directory have been
> disabled (renamed with `(disabled)` suffix). Hook logic now lives in native Python
> handlers at `src/aipass/hooks/apps/handlers/`. Provider settings route through the
> bridge at `src/aipass/hooks/apps/handlers/bridges/claude.py`.

## What Remains Active

Three testing/tooling files are still active in this directory:

| File | Purpose |
|------|---------|
| `hook_log.py` | Shared JSONL logger -- hooks call `run_and_log()` to record execution |
| `hook_report.py` | Report tool -- reads `/tmp/aipass_hook_log.jsonl`, shows table |
| `hook_test.py` | Test harness -- direct + integration tests for hook behavior |

### hook_report.py usage

```bash
python3 .claude/hooks/hook_report.py              # Last 5 minutes
python3 .claude/hooks/hook_report.py --all         # All entries
python3 .claude/hooks/hook_report.py --cwd /tmp    # Filter by CWD
python3 .claude/hooks/hook_report.py --json        # Machine-readable
python3 .claude/hooks/hook_report.py --clear       # Wipe log
```

### hook_test.py usage

```bash
python3 .claude/hooks/hook_test.py                 # All tests
python3 .claude/hooks/hook_test.py --direct        # Direct tests only (fast, ~3s)
python3 .claude/hooks/hook_test.py --integration   # Integration tests only (~2min)
python3 .claude/hooks/hook_test.py --verbose        # Show detail per test
python3 .claude/hooks/hook_test.py --list          # List available tests
python3 .claude/hooks/hook_test.py --test <name>   # Run one test
```

## Disabled Scripts (18 files)

These are the original standalone hook scripts. They were disabled as part of DPLAN-0184
Phase 2 when their logic was migrated to native handlers. The files are kept for reference
but are not executed.

| Disabled script | Migrated to |
|-----------------|-------------|
| `global_prompt_loader.py(disabled)` | `handlers/prompt/global_loader.py` |
| `branch_prompt_loader.py(disabled)` | `handlers/prompt/branch_loader.py` |
| `identity_injector.py(disabled)` | `handlers/prompt/identity.py` |
| `email_notification.py(disabled)` | `handlers/notification/email.py` |
| `tool_use_sound.py(disabled)` | `handlers/notification/tool_sound.py` |
| `git_gate.py(disabled)` | `handlers/security/git_gate.py` |
| `pre_edit_gate.py(disabled)` | `handlers/security/edit_gate.py` |
| `auto_fix_diagnostics.py(disabled)` | `handlers/lifecycle/auto_fix.py` |
| `auto_watchdog.py(disabled)` | `handlers/lifecycle/auto_watchdog.py` |
| `subagent_stop_gate.py(disabled)` | `handlers/security/subagent_gate.py` |
| `pre_compact.py(disabled)` | `handlers/lifecycle/compact.py` |
| `pre_compact_rollover.py(disabled)` | `handlers/lifecycle/rollover.py` |
| `stop_sound.py(disabled)` | `handlers/notification/stop_sound.py` |
| `notification_sound.py(disabled)` | `handlers/notification/announce.py` |
| `prompt_inject.sh(disabled)` | (combined inject -- never used in production) |
| `engine.py(disabled)` | `hooks/apps/modules/engine.py` |
| `engine_test_hook.py(disabled)` | (test fixture, no longer needed) |
| `engine_test_sound.py(disabled)` | (test fixture, disabled in hooks.json) |

All handler paths above are relative to `src/aipass/hooks/apps/`.

## Probes (Opt-In Diagnostics)

The `probes/` subdirectory contains passive observer scripts for individual hook events.
These are opt-in, not auto-wired. See `probes/README.md` for usage.

## New Architecture

```
~/.claude/settings.json
        |
        v
claude.py (bridge)       -- thin entry point, normalizes stdin
        |
        v
engine.py (dispatcher)   -- reads .aipass/hooks.json, imports handlers
        |
        v
handlers/                -- native Python, organized by domain
```

For full architecture documentation, see the parent `../.claude/README.md`.

## Related Plans

- **DPLAN-0184** -- Hook migration (standalone scripts to native handlers)
- **DPLAN-0167** -- Hook testing framework
- **DPLAN-0166** -- Hook audit + CI health
- **DPLAN-0139** -- Hook overhaul + single-path enforcement
- **DPLAN-0053** -- Original hook architecture research
