"""
SEEDGO - Standards Platform for AIPass

Routes commands to standard packs and seedgo-level modules.
- 'audit aipass' routes to standards/aipass/ pack
- 'verify' routes to seedgo-level modules
- 'list' shows installed standard packs
"""

import json
import sys
import importlib.util
from pathlib import Path
from typing import List, Any, Dict

from aipass.prax import logger
from aipass.cli import console, header

VERSION = "1.0.0"
SEEDGO_ROOT = Path(__file__).parent
MODULES_DIR = SEEDGO_ROOT / "modules"
STANDARDS_DIR = SEEDGO_ROOT / "standards"


# =============================================================================
# PACK DISCOVERY
# =============================================================================

def discover_packs() -> Dict[str, Path]:
    """Discover installed standard packs in standards/ directory."""
    packs: Dict[str, Path] = {}

    if not STANDARDS_DIR.exists():
        return packs

    for pack_dir in sorted(STANDARDS_DIR.iterdir()):
        if not pack_dir.is_dir():
            continue
        # Skip example packs
        if pack_dir.name.endswith(".example"):
            continue
        # Must have a pack.json manifest
        manifest = pack_dir / "pack.json"
        if manifest.exists():
            packs[pack_dir.name] = pack_dir

    return packs


def load_pack_manifest(pack_path: Path) -> Dict[str, Any]:
    """Load pack.json manifest from a pack directory."""
    manifest_path = pack_path / "pack.json"
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# MODULE DISCOVERY
# =============================================================================

def discover_modules() -> List[Any]:
    """Auto-discover seedgo-level modules in modules/ directory."""
    modules = []

    if not MODULES_DIR.exists():
        return modules

    for file_path in sorted(MODULES_DIR.glob("*.py")):
        if file_path.name.startswith("_"):
            continue

        try:
            spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "handle_command"):
                modules.append(module)
        except Exception as e:
            logger.error(f"[SEEDGO] Failed to load module {file_path.stem}: {e}")

    return modules


def route_command(command: str, args: List[str], modules: List[Any]) -> bool:
    """Route command to appropriate module."""
    for module in modules:
        try:
            if module.handle_command(command, args):
                return True
        except Exception as e:
            logger.error(f"[SEEDGO] Module error: {e}")
    return False


# =============================================================================
# PACK ROUTING
# =============================================================================

def route_to_pack(pack_name: str, command: str, args: List[str]) -> bool:
    """Route a command to a specific standard pack."""
    packs = discover_packs()

    if pack_name not in packs:
        console.print(f"[red]Unknown pack:[/red] {pack_name}")
        console.print(f"Available packs: {', '.join(packs.keys())}")
        return False

    pack_path = packs[pack_name]
    entry_point = pack_path / "pack_entry.py"

    if not entry_point.exists():
        console.print(f"[red]Pack entry point not found:[/red] {entry_point}")
        return False

    # Load the pack's entry point and route the command
    try:
        spec = importlib.util.spec_from_file_location(f"pack_{pack_name}", entry_point)
        if spec is None or spec.loader is None:
            console.print(f"[red]Failed to load pack:[/red] {pack_name}")
            return False
        pack_module = importlib.util.module_from_spec(spec)

        # Add pack root to sys.path so pack modules can find their handlers
        # The pack dir contains 'aipass_json/' etc but NOT an 'aipass/' dir that would shadow the package
        pack_root_str = str(pack_path)
        if pack_root_str not in sys.path:
            sys.path.insert(0, pack_root_str)

        spec.loader.exec_module(pack_module)

        if hasattr(pack_module, "main"):
            # Override sys.argv for the pack's main()
            original_argv = sys.argv
            sys.argv = [str(entry_point), command] + args
            try:
                pack_module.main()
            finally:
                sys.argv = original_argv
            return True
        elif hasattr(pack_module, "route_command"):
            modules = pack_module.discover_modules() if hasattr(pack_module, "discover_modules") else []
            return pack_module.route_command(command, args, modules)
    except Exception as e:
        logger.error(f"[SEEDGO] Pack {pack_name} error: {e}")
        console.print(f"[red]Pack error:[/red] {e}")

    return False


# =============================================================================
# DISPLAY
# =============================================================================

def show_help(packs: Dict[str, Path], modules: List[Any]) -> None:
    """Show seedgo help with packs and modules."""
    header("SEEDGO - Standards Platform")
    console.print()
    console.print(f"  Version: {VERSION}")
    console.print()

    # Show packs
    console.print("[bold]Standard Packs:[/bold]")
    if packs:
        for name, path in packs.items():
            try:
                manifest = load_pack_manifest(path)
                desc = manifest.get("description", "No description")
                count = manifest.get("standards_count", "?")
                console.print(f"  {name:20} {desc} ({count} standards)")
            except Exception:
                console.print(f"  {name:20} (manifest error)")
    else:
        console.print("  [dim]No packs installed[/dim]")
    console.print()

    # Show modules
    console.print("[bold]Seedgo Modules:[/bold]")
    if modules:
        for module in modules:
            name = getattr(module, "__name__", "unknown").split(".")[-1]
            desc = (module.__doc__ or "").strip().split("\n")[0] if module.__doc__ else "No description"
            console.print(f"  {name:20} {desc}")
    else:
        console.print("  [dim]No modules discovered[/dim]")
    console.print()

    # Usage
    console.print("[bold]Usage:[/bold]")
    console.print("  seedgo audit <pack>            Run pack audit")
    console.print("  seedgo checklist <pack> <file>  Check file against pack")
    console.print("  seedgo list                    Show installed packs")
    console.print("  seedgo verify                  Self-check seedgo")
    console.print("  seedgo --version               Show version")
    console.print()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main() -> int:
    """Main entry point - routes to packs or modules."""
    packs = discover_packs()
    modules = discover_modules()
    args = sys.argv[1:]

    if not args or args[0] in ["--help", "-h", "help"]:
        show_help(packs, modules)
        return 0

    if args[0] in ["--version", "-V"]:
        console.print(f"seedgo v{VERSION}")
        return 0

    command = args[0]
    remaining = args[1:] if len(args) > 1 else []

    # 'list' — show installed packs
    if command == "list":
        if remaining and remaining[0].startswith("--pack"):
            pack_name = remaining[1] if len(remaining) > 1 else ""
            if pack_name in packs:
                manifest = load_pack_manifest(packs[pack_name])
                header(f"Pack: {pack_name}")
                for standard in manifest.get("standards", []):
                    console.print(f"  {standard}")
            else:
                console.print(f"[red]Unknown pack:[/red] {pack_name}")
        else:
            for name, path in packs.items():
                try:
                    manifest = load_pack_manifest(path)
                    count = manifest.get("standards_count", "?")
                    console.print(f"  {name:20} ({count} standards)")
                except Exception:
                    console.print(f"  {name:20} (error)")
        return 0

    # 'audit <pack>' or 'checklist <pack> <file>' — route to pack
    if command in ["audit", "checklist"] and remaining:
        pack_name = remaining[0]
        pack_args = remaining[1:]
        if pack_name in packs:
            return 0 if route_to_pack(pack_name, command, pack_args) else 1
        # If not a pack name, try as a seedgo module command
        pass

    # Try seedgo-level modules
    if route_command(command, remaining, modules):
        return 0

    console.print(f"[red]Unknown command:[/red] {command}")
    console.print("Run 'seedgo --help' for usage")
    return 1


if __name__ == "__main__":
    sys.exit(main())
