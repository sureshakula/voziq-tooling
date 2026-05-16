# Portability Audit — Session 24 Results

## Summary

| Tool | Registry Discovery | CWD-Aware | Portable | Hardcoded |
|------|-------------------|-----------|----------|-----------|
| Drone | Walk-up + env var | No (uses registry) | Yes | Registry filename |
| Spawn | Walk-up + env var | No (uses registry) | Partial | Template location |
| Prax | Walk-up (no env) | No (sys logs at repo) | Partial | System logs dir |
| AI_Mail | Walk-up (no env) | No (inbox per branch) | Yes | Inbox location |
| Flow | Walk-up (no env) | Yes (plan creation) | Hybrid | Plan registry |

## Key Findings

- All tools use walk-up strategy to find `AIPASS_REGISTRY.json`
- Registry-relative path resolution already works (move registry + dirs = works)
- `AIPASS_REGISTRY` env var supported by drone and spawn
- System logs hardcoded to `{repo_root}/system_logs/`
- Spawn templates hardcoded to `{spawn_package}/templates/`
- Walk-up doesn't stop at project boundaries — finds nearest registry up the tree

## The Core Fix

Change `find_registry()` to:
1. Walk up from CWD looking for `*_REGISTRY.json` (glob, not hardcoded name)
2. Stop at first match — that's the project boundary
3. If none found, return error ("No AIPass project. Run `aipass init`")

## Source

Full investigation transcript: background agent session 24, 42 tool calls across drone/spawn/ai_mail/flow/prax.
