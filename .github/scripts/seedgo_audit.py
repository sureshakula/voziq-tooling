"""CI gate: run seedgo standards audit across all branches."""

import sys
from pathlib import Path

from aipass.seedgo.apps.handlers.audit.branch_audit import audit_branch
from aipass.seedgo.apps.handlers.bypass.bypass_handler import load_bypass_rules

THRESHOLD = 100

src = Path("src/aipass")
pack = src / "seedgo/apps/handlers/aipass_standards"

branches = []
for d in sorted(src.iterdir()):
    if d.is_dir() and (d / "apps").is_dir():
        entry = d / "apps" / f"{d.name}.py"
        branches.append(
            {
                "name": d.name,
                "path": str(d),
                "entry_file": str(entry) if entry.exists() else "",
            }
        )

failed = []
for branch in branches:
    bypass_rules = load_bypass_rules(branch["path"])
    result = audit_branch(branch, bypass_rules, pack_path=pack)
    avg = result.get("average", 0)
    print(f"  {branch['name']:>12}: {avg:.0f}%")
    if avg < THRESHOLD:
        failed.append((branch["name"], avg, result))

if failed:
    print(f"\nFAILED: {len(failed)} branch(es) below {THRESHOLD}%")
    for name, score, result in failed:
        print(f"  {name}: {score:.0f}%")
        # Name the failing standards + the specific checks that did not pass,
        # so CI logs say WHY (not just the percentage). Critical for diagnosing
        # working-tree-vs-clean-checkout divergence.
        scores = result.get("scores", {})
        results = result.get("results", {})
        for std, sc in scores.items():
            if sc < 100:
                checks = results.get(std, {}).get("checks", [])
                msgs = [
                    c.get("message", "")
                    for c in checks
                    if not c.get("passed", True)
                ]
                detail = " | ".join(m for m in msgs if m)[:400]
                print(f"      └ {std}: {sc:.0f}%  {detail}")
    sys.exit(1)
else:
    print(f"\nAll {len(branches)} branches pass (>={THRESHOLD}%)")
