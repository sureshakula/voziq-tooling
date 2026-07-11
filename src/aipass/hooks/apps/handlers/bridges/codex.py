# =================== AIPass ====================
# Name: codex.py
# Version: 1.0.0
# Description: Codex bridge — entry point for provider hook settings
# Branch: hooks
# Layer: apps/handlers/bridges
# Created: 2026-07-10
# Modified: 2026-07-10
# =============================================

"""Codex bridge.

Thin entry point called from .codex/hooks.json hook entries.
Normalizes Codex's stdin/stdout format and calls the engine.

Codex protocol differences from Claude Code:
  - stdin: uses 'input' instead of 'tool_input' for tool parameters
  - stdout: wraps output in hookSpecificOutput envelope
  - blocking: permissionDecision + permissionDecisionReason (not exit code 2)

Supports two forms:
  codex.py EventType          — dispatch ALL enabled hooks for that event
  codex.py EventType:hook_name — dispatch ONLY that one hook (separate output)
"""

import json
import sys

from aipass.hooks.apps.modules.engine import dispatch
from aipass.hooks.apps.handlers.config.loader import find_project_config
from aipass.prax.apps.modules.logger import system_logger as logger


def _normalize_stdin(stdin_data: str) -> str:
    """Remap Codex field names to engine-expected names."""
    if not stdin_data.strip():
        return stdin_data
    try:
        parsed = json.loads(stdin_data)
        if "input" in parsed and "tool_input" not in parsed:
            parsed["tool_input"] = parsed.pop("input")
        return json.dumps(parsed)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.info("[HOOKS:codex] stdin normalization failed: %s", exc)
        return stdin_data


def _wrap_output(event_type: str, output: str, exit_code: int) -> str:
    """Wrap engine output into Codex hookSpecificOutput envelope."""
    if exit_code == 2:
        try:
            decision = json.loads(output)
            if decision.get("decision") == "block":
                reason = decision.get("reason", "Blocked by AIPass hook")
                return json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": event_type,
                            "permissionDecision": "deny",
                            "permissionDecisionReason": reason,
                        },
                        "systemMessage": reason,
                    }
                )
        except (json.JSONDecodeError, TypeError, AttributeError) as exc:
            logger.info("[HOOKS:codex] block output parse failed: %s", exc)

    if not output:
        return json.dumps({})

    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": event_type,
                "additionalContext": output,
            },
        }
    )


def main() -> None:
    """Entry point — receive event type from Codex, dispatch via engine."""
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: codex.py <EventType> or codex.py <EventType:hook_name>\n")
        sys.exit(1)

    arg = sys.argv[1]
    hook_filter = None
    if ":" in arg:
        event_type, hook_filter = arg.split(":", 1)
    else:
        event_type = arg

    stdin_data = ""
    if not sys.stdin.isatty():
        stdin_data = sys.stdin.read()

    normalized = _normalize_stdin(stdin_data)

    config = find_project_config()
    if config is None:
        config = {"hooks_enabled": True}
        logger.info("[HOOKS:codex] no project config found, using defaults")

    if hook_filter:
        full_config: dict = config
        hook_def = full_config.get(event_type, {}).get(hook_filter, {})
        config = {"hooks_enabled": True, event_type: {hook_filter: hook_def}}

    output, exit_code = dispatch(event_type, normalized, config)

    wrapped = _wrap_output(event_type, output, exit_code)
    sys.stdout.write(wrapped)


if __name__ == "__main__":
    main()
