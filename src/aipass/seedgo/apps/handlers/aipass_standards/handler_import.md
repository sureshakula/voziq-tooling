# Handler Import Standard
**Status:** Active v1
**Date:** 2026-04-26

---

## Core Rule: Every apps/__init__.py Must Import Handlers

Every AIPass branch with an `apps/` package must include `from . import handlers` in its `apps/__init__.py`. Without this explicit import, Python 3.10's `mock.patch` cannot resolve handler subpackages through the attribute chain.

---

## Why This Matters

**The problem:** `mock.patch("aipass.branch.apps.handlers.some_module")` traverses the dotted path using `getattr`. In Python 3.10, if `handlers` was never explicitly imported in `apps/__init__.py`, the `getattr(apps, "handlers")` call raises `AttributeError` -- even though the `handlers/` directory exists on disk with its own `__init__.py`.

**What goes wrong without the import:**
1. **Tests silently break** -- `mock.patch` targeting handler submodules raises `AttributeError` instead of patching.
2. **CI false greens** -- if the test catches the exception or skips, violations slip through undetected.
3. **3.10 vs 3.11 divergence** -- Python 3.11+ is more lenient about lazy subpackage resolution. Code that works on 3.11 breaks on 3.10, which AIPass CI uses.

**What the import does:**
```python
from . import handlers
```
This single line forces Python to import and register the `handlers` subpackage on the `apps` namespace at import time. After that, `getattr(apps, "handlers")` succeeds and `mock.patch` can walk the full dotted path.

---

## What the Checker Validates

The handler_import standard checks **one thing**: does `apps/__init__.py` contain the string `from . import handlers`?

- **Scope:** `AUDIT_SCOPE = "branch_level"` -- one check per branch
- **Pass:** The string `from . import handlers` is found in the file content -- score 100
- **Fail:** The string is missing or the file does not exist -- score 0

---

## Examples

**Good -- explicit handler import present:**
```python
# apps/__init__.py
from . import handlers
from . import modules
```

**Good -- import with trailing comment:**
```python
# apps/__init__.py
from . import handlers  # required for mock.patch resolution
```

**Bad -- empty init:**
```python
# apps/__init__.py
```

**Bad -- modules imported but not handlers:**
```python
# apps/__init__.py
from . import modules
```

---

## Scoring

| Condition | Score |
|-----------|-------|
| `from . import handlers` found in apps/__init__.py | 100 |
| Import missing from apps/__init__.py | 0 |
| apps/__init__.py not found | 0 |
| apps/__init__.py not readable | 0 |
| Bypassed via `.seedgo/bypass.json` | 100 |

Binary pass/fail -- there is no partial credit. Either the import is there or it is not.

---

## How to Fix

Add the import line to `apps/__init__.py`. That is it.

**Before:**
```python
# apps/__init__.py
from . import modules
```

**After:**
```python
# apps/__init__.py
from . import handlers
from . import modules
```

---

## Bypass

If a branch genuinely does not have a `handlers/` subpackage (rare edge case), add a bypass rule in `.seedgo/bypass.json`:

```json
{
  "standard": "handler_import",
  "file": "apps/__init__.py"
}
```

---

## Summary

1. **Every apps/__init__.py needs `from . import handlers`** -- required for mock.patch resolution on Python 3.10
2. **One check per branch** -- scope is `branch_level`
3. **Binary scoring** -- 100 (import present) or 0 (import missing)
4. **Fix is one line** -- add `from . import handlers` to apps/__init__.py
