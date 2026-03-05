"""
Seed Handlers - Implementation Layer

Handlers contain ALL business logic.
Organized by domain for clarity and transportability.

Security: Cross-branch handler imports are blocked. External branches must use
the module API (seed.apps.modules.*) instead.
"""

import inspect
from pathlib import Path

MY_BRANCH = "seed"


def _find_real_caller():
    """
    Walk the stack to find the actual file that triggered this import.

    Skips:
    - This file (handlers/__init__.py)
    - Python's importlib internals
    - Frozen modules

    Returns tuple: (file_path, import_line) or (None, None)
    """
    stack = inspect.stack()
    this_file = str(Path(__file__).resolve())

    for frame_info in stack:
        filename = frame_info.filename

        # Skip this file
        if this_file in str(Path(filename).resolve()):
            continue

        # Skip Python internals
        if filename.startswith("<") or "importlib" in filename:
            continue

        # Found a real file - try to get the import line
        import_line = None
        if frame_info.code_context:
            import_line = frame_info.code_context[0].strip()

        return str(Path(filename).resolve()), import_line

    return None, None


def _extract_branch_name(filepath: str) -> str:
    """Extract branch name from a file path."""
    parts = filepath.split("/")
    for i, part in enumerate(parts):
        # Seed lives at /home/aipass/seed/ (NOT in aipass_core)
        if part == "seed":
            return "seed"
        # Check for other branches in aipass_core, MEMORY_BANK, Nexus
        if part in ("aipass_core", "MEMORY_BANK", "Nexus"):
            if i + 1 < len(parts):
                return parts[i + 1]
    return "unknown"


def _guard_branch_access():
    """
    Block cross-branch handler imports.

    Only code from within the 'seed' branch can import these handlers.
    External branches must use seed.apps.modules instead.
    """
    caller_file, import_line = _find_real_caller()

    # DEBUG: Print what we found
    import os
    if os.environ.get("AIPASS_DEBUG_GUARD"):
        import sys
        print(f"[GUARD DEBUG] caller_file = {caller_file}", file=sys.stderr)
        print(f"[GUARD DEBUG] import_line = {import_line}", file=sys.stderr)

    if caller_file is None:
        # Can't determine caller from real files
        # Check if we're being run from command line (external)
        # by looking at the raw stack for <string> or <stdin>
        stack = inspect.stack()
        for frame in stack:
            if frame.filename in ("<string>", "<stdin>"):
                # Try to get the import line from the frame
                target_line = "unknown"
                if frame.code_context:
                    target_line = frame.code_context[0].strip()
                raise ImportError(
                    f"\n{'='*60}\n"
                    f"ACCESS DENIED: Cross-branch handler import blocked\n"
                    f"{'='*60}\n"
                    f"  Caller:  interactive/script\n"
                    f"  Blocked: {target_line}\n"
                    f"\n"
                    f"  Handlers are internal to their branch.\n"
                    f"  Use the module API instead:\n"
                    f"    from {MY_BRANCH}.apps.modules.<module> import <function>\n"
                    f"\n"
                    f"  Example:\n"
                    f"    from {MY_BRANCH}.apps.modules.logger import logger\n"
                    f"\n"
                    f"  For full standards guide:\n"
                    f"    drone @seed handlers\n"
                    f"{'='*60}"
                )
        return  # Allow if truly can't determine

    # Check if caller is from our branch
    # Seed lives at /home/aipass/seed/ (NOT in aipass_core)
    if "/seed/" in caller_file:
        return  # Same branch, allowed

    # External caller - block access
    caller_branch = _extract_branch_name(caller_file)
    caller_filename = Path(caller_file).name
    blocked_import = import_line if import_line else "unknown"

    raise ImportError(
        f"\n{'='*60}\n"
        f"ACCESS DENIED: Cross-branch handler import blocked\n"
        f"{'='*60}\n"
        f"  Caller branch: {caller_branch}\n"
        f"  Caller file:   {caller_filename}\n"
        f"  Blocked:       {blocked_import}\n"
        f"\n"
        f"  Handlers are internal to their branch.\n"
        f"  Use the module API instead:\n"
        f"    from {MY_BRANCH}.apps.modules.<module> import <function>\n"
        f"\n"
        f"  Example:\n"
        f"    from {MY_BRANCH}.apps.modules.logger import logger\n"
        f"\n"
        f"  For full standards guide:\n"
        f"    drone @seed handlers\n"
        f"{'='*60}"
    )


# Run guard at import time
_guard_branch_access()
