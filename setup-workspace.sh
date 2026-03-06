#!/bin/bash
set -e

WORKSPACE="/home/coder/workspace"
REPO="git@github.com:AIOSAI/AIPass.git"

export PATH="/opt/venv/bin:$PATH"

# Ensure workspace directory is writable by coder
if [ -d "$WORKSPACE" ] && [ ! -w "$WORKSPACE" ]; then
    echo "==> Fixing workspace permissions..."
    sudo chown -R coder:coder "$WORKSPACE"
fi

# Clone repo if not already present
if [ ! -d "$WORKSPACE/.git" ]; then
    echo "==> First boot: cloning AIPass from GitHub..."
    git clone "$REPO" "$WORKSPACE"
    echo "==> Installing AIPass in editable mode..."
    cd "$WORKSPACE"
    pip install -e .
    echo "==> Workspace ready!"
else
    echo "==> Workspace exists, ensuring deps are installed..."
    cd "$WORKSPACE"
    pip install -e . 2>/dev/null || true
fi
