# dev.local.md - MEMORY
```
Branch: /home/patrick/Projects/AIPass/src/aipass/memory
Created: 2026-03-07
```

## Issues

- `search` command fails — missing `torch`/`sentence-transformers` deps
- 5 commands in `--help` not implemented: push-templates, diff-templates, template-status, symbolic demo, symbolic fragments
- `status` shows 0 branches — detector may not resolve registry/branch paths
- Help text is aspirational, not grounded in code reality

---

## Todos

- Fix or remove unimplemented commands from --help
- Investigate why status shows 0 branches (registry path resolution)
- Decide on torch/sentence-transformers — install or provide graceful fallback
