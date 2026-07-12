#!/usr/bin/env bash
#
# Regression test for setup.sh safe_symlink guard (GitHub #660).
#
# #660: `aipass install` (via setup.sh) must NEVER silently repoint a global
# `drone`/`aipass` symlink that points at a DIFFERENT install. This test sources
# the real safe_symlink function out of setup.sh and asserts its behaviour across
# the meaningful cases. Exits 0 on all-pass, non-zero on any regression.
#
# Run: bash tests/setup_symlink_guard_test.sh
set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SETUP="$REPO_ROOT/setup.sh"
TMP="$(mktemp -d)"
FAILURES=0

cleanup() { rm -f "$TMP"/binA/* "$TMP"/binB/* "$TMP"/dest/* 2>/dev/null; rmdir "$TMP"/binA "$TMP"/binB "$TMP"/dest "$TMP" 2>/dev/null; }
trap cleanup EXIT

# Pull the real safe_symlink out of setup.sh (single source of truth — no copy).
FN="$TMP/fn.sh"
sed -n '/^safe_symlink() {/,/^}/p' "$SETUP" > "$FN"
if ! grep -q "safe_symlink()" "$FN"; then
    echo "FAIL: could not extract safe_symlink from $SETUP"
    exit 1
fi
# shellcheck disable=SC1090
source "$FN"

mkdir -p "$TMP/binA" "$TMP/binB" "$TMP/dest"
echo A > "$TMP/binA/aipass"
echo B > "$TMP/binB/aipass"
echo A > "$TMP/binA/drone"

assert() { # assert <label> <expected> <actual>
    if [ "$2" = "$3" ]; then
        echo "  PASS: $1"
    else
        echo "  FAIL: $1 (expected '$2', got '$3')"
        FAILURES=$((FAILURES + 1))
    fi
}

FORCE_SYMLINK="no"; SYMLINK_SKIPPED=0

# Case 1: dest missing -> link, rc 0
safe_symlink "$TMP/binA/aipass" "$TMP/dest/aipass" >/dev/null; rc=$?
assert "fresh link returns 0" "0" "$rc"
assert "fresh link points at src" "$TMP/binA/aipass" "$(readlink "$TMP/dest/aipass")"

# Case 2: dest already points at same src (re-install same location) -> rc 0, no warn
safe_symlink "$TMP/binA/aipass" "$TMP/dest/aipass" >/dev/null; rc=$?
assert "same-target relink returns 0" "0" "$rc"

# Case 3: dest points at a DIFFERENT install, no force -> rc 1, target UNCHANGED
safe_symlink "$TMP/binB/aipass" "$TMP/dest/aipass" >/dev/null; rc=$?
assert "different-target without force returns 1 (skip)" "1" "$rc"
assert "different-target NOT repointed (no silent hijack)" "$TMP/binA/aipass" "$(readlink "$TMP/dest/aipass")"
assert "skip counter incremented" "1" "$SYMLINK_SKIPPED"

# Case 4: same, but --force-symlink -> rc 0, repointed
FORCE_SYMLINK="yes"
safe_symlink "$TMP/binB/aipass" "$TMP/dest/aipass" >/dev/null; rc=$?
assert "different-target WITH force returns 0" "0" "$rc"
assert "force repoints to new src" "$TMP/binB/aipass" "$(readlink "$TMP/dest/aipass")"

# Case 5: dest is a REAL file (not a symlink), no force -> rc 1, file intact
FORCE_SYMLINK="no"
echo realfile > "$TMP/dest/drone"
safe_symlink "$TMP/binA/drone" "$TMP/dest/drone" >/dev/null; rc=$?
assert "real-file dest without force returns 1 (skip)" "1" "$rc"
assert "real-file dest left intact" "realfile" "$(cat "$TMP/dest/drone" 2>/dev/null)"

echo ""
if [ "$FAILURES" -eq 0 ]; then
    echo "setup_symlink_guard_test: ALL PASS"
    exit 0
fi
echo "setup_symlink_guard_test: $FAILURES FAILURE(S)"
exit 1
