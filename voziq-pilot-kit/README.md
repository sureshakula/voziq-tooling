# VOZIQ Claude Code pilot kit

Everything needed to run the two-week native-stack pilot on 2 or 3 seats. No third-party dependencies; this is configuration for Claude Code as it ships.

## What's here

| Path | What it is | Where it goes |
|---|---|---|
| `managed/CLAUDE.md` | Org-wide policy: data boundaries, secrets, client identifiers | Each pilot seat's `~/.claude/CLAUDE.md` for now; the managed-policy path via MDM once IT is involved |
| `project/CLAUDE.md` | Per-repo instructions matched to the platform stack | Root of each pilot repo, merged with anything already there |
| `project/.claude/settings.json` | Hook wiring | `.claude/settings.json` in each pilot repo (merge if one exists) |
| `project/.claude/hooks/*.py` | The three enforcement hooks | `.claude/hooks/` in each pilot repo |
| `project/.claude/hooks/client_codes.txt` | Client short codes the hardcoding gate checks for | Same folder; fill in real codes before the pilot starts |

## The three hooks

1. `data_boundary_gate.py` (PreToolUse on Read, Write, Edit, Bash). Blocks any tool call touching customer-data locations (`data/staging/`, `.parquet`, `.duckdb`, `.env`) and any file write containing what looks like a credential: AWS keys, private keys, connection strings with passwords, hardcoded secrets. The block message tells the agent what to do instead, so it self-corrects.
2. `no_hardcoded_client.py` (PreToolUse on Write, Edit). Rejects `.py` and `.sql` writes containing a client code from `client_codes.txt`. This enforces the platform rule that client specifics live in YAML config, never in code. Config folders, fixtures, and test data paths are exempt.
3. `lint_on_edit.py` (PostToolUse on Write, Edit). Runs ruff on any edited Python file and feeds violations straight back to the agent, which fixes them in the same session instead of leaving them for CI. Silently skips if ruff isn't installed.

Hooks are enforced, not advisory: exit code 2 blocks the action and the stderr message is shown to the agent. That's the difference between these and CLAUDE.md guidance.

## Deploying a seat

1. Copy `managed/CLAUDE.md` to `~/.claude/CLAUDE.md` on the engineer's machine.
2. In each pilot repo: copy `project/CLAUDE.md` to the root, `project/.claude/` contents into `.claude/`.
3. Fill in `client_codes.txt` with the real client short codes.
4. Smoke-test the gates: ask the agent to write a file containing `AKIAIOSFODNN7EXAMPLE` (should be blocked), then to read a `.parquet` path (should be blocked), then to write a Python file with a deliberate lint error (should get ruff feedback and fix it).

## During the pilot

- Weekly, skim each seat's auto-memory (`~/.claude/projects/<project>/memory/`) for anything that shouldn't be there. Expect boring notes; the audit is the point.
- Every block message an engineer disagrees with is signal: tune the hook, don't disable it.
- End of a work session: `/brain-memo` files the learnings to the brain repo (see `voziq-brain/`).

## After the pilot

If memory recall feels shallow, add claude-mem on one seat and compare before rolling wider. If IT can push managed policy, move `managed/CLAUDE.md` to the managed path so seats can't override it.
