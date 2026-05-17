# CLI Test Results

**Date:** 2026-03-06
**Agent:** DevPulse sub-agent
**Environment:** Linux 6.12.72-linuxkit, Python 3.11, aipass 1.0.0

---

## Test 1: `pip install -e .`

**Result: PASS (with workaround)**

Initial attempt failed with `error: externally-managed-environment` (PEP 668). Succeeded with `--break-system-packages` flag. Package installed to `~/.local/` (user install). All dependencies resolved: rich 14.3.3, watchdog 6.0.0, markdown-it-py 4.0.0, pygments 2.19.2.

**Warning:** The `drone` and `seedgo` scripts installed to `~/.local/bin` which is NOT on PATH by default. Must `export PATH="$HOME/.local/bin:$PATH"` before CLI commands work.

---

## Test 2: `drone --help`

**Result: PASS**

Output:
```
Drone - Command Router & Discovery

Routes commands to AIPass branches and internal modules.

Usage:
  drone @target command [args]   Route command to branch or module
  drone @target --help           Show help for branch or module
  drone systems                  List registered branches and modules
  drone --help                   Show this help
  drone --version                Show version

Examples:
  drone @seedgo audit aipass
  drone @seedgo list
  drone @flow status
  drone systems
```

---

## Test 3: `drone systems`

**Result: PASS**

Output:
```
Modules (2):
  @drone              Command routing and module discovery
  @seedgo             Standards compliance through pluggable standard packs

Branches (10):
  @ai_mail
  @api
  @cli
  @devpulse
  @drone
  @flow
  @prax
  @seedgo
  @spawn
  @trigger
```

---

## Test 4: `drone @seedgo verify`

**Result: PASS**

Output:
```
SEEDGO VERIFY

  Standards directory exists
  1 standard pack(s) installed: aipass
  Pack 'aipass': valid manifest (v1.0.0, 20 standards)
  Pack 'aipass': entry point exists
  Pack 'aipass': all 20 standard check files present

  PASS  5/5 checks passed (100%)
```

---

## Test 5: `drone @seedgo list`

**Result: PASS**

Output:
```
  aipass               (20 standards)
```

---

## Test 6: Registry import

**Command:** `python3 -c "from aipass.drone.apps.modules.registry import load_registry; print(load_registry())"`

**Result: PASS**

Registry loaded successfully. Returns dict with metadata (version 1.0.0, 10 branches) and all 10 branch entries with correct paths under `/home/coder/workspace/src/aipass/`.

---

## Test 7: Prax logger import

**Command:** `python3 -c "from aipass.prax import logger; logger.info('test')"`

**Result: PASS**

No output and no errors. Logger imported and called without issue. Note: no visible output suggests the logger may not have a handler configured or the log level filtered it, but the import and call succeeded without exceptions.

---

## Test 8: CLI console/header import

**Command:** `python3 -c "from aipass.cli import console, header; header('test')"`

**Result: PASS**

Output rendered a Rich-formatted box:
```
+------+
| test |
+------+
```

---

## Test 9: DevPulse branch import

**Command:** `python3 -c "from aipass.devpulse.apps.branch import main"`

**Result: PASS**

Import succeeded with no output and no errors.

---

## Summary

| # | Test | Result |
|---|------|--------|
| 1 | `pip install -e .` | PASS (needs `--break-system-packages`) |
| 2 | `drone --help` | PASS |
| 3 | `drone systems` | PASS |
| 4 | `drone @seedgo verify` | PASS |
| 5 | `drone @seedgo list` | PASS |
| 6 | Registry import | PASS |
| 7 | Prax logger import | PASS |
| 8 | CLI console/header import | PASS |
| 9 | DevPulse branch import | PASS |

**Overall: 9/9 PASS**

### Notes

1. **PATH issue:** `~/.local/bin` is not on PATH by default in this environment. The `drone` and `seedgo` CLI entry points install there. Any automation or CI must ensure PATH includes this directory.
2. **PEP 668:** The system Python is externally managed. `--break-system-packages` or a virtualenv is required.
3. **Prax logger:** Imports cleanly but `logger.info('test')` produces no visible output -- may need handler/level configuration review (not necessarily a bug, but worth noting).
