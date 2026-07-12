#!/usr/bin/env bash
# install_boot_shim.sh — append the claude() shell function to ~/.bashrc and ~/.zshrc
#
# Usage: bash tools/install_boot_shim.sh
#
# The shim intercepts 'claude' in AIPass branch directories (those with .trinity/)
# and delegates to the session_boot wrapper. Everywhere else, claude runs normally.
# Safe to run multiple times — skips if already installed.

set -euo pipefail

MARKER="# >>> AIPass boot shim >>>"

# Resolve THIS repo's venv Python from the script's own location — no hardcoded
# user path. POSIX (.venv/bin/python) + Windows/git-bash (.venv/Scripts/python.exe)
# aware; falls back to PATH python3 if no venv is found.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    VENV_PY="$REPO_ROOT/.venv/bin/python"
elif [ -x "$REPO_ROOT/.venv/Scripts/python.exe" ]; then
    VENV_PY="$REPO_ROOT/.venv/Scripts/python.exe"
else
    VENV_PY="python3"
fi

SHIM='
# >>> AIPass boot shim >>>
# Intercepts claude in AIPass branch dirs to attach-if-live / start-in-tmux.
# Installed by: tools/install_boot_shim.sh
claude() {
    if [ -d ".trinity" ]; then
        __VENV_PY__ \
            -m aipass.hooks.apps.handlers.lifecycle.session_boot "$@"
    else
        command claude "$@"
    fi
}
# <<< AIPass boot shim <<<
'

# Bake the resolved interpreter into the shim (single-quoted above kept "$@" literal).
SHIM="${SHIM//__VENV_PY__/$VENV_PY}"

for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ ! -f "$rc" ]; then
        echo "⏭  $rc does not exist, skipping"
        continue
    fi
    if grep -qF "$MARKER" "$rc"; then
        echo "✓  $rc already has the shim"
    else
        printf '%s\n' "$SHIM" >> "$rc"
        echo "✓  Appended shim to $rc"
    fi
done

echo ""
echo "Done. Source your shell rc or open a new terminal to activate:"
echo "  source ~/.bashrc   # or ~/.zshrc"
