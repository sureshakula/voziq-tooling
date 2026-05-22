# .claude/ -- Claude Code Configuration

This directory configures Claude Code for the AIPass project.

**Related:** DPLAN-0184 (Hook Migration), DPLAN-0053 (original hook architecture research).

## How Hooks Work (Post-Migration)

All AIPass hooks run through a three-layer pipeline:

```
~/.claude/settings.json      Provider settings (Claude Code reads these)
        |
        v
claude.py (bridge)           Thin entry point -- normalizes stdin, calls engine
        |
        v
engine.py (dispatcher)       Reads .aipass/hooks.json, imports + calls handlers
        |
        v
handlers/                    Native Python handlers (the actual hook logic)
```

Provider settings in `~/.claude/settings.json` call the bridge with an event type:

```json
{
  "type": "command",
  "command": "$AIPASS_HOME/.venv/bin/python3 $AIPASS_HOME/src/aipass/hooks/apps/handlers/bridges/claude.py PreToolUse"
}
```

The bridge supports two invocation forms:
- `claude.py EventType` -- dispatch ALL enabled hooks for that event
- `claude.py EventType:hook_name` -- dispatch ONLY one specific hook (used for UserPromptSubmit where each hook needs its own system-reminder block)

Per-project configuration lives in `.aipass/hooks.json`. Each hook entry specifies:
- `enabled` -- whether the hook fires
- `handler` -- dotted import path to the handler function
- `matcher` -- tool name filter (empty string = match all)
- `timeout` -- optional timeout in seconds

## Quick Setup

Run `setup.sh` from the repo root. It creates the venv, installs the package, and wires bridge entries into `~/.claude/settings.json` automatically.

```bash
./setup.sh
```

If hooks get out of sync, `aipass doctor --fix` can auto-wire missing hook entries.

No manual script copying is needed. No global_hooks directory. No `git rev-parse` tricks.

## What's In This Directory

```
.claude/
├── settings.json              # Project settings (permissions, env vars)
├── hooks/                     # Legacy hook scripts (all disabled) + testing tools
│   ├── *.py(disabled)             # 18 disabled scripts (pre-migration)
│   ├── hook_log.py                # Shared logger -- hooks call run_and_log()
│   ├── hook_report.py             # Report tool -- reads JSONL log, shows table
│   ├── hook_test.py               # Test harness -- direct + integration tests
│   └── probes/                    # Opt-in per-event diagnostic probes
├── agents/                    # Agent definitions
│   └── builder.md
├── commands/                  # Slash commands
│   └── memo.md                    # /memo -- memory update workflow
├── sounds/                    # Audio files for sound hooks
└── README.md                  # This file
```

Hook logic has moved to `src/aipass/hooks/apps/handlers/`. See the handler README for the full layout.

## Handler Layout

All 14 hooks are native Python handlers organized by domain:

```
src/aipass/hooks/apps/handlers/
├── bridges/
│   └── claude.py              # Provider bridge (called from settings.json)
├── config/
│   ├── loader.py              # Finds and reads .aipass/hooks.json
│   └── diagnostics.py         # JSONL logging for hook execution
├── prompt/
│   ├── global_loader.py       # UserPromptSubmit -- AIPass global prompt
│   ├── branch_loader.py       # UserPromptSubmit -- branch-specific prompt
│   └── identity.py            # UserPromptSubmit -- passport identity injection
├── notification/
│   ├── email.py               # UserPromptSubmit -- unread email count
│   ├── tool_sound.py          # PreToolUse -- key-press sound
│   ├── stop_sound.py          # Stop -- achievement bell
│   └── announce.py            # Notification -- notification sound
├── security/
│   ├── git_gate.py            # PreToolUse -- blocks raw git/gh commands
│   ├── edit_gate.py           # PreToolUse -- cross-branch write block
│   └── subagent_gate.py       # SubagentStop -- seedgo checklist gate
└── lifecycle/
    ├── auto_fix.py            # PostToolUse -- pyright + ruff after edits
    ├── auto_watchdog.py       # PostToolUse -- watchdog reminder after dispatch
    ├── compact.py             # PreCompact -- save context before compaction
    └── rollover.py            # PreCompact -- memory rollover on compaction
```

## What Gets Injected Every Turn

1. **Global Prompt** -- system context, terminology, commands, rules (`.aipass/aipass_global_prompt.md`)
2. **Branch Prompt** -- branch-specific instructions based on CWD (`.aipass/aipass_local_prompt.md`)
3. **Identity** -- passport summary: role, traits, purpose (`.trinity/passport.json`)
4. **Email** -- notification only if unread mail exists (`.ai_mail.local/inbox.json`)

Each is dispatched as a separate `UserPromptSubmit:hook_name` call so it gets its own system-reminder block.

## Project Settings

Defined in `settings.json` (this directory). These fire from subdirectories.

**Environment:**
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` -- makes PostToolUse hooks fire inside subagents
- `AIPASS_HOME` -- repo root path, used by bridge commands

**Permissions:**
- Denied: `git reset`, `git rebase`, `git config`, `git push --force`, `EnterPlanMode`
- Default mode: `acceptEdits`

## Adding a New Hook

1. Create a handler in `src/aipass/hooks/apps/handlers/<domain>/your_hook.py` with a `handle(event_type, stdin_data, config)` function
2. Add an entry to `.aipass/hooks.json` under the appropriate event type
3. If the hook needs its own system-reminder output (like prompt injectors), add a separate bridge entry in `~/.claude/settings.json` using the `EventType:hook_name` form
4. Run `setup.sh` or `aipass doctor --fix` to sync provider settings

## Architecture Notes

**Why provider settings?** Claude Code project settings (`.claude/settings.json`) do not fire `UserPromptSubmit` hooks from subdirectories. Since AIPass citizens launch from `src/aipass/{name}/`, prompt injection must live in provider settings (`~/.claude/settings.json`). The bridge pattern makes this clean -- one bridge binary, many handlers.

**Why separate bridge calls for UserPromptSubmit?** Each UserPromptSubmit hook entry gets its own system-reminder block in the conversation. Bundling them into one call would merge all prompt output into a single block, losing separation.

**Why .aipass/hooks.json?** Decouples hook configuration from provider settings. The engine reads this at dispatch time, so hooks can be enabled/disabled without editing `~/.claude/settings.json`.
