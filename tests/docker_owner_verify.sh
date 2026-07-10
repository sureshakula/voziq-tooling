#!/usr/bin/env bash
#
# Owner-capability Dev-Docker verify — SOP artifact for the #678 owner-capability
# model. Runs INSIDE the container (aipass-test image): real GitHub clone of dev,
# one-command install, then proves the owner primitive on a REAL fresh install and
# on a brand-NEW project whose first agent becomes the owner (project manager).
#
# Host invocation:
#   docker run --rm -v "<AIPASS>/tests/docker_owner_verify.sh":/verify.sh:ro \
#     aipass-test:latest bash /verify.sh
#
set -uo pipefail

PASS=0
FAIL=0
ok()  { echo "  OK   $1"; PASS=$((PASS+1)); }
bad() { echo "  FAIL $1"; FAIL=$((FAIL+1)); }

echo "==============================================="
echo "  AIPass Owner-Capability Dev-Docker Verify (#678)"
echo "==============================================="

# --- Phase 1: real clone of dev + install ---
echo "--- Phase 1: clone dev + ./aipass install ---"
rm -rf "$HOME/workspace" && mkdir -p "$HOME/workspace" && cd "$HOME/workspace"
if git clone -b dev --depth 1 https://github.com/AIOSAI/AIPass.git 2>&1 | tail -1; then
    ok "clone dev"
else
    bad "clone dev"; echo "Cannot continue."; exit 1
fi
cd AIPass
AH="$HOME/workspace/AIPass"
echo "  HEAD: $(git log -1 --oneline)"
if ./aipass install 2>&1 | tail -5; then ok "installer exit 0"; else bad "installer non-zero"; fi

VPY="$AH/.venv/bin/python3"
DRONE="$AH/.venv/bin/drone"

# --- Phase 2: owner-capability CODE ships in the fresh install ---
echo "--- Phase 2: code ships (resolvers + gate) ---"
if "$VPY" -c "from aipass.spawn.apps.handlers.registry import get_owner, is_owner" 2>/dev/null; then
    ok "is_owner/get_owner importable"
else
    bad "resolvers not importable"
fi
if [ -f "$AH/src/aipass/hooks/apps/handlers/security/registry_gate.py" ]; then
    ok "registry_gate.py present"
else
    bad "registry_gate.py missing"
fi
if "$VPY" -c "from aipass.hooks.apps.handlers.security.registry_gate import handle" 2>/dev/null; then
    ok "registry_gate importable"
else
    bad "registry_gate not importable"
fi

# --- Phase 3: NEW PROJECT — first agent becomes the owner (project manager) ---
echo "--- Phase 3: new project, first agent = owner ---"
PROJ="$HOME/proj_acme"
rm -rf "$PROJ"
cd "$AH/src/aipass/spawn"   # run drone from a passport-bearing CWD
"$DRONE" @spawn create "$PROJ/manager" --purpose "Acme project manager" 2>&1 | tail -4

REG=$(find "$PROJ" -name "*_REGISTRY.json" 2>/dev/null | head -1)
if [ -n "$REG" ] && [ -f "$REG" ]; then
    ok "new project registry created ($REG)"
else
    bad "no registry created under $PROJ"; echo "Cannot continue Phase 3.";
fi

if [ -n "$REG" ]; then
  OWNERS=$(jq -r '[.branches[] | select(.owner==true) | .name] | join(",")' "$REG" 2>/dev/null)
  if [ "$(echo "$OWNERS" | tr ',' '\n' | grep -c .)" = "1" ]; then ok "exactly one owner ($OWNERS)"; else bad "owner count wrong: [$OWNERS]"; fi
  if echo "$OWNERS" | grep -qi "manager"; then ok "owner is the first agent (manager)"; else bad "owner is not manager: [$OWNERS]"; fi

  # Resolver against the new project
  "$VPY" - "$PROJ" <<'PYEOF'
import sys
from aipass.spawn.apps.handlers.registry import get_owner, is_owner
proj = sys.argv[1]
o = get_owner(proj)
name = (o or {}).get("name"); email = (o or {}).get("email")
print("  OK   get_owner(new proj) -> %s (%s)" % (name, email)) if o else print("  FAIL get_owner returned None")
print("  OK   is_owner(manager)=True")  if is_owner(email or "@manager", proj) else print("  FAIL is_owner(owner) False")
print("  FAIL is_owner(@nobody)=True (should be False)") if is_owner("@nobody_xyz", proj) else print("  OK   is_owner(@nobody)=False")
PYEOF
fi

# --- Phase 4: second agent is NOT the owner ---
echo "--- Phase 4: second agent stays non-owner ---"
"$DRONE" @spawn create "$PROJ/worker" --purpose "Acme worker" 2>&1 | tail -2
if [ -n "$REG" ]; then
  OWNERS2=$(jq -r '[.branches[] | select(.owner==true) | .name] | join(",")' "$REG" 2>/dev/null)
  CNT2=$(jq -r '.branches | length' "$REG" 2>/dev/null)
  if [ "$CNT2" = "2" ]; then ok "2 agents in project"; else bad "agent count: $CNT2 (want 2)"; fi
  if echo "$OWNERS2" | grep -qi "manager" && [ "$(echo "$OWNERS2" | tr ',' '\n' | grep -c .)" = "1" ]; then ok "owner still only manager after 2nd agent"; else bad "owner drifted: [$OWNERS2]"; fi
  "$VPY" - "$PROJ" <<'PYEOF'
import sys
from aipass.spawn.apps.handlers.registry import is_owner
proj = sys.argv[1]
print("  FAIL worker is_owner=True (should be False)") if is_owner("@worker", proj) else print("  OK   is_owner(@worker)=False")
PYEOF
fi

# --- Phase 5: gate seals the new project's registry ---
echo "--- Phase 5: registry_gate blocks raw write, allows drone @spawn ---"
"$VPY" - "$REG" <<'PYEOF'
import sys
from aipass.hooks.apps.handlers.security.registry_gate import handle
reg = sys.argv[1] if len(sys.argv) > 1 else "AIPASS_REGISTRY.json"
def R(tn, ti):
    r = handle({"tool_name": tn, "tool_input": ti})
    return "BLOCK" if r.get("exit_code") == 2 else "ALLOW"
cases = [
    ("raw write blocked",  R("Bash", {"command": "echo x > %s" % reg}) == "BLOCK"),
    ("Edit tool blocked",  R("Edit", {"file_path": reg}) == "BLOCK"),
    ("drone @spawn allowed",R("Bash", {"command": "drone @spawn create %s" % reg}) == "ALLOW"),
    ("read (cat) allowed",  R("Bash", {"command": "cat %s" % reg}) == "ALLOW"),
]
for name, good in cases:
    print("  OK   " + name) if good else print("  FAIL " + name)
PYEOF

# --- Summary ---
echo "==============================================="
echo "  Results: $PASS passed, $FAIL failed (bash) + inline python OK/FAIL above"
echo "==============================================="
[ "$FAIL" -eq 0 ]
