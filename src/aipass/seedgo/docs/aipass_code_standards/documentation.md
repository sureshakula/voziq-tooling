# Documentation Standards
**Status:** v1.0 - Verified against actual codebase
**Date:** 2025-11-13

---

## File Header Structure

Every Python file follows this header pattern:

```python
#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: filename.py - Brief Description
# Date: YYYY-MM-DD
# Version: X.Y.Z
# Category: branch_name or branch_name/handlers
#
# CHANGELOG (Max 5 entries):
#   - vX.Y.Z (YYYY-MM-DD): Change description
#
# CODE STANDARDS:
#   - Error handling: Use error handler system
# =============================================

"""
Module Title

Brief description of module purpose.
Key functionality:
- Feature 1
- Feature 2
- Feature 3
"""
```

**NOTE:** Some files also include `# -*- coding: utf-8 -*-` after the shebang line (seen in cortex files). This is optional but valid.

---

## Shebang Line

```python
#!/home/aipass/.venv/bin/python3
# -*- coding: utf-8 -*-  # Optional - seen in some cortex files
```

**WHY:** Points to AIPass venv, ensuring correct Python environment and dependencies.

**EXCEPTION - MEMORY_BANK:**
```python
#!/home/aipass/MEMORY_BANK/.venv/bin/python3
```
MEMORY_BANK uses its own isolated virtual environment at `/home/aipass/MEMORY_BANK/.venv`.

**IMPORTANT - EXECUTE PERMISSIONS:**

After creating a Python file, make it executable:
```bash
chmod +x /path/to/file.py
```

**WHY:** The shebang line only works if the file has execute permissions. Without `chmod +x`, you'll get "Permission denied" errors when trying to run the file directly.

**When to set:**
- Immediately after creating any new Python module
- After using Write tool to create files
- Verify with: `ls -la file.py` (should show `-rwxr-xr-x`)

**Fix all modules at once:**
```bash
# Make all Python files in a directory executable
chmod +x /path/to/modules/*.py
```

**VERIFIED IN:**
- `/home/aipass/aipass_core/cortex/apps/modules/create_branch.py`
- `/home/aipass/aipass_core/cortex/apps/handlers/branch/file_ops.py`
- `/home/aipass/seed/apps/handlers/domain1/ops.py`

---

## META Block

**Standard format:**
```python
# ===================AIPASS====================
# META DATA HEADER
# Name: create_branch.py - Create New AIPass Branch
# Date: 2025-11-10
# Version: 2.1.0
# Category: cortex
#
# CHANGELOG (Max 5 entries):
#   - v2.1.0 (2025-11-10): Added template placeholder system
#   - v2.0.0 (2025-11-08): Complete rewrite with handler architecture
#
# CODE STANDARDS:
#   - Error handling: Use error handler system (apps/handlers/error/)
# =============================================
```

**Fields:**
- **Name:** Filename + dash-separated description
- **Date:** Creation date (YYYY-MM-DD)
- **Version:** Semantic versioning (major.minor.patch)
- **Category:** Branch name (e.g., `cortex`) or `cortex/handlers` for handlers
- **CHANGELOG:** Max 5 entries - version, date, what changed
- **CODE STANDARDS:** Reference to error handler (standard across all files)

**WHY META blocks:**
- **AI scannable:** Agents can extract metadata without parsing code
- **Version tracking:** Know what version you're looking at immediately
- **History at a glance:** Recent changes visible without git log
- **Standardization:** Every file has same metadata structure

**Handler example:**
```python
# Category: cortex/handlers
# Category: seed/handlers/domain1
```

**Module example:**
```python
# Category: cortex
# Category: seed/test
```

**VERIFIED IN:**
- `/home/aipass/aipass_core/cortex/apps/modules/create_branch.py` (Category: cortex)
- `/home/aipass/aipass_core/cortex/apps/handlers/branch/file_ops.py` (Category: cortex/handlers)
- `/home/aipass/seed/apps/modules/test_cli_errors.py` (Category: seed/test)
- `/home/aipass/seed/apps/handlers/domain1/ops.py` (Category: seed/handlers/domain1)

---

## Module-Level Docstrings

**Pattern:** Triple-quoted string immediately after META block

```python
"""
Module Title

Brief description of module purpose.
Longer explanation if needed.

Key functionality:
- Feature 1
- Feature 2
- Feature 3

May include usage examples or workflow notes.
"""
```

**Examples:**

**Module:**
```python
"""
Create Branch Module

Creates a new AIPass branch from template with all necessary structure.
Workflow: template copy, file renaming, module migration, branch registration
"""
```

**Handler:**
```python
"""
File Operations Handler

Functions for file and directory operations:
- File renaming with placeholder replacement
- Directory renaming
- Template content copying
- Module migration
- Memory file management
"""
```

**With usage example (verified from actual code):**
```python
"""
Error Handler Decorators

Decorators for automatic error handling, logging, and result formatting.

Usage:
    from cortex.apps.handlers.error_handler import track_operation

    @track_operation
    def my_function(arg):
        # Just write business logic
        return result
"""
```
*From: `/home/aipass/aipass_core/cortex/apps/handlers/error/decorators.py`*

**WHY:** First thing you see after metadata. Tells you what the file does and key features. No need to read code to understand purpose.

---

## Function Docstrings

**Pattern:** Google-style with Args/Returns/Raises

```python
def function_name(arg1: Type, arg2: Type) -> ReturnType:
    """
    Brief one-line description

    Longer description if needed (optional).
    Can span multiple lines for complex functions.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    Raises:
        ExceptionType: When this exception occurs (optional)
    """
```

**Real examples (verified from actual code):**

```python
def find_existing_memory_files(target_dir: Path, branch_name: str) -> Dict[str, Path]:
    """
    Find existing memory files with any naming convention (hyphens, underscores, etc.)

    Args:
        target_dir: Path to branch directory
        branch_name: Branch name to match against

    Returns:
        Dict mapping file types (main, local, observations, ai_mail, id) to Path objects
    """
```
*From: `/home/aipass/aipass_core/cortex/apps/handlers/branch/file_ops.py`*

```python
def create_operation(name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Demonstrate domain-specific business logic

    [SHOWROOM] This would contain actual implementation.
    Shows structure, typing, documentation patterns.

    Args:
        name: Thing name
        data: Thing configuration

    Returns:
        Operation result dict with success/error/details
    """
```
*From: `/home/aipass/seed/apps/handlers/domain1/ops.py`*

**WHY Google-style:**
- **Readable:** Args/Returns sections visually separate
- **Parseable:** Tools can extract parameter docs automatically
- **Standard:** Widely used, AI understands it well

**When to skip Raises:** If function doesn't raise exceptions or uses decorators for error handling.

---

## Type Hints

**Rule:** ALL function signatures have type hints

```python
# Standard types
def function(path: Path, name: str, count: int) -> bool:

# Optional types
def function(data: Optional[str]) -> Optional[Path]:

# Generic types
def function(data: Dict[str, Any]) -> List[str]:

# Tuple returns
def function() -> Tuple[List[str], List[str]]:

# Modern union (Python 3.10+)
def validate_path(path: Path) -> tuple[bool, str | None]:
```

**Complex example:**
```python
def copy_template_contents(
    template_dir: Path,
    target_dir: Path,
    replacements: Dict[str, str],
    branch_name: str,
    exclude_patterns: List[str],
    file_renames: Dict[str, str],
    allowed_placeholders: set = None
) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
```

**WHY:**
- **AI comprehension:** Knows what types to expect/return
- **IDE support:** Autocomplete, error detection
- **Self-documenting:** Function signature tells you data shapes
- **Error prevention:** Catch type mismatches before runtime

---

## Section Separators

**Pattern:** Comment blocks to organize code sections

```python
# =============================================================================
# SECTION NAME
# =============================================================================
```

**Common sections (verified in actual code):**
- `CONSTANTS`
- `FILE DISCOVERY AND MATCHING`
- `HELPER FUNCTIONS`
- `CORE WORKFLOW`
- `MODULE INTERFACE`
- `FILE OPERATIONS`
- `METADATA EXTRACTION`
- `STANDALONE EXECUTION`

**Example (verified from create_branch.py):**
```python
# =============================================================================
# CONSTANTS
# =============================================================================

# Get template directory
AIPASS_ROOT = Path.home() / "aipass_core"
TEMPLATE_DIR = AIPASS_ROOT / "cortex" / "templates" / "branch_template"

# Files to exclude from template copy
EXCLUDE_PATTERNS = [
    "setup_instructions",
    "new_branch_setup.py",
    "upgrade_branch.py",
    ".git",
    "__pycache__",
]
```

**Example (verified from file_ops.py):**
```python
# =============================================================================
# FILE DISCOVERY AND MATCHING
# =============================================================================

def find_existing_memory_files(target_dir: Path, branch_name: str) -> Dict[str, Path]:
    """Find existing memory files with any naming convention"""
```

**WHY:**
- **Quick navigation:** Scan file, find section instantly
- **Logical grouping:** Related functions together
- **AI parsing:** Clear boundaries for context extraction

---

## Inline Comments

**When to use:**
1. Clarifying non-obvious logic (what and why)
2. Important warnings or gotchas
3. Algorithm steps in complex operations
4. Protection rules or edge cases

**Patterns:**

```python
# Single-line explanation above code
backup_branch()

# Inline explanation for single statement
result = complex_operation()  # Extracts metadata from template

# Multi-step process markers
# Step 1: Backup branch
backup()

# Step 2: Remove from registry
remove()
```

**Examples from actual codebase:**

```python
# Memory file suffixes to check (JSON format)
memory_suffixes = [".json", ".local.json", ".observations.json", ".ai_mail.json", ".id.json"]

# Normalize to check if it matches branch name
prefix_normalized = prefix.replace("-", "_").upper()
```
*From: `/home/aipass/aipass_core/cortex/apps/handlers/branch/file_ops.py`*

Note: The PROTECTION RULE example is a pattern that may exist in other files but was not verified in the sample files examined.

**When NOT to use:**
- Obvious code (don't narrate what's already clear)
- Repeating what docstring says
- Commenting out old code (delete it instead)

**WHY:**
- **Context for future you:** Why did I do it this way?
- **Warning flags:** PROTECTION RULE stands out
- **Algorithm clarity:** Step markers show workflow

---

## Import Organization

**Standard pattern (verified from actual code):**

```python
#!/home/aipass/.venv/bin/python3
# -*- coding: utf-8 -*-

# [META BLOCK]

"""Module docstring"""

# Infrastructure setup (if needed)
import sys
from pathlib import Path
AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))

# Standard library imports
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Prax logger
from prax.apps.modules.logger import system_logger as logger

# Internal handler imports
from cortex.apps.handlers.json import json_handler
from cortex.apps.handlers.branch import file_ops
```

**VERIFIED IN:**
- `/home/aipass/aipass_core/cortex/apps/modules/create_branch.py`
- `/home/aipass/aipass_core/cortex/apps/handlers/branch/file_ops.py`
- `/home/aipass/seed/apps/modules/test_cli_errors.py`

**Import sections (in order):**
1. Infrastructure setup (AIPASS_ROOT, sys.path) - if needed
2. Standard library imports
3. Prax logger (always from prax.apps.modules.logger)
4. Internal/local handler imports

**WHY this order:**
- **Infrastructure first:** Must run before other imports can work
- **Standard library grouped:** Easy to see external dependencies
- **Prax consistent:** Always `from prax.apps.modules.logger import system_logger as logger`
- **Internal last:** After all external dependencies resolved

**NOTE:** Some modules use try/except blocks to gracefully handle missing handlers (see create_branch.py for example).

---

## Constants

**Pattern:** ALL_CAPS names with inline comments

```python
# =============================================================================
# CONSTANTS
# =============================================================================

# Get template directory
AIPASS_ROOT = Path.home() / "aipass_core"
TEMPLATE_DIR = AIPASS_ROOT / "cortex" / "templates" / "branch_template"

# Files to exclude from template copy
EXCLUDE_PATTERNS = [
    "setup_instructions",
    "new_branch_setup.py",
    ".git",
    "__pycache__",
]

# Files to rename after copying
FILE_RENAMES = {
    "LOCAL.json": "{BRANCHNAME}.local.json",
    "OBSERVATIONS.json": "{BRANCHNAME}.observations.json",
}
```

**WHY:**
- **ALL_CAPS signals:** This is configuration, not a variable
- **Comments explain purpose:** Not just WHAT, but WHY we need it
- **Grouped together:** All config in one place, easy to modify

---

## Summary: Documentation Hierarchy

**File level (top to bottom):**
1. Shebang 
2. META block (metadata)
3. Module docstring (purpose)
4. Imports (organized)
5. Constants (configuration)
6. Section separators + functions (implementation)

**Function level:**
- Type hints (signature)
- Docstring (Args/Returns/Raises)
- Inline comments (clarification only)

**WHY this matters:**
- **AI scannable:** Can extract metadata/purpose without reading all code
- **Human scannable:** Read top to bottom, understand file in 30 seconds
- **Consistent:** Same structure everywhere, know where to look

---

## Quick Reference

| Element | Pattern | Required? |
|---------|---------|-----------|
| Shebang | `#!/home/aipass/.venv/bin/python3` | Yes |
| META Block | AIPASS format | **Yes** |
| Module Docstring | Triple-quoted | **Yes** |
| Function Docstring | Google-style | **Yes** |
| Type Hints | Full typing | **Yes** |
| Section Separators | `# ===...===` | Recommended |
| Inline Comments | Clarification only | As needed |
| Import Organization | Infrastructure → Standard → Prax → Internal | Yes |

**The standard:** If Cortex or Seed does it, that's the pattern. These aren't theoretical - verified against actual production code in:
- `/home/aipass/aipass_core/cortex/apps/`
- `/home/aipass/seed/apps/`

---

## Verification Notes

**Files examined for truth-checking (2025-11-13):**
- `/home/aipass/aipass_core/cortex/apps/modules/create_branch.py`
- `/home/aipass/aipass_core/cortex/apps/handlers/branch/file_ops.py`
- `/home/aipass/aipass_core/cortex/apps/handlers/error/decorators.py`
- `/home/aipass/seed/apps/modules/test_cli_errors.py`
- `/home/aipass/seed/apps/handlers/domain1/ops.py`

All patterns, examples, and file paths verified against actual code.

## Comments

#@comments:2025-11-13:claude: All examples now include source file references for verification
#@comments:2025-11-13:claude: Updated encoding line as optional (present in cortex, optional in seed)
#@comments:2025-11-13:claude: Corrected memory_suffixes list to include .ai_mail.json and .id.json
