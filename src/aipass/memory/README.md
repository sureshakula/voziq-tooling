[← Back to AIPass](../../../README.md)

# MEMORY

**Purpose:** Central memory archive with semantic search, rollover, and archival across all AIPass branches.
**Module:** `aipass.memory`
**Created:** 2026-03-07
**Last Updated:** 2026-04-07
**Citizen Class:** builder

---

## Overview

Memory is the central memory archive system that:
- Provides semantic search across all branch memories
- Archives memories when branches hit rollover limits (600 lines)
- Extracts symbolic dimensions from conversations
- Manages template distribution and line-count tracking across branches

---

## Commands / Usage

**Via Drone (recommended):**
```bash
# Rollover
drone @memory rollover                        # Show rollover module introspection
drone @memory rollover run                    # Execute memory rollover for files over limits
drone @memory rollover status                 # Show rollover statistics for all branches
drone @memory rollover check                  # Dry run — check which files need rollover
drone @memory rollover sync-lines             # Update line count metadata for all branches

# Search
drone @memory search "error handling"         # Semantic search across all branch memories
drone @memory search "query" --branch SEEDGO  # Filter search by branch
drone @memory search "query" --n 10           # Limit number of results

# Symbolic (fragmented memory)
drone @memory symbolic                        # Show symbolic module introspection
drone @memory symbolic demo                   # Run fragmented memory demonstration
drone @memory symbolic fragments "query"      # Search symbolic fragments (not operational — no stored fragments)
drone @memory symbolic extract <file>         # Extract fragments via LLM (requires API)

# Templates (not operational — template files missing)
drone @memory templates                       # Show templates module introspection
drone @memory templates push-templates        # Push template updates to all branches (not operational)
drone @memory templates diff-templates        # Show template differences per branch (not operational)
drone @memory templates template-status       # Show template version and push status (not operational)

# Verify
drone @memory verify FPLAN-XXXX               # Check if a plan is vectorized in ChromaDB

# Watch
drone @memory watch                           # Start auto-rollover watcher (Ctrl+C to stop)
```

**Direct execution:**
```bash
python3 -m aipass.memory.apps.memory search "query"
python3 -m aipass.memory.apps.memory rollover status
```

---

## Architecture

```
memory/
├── __init__.py              # Package init
├── README.md                # This file
├── DASHBOARD.local.json     # System status dashboard
├── pytest.ini               # Test configuration
├── apps/
│   ├── __init__.py
│   ├── memory.py            # Entry point (CLI) — auto-discovers modules
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── rollover.py      # Rollover orchestrator — line checks, archival triggers
│   │   ├── search.py        # Search orchestrator — semantic query routing
│   │   └── verify.py        # Plan verification — check vectorized plan status
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── central_writer.py    # Central memory write operations
│   │   ├── dashboard_push.py    # Dashboard status push
│   │   ├── archive/             # Memory archival indexing
│   │   ├── json/                # JSON handler operations
│   │   ├── learnings/           # Learning extraction
│   │   ├── monitor/             # File watcher for auto-rollover
│   │   ├── rollover/            # Rollover implementation logic
│   │   ├── schema/              # Memory schema definitions
│   │   ├── search/              # Search implementation (vector/semantic)
│   │   ├── storage/             # Storage backend operations
│   │   ├── tracking/            # Line count and metadata tracking
│   │   ├── symbolic/             # Symbolic dimension extraction
│   │   ├── templates/            # Template management
│   │   └── vector/              # Vector DB (ChromaDB) operations
│   ├── extensions/          # Extension plugins
│   └── plugins/             # Plugin system
├── artifacts/               # Build/output artifacts
├── docs/                    # Documentation
├── memory_json/             # Memory JSON data store
├── tests/                   # Test suite
└── tools/                   # Utility scripts
```

---

## Integration Points

### Depends On
- `rich` — Console output, panels, and tables
- Python stdlib (`sys`, `time`, `signal`, `logging`, `pathlib`, `importlib`)

### Provides To
- All branches — memory rollover, archival, and retrieval services
- All branches — semantic search across branch memories
- All branches — template distribution via `push-templates`
- All branches — line count metadata via `sync-lines`

---

## Key Modules

### rollover
The rollover module monitors memory files across all branches registered in `AIPASS_REGISTRY.json`. When files exceed entry-count limits (20 sessions, 25 key_learnings), it triggers archival — extracting oldest entries, embedding them via subprocess, and storing in ChromaDB vectors. The `watch` command runs a persistent file watcher that auto-triggers rollover on changes.

### search
Semantic search across all branch memories using ChromaDB + sentence-transformers. Requires memory `.venv/` with torch installed (~3GB). All ML operations run via subprocess isolation — main process never imports torch.

### symbolic *(partial)*
Fragmented memory extraction and search. Demo and introspection work. `fragments` search returns 0 results (no stored fragments). `extract` requires API key. Code is operational but no fragment data has been stored yet.

### templates *(not operational)*
Living template push system for distributing `.trinity/` schema updates across branches. Template files (`LOCAL.template.json`, `OBS.template`) are missing — all subcommands (`push-templates`, `diff-templates`, `template-status`) fail.

### verify
Checks whether a specific flow plan (FPLAN-XXXX) has been vectorized into ChromaDB. Works correctly.

---

## Identity

- **Passport:** `.trinity/passport.json`
- **Session History:** `.trinity/local.json`
- **Observations:** `.trinity/observations.json`
- **Branch Prompt:** `.aipass/branch_system_prompt.md`

---

*Last Updated: 2026-04-07*

---
[← Back to AIPass](../../../README.md)
