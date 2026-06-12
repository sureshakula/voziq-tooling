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
- Each project owns its backup config (`.backup_system/`) and ignore patterns (`.backupignore`)
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
│   ├── drive_test.py      # Drive test (stub — DPLAN-003)
│   ├── register.py        # Project registration + @name resolution
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
    ├── project/           # Config, registry, setup (.backup_system/)
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
backup all <path|@name>                  # Snapshot + versioned
backup status <path|@name>              # Show backup info and history
backup --version                        # Show version
```

---

## Integration Points

### Depends On
- @prax — logging
- @cli — Rich console output

### Provides To
- Any project on the PC — backups are project-owned (.backup_system/ in target root)
