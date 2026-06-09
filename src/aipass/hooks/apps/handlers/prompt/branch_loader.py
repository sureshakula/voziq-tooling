# =================== AIPass ====================
# Name: branch_loader.py
# Version: 1.0.0
# Description: Loads branch-specific prompt + private integrations (UserPromptSubmit)
# Branch: hooks
# Layer: apps/handlers/prompt
# Created: 2026-05-22
# Modified: 2026-05-22
# =============================================

"""Loads .aipass/aipass_local_prompt.md and private integration prompts for injection."""

from pathlib import Path

from aipass.hooks.apps.sound import speak
from aipass.prax.apps.modules.logger import system_logger as logger


def _find_branch_root(cwd: str) -> Path | None:
    """Walk up from CWD looking for .trinity/ or apps/ — stop at repo root."""
    search = Path(cwd).resolve()
    while search.parent != search:
        if (search / ".trinity").is_dir() or (search / "apps").is_dir():
            return search
        if (search / "pyproject.toml").exists() or (search / ".git").is_dir():
            return None
        search = search.parent
    return None


def handle(hook_data: dict) -> dict:
    """Load branch prompt and private integration prompts."""
    speak("branch prompt")

    try:
        import importlib

        cadence = importlib.import_module("aipass.hooks.apps.modules.cadence")
        if not cadence.should_fire("branch"):
            return {"stdout": "", "exit_code": 0}
    except Exception as exc:
        logger.info("[HOOKS] branch_loader: cadence check failed, firing anyway: %s", exc)

    try:
        cwd = hook_data.get("cwd", "") or str(Path.cwd())
        branch_root = _find_branch_root(cwd)
        if not branch_root:
            return {"stdout": "", "exit_code": 0}

        parts: list[str] = []

        prompt_file = branch_root / ".aipass" / "aipass_local_prompt.md"
        if prompt_file.exists():
            content = prompt_file.read_text(encoding="utf-8").strip()
            branch_name = branch_root.name.upper()
            parts.append(f"# Branch Context: {branch_name}\n<!-- Source: {prompt_file} -->\n{content}")

        integrations_dir = branch_root / "apps" / "integrations"
        if integrations_dir.is_dir():
            for prompt in sorted(integrations_dir.glob("*/private_prompt.md")):
                parts.append(prompt.read_text(encoding="utf-8").strip())

        if not parts:
            return {"stdout": "", "exit_code": 0}

        return {"stdout": "\n".join(parts), "exit_code": 0}

    except Exception as exc:
        logger.info("[HOOKS] branch_loader: unexpected error: %s", exc)
        return {"stdout": "", "exit_code": 0}
