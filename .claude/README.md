# .claude/ — Claude Code Configuration

This directory configures Claude Code for the AIPass repo. It controls hooks (prompt injection, auto-fix, recovery), custom commands, permissions, and sound effects.

## How It's Wired

There are **two** settings files that matter:

| File | Scope | Paths |
|------|-------|-------|
| `.claude/settings.json` (this dir) | Project-level, checked into git | Relative paths (e.g. `.claude/hooks/...`) |
| `~/.claude/settings.json` | Global, per-machine | Absolute paths (e.g. `/home/coder/workspace/AIPass/.claude/hooks/...`) |

**Why both?** Project settings only fire when Claude launches from the repo root. Since citizens launch from branch subdirectories (`src/aipass/{name}/`), the global config duplicates the hook definitions with absolute paths so they always fire regardless of CWD.

After a container rebuild, the global config needs to be restored. The project config is the source of truth (checked into git).

## Directory Structure

```
.claude/
├── CLAUDE.md              # Project instructions for Claude (auto-loaded)
├── settings.json          # Project-level hook config + permissions
├── hooks/                 # Hook scripts (Python)
│   ├── branch_prompt_loader.py    # Injects branch-local system prompt
│   ├── identity_injector.py       # Injects citizen identity from passport
│   ├── email_notification.py      # Alerts on unread AI Mail
│   ├── auto_fix_diagnostics.py    # Auto-fixes Python/JSON issues after edits
│   ├── pre_compact.py             # Saves recovery context before compaction
│   ├── tool_use_sound.py          # Sound on tool use (needs audio device)
│   ├── notification_sound.py      # Sound on notification (needs audio device)
│   └── stop_sound.py              # Sound on stop (needs audio device)
├── commands/              # Custom slash commands
│   └── memo.md            # /memo — triggers memory update workflow
└── sounds/                # Audio files for sound hooks
    ├── mixkit-achievement-bell-600.wav
    ├── mixkit-atm-cash-machine-key-press-2841.wav
    └── mixkit-clear-announce-tones-2861.wav
```

## Hooks

### UserPromptSubmit (fires on every prompt)

1. **Global prompt** — `cat .aipass/aipass_global_prompt.md` — injects system-wide context (terminology, commands, rules)
2. **Branch prompt** — `branch_prompt_loader.py` — finds nearest `.aipass/branch_system_prompt.md` from CWD and injects it
3. **Identity injector** — `identity_injector.py` — reads `.trinity/passport.json` and injects citizen identity (role, purpose, principles)
4. **Email notification** — `email_notification.py` — checks `.ai_mail.local/inbox.json` for unread messages

### PostToolUse (fires after file edits)

5. **Auto-fix diagnostics** — `auto_fix_diagnostics.py` — runs Python syntax check and JSON validation on edited files, outputs fix suggestions

### PreCompact (fires before context compaction)

6. **Pre-compact recovery** — `pre_compact.py` — saves session context so the citizen can recover after compaction

### PreToolUse / Stop / Notification (sound hooks)

7-9. Sound effects — **require audio device** (`--device /dev/snd` in Docker run). Currently non-functional in container.

## Custom Commands

- `/memo` — Triggers memory update workflow. Reads `.trinity/` files, updates local.json, observations.json, and optionally passport.json and README.md.

## Permissions

Defined in `settings.json`:
- **Denied**: `git reset`, `git rebase`, `git config`, `git push --force`, `EnterPlanMode`
- **Default mode**: `acceptEdits`

## Related Files

- `.aipass/aipass_global_prompt.md` — The global system prompt (at repo root, NOT in .claude/)
- `src/aipass/{name}/.aipass/branch_system_prompt.md` — Per-branch system prompts
- `src/aipass/{name}/.trinity/passport.json` — Citizen identity (read by identity_injector)
- `src/aipass/{name}/.ai_mail.local/inbox.json` — Mailbox (read by email_notification)

## After Container Rebuild

1. `pip install -e . --break-system-packages`
2. Symlink CLI tools: `ln -sf ~/.local/bin/drone /usr/local/bin/drone && ln -sf ~/.local/bin/seedgo /usr/local/bin/seedgo`
3. Copy project settings to global: restore `~/.claude/settings.json` with absolute paths (see global config format above)
