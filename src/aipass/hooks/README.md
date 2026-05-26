[← Back to AIPass](../../../README.md)

# Hooks

> Hook infrastructure for AIPass. Single engine dispatches all hooks across platforms (Claude, Codex) with per-project config, full logging, and testability. The 13th citizen.

Every hook event flows through one engine. Platform bridges normalize the event format, the engine reads per-project config (.aipass/hooks.json), dispatches matching handlers, and logs everything to prax + JSONL.

## Start here

| You want to | Read |
|---|---|
| What's happening right now | [STATUS.local.md](STATUS.local.md) |
| Identity, memory, session history | [`.trinity/`](.trinity/) |
| Hook engine design | `DPLAN-0184` |
| Per-project config | `.aipass/hooks.json` |

## Commands

| Command | What it does |
|---|---|
| `drone @hooks status` | Show hook config for current project |
| `drone @hooks log` | Tail recent hook activity (last 20 JSONL entries) |
| `drone @hooks hooksound` | Show current sound mute status |
| `drone @hooks hooksound off` | Mute all hook sounds |
| `drone @hooks hooksound on` | Unmute all hook sounds |
| `drone @hooks --help` | Full help reference |
| `drone @hooks --version` | Version info |

## Architecture

```
src/aipass/hooks/
├── .trinity/                    # Identity & memory
├── apps/
│   ├── hooks.py                 # Entry point (drone @hooks)
│   ├── sound.py                 # Shared sound utilities (speak, play, mute)
│   ├── modules/
│   │   ├── engine.py            # Core dispatch — routes events to handlers
│   │   └── hooksound.py         # Sound control (drone @hooks hooksound on/off)
│   ├── handlers/
│   │   ├── bridges/             # One per provider (thin normalization)
│   │   │   └── claude.py        # Claude Code bridge
│   │   ├── prompt/              # Prompt injection hooks
│   │   ├── security/            # Enforcement hooks (edit gate, git gate)
│   │   ├── lifecycle/           # Session hooks (compact, stop, subagent)
│   │   └── notification/        # Sound/alert hooks
│   └── config/                  # hooks.json validation
├── logs/
│   └── engine.jsonl             # JSONL diagnostics (every hook execution)
├── tests/                       # 236 tests
└── STATUS.local.md
```

## How It Works

1. Provider settings have ONE bridge entry per event type (e.g., `claude.py UserPromptSubmit`)
2. Bridge calls `engine.dispatch(event_type, stdin_data, config)`
3. Engine reads `.aipass/hooks.json` (walks up from CWD)
4. Engine runs matching hooks sequentially, logs each one
5. First hook returning `{"decision": "block"}` with exit code 2 = bail (block the action)
6. Exit code 2 without JSON = crash (log error, continue to next hook)
7. All hook stdout concatenated and returned to platform

## Integration Points

### Depends On

| Branch | What for |
|---|---|
| prax | Logging (system_logger for prax monitor visibility) |

### Provides To

All branches via hook dispatch. Every Claude Code session routes through the engine.

*Last Updated: 2026-05-22*

---

[← Back to AIPass](../../../README.md)
