[← Back to AIPass](../../../README.md)

# Hooks

> Hook infrastructure for AIPass. Single engine dispatches all hooks across platforms (Claude, Codex) with per-project config, full logging, and crash isolation. The 13th citizen.

Every hook event flows through one engine. Platform bridges normalize the event format, the engine reads per-project config (`.aipass/hooks.json`), dispatches matching handlers, and logs everything to prax + JSONL.

## Start here

| You want to | Read |
|---|---|
| Identity, memory, session history | [`.trinity/`](.trinity/) |
| Hook engine design | `DPLAN-0184` |
| Per-project config | `.aipass/hooks.json` |

## Commands

| Command | What it does |
|---|---|
| `drone @hooks` | Show branch structure (auto-discovered modules) |
| `drone @hooks status` | Show hook config for current project |
| `drone @hooks engine` | Show connected handlers |
| `drone @hooks log` | Tail recent hook activity (last 20 JSONL entries) |
| `drone @hooks hooksound` | Show current sound mute status |
| `drone @hooks hooksound off` | Mute all hook sounds |
| `drone @hooks hooksound on` | Unmute all hook sounds |
| `drone @hooks cadence` | Show prompt injection cadence config and state |
| `drone @hooks verify` | Cross-check provider settings vs project hook config |
| `drone @hooks --help` | Full help reference |
| `drone @hooks --version` | Version info |

## Two-Tier Hook Model

Hooks operate on two tiers:

**Tier 1 — Provider Settings (wiring).** Claude Code's `~/.claude/settings.json` (or project `.claude/settings.json`) defines hook entries that point to the bridge (`claude.py`). These are installed by `setup.sh` / `doctor` — they're pure wiring. Each event type has one bridge entry that fans out to all handlers for that event. Provider settings cannot be changed by branches — only setup tooling manages them.

**Tier 2 — Project Config (control).** Each project's `.aipass/hooks.json` controls which hooks fire for that project. Created by `aipass init`. Edit `enabled` flags to turn hooks on/off per project. Use `drone @hooks status` to view current config.

**Why provider-only wiring?** Claude Code does not fire `PreToolUse`/`PostToolUse` hooks from project-level settings — only from user-level settings (DPLAN-0160 platform limitation). So all hook entries live in provider settings, and per-project control happens through `.aipass/hooks.json`.

## Architecture

```
src/aipass/hooks/
├── .trinity/                    # Identity & memory
├── apps/
│   ├── hooks.py                 # Entry point (drone @hooks)
│   ├── sound.py                 # Shared sound utilities (speak, play, mute)
│   ├── modules/
│   │   ├── cadence.py           # Prompt injection cadence (every-Nth-turn gating)
│   │   ├── cc_sessions.py       # CC-native session file reader (~/.claude/sessions/<pid>.json)
│   │   ├── engine.py            # Core dispatch — routes events to handlers
│   │   ├── hooksound.py         # Sound control (drone @hooks hooksound on/off)
│   │   ├── hookstatus.py        # Config viewer (drone @hooks status)
│   │   ├── presence.py          # Branch presence — claim/release/refresh for .ai_central/PRESENCE.central.json
│   │   ├── sandbox.py           # Kernel sandbox — srt/bwrap wrapper + per-role policy generator
│   │   └── wire_verify.py       # Wire verification — provider ↔ project hook wiring checker
│   ├── handlers/
│   │   ├── bridges/             # One per provider (thin normalization)
│   │   │   └── claude.py        # Claude Code bridge
│   │   ├── prompt/              # Prompt injection hooks
│   │   │   ├── branch_loader.py #   Injects aipass_local_prompt.md
│   │   │   ├── tier0_kernel.py  #   Injects tier0 kernel prompt (every turn)
│   │   │   ├── navmap.py        #   Injects tier1 navmap prompt (periodic)
│   │   │   └── identity.py      #   Injects passport identity block
│   │   ├── security/            # Enforcement hooks
│   │   │   ├── edit_gate.py     #   Blocks unsafe edits (cross-branch, inbox, diagnostics)
│   │   │   ├── git_gate.py      #   Enforces git access tiers
│   │   │   ├── presence_gate.py  #   Single-session gate — blocks duplicate runtimes per branch
│   │   │   ├── registry_gate.py  #   Seals *_REGISTRY.json — blocks raw writes/edits/deletes, redirects to drone @spawn
│   │   │   ├── rm_gate.py       #   Guardrail — catches accidental rm -rf, teaches drone rm
│   │   │   └── subagent_gate.py #   Blocks sub-agent stop until clean
│   │   ├── lifecycle/           # Session management hooks
│   │   │   ├── auto_fix.py      #   Post-edit diagnostics (ruff, pyright, py_compile)
│   │   │   ├── auto_watchdog.py #   Watchdog arming after dispatch
│   │   │   ├── compact.py       #   Pre-compact memory archival
│   │   │   ├── rollover.py      #   Pre-compact memory rollover
│   │   │   └── session_start.py #   Cadence reset on new chat / clear (SessionStart)
│   │   └── notification/        # Sound/alert hooks
│   │       ├── announce.py      #   Announcement tone on notification
│   │       ├── email.py         #   Inbox check on prompt
│   │       ├── stop_sound.py    #   Bell on session stop
│   │       ├── telegram_response.py # Telegram reply delivery on Stop
│   │       └── tool_sound.py    #   Announces tool name via TTS
│   └── handlers/config/         # Config utilities
│       ├── loader.py            # hooks.json discovery + validation
│       └── diagnostics.py       # JSONL logging for hook execution
├── logs/
│   └── engine.jsonl             # JSONL diagnostics (every hook execution)
└── tests/                       # 913 tests across 28 test files
```

## How It Works

1. Provider settings have one bridge entry per event type (e.g., `claude.py UserPromptSubmit`)
2. Bridge normalizes stdin, loads project config via `loader.find_project_config()`
3. Bridge calls `engine.dispatch(event_type, stdin_data, config)`
4. Engine runs matching hooks sequentially, logs each to JSONL
5. First hook returning `{"decision": "block"}` with exit code 2 = bail (block the action)
6. Exit code 2 without JSON = crash (log error, continue to next hook)
7. All hook stdout concatenated and returned to platform

## Dynamic Dispatch

Handlers are called **dynamically at runtime** — the engine uses `importlib.import_module()` + `getattr()` on the dotted handler path from `hooks.json` (e.g., `aipass.hooks.apps.handlers.prompt.identity.handle`). Handlers are never statically imported. This means static analysis tools (including seedgo's dead_code checker) cannot see that they are used. Each handler has been verified wired in `hooks.json` and confirmed firing in `engine.jsonl`.

## Event Types

| Event | Hooks | Description |
|---|---|---|
| UserPromptSubmit | presence_gate, identity, email, branch_loader, tier0_kernel, navmap | Presence gate + prompt injection + inbox check |
| PreToolUse | tool_sound, edit_gate, git_gate, rm_gate, registry_gate | Security gates + guardrails + sound |
| PostToolUse | auto_fix, auto_watchdog | Diagnostics + watchdog |
| SubagentStop | subagent_gate | Seedgo validation |
| Stop | stop_sound, telegram_response, presence_release | Bell + Telegram delivery + presence release |
| Notification | announce | Announcement tone |
| PreCompact | compact, rollover | Memory archival + rollover |

## Kernel Sandbox (srt/bwrap)

The sandbox module (`apps/modules/sandbox.py`) provides the kernel-level filesystem boundary for agent sessions. It wraps Anthropic's `@anthropic-ai/sandbox-runtime` (srt) library, which uses bubblewrap (bwrap) + Landlock + seccomp on Linux to enforce write/read restrictions at the OS level.

### Key Functions

| Function | What it does |
|---|---|
| `build_policy(branch_path)` | Generates per-role writable/RO map from branch passport |
| `sandbox_launch(cmd, cwd, policy)` | Resolves bwrap command via srt, spawns sandboxed process |
| `build_srt_config(policy)` | Converts policy dict to srt config format |

### Policy Rules

- **Every agent**: own branch tree + /tmp + shared channels (system_logs, .ai_central, memory_pool, AIPASS_REGISTRY.json, flow_json) + sibling mail/dashboard carve-ins + ~/.claude/projects/
- **devpulse only**: .git writable (the only committer)
- **All other agents**: .git read-only, sibling source trees read-only
- **Deny**: broker_secret (deny_read + deny_write for all roles)

Bind-mount, not isolation: the sandbox preserves the shared live filesystem. Reads stay open everywhere. Only writes to protected paths are blocked at the kernel level (EROFS).

### Architecture

The Node helper (`_srt_resolve.mjs`) resolves the globally-installed srt library via `process.execPath` (ESM resolution doesn't walk to global node_modules). The resolver runs with CWD set to `/var/tmp` to prevent srt's mandatory-deny mask files from polluting the branch directory.

The @drone broker validates sandbox policy before agent launch. @ai_mail's dispatch_monitor wires `build_policy` + `sandbox_launch` at the launch seam.

## Integration Points

### Depends On

| Branch | What for |
|---|---|
| prax | Logging (system_logger for prax monitor visibility) |

### Provides To

- All branches via hook dispatch — every Claude Code session routes through the engine
- @ai_mail dispatch_monitor — sandbox_launch + build_policy for agent launch boundary

*Last Updated: 2026-06-29*

---

[← Back to AIPass](../../../README.md)
