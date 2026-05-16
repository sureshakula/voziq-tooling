# Path.home() / /home/aipass Full Audit
**Date:** 2026-03-06 | Cross-referenced with DPLAN-047

## Executive Summary
- **4 CRITICAL** module-level hardcoded `/home/aipass` (import-time crash)
- **11 HIGH** module-level `Path.home()` bindings (import-time)
- **14+ MEDIUM** runtime function-level `Path.home()` usage
- **203 LOW** shebang references (cosmetic)
- **28+ LOW** docstring/comment references

## CRITICAL — Import-Time Crashes (4 files)

| File | Line | Binding |
|------|------|---------|
| ai_mail/apps/handlers/registry/read.py | 41 | `BRANCH_REGISTRY_PATH = Path("/home/aipass/BRANCH_REGISTRY.json")` [stale: now AIPASS_REGISTRY.json] |
| flow/apps/modules/registry_monitor.py | 83 | `ECOSYSTEM_ROOT = Path("/home/aipass")` |
| trigger/apps/handlers/events/plan_file.py | 42 | `ECOSYSTEM_ROOT = Path("/home/aipass")` |
| api/apps/handlers/telegram/log_streamer.py | 54 | `SYSTEM_LOGS_DIR = Path("/home/aipass/system_logs")` |

## HIGH — Module-Level Path.home() (11 files)

| File | Line | Binding |
|------|------|---------|
| trigger/apps/handlers/watchers/log_watcher.py | 44 | `AIPASS_HOME = Path.home()` |
| trigger/apps/handlers/log_watcher.py | 54 | `AIPASS_HOME = Path.home()` |
| trigger/apps/handlers/events/error_detected.py | 61 | `AIPASS_HOME = Path.home()` |
| trigger/apps/handlers/events/error_logged.py | 53 | `AIPASS_HOME = Path.home()` |
| trigger/apps/handlers/events/startup.py | 41 | `AIPASS_HOME = Path.home()` |
| trigger/apps/handlers/events/bulletin_created.py | 40 | `AIPASS_HOME = Path.home()` |
| trigger/apps/handlers/events/memory_template_updated.py | 37 | `AIPASS_HOME = Path.home()` |
| trigger/apps/handlers/events/memory_threshold_exceeded.py | 42 | `AIPASS_HOME = Path.home()` |
| prax/apps/handlers/monitoring/telegram_command_bot.py | 68 | `AIPASS_HOME = Path.home()` |
| ai_mail/apps/handlers/dispatch/wake.py | 46 | `AIPASS_HOME = Path.home()` |
| ai_mail/apps/handlers/dispatch/daemon.py | 54 | `AIPASS_HOME = Path.home()` |

## MEDIUM — Runtime Function-Level (14+ files)

Key offenders:
- flow/apps/handlers/summary/write_plan_outputs.py — 4 usages
- flow/apps/modules/restore_plan.py — 4 usages
- prax/apps/handlers/config/load.py:51 — SYSTEM_LOGS_DIR + mkdir at import
- prax/apps/handlers/monitoring/branch_detector.py:191
- prax/apps/modules/monitor_module.py:597
- api/apps/handlers/telegram/bot_factory.py:369
- api/apps/handlers/telegram/response_router.py:228
- ai_mail/apps/handlers/central_writer.py:54-57 — 4 instances
- ai_mail/apps/handlers/email/delivery.py:71 — hardcoded Path("/home/aipass/...")

## Module Severity Summary

| Module | CRITICAL | HIGH | MEDIUM | Shebangs | DPLAN-047 Match |
|--------|----------|------|--------|----------|-----------------|
| api | 1 | 0 | 2 | ~20 | Yes (inflated by docs) |
| ai_mail | 1 | 2 | 6 | ~20 | Yes |
| trigger | 1 | 7 | 0 | ~15 | Yes |
| prax | 0 | 1 | 3 | ~55 | Yes |
| flow | 1 | 0 | 8 | ~7 | Yes |
| seedgo | 0 | 0 | 0 | 1 | DONE |
| drone | 0 | 0 | 0 | 2 | LOW |
| cli | 0 | 0 | 1 | 8 | LOW |
| spawn | 0 | 0 | 0 | 2 | LOW |
| devpulse | 0 | 0 | 0 | 0 | DONE |

## Safe to Import in Container
- drone, seedgo, cli, devpulse, spawn — no critical violations
- prax (top-level `from aipass.prax import logger`) — works due to lazy init
