#!/usr/bin/env bash
# Throwaway diagnostic: full ./aipass install output + exit code + symlink state.
set -uo pipefail
cd "$HOME" && rm -rf ws && mkdir ws && cd ws
git clone -b dev --depth 1 https://github.com/AIOSAI/AIPass.git 2>&1 | tail -1
cd AIPass
echo "===== FULL INSTALL OUTPUT ====="
./aipass install
rc=$?
echo "===== INSTALL_EXIT=$rc ====="
echo "===== global symlink state ====="
for p in "$HOME/.local/bin/drone" "$HOME/.local/bin/aipass" /usr/local/bin/drone /usr/local/bin/aipass; do
  if [ -L "$p" ]; then echo "SYMLINK $p -> $(readlink "$p")"; elif [ -e "$p" ]; then echo "FILE    $p"; else echo "absent  $p"; fi
done
