#!/usr/bin/env python3
# NOT a setuptools setup.py — this is the AIPass cross-platform installer.
# Runs on Linux, macOS, and Windows (Python 3.10+).
# Usage: python setup.py  OR  python3 setup.py
"""
AIPass cross-platform setup script.

Equivalent to setup.sh but works on Windows without Git Bash.
Performs the same steps: create venv, install package, verify entry points,
create secrets directory, seed .env, generate registry, bootstrap branches,
and set up global CLI access.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_windows() -> bool:
    return platform.system() == "Windows"


def _venv_bin() -> Path:
    """Return the venv executables directory (OS-aware)."""
    if _is_windows():
        return REPO_ROOT / ".venv" / "Scripts"
    return REPO_ROOT / ".venv" / "bin"


def _venv_exe(name: str) -> Path:
    """Return path to a venv executable by name."""
    if _is_windows():
        return _venv_bin() / f"{name}.exe"
    return _venv_bin() / name


def _run(cmd: list, check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    """Print and run a subprocess command."""
    print(f"    $ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, check=check, **kwargs)


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def step_create_venv() -> None:
    """[1] Create .venv using sys.executable (avoids python3 vs python ambiguity)."""
    print("\n[1/9] Creating virtual environment ...")
    venv_path = REPO_ROOT / ".venv"
    if venv_path.exists():
        print("  Removing existing .venv for a clean install ...")
        shutil.rmtree(venv_path)
    _run([sys.executable, "-m", "venv", str(venv_path)])
    print(f"  Created: {venv_path}")


def step_install() -> None:
    """[2] Install aipass in editable mode with dev extras."""
    print("\n[2/9] Installing aipass in editable mode ...")
    pip = _venv_exe("pip")
    _run([str(pip), "install", "--upgrade", "pip", "--quiet"])
    _run([str(pip), "install", "-e", ".[dev]", "--quiet"], cwd=str(REPO_ROOT))
    print("  Installed: aipass[dev]")


def step_verify() -> bool:
    """[3] Verify drone and aipass CLI entry points work."""
    print("\n[3/9] Verifying CLI entry points ...")
    ok = True

    for entry in ("drone", "aipass"):
        cmd_path = _venv_exe(entry)
        if not cmd_path.exists():
            print(f"  {entry:<8} ... FAILED (not found: {cmd_path})")
            ok = False
            continue
        flag = "--help" if entry == "drone" else "--version"
        result = subprocess.run([str(cmd_path), flag], capture_output=True)
        if result.returncode == 0:
            print(f"  {entry:<8} ... ok")
        else:
            print(f"  {entry:<8} ... FAILED (exit {result.returncode})")
            ok = False

    return ok


def step_secrets() -> None:
    """[4] Create ~/.secrets/aipass/ with restrictive permissions."""
    print("\n[4/9] Creating secrets directory ...")
    secrets_root = Path.home() / ".secrets"
    secrets_dir = secrets_root / "aipass"
    secrets_dir.mkdir(parents=True, exist_ok=True)
    if not _is_windows():
        try:
            secrets_root.chmod(0o700)
            secrets_dir.chmod(0o700)
        except OSError:
            pass  # Best-effort on non-POSIX filesystems
    print(f"  Created: {secrets_dir}")


def step_env() -> None:
    """[5] Seed .env.example into ~/.secrets/aipass/.env if not present."""
    print("\n[5/9] Seeding .env template ...")
    env_dest = Path.home() / ".secrets" / "aipass" / ".env"
    env_src = REPO_ROOT / ".env.example"

    if env_dest.exists():
        print("  ~/.secrets/aipass/.env already exists — skipping")
    elif env_src.exists():
        shutil.copy(env_src, env_dest)
        print(f"  Copied: .env.example → {env_dest}")
        print("  Add your API keys to that file")
    else:
        print("  No .env.example found — skipping")


def step_registry() -> None:
    """[6] Generate AIPASS_REGISTRY.json if not present."""
    print("\n[6/9] Generating AIPASS_REGISTRY.json ...")
    registry_path = REPO_ROOT / "AIPASS_REGISTRY.json"
    if registry_path.exists():
        print("  AIPASS_REGISTRY.json already exists — skipping")
        return

    today = date.today().isoformat()
    src_dir = REPO_ROOT / "src" / "aipass"
    branches = []

    if src_dir.exists():
        for d in sorted(src_dir.iterdir()):
            if d.is_dir() and not d.name.startswith(("_", ".")):
                branches.append({
                    "name": d.name,
                    "path": str(d),
                    "profile": "library",
                    "description": "",
                    "email": f"@{d.name}",
                    "status": "active",
                    "created": today,
                    "last_active": today,
                })

    registry = {
        "metadata": {
            "version": "1.0.0",
            "last_updated": today,
            "total_branches": len(branches),
        },
        "branches": branches,
    }
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    print(f"  {len(branches)} branches registered → AIPASS_REGISTRY.json")


def step_bootstrap_branches() -> None:
    """[7] Bootstrap .trinity/ identity and .ai_mail.local/ for each branch."""
    print("\n[7/9] Bootstrapping branch identity files ...")
    today = date.today().isoformat()

    branches = [
        ("drone",    "src/aipass/drone",    "builder", "Command routing and module discovery"),
        ("seedgo",   "src/aipass/seedgo",   "builder", "Standards enforcement and code auditing"),
        ("prax",     "src/aipass/prax",     "builder", "Logging and monitoring system"),
        ("cli",      "src/aipass/cli",      "builder", "Display formatting service"),
        ("flow",     "src/aipass/flow",     "builder", "Workflow and plan management"),
        ("ai_mail",  "src/aipass/ai_mail",  "builder", "Inter-agent messaging and dispatch"),
        ("trigger",  "src/aipass/trigger",  "builder", "Event-driven automation"),
        ("spawn",    "src/aipass/spawn",    "builder", "Branch lifecycle management"),
        ("memory",   "src/aipass/memory",   "builder", "Vector memory bank"),
        ("devpulse", "src/aipass/devpulse", "manager", "Orchestration hub and coordination"),
    ]

    for name, rel_path, citizen_class, role in branches:
        branch_path = REPO_ROOT / rel_path
        if not branch_path.exists():
            print(f"  @{name:<10} ... skipped (directory not found)")
            continue

        created = False
        trinity = branch_path / ".trinity"
        trinity.mkdir(exist_ok=True)

        passport = trinity / "passport.json"
        if not passport.exists():
            passport.write_text(json.dumps({
                "document_metadata": {
                    "document_type": "identity",
                    "document_name": f"{name}.PASSPORT",
                    "version": "1.0.0",
                    "schema_version": "1.0.0",
                    "created": today,
                    "last_updated": today,
                    "managed_by": name,
                },
                "identity": {
                    "name": name,
                    "citizen_class": citizen_class,
                    "role": role,
                    "status": "active",
                },
            }, indent=2) + "\n", encoding="utf-8")
            created = True

        local = trinity / "local.json"
        if not local.exists():
            local.write_text(json.dumps({
                "document_metadata": {
                    "document_type": "session_history",
                    "document_name": f"{name}.LOCAL",
                    "version": "1.0.0",
                    "schema_version": "1.0.0",
                    "created": today,
                    "last_updated": today,
                    "managed_by": name,
                    "tags": ["session_tracking", "work_log", name],
                    "limits": {"max_lines": 600, "note": "Auto-rollover when max_lines exceeded"},
                    "status": {"health": "healthy", "current_lines": 0, "last_health_check": today},
                },
                "active_tasks": {
                    "today_focus": "First session — explore codebase and capabilities",
                    "recently_completed": [],
                },
                "key_learnings": {},
                "sessions": [],
            }, indent=2) + "\n", encoding="utf-8")
            created = True

        mail_dir = branch_path / ".ai_mail.local"
        mail_dir.mkdir(exist_ok=True)
        inbox = mail_dir / "inbox.json"
        if not inbox.exists():
            inbox.write_text(
                json.dumps({"mailbox": "inbox", "total_messages": 0, "unread_count": 0, "messages": []})
                + "\n",
                encoding="utf-8",
            )
            created = True

        seedgo_dir = branch_path / ".seedgo"
        seedgo_dir.mkdir(exist_ok=True)
        bypass = seedgo_dir / "bypass.json"
        if not bypass.exists():
            bypass.write_text("{}\n", encoding="utf-8")
            created = True

        status = "bootstrapped" if created else "exists (skipped)"
        print(f"  @{name:<10} ... {status}")


def step_global_access() -> None:
    """[8/9] Set up global CLI access (symlink on Linux/macOS, PATH hint on Windows)."""
    print("\n[8/9] Setting up global CLI access ...")
    bin_dir = _venv_bin()

    if _is_windows():
        # [9] Windows: no ln, no sudo — print PATH instructions
        print("  Windows detected — symlink not available")
        print("")
        print("  To use drone from any directory, add the venv to your PATH.")
        print("  Choose the method for your shell:")
        print(f"    PowerShell:  $env:PATH = \"{bin_dir};\" + $env:PATH")
        print(f"    CMD:         set PATH={bin_dir};%PATH%")
        print(f"    Git Bash:    export PATH=\"{bin_dir}:$PATH\"")
        print("")
        print("  To make it permanent (PowerShell):")
        print(
            f'    [Environment]::SetEnvironmentVariable('
            f'"PATH", "{bin_dir};" + '
            f'[Environment]::GetEnvironmentVariable("PATH","User"), "User")'
        )
        return

    # Linux/macOS: offer symlink creation
    drone_src = _venv_exe("drone")
    drone_dst = Path("/usr/local/bin/drone")

    if not drone_src.exists():
        print(f"  drone not found at {drone_src} — skipping symlink")
        print(f"  Add {bin_dir} to your PATH manually")
        return

    try:
        answer = input(f"  Create symlink {drone_dst} → {drone_src}? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = ""

    if answer == "y":
        result = subprocess.run(
            ["sudo", "ln", "-sf", str(drone_src), str(drone_dst)],
            check=False,
        )
        if result.returncode == 0:
            print(f"  {drone_dst} -> {drone_src}")
        else:
            print("  WARN: sudo failed — create manually:")
            print(f"    sudo ln -sf {drone_src} {drone_dst}")
    else:
        print(f"  Skipped. To add manually:")
        print(f"    sudo ln -sf {drone_src} {drone_dst}")
        print(f"  Or add {bin_dir} to your PATH")


def step_summary(ok: bool) -> None:
    """[9/9] Print success or warning summary."""
    print("\n[9/9] Done")
    print("")
    if ok:
        print("=== Setup complete ===")
        print("")
        print(f"  Python: {sys.version.split()[0]}")
        print(f"  Venv:   {REPO_ROOT / '.venv'}")
        if _is_windows():
            print("  Add .venv/Scripts to your PATH (see step 8 above)")
        else:
            print("  drone is available globally (or activate: source .venv/bin/activate)")
        print("")
    else:
        print("=== Setup finished with warnings ===")
        print("  Package installed but CLI verification had issues.")
        print("  Check the output above for details.")
        print("")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== AIPass Setup (cross-platform) ===")
    print(f"  Platform: {platform.system()} {platform.machine()}")
    print(f"  Python:   {sys.version.split()[0]} ({sys.executable})")
    print(f"  Repo:     {REPO_ROOT}")

    if sys.version_info < (3, 10):
        print("\nFAIL: Python 3.10+ required")
        sys.exit(1)

    step_create_venv()
    step_install()
    ok = step_verify()
    step_secrets()
    step_env()
    step_registry()
    step_bootstrap_branches()
    step_global_access()
    step_summary(ok)

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
