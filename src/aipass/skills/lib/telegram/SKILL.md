---
name: telegram
description: Multi-bot Telegram bridge — routes messages between Telegram and Claude tmux sessions
version: 1.0.0
tags: [communication, bridge, telegram, bot]
requires:
  pip: [telethon]
  bins: [tmux, claude]
  config: []
  aipass: [api, prax, hooks, cli]
has_handler: true
---

# Telegram Bridge

Multi-bot personal-assistant bridge: long-polling listener routes user Telegram messages into Claude tmux sessions; Claude's Stop hook writes a pending file and the bot sends the response back to Telegram.

## Architecture

- **BaseBot** — polling loop, tmux injection, heartbeat, lock management
- **BranchPlugin** — per-branch overrides (message prefix, response prefix, session startup)
- **ResponseRouter** — CWD-safe pending-file routing for multi-bot
- **TelegramStandards** — shared /start, /help, /new, /status command handlers
- **BotFactory** — bot create/delete lifecycle (8-step)
- **BotRegistry** — fcntl-locked JSON registry CRUD
- **BotOperations** — start/stop/status ops
- **BotFatherClient** — optional Telethon BotFather automation
- **Config** — bot configuration via @api secrets store
- **FileHandler** — download, classify, and prompt file uploads
- **LogStreamer** — daemon thread tailing logs to Telegram
- **Notifier** — standalone push notification sender
- **TmuxManager** — tmux session helpers

## Usage

```bash
drone @skills run telegram start <bot_id>
drone @skills run telegram stop <bot_id>
drone @skills run telegram status [bot_id]
drone @skills run telegram create <bot_id> --token <token>
drone @skills run telegram delete <bot_id>
drone @skills run telegram notify "message"
```

## Secrets

Bot tokens and config accessed via the in-process `aipass.api.apps.modules.secrets.get_secret` API.
State files (offset, lock, registry) stay with the skill in `.local/`.

## Ported-but-unwired (DPLAN-0220)

This bridge is a partial port of the ~9k-line "Dev-Pass" telegram system. Several
functions are **ported but not yet wired** — they have no caller today and will be
connected as DPLAN-0220 completes. They are *not* dead code (do not delete them; see
S249), so seedgo's `unused_function` check is bypassed for them in
`.seedgo/bypass.json`. As each one is wired up, remove its bypass entry.

| File | Function(s) | Awaiting |
|---|---|---|
| `base_bot.py` | `chunk_text`, `on_response` | long-message split + response hook (on_response = Wave-2 design call) |
| `branch_plugin.py` | `on_response` | per-branch response hook (Wave-2 design call) |
| `response_router.py` | `find_pending_bot`, `clean_expired_pending` | response_router import-vs-delete decision |
| `bot_registry.py` | `get_bot_by_work_dir` | CWD→bot match for the response router |
| `bot_operations.py` | `get_all_bots` | multi-bot listing |
| `config.py` | `get_allowed_user_ids`, `validate_config` | config accessor/validator wiring |
| `file_handler.py` | `download_telegram_file`, `cleanup_file` | file up/download feature |
| `tmux_manager.py` | `_send_rename`, `has_tmux`, `kill_session`, `list_sessions`, `get_session_pane` | interactive tmux session management |
