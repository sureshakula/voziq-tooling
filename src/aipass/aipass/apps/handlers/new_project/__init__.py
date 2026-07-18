# =================== AIPass ====================
# Name: __init__.py
# Description: New project handler — create projects inside AIPass
# Version: 1.0.0
# Created: 2026-07-17
# Modified: 2026-07-17
# =============================================

"""
New Project Handler — creates projects inside AIPass installations.

Business logic for `aipass new`. Creates a project at <host>/projects/<name>
with its own git repo, registry, and optional AIPass agent.

Flow: find host -> validate -> mkdir -> mint registry (FIRST) ->
      write template -> scaffold AIPass files -> git init -> optional agent.

RULES:
  - Registry MUST be minted before any spawn call
  - git init via subprocess (hooks git gate only intercepts agent Bash)
  - Cleanup on failure: partial project is worse than no project
"""

import json
import re
import shutil
import subprocess
import uuid
from datetime import date
from pathlib import Path

from aipass.prax import logger

TEMPLATES = ("empty", "python")


def find_host_root(start: Path) -> Path | None:
    """Walk up from *start* to find the AIPass host installation root.

    Returns the directory containing ``*_REGISTRY.json``, or ``None``.
    """
    for p in [start, *start.parents]:
        try:
            entries = list(p.iterdir())
        except OSError:
            continue
        for f in entries:
            try:
                if f.is_file() and f.name.endswith("_REGISTRY.json"):
                    return p
            except OSError:
                continue
    return None


def _validate_name(name: str) -> str:
    if not name:
        raise ValueError("Project name cannot be empty")
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", name):
        raise ValueError(
            f"Invalid project name '{name}'. "
            "Must start with a letter, contain only letters, digits, hyphens, underscores."
        )
    return name


def _registry_name(name: str) -> str:
    return re.sub(r"[^A-Z0-9_-]", "_", name.upper()).strip("_")


def _git(args: list[str], cwd: Path) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


# ── registry ────────────────────────────────────────────────────────────


def _write_registry(target: Path, name: str) -> tuple[str, str]:
    """Mint the project registry. Returns ``(registry_id, filename)``."""
    registry_id = str(uuid.uuid4())
    today = date.today().isoformat()
    reg = _registry_name(name)
    filename = f"{reg}_REGISTRY.json"

    data = {
        "metadata": {
            "id": registry_id,
            "name": reg,
            "version": "1.0.0",
            "created": today,
            "last_updated": today,
            "total_branches": 0,
        },
        "branches": [],
    }
    (target / filename).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return registry_id, filename


# ── templates ───────────────────────────────────────────────────────────


def _write_template(target: Path, name: str, template: str) -> list[str]:
    """Write template-specific files. Returns relative paths created."""
    created: list[str] = []

    (target / "README.md").write_text(
        f"# {name}\n\nCreated with `aipass new`. Template: {template}.\n",
        encoding="utf-8",
    )
    created.append("README.md")

    (target / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n.venv/\n.trinity/\n.ai_mail.local/\n*.local.json\n*.local/\nlogs/\n",
        encoding="utf-8",
    )
    created.append(".gitignore")

    if template == "python":
        pkg = name.replace("-", "_").lower()
        (target / "pyproject.toml").write_text(
            "[build-system]\n"
            'requires = ["setuptools>=61.0"]\n'
            'build-backend = "setuptools.build_meta"\n\n'
            "[project]\n"
            f'name = "{name}"\n'
            'version = "0.1.0"\n'
            f'description = "{name} — born deployable"\n'
            'requires-python = ">=3.10"\n\n'
            "[tool.setuptools.packages.find]\n"
            'where = ["src"]\n\n'
            "[tool.pytest.ini_options]\n"
            'testpaths = ["src"]\n'
            'pythonpath = ["src"]\n',
            encoding="utf-8",
        )
        created.append("pyproject.toml")
        src = target / "src" / pkg
        src.mkdir(parents=True)
        (src / "__init__.py").write_text(
            f'"""{name} — born deployable."""\n\n__version__ = "0.1.0"\n',
            encoding="utf-8",
        )
        created.append(f"src/{pkg}/__init__.py")

    return created


# ── AIPass scaffold ─────────────────────────────────────────────────────


def _scaffold_aipass(target: Path, name: str) -> list[str]:
    """Write AIPass scaffold files (tiers, hooks, CLAUDE.md, settings, .venv)."""
    from aipass.aipass.apps.handlers.init.bootstrap import (
        _claude_settings,
        _detect_aipass_home,
        _enroll_project,
    )
    from aipass.aipass.apps.handlers.init import scaffold_content as sc

    created: list[str] = []
    aipass_home = _detect_aipass_home()
    reg = _registry_name(name)

    # .aipass/
    aipass_dir = target / ".aipass"
    aipass_dir.mkdir(exist_ok=True)

    # Tier files
    if aipass_home:
        for tier_file in ("tier0_kernel.md", "tier1_navmap.md"):
            dest = aipass_dir / tier_file
            src_path = Path(aipass_home) / ".aipass" / tier_file
            if src_path.is_file():
                shutil.copy2(str(src_path), str(dest))
                created.append(f".aipass/{tier_file}")

    # hooks.json + trust enrollment
    if aipass_home:
        template = Path(aipass_home) / ".aipass" / "project_hooks.json"
        if template.is_file():
            shutil.copy2(str(template), str(aipass_dir / "hooks.json"))
            created.append(".aipass/hooks.json")
            _enroll_project(target)

    # CLAUDE.md, AGENTS.md
    for md_name in ("CLAUDE.md", "AGENTS.md"):
        dest = target / md_name
        if dest.exists():
            continue
        if aipass_home:
            tmpl = Path(aipass_home) / ".aipass" / f"project_{md_name}"
            if tmpl.is_file():
                content = tmpl.read_text(encoding="utf-8").replace("{name}", reg)
                dest.write_text(content, encoding="utf-8")
                created.append(md_name)
                continue
        if md_name == "AGENTS.md":
            dest.write_text(sc.agents_md(reg), encoding="utf-8")
            created.append(md_name)

    # .claude/settings.json
    claude_dir = target / ".claude"
    claude_dir.mkdir(exist_ok=True)
    (claude_dir / "settings.json").write_text(
        _claude_settings(aipass_home),
        encoding="utf-8",
    )
    created.append(".claude/settings.json")

    # .claude/commands/prep.md
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir(exist_ok=True)
    (commands_dir / "prep.md").write_text(sc.prep_md(), encoding="utf-8")
    created.append(".claude/commands/prep.md")

    # .venv symlink
    if aipass_home:
        venv = Path(aipass_home) / ".venv"
        if venv.is_dir():
            link = target / ".venv"
            link.symlink_to(venv)
            created.append(".venv")

    return created


# ── git ─────────────────────────────────────────────────────────────────


def _git_init(target: Path, name: str, template: str) -> None:
    """Initialize git repo with birth commit. Guards against re-init."""
    if (target / ".git").exists():
        raise RuntimeError(f"'{target}' already has a .git directory")
    _git(["init", "-b", "main"], target)
    _git(["add", "-A"], target)
    _git(
        ["commit", "-m", f"birth: {name} ({template} template) via aipass new"],
        target,
    )


# ── agent (passport + registry seat) ────────────────────────────────────


def _entry_point_content(name: str) -> str:
    """Generate the entry point script for the newborn project agent."""
    reg = _registry_name(name)
    return (
        f'"""\n'
        f"{reg} — project agent\n"
        f"\n"
        f"Auto-discovery architecture:\n"
        f"- Scans modules/ directory for .py files with handle_command()\n"
        f"- Routes commands to discovered modules automatically\n"
        f'"""\n'
        f"\n"
        f"import importlib\n"
        f"import os\n"
        f"import sys\n"
        f"from pathlib import Path\n"
        f"from typing import Any, List\n"
        f"\n"
        f"PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)\n"
        f"if PROJECT_ROOT not in sys.path:\n"
        f"    sys.path.insert(0, PROJECT_ROOT)\n"
        f"\n"
        f'os.environ.setdefault("AIPASS_BRANCH_NAME", "{name}")\n'
        f"\n"
        f"from aipass.cli.apps.modules import console  # noqa: E402\n"
        f"from aipass.prax import logger  # noqa: E402\n"
        f"\n"
        f'MODULES_DIR = Path(__file__).parent / "modules"\n'
        f"\n"
        f"\n"
        f"def discover_modules() -> List[Any]:\n"
        f'    """Auto-discover modules in modules/ directory."""\n'
        f"    modules = []\n"
        f"    if not MODULES_DIR.exists():\n"
        f"        return modules\n"
        f'    for file_path in MODULES_DIR.glob("*.py"):\n'
        f'        if file_path.name.startswith("_"):\n'
        f"            continue\n"
        f"        for prefix in (\n"
        f'            f"aipass.{name}.apps.modules.{{file_path.stem}}",\n'
        f'            f"apps.modules.{{file_path.stem}}",\n'
        f"        ):\n"
        f"            try:\n"
        f"                mod = importlib.import_module(prefix)\n"
        f'                if hasattr(mod, "handle_command"):\n'
        f"                    modules.append(mod)\n"
        f"                break\n"
        f"            except ImportError:\n"
        f"                continue\n"
        f"    return modules\n"
        f"\n"
        f"\n"
        f"def print_introspection() -> None:\n"
        f'    """Bare invocation — title, purpose, --help pointer."""\n'
        f"    console.print()\n"
        f'    console.print("[bold cyan]{reg} — Project Agent[/bold cyan]")\n'
        f'    console.print("[dim]Resident agent of the {name} project.[/dim]")\n'
        f"    console.print()\n"
        f"    modules = discover_modules()\n"
        f"    if modules:\n"
        f'        console.print("[yellow]Modules:[/yellow]")\n'
        f"        for m in modules:\n"
        f'            cmd = getattr(m, "COMMAND", m.__name__.split(".")[-1])\n'
        f'            desc = (m.__doc__ or "").strip().split("\\n")[0]\n'
        f'            console.print(f"  [green]{{cmd:16}}[/green] [dim]{{desc}}[/dim]")\n'
        f"        console.print()\n"
        f"    console.print(\"[dim]Run 'drone @{name} --help' for usage[/dim]\")\n"
        f"    console.print()\n"
        f"\n"
        f"\n"
        f"def print_help() -> None:\n"
        f'    """Full help — usage, commands, examples."""\n'
        f"    console.print()\n"
        f'    console.print("[bold cyan]{reg} — Project Agent[/bold cyan]")\n'
        f"    console.print()\n"
        f'    console.print("[yellow]Usage:[/yellow]")\n'
        f'    console.print("  [green]drone @{name}[/green] [dim]<command>[/dim]")\n'
        f"    console.print()\n"
        f'    console.print("[yellow]Commands:[/yellow]")\n'
        f'    console.print("  [green]hello[/green]     [dim]Confirm the agent is alive[/dim]")\n'
        f"    console.print()\n"
        f'    console.print("[yellow]Examples:[/yellow]")\n'
        f'    console.print("  [green]drone @{name} hello[/green]")\n'
        f"    console.print()\n"
        f"\n"
        f"\n"
        f"def route_command(command: str, args: List[str], modules: List[Any]) -> bool:\n"
        f'    """Route command to appropriate module."""\n'
        f"    for module in modules:\n"
        f"        try:\n"
        f"            if module.handle_command(command, args):\n"
        f"                return True\n"
        f"        except Exception as e:\n"
        f'            logger.error("[{reg}] Module error: %s", e)\n'
        f"    return False\n"
        f"\n"
        f"\n"
        f"def main():\n"
        f'    """Main entry point."""\n'
        f"    modules = discover_modules()\n"
        f"    args = sys.argv[1:]\n"
        f"\n"
        f"    if not args:\n"
        f"        print_introspection()\n"
        f"        return 0\n"
        f'    if args[0] in ("--help", "-h", "help"):\n'
        f"        print_help()\n"
        f"        return 0\n"
        f'    if args[0] == "hello":\n'
        f'        console.print(f"[cyan]{reg}[/cyan] here. '
        f'Project agent, alive and ready.")\n'
        f"        return 0\n"
        f"\n"
        f"    command = args[0]\n"
        f"    remaining = args[1:] if len(args) > 1 else []\n"
        f"    if route_command(command, remaining, modules):\n"
        f"        return 0\n"
        f'    console.print(f"Unknown command: {{command}}")\n'
        f"    return 1\n"
        f"\n"
        f"\n"
        f'if __name__ == "__main__":\n'
        f"    sys.exit(main())\n"
    )


def _local_json_content(name: str) -> dict:
    """Generate initial local.json for the newborn agent."""
    reg = _registry_name(name)
    today = date.today().isoformat()
    return {
        "document_metadata": {
            "document_type": "session_history",
            "document_name": f"{reg}.LOCAL",
            "version": "1.0.0",
            "schema_version": "3.0.0",
            "created": today,
            "last_updated": today,
            "managed_by": reg,
            "tags": ["session_tracking", "work_log", reg],
        },
        "todos": [],
        "key_learnings": [],
        "sessions": [],
    }


def _observations_json_content(name: str) -> dict:
    """Generate initial observations.json for the newborn agent."""
    reg = _registry_name(name)
    today = date.today().isoformat()
    return {
        "document_metadata": {
            "document_type": "observations",
            "document_name": f"{reg}.OBSERVATIONS",
            "version": "1.0.0",
            "created": today,
            "last_updated": today,
            "managed_by": reg,
        },
        "observations": [],
    }


def _write_agent(target: Path, name: str, registry_id: str, registry_file: str) -> list[str]:
    """Create the full framework agent: entry point, structure, identity, registry seat.

    Models the credential linkage from the proven proto:
    ``registry.metadata.id == passport.citizenship.registry_id``.
    """
    today = date.today().isoformat()
    reg = _registry_name(name)
    created: list[str] = []

    # ── apps/ entry point + skeleton ─────────────────────────────────
    apps_dir = target / "apps"
    apps_dir.mkdir(exist_ok=True)
    (apps_dir / "__init__.py").write_text("")
    created.append("apps/__init__.py")

    entry_file = apps_dir / f"{name}.py"
    entry_file.write_text(_entry_point_content(name), encoding="utf-8")
    created.append(f"apps/{name}.py")

    for sub in ("modules", "handlers"):
        d = apps_dir / sub
        d.mkdir(exist_ok=True)
        (d / "__init__.py").write_text("")
        created.append(f"apps/{sub}/__init__.py")

    # ── .trinity/ identity ───────────────────────────────────────────
    trinity = target / ".trinity"
    trinity.mkdir(exist_ok=True)
    passport = {
        "document_metadata": {
            "document_type": "branch_identity",
            "document_name": f"{reg}.PASSPORT",
            "version": "1.0.0",
            "schema_version": "1.0.0",
            "created": today,
            "last_updated": today,
            "managed_by": reg,
            "tags": ["identity", "passport", "branch_profile"],
        },
        "branch_info": {
            "branch_name": reg,
            "alias": "",
            "path": ".",
            "module": name,
            "created": today,
            "git_branch": "main",
        },
        "identity": {
            "citizen_class": "worker",
            "role": "project_agent",
            "purpose": f"Resident agent of the {name} project.",
            "what_i_do": [],
            "what_i_dont_do": [],
        },
        "principles": [
            "Code is truth - fail honestly",
            "Memory persists - context survives",
            "Simple solutions over complex architecture",
        ],
        "citizenship": {
            "registered": True,
            "registry_id": registry_id,
            "communications": True,
            "memory": True,
        },
    }
    for fname, data in (
        ("passport.json", passport),
        ("local.json", _local_json_content(name)),
        ("observations.json", _observations_json_content(name)),
    ):
        (trinity / fname).write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        created.append(f".trinity/{fname}")

    # ── mailbox + logs ───────────────────────────────────────────────
    (target / ".ai_mail.local").mkdir(exist_ok=True)
    (target / "logs").mkdir(exist_ok=True)

    # ── registry seat ────────────────────────────────────────────────
    reg_path = target / registry_file
    reg_data = json.loads(reg_path.read_text(encoding="utf-8"))
    reg_data["metadata"]["total_branches"] = 1
    reg_data["branches"] = [
        {
            "name": reg,
            "registry_id": registry_id,
            "path": ".",
            "profile": "AIPass Project",
            "description": f"Resident agent of the {name} project.",
            "email": f"@{name}",
            "status": "active",
            "created": today,
            "last_active": today,
            "owner": True,
        },
    ]
    reg_path.write_text(
        json.dumps(reg_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    created.append(registry_file)

    logger.info("[aipass new] full agent created: %s (%d files)", reg, len(created))
    return created


# ── public API ──────────────────────────────────────────────────────────


def create_project(
    name: str,
    template: str = "empty",
    no_agent: bool = False,
) -> dict:
    """Create a new project inside the AIPass host installation.

    Returns:
        dict with name, template, target, host, registry_id, registry_file,
        files, agent_spawned.

    Raises:
        ValueError: Invalid name or template.
        RuntimeError: Not inside AIPass, target exists, git failure.
    """
    _validate_name(name)
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template '{template}'. Choose from: {', '.join(TEMPLATES)}")

    host = find_host_root(Path.cwd())
    if host is None:
        raise RuntimeError(
            "Not inside an AIPass installation (no *_REGISTRY.json found). "
            "`aipass new` creates projects inside the AIPass environment."
        )

    target = host / "projects" / name
    if target.exists():
        raise RuntimeError(f"Project already exists: {target}")

    target.mkdir(parents=True)

    try:
        registry_id, registry_file = _write_registry(target, name)
        logger.info("[aipass new] registry minted: %s (%s)", registry_file, registry_id)

        template_files = _write_template(target, name, template)
        scaffold_files = _scaffold_aipass(target, name)

        agent_files: list[str] = []
        if not no_agent:
            agent_files = _write_agent(target, name, registry_id, registry_file)

        _git_init(target, name, template)
        logger.info("[aipass new] git repo initialized with birth commit")

        return {
            "name": name,
            "template": template,
            "target": str(target),
            "host": str(host),
            "registry_id": registry_id,
            "registry_file": registry_file,
            "files": template_files + scaffold_files + agent_files,
            "agent_created": not no_agent,
        }
    except Exception:
        if target.exists():
            shutil.rmtree(target)
        raise
