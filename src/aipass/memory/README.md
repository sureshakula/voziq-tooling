[← Back to AIPass](../../../README.md)

# MEMORY

**Central memory archive — vector search, rollover, and memory management for all AIPass branches.**

`drone @memory <command>` | Module: `aipass.memory` | Created: 2026-03-07

---

## Commands

```bash
drone @memory rollover run                 # Execute rollover for files over limits
drone @memory rollover status              # Show per-branch rollover statistics
drone @memory rollover check               # Dry run — what needs rollover
drone @memory rollover sync-lines          # Update line count metadata

drone @memory search "query"               # Semantic search across all branch memories
drone @memory search "query" --branch X    # Filter by branch
drone @memory search "query" --n 10        # Limit results

drone @memory symbolic demo                # Mock analysis demonstration
drone @memory symbolic fragments "query"   # Search stored symbolic fragments
drone @memory symbolic extract <file>      # Extract fragments via LLM (requires API key)
drone @memory symbolic bootstrap           # Populate fragments from session JSONLs
drone @memory symbolic hook-test           # Test hook with sample conversation text

drone @memory templates push-templates     # Push template updates to all branches
drone @memory templates diff-templates     # Show template differences per branch
drone @memory templates template-status    # Show template version and push status

drone @memory lint                         # Audit .trinity entries for over-limit violations (read-only)
drone @memory lint @devpulse               # Lint a specific branch

drone @memory verify FPLAN-XXXX            # Check if plan is vectorized in ChromaDB
drone @memory watch                        # Auto-rollover watcher daemon (Ctrl+C to stop)
```

---

## Architecture

```
memory/
├── apps/
│   ├── memory.py                # Entry point — auto-discovers modules
│   ├── modules/                 # 6 modules
│   │   ├── lint.py              # Entry limit violation scanner (read-only)
│   │   ├── rollover.py          # Rollover orchestration, status, sync-lines
│   │   ├── search.py            # Semantic query routing
│   │   ├── symbolic.py          # Fragmented memory extraction and search
│   │   ├── templates.py         # Template push, diff, status
│   │   └── verify.py            # Plan vectorization check
│   └── handlers/                # 14 handler groups
│       ├── archive/             # indexer.py
│       ├── intake/              # plans_processor.py, pool_processor.py
│       ├── json/                # json_handler.py, memory_files.py, entry_limits.py, lint_handler.py, config_loader.py
│       ├── learnings/           # manager.py
│       ├── monitor/             # detector.py, memory_watcher.py
│       ├── rollover/            # extractor.py, orchestrator.py
│       ├── schema/              # normalize.py
│       ├── search/              # query_executor.py, vector_search.py
│       ├── storage/             # chroma.py, chroma_subprocess.py
│       ├── symbolic/            # chroma_client, deduplicator, extractor, hook, retriever, storage
│       ├── templates/           # pusher.py, differ.py, spawn_pusher.py
│       ├── tracking/            # line_counter.py
│       ├── vector/              # embedder.py, embed_subprocess.py
│       └── central_writer.py
├── templates/                   # LOCAL.template.json, OBSERVATIONS.template.json
├── tests/                       # 949 tests (31 test files)
├── .chroma/                     # ChromaDB vector store
└── memory_json/                 # Operation logs + custom_config/memory.config.json
```

### Rollover Pipeline

```
detector.check_all_branches()        # scan AIPASS_REGISTRY.json + external registries
→ _should_rollover(file)             # v1: line_count >= max_lines (600)
                                     # v2: len(sessions) >= max_sessions (20)
→ orchestrator.execute_rollover()
  → create_rollover_backup()         # safety copy to branch/.backup/
  → extract_items()                  # v2: max(excess, 1) oldest entries
  → embed via subprocess             # fastembed (ONNX) in memory .venv
  → upsert in ChromaDB               # content-hash IDs (sha256[:16]), no duplicates
  → trim source file                 # write back with oldest removed
```

Rollover writes safety copies (`rollover_backup_*.json`) into `<branch>/.backup/` — a shared runtime namespace (see `@backup`'s README for all writers).

### Subprocess Isolation

All ML operations (fastembed, chromadb) run via subprocess. The main process never imports these libraries. Python interpreter resolved via `_get_memory_python()` (env var `AIPASS_MEMORY_PYTHON` → `memory/.venv/bin/python` → `sys.executable`).

---

## Integration Points

**Depends on:**
- `prax` — logging via `get_system_logger()`
- `api` — API key for symbolic extraction (`get_api_key()`)
- `AIPASS_REGISTRY.json` — branch discovery for rollover scanning
- External `*_REGISTRY.json` — scanned via `AIPASS_CALLER_CWD`

**Provides to:**
- All branches — rollover archival when `.trinity/` files hit limits
- All branches — semantic search across archived memories
- All branches — `.trinity/` template distribution and sync

**ML dependencies (memory `.venv/` only):**
- `fastembed` — ONNX embeddings (model: `sentence-transformers/all-MiniLM-L6-v2`)
- `chromadb` — vector storage and semantic search
- `numpy`

---

## Quality

- **Tests:** 949 passed, 0 failures, 0 skips
- **Test files:** 31
- **Seedgo:** 100% — maintained since s12

---

## Known Issues

- `search` requires fastembed in memory `.venv/` — fails without it
- `rollover status` shows 0 branches when registry path not resolved
- `memory_threshold_exceeded` trigger event registered but never fired

---

*Last Updated: 2026-05-16*

---
[← Back to AIPass](../../../README.md)
