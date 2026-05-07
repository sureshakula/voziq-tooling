#!/usr/bin/env python3
"""
Shared hook execution logger for AIPass.

Every hook imports this and calls log_fire() once. The log file is a JSONL
append-only stream at /tmp/aipass_hook_log.jsonl — one line per hook invocation.

Usage in any hook script:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from hook_log import log_fire

    # At the end of main():
    log_fire("UserPromptSubmit", "provider", __file__, elapsed_ms=12.3, output_bytes=21400)
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

_LOG_FILE = Path("/tmp/aipass_hook_log.jsonl")
_VERSION = "1.0.0"


def log_fire(
    event: str,
    source: str,
    script: str,
    *,
    elapsed_ms: float = 0.0,
    output_bytes: int = 0,
    exit_code: int = 0,
    tool: str = "",
    extra: dict | None = None,
) -> None:
    """Append one structured log entry. Never raises."""
    try:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "v": _VERSION,
            "event": event,
            "source": source,
            "script": Path(script).name,
            "script_path": str(script),
            "cwd": os.getcwd(),
            "session": os.environ.get("CLAUDE_CODE_SESSION_ID", ""),
            "tool": tool,
            "exit_code": exit_code,
            "elapsed_ms": round(elapsed_ms, 1),
            "output_bytes": output_bytes,
        }
        if extra:
            entry.update(extra)
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


class HookTimer:
    """Context manager for timing hook execution."""

    def __init__(self) -> None:
        self.start: float = 0.0
        self.elapsed_ms: float = 0.0

    def __enter__(self) -> "HookTimer":
        self.start = time.monotonic()
        return self

    def __exit__(self, *_: object) -> None:
        self.elapsed_ms = (time.monotonic() - self.start) * 1000.0


def run_and_log(
    event: str,
    source: str,
    script: str,
    fn: "callable",  # noqa: F821
) -> None:
    """Run a hook function, capture stdout, time it, log the result.

    Usage in __main__ block (4 lines total):
        import sys
        sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
        from hook_log import run_and_log
        run_and_log("UserPromptSubmit", "provider", __file__, main)
    """
    import io
    import sys as _sys

    buf = io.StringIO()
    orig = _sys.stdout
    _sys.stdout = buf

    _exit_code = 0
    try:
        with HookTimer() as t:
            fn()
    except SystemExit as e:
        _exit_code = e.code if isinstance(e.code, int) else 0
    finally:
        _sys.stdout = orig

    output = buf.getvalue()
    if output:
        print(output, end="")

    log_fire(
        event,
        source,
        script,
        elapsed_ms=t.elapsed_ms,
        output_bytes=len(output.encode("utf-8")),
        exit_code=_exit_code,
    )
    _sys.exit(_exit_code)
