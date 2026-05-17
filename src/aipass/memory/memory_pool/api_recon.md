# API Module Recon
**Date:** 2026-03-06

## Summary
LLM access and Telegram multi-bot system. **Heaviest path debt** (31 Path.home()). 46 Python files.

## Structure
```
api/
├── apps/
│   ├── api.py                # Entry point (auto-discovers modules)
│   ├── modules/
│   │   ├── api_key.py        # Key retrieval, validation
│   │   ├── openrouter_client.py  # LLM API calls, model listing
│   │   ├── telegram_bot.py   # Multi-bot management (PUBLIC)
│   │   ├── telegram_service.py   # Systemd service control
│   │   └── usage_tracker.py  # Cost tracking
│   ├── handlers/
│   │   ├── auth/             # Key management, .env fallback
│   │   ├── config/           # Configuration
│   │   ├── openrouter/       # OpenRouter client + retry
│   │   ├── telegram/         # 12 files (BaseBot, factory, registry, plugins)
│   │   ├── telegram_service/ # Service control
│   │   ├── usage/            # Usage tracking
│   │   └── json/             # JSON tracking
│   └── json_templates/
└── tests/                    # Empty
```

## Commands
```
drone @api get-key|validate|test|models
drone @api track|stats
drone @api telegram start|stop|status|logs
drone @api telegram_bot list|create|delete|status|start|stop
```

## Path.home() Debt: 31 instances (CRITICAL)
**Telegram handlers (23/31):**
- base_bot.py — 7 hits
- bot_factory.py — 5 hits
- config.py — 2 hits
- branch_plugin.py, response_router.py, notifier.py, tmux_manager.py, botfather_client.py

**Other:**
- json_handler.py:29 — `API_ROOT = Path.home() / "aipass_core" / "api"` (import-time) [stale: aipass_core]
- log_streamer.py:54 — `SYSTEM_LOGS_DIR = Path("/home/aipass/system_logs")` (CRITICAL, import-time)
- auth/env.py:54, telegram_service/service.py:26

## Key Insight
23 of 31 Path.home() issues are in **Telegram handlers** — this is legacy AIPass infrastructure. DPLAN-047 recommends stripping it for v1.0 (Option B).

## Disabled Legacy Files
- `spawner.py(disabled)` — old Claude session spawner
- `output_parser.py(disabled)` — old JSON stream parser

## Notes
- Entry point is `api.py` not `branch.py` (naming deviation)
- No .trinity files, no tests
- OpenRouter integration is stdlib-only BaseBot (no python-telegram-bot dep)
