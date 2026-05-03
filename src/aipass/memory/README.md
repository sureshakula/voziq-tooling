[← Back to AIPass](../../../README.md)

# MEMORY

**Purpose:** Central memory archive — vector search, rollover, and memory management for all AIPass branches.
**Module:** `aipass.memory`
**Created:** 2026-03-07
**Last Updated:** 2026-05-02
**Citizen Class:** builder

---

## Overview

Memory is the archival backbone of AIPass. Every branch accumulates session history and learnings in `.trinity/` files. When those files reach capacity, Memory archives the oldest entries into ChromaDB vectors — searchable, permanent, never lost.

What Memory does:
- **Rollover** — detects when `.trinity/local.json` or `observations.json` exceed limits, extracts oldest entries, embeds them via sentence-transformers, stores in ChromaDB, trims the source file
- **Search** — semantic search across all archived branch memories (4+ collections, 2200+ vectors)
- **Templates** — distributes `.trinity/` schema updates across all branches (push, diff, status)
- **Symbolic** — fragmented memory extraction from conversations (demo, analyze, extract, fragments, bootstrap, hook-test)
- **Verify** — checks whether a flow plan is vectorized in ChromaDB
- **Watch** — persistent file watcher that auto-triggers rollover on changes

---

## Commands

All commands via `drone @memory <command>`:

```bash
# Introspection
drone @memory                              # Module list, version
drone @memory --help                       # Full command reference
drone @memory --version                    # Version string

# Rollover
drone @memory rollover                     # Module introspection (handlers + subcommands)
drone @memory rollover run                 # Execute rollover for files over limits
drone @memory rollover status              # Show per-branch rollover statistics
drone @memory rollover check               # Dry run — check what needs rollover
drone @memory rollover sync-lines          # Update line count metadata for all branches

# Search
drone @memory search "error handling"      # Semantic search across all branch memories
drone @memory search "query" --branch X    # Filter search by branch
drone @memory search "query" --n 10        # Limit number of results

# Symbolic
drone @memory symbolic                     # Module introspection (6 handlers, subcommands)
drone @memory symbolic demo                # Run v1 + v2 mock analysis demonstration
drone @memory symbolic fragments "query"   # Search stored symbolic fragments
drone @memory symbolic extract <file>      # Extract fragments via LLM (requires API key)
drone @memory symbolic bootstrap           # Populate fragments from session JSONLs
drone @memory symbolic hook-test           # Test hook with sample conversation text

# Templates
drone @memory templates push-templates     # Push template updates to all branches
drone @memory templates diff-templates     # Show template differences per branch
drone @memory templates template-status    # Show template version and push status

# Verify
drone @memory verify FPLAN-XXXX            # Check if plan is vectorized in ChromaDB

# Watch
drone @memory watch                        # Auto-rollover watcher daemon (Ctrl+C to stop)
```

---

## Architecture

```
memory/
├── .trinity/                    # Identity & memory
│   ├── passport.json            # Branch identity
│   ├── local.json               # Session history (v2 schema, entry-count limits)
│   └── observations.json        # Collaboration patterns (v1 schema, line-count limits)
├── .aipass/                     # Branch prompt
├── .ai_mail.local/              # Mailbox
├── apps/
│   ├── memory.py                # Entry point — auto-discovers modules via handle_command()
│   ├── modules/                 # Business logic (5 modules)
│   │   ├── rollover.py          # Rollover orchestration, status display, sync-lines
│   │   ├── search.py            # Semantic query routing
│   │   ├── verify.py            # Plan vectorization check
│   │   ├── symbolic.py          # Fragmented memory extraction and search
│   │   └── templates.py         # Template push, diff, status
│   └── handlers/                # Implementation (14 handler groups, 35 files)
│       ├── archive/             # indexer.py — memory archival indexing
│       ├── intake/              # plans_processor.py, pool_processor.py — ingest pipelines
│       ├── json/                # json_handler.py, memory_files.py — JSON operations
│       ├── learnings/           # manager.py — learning extraction and management
│       ├── monitor/             # detector.py, memory_watcher.py — rollover detection + auto-trigger
│       ├── rollover/            # extractor.py, orchestrator.py — backup → extract → embed → store
│       ├── schema/              # normalize.py — schema version normalization
│       ├── search/              # query_executor.py, vector_search.py — semantic search impl
│       ├── storage/             # chroma.py, chroma_subprocess.py — ChromaDB backend
│       ├── symbolic/            # 6 handlers — chroma_client, deduplicator, extractor, hook, retriever, storage
│       ├── templates/           # pusher.py, differ.py, spawn_pusher.py — template distribution
│       ├── tracking/            # line_counter.py — metadata line count tracking
│       ├── vector/              # embedder.py, embed_subprocess.py — sentence-transformer embeddings
│       ├── central_writer.py    # Central memory write operations
│       └── dashboard_push.py    # Dashboard status push
├── config/                      # memory_bank.config.json — per-branch rollover limits
├── templates/                   # LOCAL.template.json, OBS.template — schema templates
├── tests/                       # 450 tests (16/16 module coverage)
├── .chroma/                     # Global ChromaDB vector store
└── memory_json/                 # Operation log files (auto-created)
```

### Rollover Pipeline

```
startup trigger → check_and_rollover()
  → detector.check_all_branches()      # scan AIPASS_REGISTRY.json
  → _should_rollover(file)             # v1: line_count >= max_lines
                                       # v2: len(sessions) >= max_sessions, etc.
  → orchestrator.execute_rollover()
    → create_rollover_backup()         # safety copy to branch/.backup/
    → extract_items()                  # v2: max(excess, 1) oldest entries
    → embed via subprocess             # sentence-transformers in memory .venv
    → store in ChromaDB                # global + local collections
    → trim source file                 # write back with oldest removed
```

### Dual Schema Support

- **v1** (line-count): `schema_version: "1.0.0"` — triggers at `current_lines >= max_lines` (default 600)
- **v2** (entry-count): `schema_version: "2.0.0"` — triggers at `len(sessions) >= max_sessions` or `len(key_learnings) >= max_key_learnings`. Extractor uses `max(excess, 1)` guard to prevent Python's `list[-0:]` trap.

### Subprocess Isolation

All ML operations (torch, sentence-transformers, chromadb) run via subprocess. The main process never imports these heavy libraries. Each embedding call spawns `memory/.venv/bin/python3` with a self-contained script that reads stdin JSON and writes stdout JSON.

---

## Dependencies

### Runtime
- `rich` — console output, panels, tables
- Python stdlib (`json`, `pathlib`, `logging`, `importlib`, `signal`)
- `prax` (internal) — logging via `get_system_logger()`

### ML (in memory `.venv/` only)
- `torch` + `sentence-transformers` — embedding generation
- `chromadb` — vector storage and semantic search
- `numpy` — numerical operations

### Provides To
- All branches — memory rollover and archival when `.trinity/` files hit limits
- All branches — semantic search across archived memories
- All branches — template schema distribution
- All branches — line count metadata sync

---

## Quality

- **Seedgo:** 100% (33/33 standards) — maintained since s12
- **Tests:** 450 pass, 1 skip (test_vector.py gated with `importorskip` for numpy)
- **Coverage:** 175 public functions, 102 tested (58%), 16/16 modules
- **Type checking:** 35 files, 0 errors

---

## Known Issues

- `search` requires torch/sentence-transformers in memory `.venv/` — fails without them
- memory_watcher.py at 704 lines (near 700 threshold, bypassed in seedgo)
- symbolic.py at 1604 lines (legacy port, bypassed)
- manager.py at 1076 lines (complex learning extraction, bypassed)
- `memory_threshold_exceeded` trigger event registered but never fired — rollover auto-runs at startup via watcher
- `rollover status` shows 0 branches when `AIPASS_REGISTRY.json` path not resolved

---

## Identity

- **Passport:** `.trinity/passport.json`
- **Session History:** `.trinity/local.json` (v2 schema, 20 sessions max, 25 key_learnings max)
- **Observations:** `.trinity/observations.json` (v1 schema, 600 lines max)
- **Branch Prompt:** `.aipass/aipass_local_prompt.md`

---

*Last Updated: 2026-04-22*

---
[← Back to AIPass](../../../README.md)
