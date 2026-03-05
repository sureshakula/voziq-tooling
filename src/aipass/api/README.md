# API

**Purpose:** Model routing, provider abstraction, LLM API access layer
**Module:** `aipass.api`
**Created:** 2026-03-05

---

## Overview

### What I Do


### How I Work
- **Entry Point:** `apps/api.py`
- **Pattern:** Auto-discovers and routes to modules

---

## Architecture

```
API/
├── apps/
│   ├── api.py       # Entry point
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

*Configure after initialization*

---

## Integration Points

### Depends On


### Provides To

