# =================== AIPass ====================
# Name: engine.py
# Version: 1.1.0
# Description: Hook engine — unified dispatcher for all hook events
# Branch: hooks
# Layer: apps/modules
# Created: 2026-05-18
# Modified: 2026-05-19
# =============================================

"""Hook engine — dispatches hook events to handlers, logs via prax + JSONL."""

import importlib
import json
import os
import subprocess
import time
from pathlib import Path

from aipass.prax.apps.modules.logger import system_logger as logger
from aipass.cli.apps.modules import err_console
from aipass.hooks.apps.handlers.config.loader import find_project_config
from aipass.hooks.apps.handlers.config.diagnostics import log_entry as _log, tail_log

CONSOLE = err_console
BRANCH_ROOT = Path(__file__).resolve().parent.parent.parent


def _run_hook(hook_cmd: str, stdin_data: str, timeout_s: int = 30) -> dict:
    """Run a single hook subprocess, capture output and timing."""
    env = os.environ.copy()
    start = time.monotonic()
    try:
        result = subprocess.run(
            hook_cmd,
            shell=True,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "elapsed_ms": round(elapsed_ms, 1),
        }
    except subprocess.TimeoutExpired:
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.error("[HOOKS] timeout after %ds: %s", timeout_s, hook_cmd)
        return {"exit_code": -1, "stdout": "", "stderr": "TIMEOUT", "elapsed_ms": round(elapsed_ms, 1)}
    except OSError as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.error("[HOOKS] exec error: %s: %s", hook_cmd, exc)
        return {"exit_code": -1, "stdout": "", "stderr": str(exc), "elapsed_ms": round(elapsed_ms, 1)}


def _run_handler(handler_path: str, hook_data: dict) -> dict:
    """Call a handler function directly (no subprocess). Module imports handler."""
    start = time.monotonic()
    try:
        module_path, func_name = handler_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        handler_func = getattr(module, func_name)
        result = handler_func(hook_data)
        elapsed_ms = (time.monotonic() - start) * 1000
        return {
            "exit_code": result.get("exit_code", 0),
            "stdout": result.get("stdout", ""),
            "stderr": "",
            "elapsed_ms": round(elapsed_ms, 1),
        }
    except Exception as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.error("[HOOKS] handler error %s: %s", handler_path, exc)
        return {"exit_code": -1, "stdout": "", "stderr": str(exc), "elapsed_ms": round(elapsed_ms, 1)}


def _matches(matcher: str, value: str) -> bool:
    """Check if a hook's matcher string matches the given value. Empty matcher = always match."""
    if not matcher:
        return True
    return value in matcher.split("|")


def dispatch(event_type: str, stdin_data: str, config: dict) -> str:
    """Core dispatch — run hooks for event, return merged stdout."""
    if not config.get("hooks_enabled", True):
        logger.info("[HOOKS] all hooks disabled")
        _log({"ts": time.time(), "event": event_type, "action": "all_hooks_disabled"})
        return ""

    event_hooks = config.get(event_type, {})
    if not event_hooks:
        _log({"ts": time.time(), "event": event_type, "action": "no_hooks_configured"})
        return ""

    match_value = ""
    parsed = {}
    try:
        parsed = json.loads(stdin_data) if stdin_data.strip() else {}
        match_value = parsed.get("tool_name", "") or parsed.get("compact_type", "") or parsed.get("type", "")
    except json.JSONDecodeError as exc:
        logger.warning("[HOOKS] stdin parse error: %s", exc)

    outputs = []
    total_start = time.monotonic()

    for hook_name, hook_def in event_hooks.items():
        if not hook_def.get("enabled", True):
            logger.info("[HOOKS] %s.%s skipped (disabled)", event_type, hook_name)
            _log({"ts": time.time(), "event": event_type, "hook": hook_name, "action": "skipped_disabled"})
            continue

        handler = hook_def.get("handler", "")
        command = hook_def.get("command", "")
        matcher = hook_def.get("matcher", "")
        if not handler and not command:
            continue

        if matcher and not _matches(matcher, match_value):
            _log(
                {
                    "ts": time.time(),
                    "event": event_type,
                    "hook": hook_name,
                    "action": "skipped_no_match",
                    "matcher": matcher,
                    "value": match_value,
                }
            )
            continue

        if handler:
            result = _run_handler(handler, parsed)
        else:
            hook_timeout = hook_def.get("timeout", 30)
            result = _run_hook(command, stdin_data, timeout_s=hook_timeout)

        logger.info(
            "[HOOKS] %s.%s exit=%d out=%db %dms",
            event_type,
            hook_name,
            result["exit_code"],
            len(result["stdout"]),
            result["elapsed_ms"],
        )
        _log(
            {
                "ts": time.time(),
                "event": event_type,
                "hook": hook_name,
                "exit_code": result["exit_code"],
                "elapsed_ms": result["elapsed_ms"],
                "stdout_len": len(result["stdout"]),
                "stderr_preview": result["stderr"][:200] if result["stderr"] else "",
                "cwd": str(Path.cwd()),
            }
        )

        # Exit code 2: crash vs intentional block
        if result["exit_code"] == 2:
            is_intentional_block = False
            try:
                decision = json.loads(result["stdout"]) if result["stdout"].strip() else {}
                is_intentional_block = decision.get("decision") == "block"
            except (json.JSONDecodeError, AttributeError):
                logger.info("[HOOKS] %s.%s exit=2 stdout not JSON, treating as crash", event_type, hook_name)

            if is_intentional_block:
                total_ms = (time.monotonic() - total_start) * 1000
                logger.warning("[HOOKS] %s BLOCKED by %s (%dms)", event_type, hook_name, total_ms)
                _log(
                    {
                        "ts": time.time(),
                        "event": event_type,
                        "action": "blocked",
                        "hook": hook_name,
                        "total_ms": round(total_ms, 1),
                    }
                )
                return result["stdout"]

            logger.error(
                "[HOOKS] %s.%s CRASHED exit=2: %s",
                event_type,
                hook_name,
                result["stderr"][:200],
            )
            _log(
                {
                    "ts": time.time(),
                    "event": event_type,
                    "hook": hook_name,
                    "action": "crashed",
                    "stderr": result["stderr"][:200],
                }
            )

        if result["stdout"]:
            outputs.append(result["stdout"])

    total_ms = (time.monotonic() - total_start) * 1000
    logger.info("[HOOKS] %s complete: %d hooks %dms", event_type, len(outputs), total_ms)
    _log(
        {
            "ts": time.time(),
            "event": event_type,
            "action": "complete",
            "hooks_run": len(outputs),
            "total_ms": round(total_ms, 1),
        }
    )

    return "\n".join(outputs)


# =============================================================================
# MODULE INTERFACE (drone @hooks routing)
# =============================================================================


def print_introspection():
    """Print module structure — connected handlers."""
    CONSOLE.print("[bold cyan]engine[/bold cyan] Module")
    CONSOLE.print("  Connected Handlers:")
    handlers_root = BRANCH_ROOT / "apps" / "handlers"
    for category_dir in sorted(handlers_root.iterdir()):
        if not category_dir.is_dir() or category_dir.name.startswith("_"):
            continue
        handler_files = [f.name for f in sorted(category_dir.glob("*.py")) if not f.name.startswith("_")]
        if handler_files:
            CONSOLE.print(f"    handlers/{category_dir.name}/ — {', '.join(handler_files)}")


def handle_command(command: str, args: list) -> bool:
    """Route engine commands from drone @hooks."""
    if not args and command in ("engine", ""):
        print_introspection()
        return True

    if command in ("--help", "-h", "help"):
        CONSOLE.print("[bold cyan]engine[/bold cyan] — Hook dispatch engine")
        CONSOLE.print()
        CONSOLE.print("  drone @hooks status    Show hook config for current project")
        CONSOLE.print("  drone @hooks log       Tail recent hook activity")
        return True

    if command == "status":
        config = find_project_config()
        if config is None:
            CONSOLE.print("No .aipass/hooks.json found for current project")
        else:
            enabled = config.get("hooks_enabled", True)
            CONSOLE.print(f"Hooks enabled: {enabled}")
            for event_type, hooks in config.items():
                if event_type.startswith("_") or event_type == "hooks_enabled":
                    continue
                if isinstance(hooks, dict):
                    active = sum(1 for h in hooks.values() if isinstance(h, dict) and h.get("enabled", True))
                    total = sum(1 for h in hooks.values() if isinstance(h, dict))
                    CONSOLE.print(f"  {event_type}: {active}/{total} hooks active")
        return True

    if command == "log":
        lines = tail_log(20)
        if not lines:
            CONSOLE.print("No engine log found")
        else:
            for line in lines:
                CONSOLE.print(line)
        return True

    return False
