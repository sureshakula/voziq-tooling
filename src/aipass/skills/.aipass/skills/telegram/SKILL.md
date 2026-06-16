---
name: telegram
description: Multi-bot Telegram bridge — routes messages between Telegram and Claude tmux sessions
version: 1.0.0
tags: [communication, bridge, telegram, bot]
requires:
  pip: []
  bins: [tmux, claude]
  config: []
  aipass: [api, prax, hooks, cli]
has_handler: true
---

# Telegram Bridge

Multi-bot personal-assistant bridge: long-polling listener routes Patrick's Telegram messages into Claude tmux sessions; Claude's Stop hook writes a pending file and the bot sends the response back to Telegram.

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
