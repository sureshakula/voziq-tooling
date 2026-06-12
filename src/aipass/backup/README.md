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
BACKUP/
├── apps/
│   ├── backup.py       # Entry point
│   ├── modules/            # Business logic
│   ├── handlers/           # Implementation
│   └── plugins/            # Extensions
├── docs/
├── tests/
├── passport.json           # Identity
├── local.json              # Session history
├── observations.json       # Collaboration patterns
└── README.md
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


### Provides To

