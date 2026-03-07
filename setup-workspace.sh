#!/bin/bash
set -e

WORKSPACE="/home/coder/workspace"
PROJECT="$WORKSPACE/AIPass"
FORK="https://github.com/Input-X/AIPass.git"
UPSTREAM="https://github.com/AIOSAI/AIPass.git"

export PATH="/opt/venv/bin:$PATH"

# Ensure workspace directory exists and is writable
mkdir -p "$WORKSPACE"
if [ ! -w "$WORKSPACE" ]; then
    echo "==> Fixing workspace permissions..."
    sudo chown -R coder:coder "$WORKSPACE"
fi

# Clone repo if not already present
if [ ! -d "$PROJECT/.git" ]; then
    echo "==> First boot: cloning into AIPass/..."
    git clone "$FORK" "$PROJECT"
    cd "$PROJECT"
    git remote add upstream "$UPSTREAM"
    echo "==> Installing AIPass in editable mode..."
    pip install -e .
    echo "==> Workspace ready!"
    echo "==> origin  = $FORK (your fork - push here)"
    echo "==> upstream = $UPSTREAM (pull updates from here)"
else
    echo "==> Workspace exists, ensuring deps are installed..."
    cd "$PROJECT"
    pip install -e . 2>/dev/null || true
fi
