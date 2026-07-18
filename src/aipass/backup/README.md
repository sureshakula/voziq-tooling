# BACKUP

**Purpose:** Standalone backup system — project-owned, local-first backups for any directory
**Module:** `aipass.backup`
**Version:** 1.0.0
**Created:** 2026-04-16
**Last Updated:** 2026-05-03

---

## Overview

### What I Do

- Back up any project directory on the system (not just AIPass projects)
- Each project owns its backup config (`.backup/`) and ignore patterns (`.backupignore`)
- Snapshot mode: full mirror copy
- Versioned mode: incremental timestamped backups with automatic pruning
- Project registry for name-based lookups (`backup snapshot @AIPass`)

### How I Work
- **Entry Point:** `apps/backup.py`
- **Pattern:** Auto-discovers and routes to modules

---

## Architecture

```
apps/
├── backup.py              # Entry point (auto-discovery router)
├── modules/
│   ├── all.py             # Snapshot + versioned orchestration
│   ├── display.py         # Rich CLI rendering (used by snapshot/versioned/all)
│   ├── drive_clear.py     # Drive clear (stub — DPLAN-003)
│   ├── drive_stats.py     # Drive stats (stub — DPLAN-003)
│   ├── drive_sync.py      # Drive sync (stub — DPLAN-003)
│   ├── drive_check.py     # Drive check (stub — DPLAN-003)
│   ├── register.py        # Project registration + @name resolution
│   ├── restore.py         # Version discovery + file restoration
│   ├── settings.py        # Settings UI (stub)
│   ├── snapshot.py        # Full mirror backup
│   ├── status.py          # Backup status display
│   └── versioned.py       # Incremental timestamped backup
└── handlers/
    ├── copy/              # File copying (snapshot + versioned)
    ├── diff/              # Diff generation (stub)
    ├── drive/             # Google Drive handlers (stubs)
    ├── ignore/            # .backupignore patterns + whitelist
    ├── json/              # JSON persistence, atomic writes, ops log
    ├── path/              # Backup path building
    ├── project/           # Config, registry, setup (.backup/)
    ├── report/            # Result formatting
    ├── scan/              # Directory walking + filtering
    ├── state/             # Changelog, metadata, timestamps
    └── ui/                # Settings window (stub)
```

---

## Commands

```
backup register <path> [--name <name>]   # Register a project for backup
backup snapshot <path|@name>             # Full mirror backup
backup versioned <path|@name>            # Incremental timestamped backup
backup all <path|@name>                  # Snapshot + versioned + drive
backup status <path|@name>              # Show backup info and history
backup restore <path|@name> list <file>  # List available versions of a file
backup restore <path|@name> file <f> <o> # Restore a file version to output path
backup settings <path|@name>             # Settings UI (stub)
backup drive_sync <path|@name>           # Google Drive sync (stub — DPLAN-003)
backup drive_check <path|@name>          # Drive connectivity check (stub — DPLAN-003)
backup drive_stats <path|@name>          # Drive storage stats (stub — DPLAN-003)
backup drive_clear <path|@name>          # Clear Drive sync state (stub — DPLAN-003)
```

All 11 commands are auto-discovered by the entry point router.

---

## Quick Start

```bash
# Register a project for backup
drone @backup register /path/to/project --name myapp

# Full mirror snapshot
drone @backup snapshot @myapp

# Incremental timestamped backup
drone @backup versioned @myapp

# Check backup status
drone @backup status @myapp

# List available versions of a file
drone @backup restore @myapp list src/main.py
```

---

## `.backup/` Store Structure

Each registered project gets a `.backup/` directory at its root:

```
.backup/
├── config.json          # Project backup configuration
├── snapshots/           # Full mirror copies (eager — created on register)
├── versioned/           # Incremental timestamped backups (lazy)
├── logs/                # Operation logs (eager — created on register)
├── timestamps.json      # Backup timing metadata (lazy)
├── changelog.json       # Change history (lazy)
└── drive_tracker.json   # Drive sync dedup tracker (lazy)
```

On `register`, only `snapshots/` and `logs/` are created eagerly (plus `config.json`). The rest are created lazily on first use.

**Shared namespace:** `.backup/` is NOT exclusive to @backup. Three writers use it:
- **@backup** — snapshot/versioned stores at a registered project root
- **@memory** — rollover safety copies (`rollover_backup_*.json`) written to `<branch>/.backup/` during memory overflow
- **@flow** — closed plans archived to `<repo-root>/.backup/processed_plans/` for vectorization by @memory

The root `.gitignore` covers all three with a single `.backup/` entry.

---

## How Ignores Work

Two layers — seed and runtime:

1. **`templates/backupignore.template`** — the **seed**. Read by `setup._build_backupignore()` and written into a new project's `.backupignore` at `register` time. Never consulted at backup time. If this file is missing, registration raises — an empty seed would back up everything and crash the machine.
2. **`.backupignore`** — the **runtime source of truth**. `load_spec()` reads it on every backup; the seed template is not applied. True pathspec/gitwildmatch semantics: `#` comments, `!` negation, trailing `/` for dirs, last-match-wins.

There is no static fallback. The seed IS the safety mechanism — an empty or missing `.backupignore` means back up everything (`.venv`, `node_modules`, `.git`), which can crash the machine. Keep the template sane.

- To change defaults for **new** projects → edit `templates/backupignore.template`
- To change ignores for an **existing** project → edit its `.backupignore`

The repo-root `/.backupignore` ships intentionally as the curated default so users don't snapshot junk.

---

## Integration Points

### Depends On
- @prax — logging
- @cli — Rich console output

### Provides To
- Any project on the PC — backups are project-owned (`.backup/` in target root)
