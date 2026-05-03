# =================== AIPass ====================
# Name: bootstrap.py
# Description: Init handler — bootstrap an AIPass project in any directory
# Version: 2.0.0
# Created: 2026-03-14
# Modified: 2026-04-22
# =============================================

"""
Init Bootstrap Handler - PRIVATE implementation

Business logic for `aipass init`. Creates the project scaffold:
   1. {NAME}_REGISTRY.json            — project registry with UUID
   2. .aipass/aipass_global_prompt.md  — global prompt (injected every turn)
   3. CLAUDE.md                       — project prompt (Claude Code reads this)
   4. AGENTS.md                       — Codex equivalent of CLAUDE.md
   5. GEMINI.md                       — Gemini equivalent of CLAUDE.md
   6. README.md                       — getting started guide
   7. STATUS.local.md                 — project status
   8. .gitignore                      — standard AIPass ignores
   9. .claude/settings.json           — Claude Code hooks configuration
  10. src/                            — directory where agents live
  11. .ai_mail.local/inbox.json       — empty project mailbox

Projects are NOT citizens — no .trinity/ directory. Identity lives in the
registry JSON. Init is re-runnable: existing files are skipped, not errors.

RULES:
  - Pure Python only (no module/prax/cli imports)
  - Returns dict, raises exceptions on errors
  - No hardcoded paths
"""

import importlib.util
import json
import logging
import re
import shutil
import uuid
from datetime import date
from pathlib import Path

from aipass.cli.apps.handlers.init import scaffold_content as sc

logger = logging.getLogger(__name__)

ENFORCEMENT_HOOKS = [
    "auto_fix_diagnostics.py",
    "pre_edit_gate.py",
    "subagent_stop_gate.py",
    "pre_compact.py",
]

INJECTOR_HOOKS = [
    "branch_prompt_loader.py",
    "email_notification.py",
    "identity_injector.py",
]

HOOKS_TO_SHIP = ENFORCEMENT_HOOKS + INJECTOR_HOOKS

HOOK_EVENTS: dict[str, str] = {
    "auto_fix_diagnostics.py": "PostToolUse",
    "pre_edit_gate.py": "PreToolUse",
    "subagent_stop_gate.py": "Stop",
    "pre_compact.py": "PreCompact",
    "branch_prompt_loader.py": "UserPromptSubmit",
    "email_notification.py": "UserPromptSubmit",
    "identity_injector.py": "UserPromptSubmit",
}


def _ship_hooks(aipass_home: str, target: Path) -> list[str]:
    """Copy enforcement + injector hooks from AIPass install to target project.

    Copies each hook file to {target}/.claude/hooks/. Looks for hooks in two
    locations (first match wins):
      1. {aipass_home}/.claude/hooks/  — dev install (git clone)
      2. aipass/_hooks/                — pip install (wheel-bundled)

    Skips audio hooks. Overwrites existing files only if source content
    differs (idempotent re-sync). Returns list of files written.
    """
    source_dir = Path(aipass_home) / ".claude" / "hooks"
    if not source_dir.is_dir():
        # Fallback: pip install bundles hooks at aipass/_hooks/ inside the package
        package_hooks = Path(__file__).resolve().parents[4] / "_hooks"
        if package_hooks.is_dir():
            source_dir = package_hooks
        else:
            logger.info("No hooks directory at %s or %s — skipping", source_dir, package_hooks)
            return []

    dest_dir = target / ".claude" / "hooks"
    dest_dir.mkdir(parents=True, exist_ok=True)
    shipped: list[str] = []

    for hook_name in HOOKS_TO_SHIP:
        src = source_dir / hook_name
        dst = dest_dir / hook_name
        if not src.exists():
            logger.info("Hook %s not found at %s — skipping", hook_name, src)
            continue
        src_content = src.read_bytes()
        if dst.exists() and dst.read_bytes() == src_content:
            continue
        shutil.copy2(src, dst)
        shipped.append(str(dst))

    return shipped


def _sanitize_name(raw: str) -> str:
    """Sanitize a project name for use in filenames.

    Replaces non-alphanumeric characters (except underscore/hyphen) with
    underscores and strips leading/trailing underscores.
    """
    return re.sub(r"[^A-Z0-9_-]", "_", raw.upper()).strip("_")


def _detect_aipass_home() -> str | None:
    """Detect the AIPass installation root from the aipass package location.

    Returns the parent of the src/ directory (the repo root).
    Returns None if detection fails.
    """
    try:
        spec = importlib.util.find_spec("aipass")
        if spec and spec.origin:
            # aipass/__init__.py lives at src/aipass/__init__.py
            # parent = src/aipass/, parent.parent = src/, parent.parent.parent = AIPass root
            return str(Path(spec.origin).resolve().parent.parent.parent)
    except Exception as exc:
        logger.info("AIPASS_HOME detection skipped: %s", exc)
    return None


def _claude_settings(aipass_home: str | None = None) -> str:
    """Generate .claude/settings.json — hooks for prompt injection + enforcement.

    Wires all AIPass hooks into their respective event types:
    - UserPromptSubmit: global/local prompt injection + branch_prompt_loader,
      email_notification, identity_injector
    - PostToolUse: auto_fix_diagnostics
    - PreToolUse: pre_edit_gate
    - Stop: subagent_stop_gate
    - PreCompact: pre_compact

    Args:
        aipass_home: Optional AIPass installation root to add as env.AIPASS_HOME.
    """
    _local_prompt_cmd = (
        'python3 -c "'
        "from pathlib import Path; "
        "p=next((x/'.aipass'/'aipass_local_prompt.md' "
        "for x in [Path.cwd(),*Path.cwd().parents] "
        "if (x/'.aipass'/'aipass_local_prompt.md').exists()),None); "
        "p and print(p.read_text(encoding='utf-8'),end='')"
        '"'
    )

    event_hooks: dict[str, list] = {}
    for hook_name, event in HOOK_EVENTS.items():
        entry = {
            "matcher": "",
            "hooks": [{"type": "command", "command": f"python3 .claude/hooks/{hook_name}"}],
        }
        event_hooks.setdefault(event, []).append(entry)

    prompt_hooks = [
        {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": "cat .aipass/aipass_global_prompt.md 2>/dev/null || true",
                }
            ],
        },
        {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": _local_prompt_cmd,
                }
            ],
        },
    ]
    event_hooks["UserPromptSubmit"] = prompt_hooks + event_hooks.get("UserPromptSubmit", [])

    data: dict = {"hooks": event_hooks}
    if aipass_home:
        data["env"] = {"AIPASS_HOME": aipass_home}
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def init_project(target: Path, project_name: str | None = None) -> dict:
    """Initialize an AIPass project in the target directory.

    Args:
        target: Directory to initialize
        project_name: Name for the registry (defaults to directory name)

    Returns:
        dict with registry_id, registry_file, project_name, target, created_files

    Raises:
        ValueError: If project name is empty after sanitization
    """
    target = target.resolve()
    if not target.exists():
        target.mkdir(parents=True)

    raw_name = project_name or target.name
    name = _sanitize_name(raw_name)
    if not name:
        raise ValueError(f"Cannot derive project name from '{raw_name}'. Pass a project name explicitly.")

    registry_id = str(uuid.uuid4())
    today = date.today().isoformat()
    created = []
    aipass_home = _detect_aipass_home()

    # 1. Registry (skip if exists — init is re-runnable)
    registry_filename = f"{name}_REGISTRY.json"
    registry_path = target / registry_filename
    if registry_path.exists():
        # Read existing registry to get its ID
        existing = json.loads(registry_path.read_text(encoding="utf-8"))
        registry_id = existing["metadata"]["id"]
    else:
        registry_data = {
            "metadata": {
                "id": registry_id,
                "name": name,
                "version": "1.0.0",
                "created": today,
                "last_updated": today,
                "total_branches": 0,
            },
            "branches": [],
        }
        registry_path.write_text(
            json.dumps(registry_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        created.append(str(registry_path))

    # 2. .aipass/
    aipass_dir = target / ".aipass"
    aipass_dir.mkdir(exist_ok=True)

    global_prompt_path = aipass_dir / "aipass_global_prompt.md"
    if not global_prompt_path.exists():
        global_prompt_path.write_text(
            sc.with_source(sc.global_prompt_md(name), global_prompt_path),
            encoding="utf-8",
        )
        created.append(str(global_prompt_path))

    # 3. CLAUDE.md
    claude_md_path = target / "CLAUDE.md"
    if not claude_md_path.exists():
        claude_md_path.write_text(
            sc.with_source(sc.claude_md(name), claude_md_path),
            encoding="utf-8",
        )
        created.append(str(claude_md_path))

    # 4. AGENTS.md (Codex)
    agents_md_path = target / "AGENTS.md"
    if not agents_md_path.exists():
        agents_md_path.write_text(
            sc.with_source(sc.agents_md(name), agents_md_path),
            encoding="utf-8",
        )
        created.append(str(agents_md_path))

    # 5. GEMINI.md
    gemini_md_path = target / "GEMINI.md"
    if not gemini_md_path.exists():
        gemini_md_path.write_text(
            sc.with_source(sc.gemini_md(name), gemini_md_path),
            encoding="utf-8",
        )
        created.append(str(gemini_md_path))

    # 6. README.md
    readme_md_path = target / "README.md"
    if not readme_md_path.exists():
        readme_content = sc.readme_md(name).replace("{date}", today)
        readme_md_path.write_text(readme_content, encoding="utf-8")
        created.append(str(readme_md_path))

    # 7. STATUS.local.md
    status_md_path = target / "STATUS.local.md"
    if not status_md_path.exists():
        status_md_path.write_text(
            f"# {name}\n\n**State:** New\n**Last update:** {today}\n\n## Current Work\n\n## Known Issues\n- None\n",
            encoding="utf-8",
        )
        created.append(str(status_md_path))

    # 8. .gitignore
    gitignore_path = target / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text(sc.gitignore(), encoding="utf-8")
        created.append(str(gitignore_path))

    # 9. .claude/settings.json
    claude_dir = target / ".claude"
    claude_dir.mkdir(exist_ok=True)

    settings_path = claude_dir / "settings.json"
    if not settings_path.exists():
        settings_path.write_text(_claude_settings(aipass_home), encoding="utf-8")
        created.append(str(settings_path))

    # 9b. .claude/commands/prep.md — /prep session wrap-up slash command
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir(exist_ok=True)
    prep_path = commands_dir / "prep.md"
    if not prep_path.exists():
        prep_path.write_text(sc.prep_md(), encoding="utf-8")
        created.append(str(prep_path))

    # 9c. .claude/commands/memo.md — /memo memory update slash command
    memo_path = commands_dir / "memo.md"
    if not memo_path.exists():
        memo_path.write_text(sc.memo_md(), encoding="utf-8")
        created.append(str(memo_path))

    # 9d. Ship enforcement + injector hooks from AIPass install
    if aipass_home:
        shipped = _ship_hooks(aipass_home, target)
        created.extend(shipped)

    # 10. src/ directory (where agents live)
    src_dir = target / "src"
    if not src_dir.exists():
        src_dir.mkdir()
        created.append(str(src_dir))

    # 12. .ai_mail.local/inbox.json — empty project mailbox
    mail_dir = target / ".ai_mail.local"
    mail_dir.mkdir(exist_ok=True)
    inbox_path = mail_dir / "inbox.json"
    if not inbox_path.exists():
        inbox_path.write_text(sc.inbox_json(), encoding="utf-8")
        created.append(str(inbox_path))

    return {
        "registry_id": registry_id,
        "registry_file": registry_filename,
        "project_name": name,
        "target": str(target),
        "created_files": created,
        "aipass_home": aipass_home,
    }


def update_project(target: Path) -> dict:
    """Update managed scaffold files in an existing AIPass project.

    Overwrites managed prompt and config files with the latest templates while
    leaving all user-owned files (registry, README, STATUS.local.md, .gitignore,
    src/) untouched.

    Args:
        target: Directory containing the AIPass project to update.

    Returns:
        dict with project_name, target, updated_files, skipped_files.

    Raises:
        ValueError: If no ``*_REGISTRY.json`` is found in target (not an AIPass
            project or init has not been run yet).
    """
    target = target.resolve()

    # Guard: refuse to update the AIPass source repo itself. The source repo
    # has hand-maintained production files that must not be overwritten with
    # generic templates. External projects created via `aipass init` are fine.
    if (target / "src" / "aipass").is_dir() and (target / "pyproject.toml").exists():
        raise ValueError(
            "Cannot update the AIPass source repository — its files are hand-maintained, not template-generated"
        )

    # Locate the project registry to confirm this is an AIPass project and
    # derive the project name without parsing JSON (filename encodes the name).
    registry_files = list(target.glob("*_REGISTRY.json"))
    if not registry_files:
        raise ValueError("No AIPass project found — run 'aipass init' first")
    registry_path = registry_files[0]
    name = registry_path.stem.replace("_REGISTRY", "")

    updated: list[str] = []
    already_current: list[str] = []
    skipped: list[str] = []
    aipass_home: str | None = None

    # Managed directories — create if missing (graceful recovery).
    aipass_dir = target / ".aipass"
    aipass_dir.mkdir(exist_ok=True)

    claude_dir = target / ".claude"
    claude_dir.mkdir(exist_ok=True)

    # --- Managed files: write only when content has changed ---

    global_prompt_path = aipass_dir / "aipass_global_prompt.md"
    generated = sc.with_source(sc.global_prompt_md(name), global_prompt_path)
    if not global_prompt_path.exists() or global_prompt_path.read_text(encoding="utf-8") != generated:
        global_prompt_path.write_text(generated, encoding="utf-8")
        updated.append(str(global_prompt_path))
    else:
        already_current.append(str(global_prompt_path))

    # settings.json — smart merge: preserve existing AIPASS_HOME, detect if missing
    settings_path = claude_dir / "settings.json"
    if not settings_path.exists():
        aipass_home = _detect_aipass_home()
        settings_path.write_text(_claude_settings(aipass_home), encoding="utf-8")
        updated.append(str(settings_path))
    else:
        existing_content = settings_path.read_text(encoding="utf-8")
        try:
            existing_env = json.loads(existing_content).get("env", {})
        except json.JSONDecodeError as exc:
            logger.info("settings.json parse failed, rebuilding: %s", exc)
            existing_env = {}
        # Preserve existing AIPASS_HOME; detect and add if missing
        aipass_home = existing_env.get("AIPASS_HOME") or _detect_aipass_home()
        generated = _claude_settings(aipass_home)
        if existing_content != generated:
            settings_path.write_text(generated, encoding="utf-8")
            updated.append(str(settings_path))
        else:
            already_current.append(str(settings_path))

    claude_md_path = target / "CLAUDE.md"
    generated = sc.with_source(sc.claude_md(name), claude_md_path)
    if not claude_md_path.exists() or claude_md_path.read_text(encoding="utf-8") != generated:
        claude_md_path.write_text(generated, encoding="utf-8")
        updated.append(str(claude_md_path))
    else:
        already_current.append(str(claude_md_path))

    agents_md_path = target / "AGENTS.md"
    generated = sc.with_source(sc.agents_md(name), agents_md_path)
    if not agents_md_path.exists() or agents_md_path.read_text(encoding="utf-8") != generated:
        agents_md_path.write_text(generated, encoding="utf-8")
        updated.append(str(agents_md_path))
    else:
        already_current.append(str(agents_md_path))

    gemini_md_path = target / "GEMINI.md"
    generated = sc.with_source(sc.gemini_md(name), gemini_md_path)
    if not gemini_md_path.exists() or gemini_md_path.read_text(encoding="utf-8") != generated:
        gemini_md_path.write_text(generated, encoding="utf-8")
        updated.append(str(gemini_md_path))
    else:
        already_current.append(str(gemini_md_path))

    # .claude/commands/prep.md — managed slash command, refresh to latest
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir(exist_ok=True)
    prep_path = commands_dir / "prep.md"
    generated = sc.prep_md()
    if not prep_path.exists() or prep_path.read_text(encoding="utf-8") != generated:
        prep_path.write_text(generated, encoding="utf-8")
        updated.append(str(prep_path))
    else:
        already_current.append(str(prep_path))

    # .claude/commands/memo.md — managed slash command, refresh to latest
    memo_path = commands_dir / "memo.md"
    generated = sc.memo_md()
    if not memo_path.exists() or memo_path.read_text(encoding="utf-8") != generated:
        memo_path.write_text(generated, encoding="utf-8")
        updated.append(str(memo_path))
    else:
        already_current.append(str(memo_path))

    # Re-sync enforcement + injector hooks from AIPass install
    hook_home = aipass_home or _detect_aipass_home()
    if hook_home:
        shipped = _ship_hooks(hook_home, target)
        updated.extend(shipped)

    # --- User-owned files: always skip ---
    for skip_name in (
        str(registry_path),
        str(target / "README.md"),
        str(target / "STATUS.local.md"),
        str(target / ".gitignore"),
    ):
        skipped.append(skip_name)

    # Mailbox — create if missing, never overwrite existing
    mail_dir = target / ".ai_mail.local"
    mail_dir.mkdir(exist_ok=True)
    inbox_path = mail_dir / "inbox.json"
    if not inbox_path.exists():
        inbox_path.write_text(sc.inbox_json(), encoding="utf-8")
        updated.append(str(inbox_path))
    else:
        skipped.append(str(inbox_path))

    return {
        "project_name": name,
        "target": str(target),
        "updated_files": updated,
        "already_current": already_current,
        "skipped_files": skipped,
        "aipass_home": aipass_home,
    }
