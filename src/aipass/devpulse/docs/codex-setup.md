# Codex CLI Integration

Status: **Working** (S159, 2026-05-16)

## Overview

OpenAI Codex CLI runs AIPass with the same hook-driven identity system as Claude Code. Same prompts, same drone commands, same branch awareness.

- CLI: `codex-cli 0.130.0`
- Model: gpt-5.5 (free tier)
- System prompt: `AGENTS.md` (equivalent to `CLAUDE.md`)
- Hooks: 3 active (SessionStart, UserPromptSubmit, PreToolUse)

## How It Works

Codex hooks use the same JSON stdin/stdout protocol as Claude Code. The hook scripts live in `.codex/hooks/` at project level. User-level wrappers in `~/.codex/hooks/` hardcode CWD to devpulse (Codex doesn't reliably set CWD for hook commands).

```
~/.codex/config.toml          # User config — hooks registered here
~/.codex/hooks/                # Wrapper scripts (anchor CWD)
.codex/hooks.json              # Project-level hooks (not actively used — discovery unreliable)
.codex/hooks/                  # Actual hook logic
.codex/skills/                 # /memo, /prep skills
AGENTS.md                      # System prompt (loaded hierarchically, 32KB max)
```

## Hooks

| Event | Script | Purpose |
|-------|--------|---------|
| SessionStart | `session_start_identity.py` | Loads global prompt + branch passport + local prompt |
| UserPromptSubmit | `prompt_inject.py` | Per-turn: current time, branch identity, email count |
| PreToolUse | `pre_edit_gate.py` | Blocks edits to passport.json, registry.json, setup.sh |

## Running

```bash
# Interactive (full access)
codex --dangerously-bypass-approvals-and-sandbox

# Headless one-shot
codex --dangerously-bypass-approvals-and-sandbox exec "your prompt"

# Sandboxed (drone logs will error but commands still work)
codex exec "your prompt"
```

## Config — ~/.codex/config.toml

```toml
[features]
hooks = true

[hooks]
SessionStart = [{ hooks = [{ type = "command", command = "python3 /home/patrick/.codex/hooks/aipass_session_start_wrapper.py", timeout = 10 }] }]
UserPromptSubmit = [{ hooks = [{ type = "command", command = "python3 /home/patrick/.codex/hooks/aipass_prompt_wrapper.py", timeout = 10 }] }]
PreToolUse = [{ matcher = "^(write_file|edit_file|patch)$", hooks = [{ type = "command", command = "python3 /home/patrick/.codex/hooks/aipass_pre_edit_gate_wrapper.py", timeout = 5 }] }]
```

## Known Issues

- **Sandbox vs drone logging:** Default `workspace-write` sandbox blocks drone's prax/trigger/json_handler log writes (they target paths outside workdir). Commands still execute and return results — just noisy stderr. Fix: use `--dangerously-bypass-approvals-and-sandbox`.
- **Hook CWD unreliable:** Codex doesn't set hook command CWD to the session workdir. Wrappers in `~/.codex/hooks/` hardcode `os.chdir()` as workaround.
- **`drone @fs` doesn't exist:** Codex sometimes invents this command when following AGENTS.md "Read" instructions. Updated AGENTS.md to say "Read (cat)" to clarify.
- **Project hooks.json not auto-discovered:** Despite `.codex/hooks.json` existing at project level with trusted hashes, Codex didn't reliably fire them. Moved all hook registration to `~/.codex/config.toml`.
- **Free tier rate limits:** gpt-5.5 free tier. May hit limits under heavy use.

## History

- **2026-04-05:** DPLAN-0094 through DPLAN-0097 created. Research + Docker proof-of-concept.
- **2026-04-28:** Hook scripts written, project `.codex/` directory scaffolded.
- **2026-05-15:** Codex tested interactively. Hooks wired but double-firing (project + user level). Trust/review gate discovered. Wrapper approach proven. Prompts received.
- **2026-05-16 (S159):** Cleaned up double-firing. Wired SessionStart + PreToolUse into config.toml. Removed stale trust entries. Verified end-to-end: identity loads, drone works, inbox checks, STATUS recognized. Full bypass mode clean.

## Differences from Claude Code

| Feature | Claude Code | Codex |
|---------|-------------|-------|
| System prompt | CLAUDE.md | AGENTS.md (hierarchical, concatenates all levels) |
| Override file | None | AGENTS.override.md (per-user, not committed) |
| Hooks config | Embedded in settings.json | Separate config.toml + hooks.json |
| Hook events | 6 (incl. PreCompact, Notification) | 5 (incl. SessionStart) |
| Sandbox bypass | `--dangerously-skip-permissions` | `--dangerously-bypass-approvals-and-sandbox` |
| File reading | Read tool (built-in) | `cat`/`sed` via exec_command |
| Model | claude-opus-4-6[1m] | gpt-5.5 |
| Max prompt | No hard limit | 32KB AGENTS.md (hooks inject separately) |

## Next Steps

- Gemini CLI integration (same pattern — `.gemini/` directory exists)
- Seedgo ignore pattern for files outside branch tree (false positives on `~/.codex/hooks/`)
- Consider: can Codex be used as a dispatch target? (different model for different tasks)
