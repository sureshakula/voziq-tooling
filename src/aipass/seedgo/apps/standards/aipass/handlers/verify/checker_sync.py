#!/home/aipass/.venv/bin/python3

# ===================AIPASS====================
# META DATA HEADER
# Name: checker_sync.py - Checker Documentation Sync Check
# Date: 2025-12-04
# Version: 0.1.0
# Category: seed/handlers/verify
#
# CHANGELOG (Max 5 entries):
#   - v0.1.0 (2025-12-04): Initial - verifies checker patterns match docs
#
# CODE STANDARDS:
#   - Pure handler - returns check data dict
#   - Verifies pattern counts match between checker and content handler
# =============================================

"""
Checker Documentation Sync Check

Verifies that checker implementations match their documentation.
Catches drift between trigger_check.py patterns and trigger_content.py docs.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List

# =============================================================================
# INFRASTRUCTURE SETUP
# =============================================================================

AIPASS_ROOT = Path.home() / "aipass_core"
SEED_ROOT = Path.home() / "seed"
sys.path.insert(0, str(AIPASS_ROOT))
sys.path.insert(0, str(Path.home()))


def check_checker_sync() -> Dict:
    """
    Verify checker implementations match their documentation

    Checks:
    - trigger_check.py pattern count matches trigger_content.py
    - trigger.md documents the checker patterns
    - README.md standards count is accurate
    - verify --help lists all actual checks

    Returns:
        Dict with check results
    """
    issues = []
    checked = []

    # Check trigger_check.py vs trigger_content.py
    trigger_check_path = SEED_ROOT / "apps/handlers/standards/trigger_check.py"
    trigger_content_path = SEED_ROOT / "apps/handlers/standards/trigger_content.py"

    if trigger_check_path.exists() and trigger_content_path.exists():
        check_content = trigger_check_path.read_text()
        content_content = trigger_content_path.read_text()

        # Count pattern categories in trigger_check.py
        # Look for "# Pattern N:" comments
        pattern_matches = re.findall(r'#\s*Pattern\s+(\d+):', check_content)
        check_pattern_count = len(set(pattern_matches))

        # Get version from trigger_check.py
        version_match = re.search(r'#\s*Version:\s*([\d.]+)', check_content)
        check_version = version_match.group(1) if version_match else "unknown"

        # Check if trigger_content.py mentions pattern count
        # Match "10 pattern categories" or "10 categories" or "(10 categories)"
        content_pattern_count_match = re.search(r'(\d+)\s*(?:pattern\s*)?categor', content_content, re.IGNORECASE)
        content_pattern_count = int(content_pattern_count_match.group(1)) if content_pattern_count_match else 0

        checked.append(f"trigger_check.py v{check_version}: {check_pattern_count} pattern categories")

        if content_pattern_count > 0:
            checked.append(f"trigger_content.py documents: {content_pattern_count} pattern categories")

            if check_pattern_count != content_pattern_count:
                issues.append(f"Pattern count mismatch: trigger_check.py has {check_pattern_count}, trigger_content.py documents {content_pattern_count}")
        else:
            issues.append("trigger_content.py doesn't document pattern category count")

        # Check for specific keywords in checker that should be documented
        key_terms = [
            ('unlink', '.unlink() detection'),
            ('rename', '.rename() detection'),
            ('auto_close_', 'auto_close_* pattern'),
            ('recover_', 'recover_* pattern'),
            ('cleanup_', 'cleanup_* pattern'),
            ('backup_', 'backup_* pattern'),
            ('heal_', 'heal_* pattern'),
            ('aggregate_central', 'aggregate_central pattern'),
        ]

        for term, name in key_terms:
            if term in check_content:
                if term not in content_content:
                    # Term in checker but not in content docs
                    issues.append(f"{name} in checker but not documented in trigger_content.py")
    else:
        if not trigger_check_path.exists():
            issues.append("trigger_check.py not found")
        if not trigger_content_path.exists():
            issues.append("trigger_content.py not found")

    # Define common paths
    checkers_dir = SEED_ROOT / "apps/handlers/standards"

    # Check README.md standards count
    readme_path = SEED_ROOT / "README.md"
    if readme_path.exists():
        readme_content = readme_path.read_text()
        # Count actual checker files
        if checkers_dir.exists():
            actual_checkers = len([f for f in checkers_dir.glob("*_check.py")])
            # Find claimed count in README (e.g., "10 Standards" or "12 standards")
            readme_count_match = re.search(r'(\d+)\s*[Ss]tandards?\s*[Mm]odules?', readme_content)
            if readme_count_match:
                readme_count = int(readme_count_match.group(1))
                checked.append(f"README.md claims {readme_count} standards, {actual_checkers} checkers exist")
                if readme_count != actual_checkers:
                    issues.append(f"README.md says {readme_count} standards but {actual_checkers} checkers exist")

    # Check verify --help lists all checks
    verify_module_path = SEED_ROOT / "apps/modules/standards_verify.py"
    orchestrator_path = SEED_ROOT / "apps/handlers/verify/orchestrator.py"
    if verify_module_path.exists() and orchestrator_path.exists():
        verify_content = verify_module_path.read_text()
        orchestrator_content = orchestrator_path.read_text()

        # Count checks in orchestrator (check_* calls in the checks list)
        actual_checks = len(re.findall(r'check_\w+\(\)', orchestrator_content))

        # Count checks documented in verify --help (lines with "[green]N.[/green]")
        documented_checks = len(re.findall(r'\[green\]\d+\.\[/green\]', verify_content))

        checked.append(f"verify --help documents {documented_checks} checks, orchestrator has {actual_checks}")
        if documented_checks != actual_checks:
            issues.append(f"verify --help shows {documented_checks} checks but orchestrator runs {actual_checks}")

    # Check trigger.md documents pattern categories
    trigger_md_path = SEED_ROOT / "standards/CODE_STANDARDS/trigger.md"
    if trigger_md_path.exists() and trigger_check_path.exists():
        trigger_md_content = trigger_md_path.read_text()
        check_content = trigger_check_path.read_text()

        # Get pattern count from checker
        pattern_matches = re.findall(r'#\s*Pattern\s+(\d+):', check_content)
        check_pattern_count = len(set(pattern_matches))

        # Check if trigger.md mentions pattern categories
        md_pattern_match = re.search(r'(\d+)\s*(?:pattern\s*)?categor', trigger_md_content, re.IGNORECASE)
        if md_pattern_match:
            md_count = int(md_pattern_match.group(1))
            if md_count != check_pattern_count:
                issues.append(f"trigger.md documents {md_count} categories but checker has {check_pattern_count}")
        else:
            # Check if it at least mentions key patterns
            if 'unlink' not in trigger_md_content.lower() and 'unlink' in check_content:
                issues.append("trigger.md doesn't document inline filesystem detection (.unlink/.rename)")

    # Check each checker has corresponding CODE_STANDARDS doc
    code_standards_dir = SEED_ROOT / "standards/CODE_STANDARDS"
    if checkers_dir.exists() and code_standards_dir.exists():
        checker_names = [f.stem.replace('_check', '') for f in checkers_dir.glob("*_check.py")]
        doc_names = [f.stem for f in code_standards_dir.glob("*.md") if f.stem not in ['README', '_template']]

        missing_docs = [c for c in checker_names if c not in doc_names]
        if missing_docs:
            issues.append(f"Checkers missing CODE_STANDARDS docs: {missing_docs}")

    # Check docs/checkers.md mentions all checkers
    checkers_doc_path = SEED_ROOT / "docs/checkers.md"
    if checkers_doc_path.exists() and checkers_dir.exists():
        checkers_doc_content = checkers_doc_path.read_text()
        checker_files = [f.name for f in checkers_dir.glob("*_check.py")]

        missing_in_doc = []
        for checker in checker_files:
            checker_name = checker.replace('_check.py', '')
            if checker_name not in checkers_doc_content.lower():
                missing_in_doc.append(checker_name)

        if missing_in_doc:
            issues.append(f"docs/checkers.md missing: {missing_in_doc}")

    # Check SEED.id.json standards count
    seed_id_path = SEED_ROOT / "SEED.id.json"
    if seed_id_path.exists() and checkers_dir.exists():
        seed_id_content = seed_id_path.read_text()
        actual_checkers = len([f for f in checkers_dir.glob("*_check.py")])

        # Find any "N standards" or "N core standards" mentions
        id_counts = re.findall(r'(\d+)\s*(?:core\s*)?(?:AIPass\s*)?(?:code\s*)?standards?', seed_id_content, re.IGNORECASE)
        for count_str in set(id_counts):
            count = int(count_str)
            if count != actual_checkers:
                issues.append(f"SEED.id.json says {count} standards but {actual_checkers} checkers exist")

    # Check seed.py --help for consistent standards count
    seed_entry_path = SEED_ROOT / "apps/seed.py"
    if seed_entry_path.exists() and checkers_dir.exists():
        seed_py_content = seed_entry_path.read_text()
        actual_checkers = len([f for f in checkers_dir.glob("*_check.py")])

        # Find standards count mentions
        seed_py_counts = re.findall(r'(\d+)\s*(?:queryable\s*)?(?:code\s*)?standards?', seed_py_content, re.IGNORECASE)
        wrong_counts = [int(c) for c in set(seed_py_counts) if int(c) != actual_checkers and int(c) > 5]
        if wrong_counts:
            issues.append(f"seed.py mentions {wrong_counts} standards but {actual_checkers} checkers exist")

    return {
        'name': 'Checker-Doc Sync',
        'passed': len(issues) == 0,
        'checked': checked,
        'issues': issues
    }
