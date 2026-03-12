# dev.local.md - DAEMON
```
Branch: /home/patrick/Projects/AIPass/src/aipass/daemon
Created: 2026-03-07
```

## Issues

- Memory health monitoring expects `DAEMON.local.json` (uppercase prefix) but actual files are `.trinity/local.json` — file naming mismatch in monitoring handlers
- `branch-health` requires uppercase branch name from registry — `daemon` fails, needs `DAEMON`
- Extensions dir is empty — no extensions implemented yet
- Type errors in scheduler_cron.py (15) from optional imports with None fallback — pyright can't see runtime guards
- Plugins vs actions registry redundancy — process_plugins() still exists alongside process_actions()

## Resolved

- ~~`activity_report` module routing mismatch~~ — FIXED: added `activity_report` as alias + help now shows actual commands
- ~~`send_email_direct` phantom import~~ — FIXED: replaced with `_send_email_via_drone` subprocess wrapper
- ~~AIPASS_REGISTRY.json path~~ — FIXED: activity_collector now checks repo root + ~/.aipass/
- ~~Telegram code everywhere~~ — STRIPPED: 8 files cleaned, stubs remain for import compat

---

## Todos

- Populate passport `what_i_do` / `what_i_dont_do` fields
- Consolidate telegram notifier stubs into single file (or remove entirely once no callers remain)
- Remove legacy process_plugins() once all plugins fully migrated to action registry
- Fix memory_health to look for `.trinity/local.json` pattern instead of `{BRANCH}.local.json`
- Secrets at `~/.secrets/aipass/` — note for Telegram bot token location (now stripped)
