"""
Seedgo Verify Module

Self-check for seedgo installation integrity.
Verifies packs are loadable, manifests are valid, and standards are consistent.

Run: seedgo verify
"""

# =================== META ====================
# Name: seedgo_verify.py
# Description: Seedgo Verify Module
# Version: 1.0.0
# Created: 2026-03-05
# Modified: 2026-03-05
# =============================================


import json
from pathlib import Path
from typing import List

from aipass.prax import logger
from aipass.cli import console


SEEDGO_ROOT = Path(__file__).resolve().parent.parent  # modules/ -> apps/
STANDARDS_DIR = SEEDGO_ROOT / "standards"


def handle_command(command: str, args: List[str]) -> bool:
    """Handle 'verify' command."""
    if command != "verify":
        return False

    if args and args[0] in ["--help", "-h", "help"]:
        print_help()
        return True

    run_verify()
    return True


def run_verify() -> None:
    """Run seedgo self-verification checks."""
    console.print()
    console.print("[bold cyan]SEEDGO VERIFY[/bold cyan]")
    console.print()

    checks_passed = 0
    checks_total = 0

    # Check 1: Standards directory exists
    checks_total += 1
    if STANDARDS_DIR.exists():
        console.print("[green]✓[/green] Standards directory exists")
        checks_passed += 1
    else:
        console.print("[red]✗[/red] Standards directory missing")

    # Check 2: At least one pack installed
    checks_total += 1
    packs = [d for d in STANDARDS_DIR.iterdir()
             if d.is_dir() and not d.name.endswith(".example") and (d / "pack.json").exists()]
    if packs:
        console.print(f"[green]✓[/green] {len(packs)} standard pack(s) installed: {', '.join(p.name for p in packs)}")
        checks_passed += 1
    else:
        console.print("[red]✗[/red] No standard packs found")

    # Check 3: Each pack has valid manifest
    for pack_dir in packs:
        checks_total += 1
        manifest_path = pack_dir / "pack.json"
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            required_keys = ["name", "version", "standards"]
            missing = [k for k in required_keys if k not in manifest]
            if missing:
                console.print(f"[red]✗[/red] Pack '{pack_dir.name}': manifest missing keys: {missing}")
            else:
                console.print(f"[green]✓[/green] Pack '{pack_dir.name}': valid manifest (v{manifest['version']}, {len(manifest['standards'])} standards)")
                checks_passed += 1
        except Exception as e:
            console.print(f"[red]✗[/red] Pack '{pack_dir.name}': manifest error: {e}")

    # Check 4: Each pack has entry point
    for pack_dir in packs:
        checks_total += 1
        entry = pack_dir / "pack_entry.py"
        if entry.exists():
            console.print(f"[green]✓[/green] Pack '{pack_dir.name}': entry point exists")
            checks_passed += 1
        else:
            console.print(f"[red]✗[/red] Pack '{pack_dir.name}': missing entry point ({entry.name})")

    # Check 5: Each pack's listed standards have check files
    for pack_dir in packs:
        manifest_path = pack_dir / "pack.json"
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            standards = manifest.get("standards", [])
            checks_dir = pack_dir / "handlers" / "standards"
            missing_checks = []
            for std in standards:
                check_file = checks_dir / f"{std}_check.py"
                if not check_file.exists():
                    missing_checks.append(std)

            checks_total += 1
            if missing_checks:
                console.print(f"[red]✗[/red] Pack '{pack_dir.name}': missing check files: {missing_checks}")
            else:
                console.print(f"[green]✓[/green] Pack '{pack_dir.name}': all {len(standards)} standard check files present")
                checks_passed += 1
        except Exception as e:
            console.print(f"[red]✗[/red] Pack '{pack_dir.name}': verification error: {e}")

    # Summary
    console.print()
    score = int(checks_passed / checks_total * 100) if checks_total > 0 else 0
    status = "[green]PASS[/green]" if checks_passed == checks_total else "[yellow]PARTIAL[/yellow]"
    console.print(f"  {status}  {checks_passed}/{checks_total} checks passed ({score}%)")
    console.print()

    logger.info(f"Seedgo verify: {checks_passed}/{checks_total} ({score}%)")


def print_help() -> None:
    """Print help information."""
    console.print()
    console.print("[bold cyan]Seedgo Verify[/bold cyan]")
    console.print("Self-check for seedgo installation integrity")
    console.print()
    console.print("[bold]Usage:[/bold]")
    console.print("  seedgo verify          Run all verification checks")
    console.print("  seedgo verify --help   Show this help")
    console.print()
    console.print("[bold]Checks:[/bold]")
    console.print("  1. Standards directory exists")
    console.print("  2. At least one pack installed")
    console.print("  3. Pack manifests are valid")
    console.print("  4. Pack entry points exist")
    console.print("  5. Standard check files present")
    console.print()
