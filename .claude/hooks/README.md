# AIPass Hook System

Provider-level hooks for the AIPass ecosystem. These fire for every Claude Code
session on this machine via `~/.claude/settings.json`.

## File Layout

```
.claude/hooks/
├── README.md                    # This file
│
│ ── Hooks (wired in ~/.claude/settings.json) ──
├── global_prompt_loader.py      # UserPromptSubmit — AIPass global prompt (~22KB)
├── branch_prompt_loader.py      # UserPromptSubmit — branch-specific prompt
├── identity_injector.py         # UserPromptSubmit — branch identity from passport
├── email_notification.py        # UserPromptSubmit — unread email count
├── tool_use_sound.py            # PreToolUse — key-press sound on tool calls
├── git_gate.py                  # PreToolUse — blocks raw git/gh, protects settings
├── auto_fix_diagnostics.py      # PostToolUse — pyright + ruff on edited files
├── subagent_stop_gate.py        # SubagentStop — seedgo checklist on modified files
├── pre_compact.py               # PreCompact — post-compact recovery context
├── stop_sound.py                # Stop — achievement bell
├── notification_sound.py        # Notification — notification sound
│
│ ── Also wired but lives in ~/.claude/hooks/ ──
│   pre_edit_gate.py             # PreToolUse — cross-branch write block, error-fix gate
│   auto_watchdog.py             # PostToolUse — watchdog reminder after dispatch
│
│ ── Testing & debugging tools ──
├── hook_log.py                  # Shared logger — every hook calls run_and_log()
├── hook_report.py               # Report tool — reads JSONL log, shows table
├── hook_test.py                 # Test harness — 20 tests (11 direct + 9 integration)
│
│ ── Legacy probes ──
└── probes/
    ├── README.md
    └── probe_*.py               # Opt-in per-event diagnostic hooks
```

## Architecture

Hooks fire from three levels (can fire simultaneously):

| Level | Settings file | When it fires |
|-------|--------------|---------------|
| **Provider** | `~/.claude/settings.json` | Every session, everywhere |
| **Project** | `<project>/.claude/settings.json` | When CWD is inside the project |
| **Branch** | deeper `.claude/settings.json` | When CWD is inside that branch |

**Critical limitation:** PreToolUse and PostToolUse ONLY fire from provider settings.
UserPromptSubmit fires from ALL levels. This means project-level PreToolUse/PostToolUse
hooks provisioned by `aipass init` are dead weight — they never execute.

## CWD Guards

Four UserPromptSubmit hooks have CWD-aware guards. When CWD is inside a project that
has its own UserPromptSubmit hooks, the provider hook exits silently — preventing
AIPass context from bleeding into standalone projects.

Guarded: `global_prompt_loader.py`, `branch_prompt_loader.py`,
`identity_injector.py`, `email_notification.py`.

## Hook Inventory

### UserPromptSubmit (provider, CWD-guarded)
| Script | Purpose |
|--------|---------|
| `global_prompt_loader.py` | Injects AIPass global prompt (~22KB) |
| `branch_prompt_loader.py` | Injects branch-specific prompt from `.aipass/aipass_local_prompt.md` |
| `identity_injector.py` | Injects branch identity from `.trinity/passport.json` |
| `email_notification.py` | Shows unread email count from `.ai_mail.local/inbox.json` |

### PreToolUse (provider only)
| Script | Matcher | Purpose |
|--------|---------|---------|
| `tool_use_sound.py` | Bash\|Edit\|Write\|Read\|... | Plays key-press sound |
| `pre_edit_gate.py` | Edit\|Write\|NotebookEdit | Cross-branch write block + error-fix gate |
| `git_gate.py` | Bash\|Edit\|Write\|NotebookEdit | Blocks raw git/gh, protects settings files |

### PostToolUse (provider only)
| Script | Matcher | Purpose |
|--------|---------|---------|
| `auto_fix_diagnostics.py` | Edit\|Write\|NotebookEdit | Runs pyright + ruff on edited files |
| `auto_watchdog.py` | Bash | Reminds agent to arm watchdog after dispatch |

### Other events (provider)
| Script | Event | Purpose |
|--------|-------|---------|
| `subagent_stop_gate.py` | SubagentStop | Runs seedgo checklist on subagent-modified files |
| `pre_compact.py` | PreCompact | Injects post-compact recovery context |
| `stop_sound.py` | Stop | Plays achievement bell |
| `notification_sound.py` | Notification | Plays notification sound |

## Testing

### Execution log (always-on)
Every instrumented hook writes one JSONL line to `/tmp/aipass_hook_log.jsonl` via
`hook_log.py`. Each entry: timestamp, event, source, script, CWD, session, timing,
output_bytes, exit_code.

### Report tool
```bash
python3 .claude/hooks/hook_report.py              # Last 5 minutes
python3 .claude/hooks/hook_report.py --all         # All entries
python3 .claude/hooks/hook_report.py --cwd /tmp    # Filter by CWD
python3 .claude/hooks/hook_report.py --json         # Machine-readable
python3 .claude/hooks/hook_report.py --clear        # Wipe log
```

### Test harness (20 tests)
```bash
python3 .claude/hooks/hook_test.py                 # All 20 tests
python3 .claude/hooks/hook_test.py --direct        # 11 direct tests only (fast, ~3s)
python3 .claude/hooks/hook_test.py --integration   # 9 integration tests only (~2min)
python3 .claude/hooks/hook_test.py --verbose       # Show detail per test
python3 .claude/hooks/hook_test.py --list          # List available tests
python3 .claude/hooks/hook_test.py --test <name>   # Run one test
```

**Direct tests** (11) pipe JSON to hook scripts via subprocess. Deterministic,
no model, HIGH confidence. Tests CWD guards, git_gate block/allow, settings schema,
project-level guards.

**Integration tests** (9) run `claude -p` from different CWDs and read the JSONL log.
Tests full pipeline including cross-project behavior, subagent hooks, and the
`disableAllHooks` toggle.

### Disable all hooks
Add `"disableAllHooks": true` to `~/.claude/settings.json`. Remove to re-enable.

### Debug mode
```bash
claude --debug hooks --debug-file /tmp/debug.log
```

### Interactive inspection
Type `/hooks` inside a Claude session — shows all hooks with source labels
(`[User]`, `[Project]`, `[Local]`).

## Related
- **DPLAN-0167** — Hook testing framework
- **DPLAN-0166** — Hook audit + CI health
- **DPLAN-0139** — Hook overhaul + single-path enforcement
- **DPLAN-0131** — Hook system alignment (seedgo ownership)
