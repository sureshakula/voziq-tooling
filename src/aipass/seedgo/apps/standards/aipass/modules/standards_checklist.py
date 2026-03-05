#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: standards_checklist.py - Standards Checklist Module
# Date: 2025-11-12
# Version: 0.1.0
# Category: seed/standards
#
# CHANGELOG (Max 5 entries):
#   - v0.1.0 (2025-11-12): Initial standards checklist module - framework only
#
# CODE STANDARDS:
#   - This module checks other modules for standards compliance
# =============================================

"""
Standards Checklist Module

Validates modules against AIPass code standards.
Run directly or via: drone @seed checklist
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# =============================================================================
# INFRASTRUCTURE SETUP
# =============================================================================

AIPASS_ROOT = Path.home() / "aipass_core"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))  # For seed package imports

# =============================================================================
# IMPORTS - DEMONSTRATES PROPER IMPORT PATTERN
# =============================================================================

# Prax logger (system-wide, always first)
from prax.apps.modules.logger import system_logger as logger

# JSON handler for tracking
from seed.apps.handlers.json import json_handler

# CLI services (display/output formatting)
from cli.apps.modules import console, header

# Standards checkers
from seed.apps.handlers.standards import imports_check
from seed.apps.handlers.standards import architecture_check
from seed.apps.handlers.standards import naming_check
from seed.apps.handlers.standards import cli_check
from seed.apps.handlers.standards import handlers_check
from seed.apps.handlers.standards import modules_check
from seed.apps.handlers.standards import documentation_check
from seed.apps.handlers.standards import json_structure_check
from seed.apps.handlers.standards import testing_check
from seed.apps.handlers.standards import error_handling_check
from seed.apps.handlers.standards import encapsulation_check
from seed.apps.handlers.standards import trigger_check
from seed.apps.handlers.standards import log_level_check
from seed.apps.handlers.standards import cli_flags_check
from seed.apps.handlers.standards import log_handler_check
from seed.apps.handlers.standards import log_visibility_check
from seed.apps.handlers.standards import permission_flags_check

# =============================================================================
# BYPASS SYSTEM - .seed/ config per branch
# =============================================================================

BRANCH_REGISTRY_PATH = Path.home() / "BRANCH_REGISTRY.json"

BYPASS_TEMPLATE = {
    "metadata": {
        "version": "1.0.0",
        "created": "",
        "description": "Standards bypass configuration for this branch"
    },
    "bypass": [],
    "notes": {
        "usage": "Add entries to 'bypass' list to exclude specific violations",
        "example": {
            "file": "apps/modules/logger.py",
            "standard": "cli",
            "lines": [146, 177],
            "pattern": "if __name__ == '__main__'",
            "reason": "Circular dependency - logger cannot import CLI"
        },
        "fields": {
            "file": "Relative path from branch root (required)",
            "standard": "Standard name: cli, imports, naming, etc. (required)",
            "lines": "Optional - specific line numbers to bypass",
            "pattern": "Optional - pattern to match (e.g. 'if __name__')",
            "reason": "Required - why this bypass exists"
        }
    }
}


def get_branch_from_path(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Detect which branch a file belongs to using BRANCH_REGISTRY

    Args:
        file_path: Absolute path to file being checked

    Returns:
        Branch dict with name, path, etc. or None if not in a branch
    """
    try:
        if not BRANCH_REGISTRY_PATH.exists():
            logger.warning("[standards_checklist] BRANCH_REGISTRY.json not found")
            return None

        with open(BRANCH_REGISTRY_PATH, 'r', encoding='utf-8') as f:
            registry = json.load(f)

        file_path = str(Path(file_path).resolve())

        # Sort branches by path length (longest first) to match most specific
        branches = sorted(registry.get('branches', []),
                         key=lambda b: len(b.get('path', '')),
                         reverse=True)

        for branch in branches:
            branch_path = branch.get('path', '')
            if file_path.startswith(branch_path + '/') or file_path == branch_path:
                return branch

        return None
    except Exception as e:
        logger.error(f"[standards_checklist] Error reading branch registry: {e}")
        return None


def ensure_seed_config(branch_path: str) -> Path:
    """
    Ensure .seed/bypass.json exists for a branch, create if missing

    Args:
        branch_path: Path to branch root

    Returns:
        Path to bypass.json file
    """
    seed_dir = Path(branch_path) / ".seed"
    bypass_file = seed_dir / "bypass.json"

    try:
        # Create .seed directory if needed
        seed_dir.mkdir(exist_ok=True)

        # Create bypass.json if missing
        if not bypass_file.exists():
            template = BYPASS_TEMPLATE.copy()
            template["metadata"]["created"] = datetime.now().isoformat()

            with open(bypass_file, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2)

            logger.info(f"[standards_checklist] Created {bypass_file}")

        return bypass_file
    except Exception as e:
        logger.error(f"[standards_checklist] Error creating seed config: {e}")
        return bypass_file


def load_bypass_rules(branch_path: str) -> List[Dict[str, Any]]:
    """
    Load bypass rules from branch's .seed/bypass.json

    Args:
        branch_path: Path to branch root

    Returns:
        List of bypass rule dicts
    """
    bypass_file = ensure_seed_config(branch_path)

    try:
        if bypass_file.exists():
            with open(bypass_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config.get('bypass', [])
    except Exception as e:
        logger.error(f"[standards_checklist] Error loading bypass rules: {e}")

    return []


def is_bypassed(file_path: str, branch_path: str, standard: str,
                line: Optional[int], bypass_rules: List[Dict]) -> bool:
    """
    Check if a specific violation should be bypassed

    Args:
        file_path: Absolute path to file
        branch_path: Path to branch root
        standard: Standard name (cli, imports, etc.)
        line: Line number of violation (optional)
        bypass_rules: List of bypass rules

    Returns:
        True if this violation should be bypassed
    """
    # Get relative path from branch root
    try:
        rel_path = str(Path(file_path).relative_to(branch_path))
    except ValueError:
        rel_path = file_path

    for rule in bypass_rules:
        # Check if rule matches this file and standard
        rule_file = rule.get('file', '')
        rule_standard = rule.get('standard', '')

        if rule_file and rule_file != rel_path:
            continue
        if rule_standard and rule_standard != standard:
            continue

        # Check line-specific bypass
        rule_lines = rule.get('lines', [])
        if rule_lines and line is not None:
            if line in rule_lines:
                return True
        elif not rule_lines:
            # No line restriction - bypass all violations for this file/standard
            return True

    return False


def print_help():
    """Print drone-compliant help output"""
    console.print()
    console.print("[bold cyan]Standards Checklist Module[/bold cyan]")
    console.print("Validates modules against AIPass code standards")
    console.print()

    console.print("[yellow]COMMANDS:[/yellow]")
    console.print("  Commands: checklist, check, validate, --help, --introspect")
    console.print()
    console.print("  [cyan]checklist[/cyan]   - Run standards validation on a module")
    console.print("  [cyan]check[/cyan]       - Run standards validation (alias)")
    console.print("  [cyan]validate[/cyan]    - Run standards validation (alias)")
    console.print()

    console.print("[yellow]USAGE:[/yellow]")
    console.print("  [dim]# Via drone[/dim]")
    console.print("  drone @seed checklist <module_path>")
    console.print()
    console.print("  [dim]# Standalone[/dim]")
    console.print("  python3 /home/aipass/seed/apps/modules/standards_checklist.py <module_path>")
    console.print("  python3 /home/aipass/seed/apps/modules/standards_checklist.py --introspect")
    console.print("  python3 /home/aipass/seed/apps/modules/standards_checklist.py --help")
    console.print()

    console.print("[yellow]EXAMPLES:[/yellow]")
    console.print("  [dim]# Check a seed module[/dim]")
    console.print("  python3 /home/aipass/seed/apps/modules/standards_checklist.py /home/aipass/seed/apps/modules/imports_standard.py")
    console.print()
    console.print("  [dim]# Check a different branch module[/dim]")
    console.print("  python3 /home/aipass/seed/apps/modules/standards_checklist.py /home/aipass/aipass_core/api/apps/api.py")
    console.print()
    console.print("  [dim]# Show json_handler introspection[/dim]")
    console.print("  python3 /home/aipass/seed/apps/modules/standards_checklist.py --introspect")
    console.print()

    console.print("[yellow]REFERENCE:[/yellow]")
    console.print("  Checks imports, architecture, naming, CLI, handlers, modules,")
    console.print("  documentation, JSON structure, testing, and error handling standards.")
    console.print()


def print_json_handler_introspection():
    """Show introspection of handlers/json/json_handler.py"""
    console.print()
    header("json_handler.py INTROSPECTION")
    console.print()
    console.print("[bold cyan]Auto-Creating & Self-Healing JSON System[/bold cyan]")
    console.print("[dim]Location: /home/aipass/seed/apps/handlers/json/json_handler.py[/dim]")
    console.print()

    # OVERVIEW
    console.print("[bold white]OVERVIEW:[/bold white]")
    console.print("  Handles default JSON files (config, data, log) for seed modules.")
    console.print("  Never manually create JSONs - they build themselves on first use.")
    console.print()

    # KEY FUNCTIONS
    console.print("[bold white]KEY FUNCTIONS:[/bold white]")
    console.print()

    console.print("[bold cyan]1. AUTO-DETECTION[/bold cyan] [dim](_get_caller_module_name)[/dim]")
    console.print("   Automatically detects the calling module name from the call stack")
    console.print("   [green]module_name = _get_caller_module_name()  # 'imports_standard'[/green]")
    console.print()

    console.print("[bold cyan]2. TEMPLATE LOADING[/bold cyan] [dim](load_template)[/dim]")
    console.print("   Loads JSON templates and replaces placeholders")
    console.print("   [green]template = load_template('config', 'imports_standard')[/green]")
    console.print("   [dim]Replaces: {{MODULE_NAME}}, {{TIMESTAMP}}[/dim]")
    console.print()

    console.print("[bold cyan]3. STRUCTURE VALIDATION[/bold cyan] [dim](validate_json_structure)[/dim]")
    console.print("   Validates JSON structure matches expected type")
    console.print("   [green]if validate_json_structure(data, 'config'):[/green]")
    console.print("   [dim]Config requires: module_name, version, config[/dim]")
    console.print("   [dim]Data requires: created, last_updated[/dim]")
    console.print("   [dim]Log requires: list structure[/dim]")
    console.print()

    console.print("[bold cyan]4. AUTO-CREATION[/bold cyan] [dim](ensure_json_exists)[/dim]")
    console.print("   Creates JSON from template if missing or corrupted")
    console.print("   [green]ensure_json_exists('imports_standard', 'config')[/green]")
    console.print("   [dim]• Checks if file exists[/dim]")
    console.print("   [dim]• Validates structure[/dim]")
    console.print("   [dim]• Regenerates if corrupted[/dim]")
    console.print()

    console.print("[bold cyan]5. LOAD & SAVE[/bold cyan] [dim](load_json, save_json)[/dim]")
    console.print("   Load and save JSON files with auto-creation")
    console.print("   [green]data = load_json('imports_standard', 'data')[/green]")
    console.print("   [green]save_json('imports_standard', 'data', updated_data)[/green]")
    console.print("   [dim]Auto-updates 'last_updated' timestamp[/dim]")
    console.print()

    console.print("[bold cyan]6. LOG OPERATIONS[/bold cyan] [dim](log_operation)[/dim]")
    console.print("   Add entries to module log with automatic rotation")
    console.print("   [green]json_handler.log_operation('validation_run', {'files': 42})[/green]")
    console.print("   [dim]• Auto-detects calling module[/dim]")
    console.print("   [dim]• Creates all 3 JSONs if needed[/dim]")
    console.print("   [dim]• Rotates log when max_log_entries reached (FIFO)[/dim]")
    console.print()

    console.print("[bold cyan]7. COUNTER MANAGEMENT[/bold cyan] [dim](increment_counter)[/dim]")
    console.print("   Increment counters in data JSON")
    console.print("   [green]increment_counter('imports_standard', 'validations_run', 1)[/green]")
    console.print()

    console.print("[bold cyan]8. METRICS UPDATE[/bold cyan] [dim](update_data_metrics)[/dim]")
    console.print("   Update multiple data metrics at once")
    console.print("   [green]update_data_metrics('module', last_run='2025-11-13', status='ok')[/green]")
    console.print()

    # TYPICAL WORKFLOW
    console.print("[bold white]TYPICAL WORKFLOW IN A MODULE:[/bold white]")
    console.print()
    console.print("[bold cyan]Step 1:[/bold cyan] Import the handler")
    console.print("   [dim]from seed.apps.handlers.json import json_handler[/dim]")
    console.print()

    console.print("[bold cyan]Step 2:[/bold cyan] Log operations (auto-creates all JSONs)")
    console.print("   [green]json_handler.log_operation('validation_started', {'target': file_path})[/green]")
    console.print("   [dim]Creates: module_config.json, module_data.json, module_log.json[/dim]")
    console.print()

    console.print("[bold cyan]Step 3:[/bold cyan] Update metrics as needed")
    console.print("   [green]json_handler.increment_counter(module_name, 'validations_run')[/green]")
    console.print("   [green]json_handler.update_data_metrics(module_name, last_status='pass')[/green]")
    console.print()

    console.print("[bold cyan]Step 4:[/bold cyan] Log completion")
    console.print("   [green]json_handler.log_operation('validation_complete', {'result': 'pass'})[/green]")
    console.print()

    # FILE LOCATIONS
    console.print("[bold white]FILE LOCATIONS:[/bold white]")
    console.print("  Templates: [cyan]/home/aipass/seed/apps/json_templates/default/[/cyan]")
    console.print("    - config.json")
    console.print("    - data.json")
    console.print("    - log.json")
    console.print()
    console.print("  Generated: [cyan]/home/aipass/seed/seed_json/[/cyan]")
    console.print("    - {module_name}_config.json")
    console.print("    - {module_name}_data.json")
    console.print("    - {module_name}_log.json")
    console.print()

    # KEY FEATURES
    console.print("[bold white]KEY FEATURES:[/bold white]")
    console.print("  [green]✓[/green] Auto-detects calling module (no module_name needed)")
    console.print("  [green]✓[/green] Creates JSONs on first use (never manual creation)")
    console.print("  [green]✓[/green] Self-healing (regenerates corrupted files)")
    console.print("  [green]✓[/green] Log rotation (prevents unbounded growth)")
    console.print("  [green]✓[/green] Structure validation (ensures data integrity)")
    console.print("  [green]✓[/green] Template-based (consistent structure)")
    console.print("  [green]✓[/green] Timestamp management (auto-updates last_updated)")
    console.print()

    # CONSTANTS
    console.print("[bold white]CONSTANTS:[/bold white]")
    console.print("  [dim]SEED_ROOT = Path.home() / 'seed'[/dim]")
    console.print("  [dim]SEED_JSON_DIR = SEED_ROOT / 'seed_json'[/dim]")
    console.print("  [dim]JSON_TEMPLATES_DIR = SEED_ROOT / 'apps' / 'json_templates'[/dim]")
    console.print()

    console.print("─" * 70)
    console.print()


def handle_command(command: str, args: List[str]) -> bool:
    """
    Handle 'checklist' command

    Pattern: Return True if this module handled the command, False otherwise

    Args:
        command: Command name
        args: Additional arguments

    Returns:
        True if handled, False if not this module's command
    """
    if command != "checklist":
        return False  # Not our command

    # Check for introspect flag
    if "--introspect" in args or "introspect" in args:
        # Log introspection usage
        json_handler.log_operation(
            "introspect_shown",
            {"command": command, "args": args}
        )
        print_json_handler_introspection()
        return True

    # Log module usage - triggers JSON auto-creation
    json_handler.log_operation(
        "checklist_run",
        {"command": command, "args": args}
    )

    print_checklist(args)
    return True


def print_checklist(args: List[str]):
    """Print standards checklist and run checks"""

    MODULE_NAME = "standards_checklist"

    # Parse file path from args
    if len(args) == 0:
        # No file path provided - show usage
        console.print()
        header("Standards Checklist")
        console.print()
        console.print("[yellow]USAGE:[/yellow]")
        console.print("  python3 /home/aipass/seed/apps/modules/standards_checklist.py <module_path>")
        console.print()
        console.print("[yellow]EXAMPLES:[/yellow]")
        console.print("  # Check a seed module")
        console.print("  python3 /home/aipass/seed/apps/modules/standards_checklist.py /home/aipass/seed/apps/modules/imports_standard.py")
        console.print()
        console.print("  # Check a different branch module")
        console.print("  python3 /home/aipass/seed/apps/modules/standards_checklist.py /home/aipass/aipass_core/api/apps/api.py")
        console.print()
        console.print("[yellow]AVAILABLE CHECKERS (17/17 COMPLETE):[/yellow]")
        console.print("  [green]✓[/green] imports_check          - Import standards validation")
        console.print("  [green]✓[/green] architecture_check     - Architecture standards validation")
        console.print("  [green]✓[/green] naming_check           - Naming standards validation")
        console.print("  [green]✓[/green] cli_check              - CLI standards validation")
        console.print("  [green]✓[/green] handlers_check         - Handler standards validation")
        console.print("  [green]✓[/green] modules_check          - Module standards validation")
        console.print("  [green]✓[/green] documentation_check    - Documentation standards validation")
        console.print("  [green]✓[/green] json_structure_check   - JSON structure standards validation")
        console.print("  [green]✓[/green] testing_check          - Testing standards validation")
        console.print("  [green]✓[/green] error_handling_check   - Error handling standards validation")
        console.print("  [green]✓[/green] encapsulation_check    - Handler encapsulation (cross-branch/package imports)")
        console.print("  [green]✓[/green] log_level_check        - Log level hygiene (ERROR vs WARNING)")
        console.print("  [green]✓[/green] log_handler_check      - Log handler rotation (RotatingFileHandler required)")
        console.print("  [green]✓[/green] log_visibility_check   - Log visibility (prax system_logger required)")
        console.print("  [green]✓[/green] permission_flags_check - Permission flags (no --skip-permissions)")
        console.print()
        console.print("─" * 70)
        console.print()
        return

    # Get file path
    file_path = args[0]

    logger.info(f"[{MODULE_NAME}] Starting standards compliance check on {file_path}")

    # Detect branch and setup .seed/ config
    branch = get_branch_from_path(file_path)
    bypass_rules = []
    branch_name = "Unknown"
    branch_path = None

    if branch:
        branch_name = branch.get('name', 'Unknown')
        branch_path = branch.get('path', '')
        bypass_rules = load_bypass_rules(branch_path)
        logger.info(f"[{MODULE_NAME}] Branch: {branch_name}, Bypass rules: {len(bypass_rules)}")

    # Run checklist
    console.print()
    header(f"Standards Checklist - {file_path}")
    console.print()

    # Show branch info
    console.print(f"[dim]Branch: {branch_name}[/dim]")
    if branch_path:
        bypass_file = Path(branch_path) / ".seed" / "bypass.json"
        console.print(f"[dim]Bypass config: {bypass_file}[/dim]")
        if bypass_rules:
            console.print(f"[dim]Active bypasses: {len(bypass_rules)}[/dim]")
    console.print()
    console.print()

    # Run imports check
    logger.info(f"[{MODULE_NAME}] Running IMPORTS standard check on {file_path}")
    console.print("[bold cyan]IMPORTS STANDARD:[/bold cyan]")
    imports_result = imports_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in imports_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    imports_score = imports_result['score']
    imports_status = "[green]PASS[/green]" if imports_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {imports_score}/100 - {imports_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] IMPORTS check complete: {imports_score}/100")

    # Run architecture check
    logger.info(f"[{MODULE_NAME}] Running ARCHITECTURE standard check on {file_path}")
    console.print("[bold cyan]ARCHITECTURE STANDARD:[/bold cyan]")
    architecture_result = architecture_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in architecture_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    architecture_score = architecture_result['score']
    architecture_status = "[green]PASS[/green]" if architecture_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {architecture_score}/100 - {architecture_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] ARCHITECTURE check complete: {architecture_score}/100")

    # Run naming check
    logger.info(f"[{MODULE_NAME}] Running NAMING standard check on {file_path}")
    console.print("[bold cyan]NAMING STANDARD:[/bold cyan]")
    naming_result = naming_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in naming_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    naming_score = naming_result['score']
    naming_status = "[green]PASS[/green]" if naming_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {naming_score}/100 - {naming_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] NAMING check complete: {naming_score}/100")

    # Run CLI check
    logger.info(f"[{MODULE_NAME}] Running CLI standard check on {file_path}")
    console.print("[bold cyan]CLI STANDARD:[/bold cyan]")
    cli_result = cli_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in cli_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    cli_score = cli_result['score']
    cli_status = "[green]PASS[/green]" if cli_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {cli_score}/100 - {cli_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] CLI check complete: {cli_score}/100")

    # Run HANDLERS check
    logger.info(f"[{MODULE_NAME}] Running HANDLERS standard check on {file_path}")
    console.print("[bold cyan]HANDLERS STANDARD:[/bold cyan]")
    handlers_result = handlers_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in handlers_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    handlers_score = handlers_result['score']
    handlers_status = "[green]PASS[/green]" if handlers_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {handlers_score}/100 - {handlers_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] HANDLERS check complete: {handlers_score}/100")

    # Run modules check
    logger.info(f"[{MODULE_NAME}] Running MODULES standard check on {file_path}")
    console.print("[bold cyan]MODULES STANDARD:[/bold cyan]")
    modules_result = modules_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in modules_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    modules_score = modules_result['score']
    modules_status = "[green]PASS[/green]" if modules_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {modules_score}/100 - {modules_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] MODULES check complete: {modules_score}/100")

    # Run documentation check
    logger.info(f"[{MODULE_NAME}] Running DOCUMENTATION standard check on {file_path}")
    console.print("[bold cyan]DOCUMENTATION STANDARD:[/bold cyan]")
    documentation_result = documentation_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in documentation_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    documentation_score = documentation_result['score']
    documentation_status = "[green]PASS[/green]" if documentation_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {documentation_score}/100 - {documentation_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] DOCUMENTATION check complete: {documentation_score}/100")

    # Run JSON structure check
    logger.info(f"[{MODULE_NAME}] Running JSON_STRUCTURE standard check on {file_path}")
    console.print("[bold cyan]JSON STRUCTURE STANDARD:[/bold cyan]")
    json_structure_result = json_structure_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in json_structure_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    json_structure_score = json_structure_result['score']
    json_structure_status = "[green]PASS[/green]" if json_structure_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {json_structure_score}/100 - {json_structure_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] JSON_STRUCTURE check complete: {json_structure_score}/100")

    # Run testing check
    logger.info(f"[{MODULE_NAME}] Running TESTING standard check on {file_path}")
    console.print("[bold cyan]TESTING STANDARD:[/bold cyan]")
    testing_result = testing_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in testing_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    testing_score = testing_result['score']
    testing_status = "[green]PASS[/green]" if testing_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {testing_score}/100 - {testing_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] TESTING check complete: {testing_score}/100")

    # Run error handling check
    logger.info(f"[{MODULE_NAME}] Running ERROR_HANDLING standard check on {file_path}")
    console.print("[bold cyan]ERROR HANDLING STANDARD:[/bold cyan]")
    error_handling_result = error_handling_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in error_handling_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    error_handling_score = error_handling_result['score']
    error_handling_status = "[green]PASS[/green]" if error_handling_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {error_handling_score}/100 - {error_handling_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] ERROR_HANDLING check complete: {error_handling_score}/100")

    # Run encapsulation check
    logger.info(f"[{MODULE_NAME}] Running ENCAPSULATION standard check on {file_path}")
    console.print("[bold cyan]ENCAPSULATION STANDARD:[/bold cyan]")
    encapsulation_result = encapsulation_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in encapsulation_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    encapsulation_score = encapsulation_result['score']
    encapsulation_status = "[green]PASS[/green]" if encapsulation_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {encapsulation_score}/100 - {encapsulation_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] ENCAPSULATION check complete: {encapsulation_score}/100")

    # Run trigger check
    logger.info(f"[{MODULE_NAME}] Running TRIGGER standard check on {file_path}")
    console.print("[bold cyan]TRIGGER STANDARD:[/bold cyan]")
    trigger_result = trigger_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in trigger_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    trigger_score = trigger_result['score']
    trigger_status = "[green]PASS[/green]" if trigger_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {trigger_score}/100 - {trigger_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] TRIGGER check complete: {trigger_score}/100")

    # Run log level check
    logger.info(f"[{MODULE_NAME}] Running LOG_LEVEL standard check on {file_path}")
    console.print("[bold cyan]LOG LEVEL STANDARD:[/bold cyan]")
    log_level_result = log_level_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in log_level_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    log_level_score = log_level_result['score']
    log_level_status = "[green]PASS[/green]" if log_level_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {log_level_score}/100 - {log_level_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] LOG_LEVEL check complete: {log_level_score}/100")

    # Run CLI flags check
    logger.info(f"[{MODULE_NAME}] Running CLI_FLAGS standard check on {file_path}")
    console.print("[bold cyan]CLI FLAGS STANDARD:[/bold cyan]")
    cli_flags_result = cli_flags_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in cli_flags_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    cli_flags_score = cli_flags_result['score']
    cli_flags_status = "[green]PASS[/green]" if cli_flags_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {cli_flags_score}/100 - {cli_flags_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] CLI_FLAGS check complete: {cli_flags_score}/100")

    # Run log handler check
    logger.info(f"[{MODULE_NAME}] Running LOG_HANDLER standard check on {file_path}")
    console.print("[bold cyan]LOG HANDLER STANDARD:[/bold cyan]")
    log_handler_result = log_handler_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in log_handler_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    log_handler_score = log_handler_result['score']
    log_handler_status = "[green]PASS[/green]" if log_handler_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {log_handler_score}/100 - {log_handler_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] LOG_HANDLER check complete: {log_handler_score}/100")

    # Run log visibility check
    logger.info(f"[{MODULE_NAME}] Running LOG_VISIBILITY standard check on {file_path}")
    console.print("[bold cyan]LOG VISIBILITY STANDARD:[/bold cyan]")
    log_visibility_result = log_visibility_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in log_visibility_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    log_visibility_score = log_visibility_result['score']
    log_visibility_status = "[green]PASS[/green]" if log_visibility_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {log_visibility_score}/100 - {log_visibility_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] LOG_VISIBILITY check complete: {log_visibility_score}/100")

    # Run permission flags check
    logger.info(f"[{MODULE_NAME}] Running PERMISSION_FLAGS standard check on {file_path}")
    console.print("[bold cyan]PERMISSION FLAGS STANDARD:[/bold cyan]")
    permission_flags_result = permission_flags_check.check_module(file_path, bypass_rules=bypass_rules)

    # Display results
    for check in permission_flags_result['checks']:
        symbol = "[green]✓[/green]" if check['passed'] else "[red]✗[/red]"
        console.print(f"  {symbol} {check['name']}: {check['message']}")

    console.print()

    # Show score
    permission_flags_score = permission_flags_result['score']
    permission_flags_status = "[green]PASS[/green]" if permission_flags_result['passed'] else "[red]FAIL[/red]"
    console.print(f"  Score: {permission_flags_score}/100 - {permission_flags_status}")
    console.print()
    logger.info(f"[{MODULE_NAME}] PERMISSION_FLAGS check complete: {permission_flags_score}/100")

    # Overall summary
    avg_score = int((imports_score + architecture_score + naming_score + cli_score + handlers_score + modules_score + documentation_score + json_structure_score + testing_score + error_handling_score + encapsulation_score + trigger_score + log_level_score + cli_flags_score + log_handler_score + log_visibility_score + permission_flags_score) / 17)
    console.print("─" * 70)
    console.print(f"[bold]OVERALL:[/bold] 17/17 standards checked - {avg_score}% average compliance")
    console.print("─" * 70)
    console.print()
    logger.info(f"[{MODULE_NAME}] Standards check complete: {avg_score}% average compliance")


if __name__ == "__main__":
    # Handle help flag (drone compliance)
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        print_help()
        sys.exit(0)

    # Confirm Prax logger connection
    logger.info("Prax logger connected to standards_checklist")

    # Check for introspect flag
    if len(sys.argv) > 1 and sys.argv[1] in ['--introspect', 'introspect']:
        # Log standalone introspection - triggers JSON auto-creation
        json_handler.log_operation(
            "introspect_shown",
            {"command": "standalone"}
        )
        print_json_handler_introspection()
    else:
        # Log standalone execution - triggers JSON auto-creation
        # Pass file path arguments (skip script name)
        file_args = sys.argv[1:] if len(sys.argv) > 1 else []
        json_handler.log_operation(
            "checklist_run",
            {"command": "standalone", "args": file_args}
        )
        print_checklist(file_args)
