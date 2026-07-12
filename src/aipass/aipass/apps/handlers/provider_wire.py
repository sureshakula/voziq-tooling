# =================== AIPass ====================
# Name: provider_wire.py
# Description: Auto-wire provider settings from manifest into user config
# Version: 1.0.0
# Created: 2026-07-11
# Modified: 2026-07-11
# =============================================

"""provider_wire — auto-wire provider settings.

Implements the additive merge of manifest into ~/.claude/settings.json.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from aipass.aipass.apps.handlers.json import json_handler

# =============================================================================
# HOOK & ENV DESCRIPTIONS
# =============================================================================

HOOK_DESCRIPTIONS: Dict[str, str] = {
    "pre_edit_gate.py": "blocks edits outside agent's branch",
    "subagent_stop_gate.py": "validates agent output on exit",
    "auto_fix_diagnostics.py": "auto-fixes lint issues after edits",
    "global_prompt_loader.py": "injects branch context on each turn",
    "identity_injector.py": "injects agent identity on each turn",
    "email_notification.py": "notifies on incoming agent mail",
    "branch_prompt_loader.py": "loads branch-specific prompts",
    "pre_compact.py": "saves state before context compaction",
}

ENV_DESCRIPTIONS: Dict[str, str] = {
    "AIPASS_HOME": "tells agents where AIPass lives",
    "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "prevents conflict with .trinity/ memory system",
}


# =============================================================================
# AUTO-WIRE
# =============================================================================


def auto_wire_provider(manifest_path: Path, interactive: bool = True) -> List[str]:
    """Auto-wire provider settings from manifest into ~/.claude/settings.json.

    Additive merge only — never removes or overwrites existing keys/values.
    Returns list of action descriptions (for logging/display).
    """
    actions: List[str] = []

    manifest = json_handler.load_path(manifest_path)
    if manifest is None:
        return actions
    claude_section = manifest.get("cli", {}).get("claude", {})
    if not claude_section:
        return actions

    settings_path = Path.home() / ".claude" / "settings.json"
    if settings_path.exists():
        settings = json_handler.load_path(settings_path) or {}
    else:
        settings = {}

    if settings_path.exists():
        date_stamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        backup_path = settings_path.with_suffix(f".json.bak.{date_stamp}")
        shutil.copy2(settings_path, backup_path)
        actions.append(f"Backed up settings to {backup_path.name}")

    manifest_hooks = claude_section.get("hooks", [])

    for hook in manifest_hooks:
        command = hook.get("command", "")
        event = hook.get("event", "")
        if not command or not event:
            continue

        if "hooks" not in settings:
            settings["hooks"] = {}
        if event not in settings["hooks"]:
            settings["hooks"][event] = []
        event_hooks = settings["hooks"][event]
        if not isinstance(event_hooks, list):
            event_hooks = [event_hooks]
            settings["hooks"][event] = event_hooks

        hook_matcher = hook.get("matcher", "")
        already_wired = any(
            isinstance(h, dict) and command in json.dumps(h) and h.get("matcher", "") == hook_matcher
            for h in event_hooks
        )
        if not already_wired:
            cmd_entry: Dict[str, object] = {
                "type": "command",
                "command": command,
            }
            if hook.get("timeout"):
                cmd_entry["timeout"] = hook["timeout"]
            wrapper: Dict[str, object] = {}
            if hook.get("matcher"):
                wrapper["matcher"] = hook["matcher"]
            wrapper["hooks"] = [cmd_entry]
            event_hooks.append(wrapper)
            label = command.rsplit(" ", 1)[-1] if " " in command else command
            actions.append(f"Wired hook {label} -> {event}")

    manifest_env = claude_section.get("env", {})
    if manifest_env:
        if "env" not in settings:
            settings["env"] = {}
        repo_root = str(manifest_path.parent.parent)
        project_root = str(Path.cwd())
        for key, value in manifest_env.items():
            if key not in settings["env"]:
                resolved = value.replace("{{REPO_ROOT}}", repo_root)
                resolved = resolved.replace("{{PROJECT_ROOT}}", project_root)
                settings["env"][key] = resolved
                actions.append(f"Set env {key}={resolved}")

    manifest_perms = claude_section.get("permissions", {})
    manifest_deny = manifest_perms.get("deny", [])
    manifest_ask = manifest_perms.get("ask", [])

    if manifest_deny or manifest_ask:
        if "permissions" not in settings:
            settings["permissions"] = {}
        if "deny" not in settings["permissions"]:
            settings["permissions"]["deny"] = []
        if "ask" not in settings["permissions"]:
            settings["permissions"]["ask"] = []

        existing_deny = set(settings["permissions"]["deny"])
        for rule in manifest_deny:
            if rule not in existing_deny:
                settings["permissions"]["deny"].append(rule)
                actions.append(f"Added deny rule: {rule}")

        existing_ask = set(settings["permissions"]["ask"])
        for rule in manifest_ask:
            if rule not in existing_ask:
                settings["permissions"]["ask"].append(rule)
                actions.append(f"Added ask rule: {rule}")

    json_handler.save_path(settings_path, settings)
    actions.append("Updated ~/.claude/settings.json")

    json_handler.log_operation("auto_wire_provider", {"actions": len(actions)})
    return actions
