[← Back to DevPulse](README.md)

# DevPulse Setup, Uninstall, Troubleshooting

Everything you need to install, run, maintain, or remove DevPulse (and AIPass as a whole). Kept here so the DevPulse README can stay lean and loads quickly on every session startup.

---

## Platform support at a glance

| Platform | Install status | Notes |
|---|---|---|
| **Linux** (Ubuntu, Debian, Fedora, Arch) | Supported | Primary development target. `setup.sh` works out of the box. |
| **macOS** (Intel and Apple Silicon) | Supported | `setup.sh` works with minor caveats (see macOS section). |
| **Windows 10 / 11** | **In progress** | Native Windows support is actively being built. Track progress in [issue #261](https://github.com/AIOSAI/AIPass/issues/261). For now: use WSL2 (Ubuntu), or wait for the cross-platform `setup.py` landing in a PR soon. |

---

## Linux install

### Requirements

- Python 3.10 or newer (`python3 --version`)
- `git`, `bash`, `sudo`
- Claude Code CLI installed and authenticated (`claude --version`)
- ~500 MB disk for the venv and dependencies

### Install

```bash
git clone https://github.com/AIOSAI/AIPass.git ~/Projects/AIPass
cd ~/Projects/AIPass
bash setup.sh
```

`setup.sh` will:
1. Create a Python venv at `.venv/`
2. Install AIPass in editable mode (`pip install -e .`)
3. Verify the `drone` and `aipass` CLI entry points
4. Create `~/.secrets/aipass/` with `chmod 700` and seed an `.env.example`
5. Generate the AIPass branch registry
6. Bootstrap branch identity files (`.trinity/passport.json` per branch)
7. Wire Claude Code hooks into `~/.claude/settings.json`
8. Create a global symlink at `/usr/local/bin/drone` (asks for `sudo`)

### Post-install

```bash
# Verify
drone systems

# Enter the DevPulse branch
cd ~/Projects/AIPass/src/aipass/devpulse
claude
```

You should see DevPulse greet you, read its memory, and be ready.

### Optional

- Add API keys to `~/.secrets/aipass/.env` if you want LLM routing beyond Claude Code
- Set `AIPASS_HOME=~/Projects/AIPass` in your shell rc if you plan to use AIPass from other projects
- Add `export AIPASS_HOME=~/Projects/AIPass` to `~/.bashrc` **and** `~/.claude/settings.json` (the `env` section) — both are needed for full cross-project access

---

## macOS install

Same as Linux. `setup.sh` uses bash and runs on macOS out of the box.

**Caveats**:
- `chmod 700` and `chown` work correctly on macOS's HFS+ and APFS
- `sudo ln -sf /usr/local/bin/drone` works but may prompt for your admin password
- Homebrew users: if you have multiple Python installs, make sure `python3` points to Python 3.10+ before running `setup.sh`

---

## Windows install

**Short version**: use [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) (Ubuntu) and follow the Linux instructions. Full native Windows support is landing in a PR soon — follow [issue #261](https://github.com/AIOSAI/AIPass/issues/261) for status.

**Why it's in progress**: the current `setup.sh` uses bash, `sudo`, and `ln -sf /usr/local/bin/drone`, none of which translate to Windows. The `aipass init` command also writes a shell loop into `.claude/settings.json` that assumes Unix root `/`. Fixes are in flight:
- A cross-platform `setup.py` that replaces `setup.sh` on Windows
- A Python-based directory traversal replacing the bash loop in `aipass init`
- OS detection in `setup.sh` to skip the symlink step on Windows and print PATH instructions instead

**Interim workaround**: install WSL2 with an Ubuntu distribution, then clone and run `setup.sh` inside WSL. Claude Code also runs well inside WSL.

---

## Uninstall

### Full removal (Linux / macOS)

```bash
# 1. Remove the venv and repo
rm -rf ~/Projects/AIPass

# 2. Remove the global drone symlink
sudo rm /usr/local/bin/drone

# 3. Remove secrets (if you won't reinstall)
rm -rf ~/.secrets/aipass

# 4. Clean Claude Code hooks
# Edit ~/.claude/settings.json and remove any "hooks" sections that reference AIPass paths.
# Safer: back up the file first.
cp ~/.claude/settings.json ~/.claude/settings.json.bak
nano ~/.claude/settings.json   # or your editor of choice

# 5. Clean your shell rc
# Remove any AIPASS_HOME export from ~/.bashrc, ~/.zshrc, etc.
```

### Partial removal (keeping secrets for reinstall)

Skip step 3 above. Your `~/.secrets/aipass/.env` will persist and be reused on next install.

### Windows (WSL2)

Same as Linux, inside the WSL distribution. To also remove the WSL distribution itself: `wsl --unregister Ubuntu` from PowerShell.

---

## Troubleshooting

### `drone: command not found`

Your venv is not activated or the `/usr/local/bin/drone` symlink is missing.

```bash
# Option A: activate the venv
source ~/Projects/AIPass/.venv/bin/activate
drone systems

# Option B: run via full path
~/Projects/AIPass/.venv/bin/drone systems

# Option C: reinstall the symlink
sudo ln -sf ~/Projects/AIPass/.venv/bin/drone /usr/local/bin/drone
```

### `AIPASS_HOME not set` warnings

```bash
# In your shell rc (~/.bashrc or ~/.zshrc)
export AIPASS_HOME=~/Projects/AIPass

# Then restart the shell or:
source ~/.bashrc
```

Also add it to `~/.claude/settings.json` under the `env` block for Claude Code sessions to pick it up.

### DevPulse greets you but doesn't read its memory

Check that `.trinity/passport.json`, `.trinity/local.json`, and `.trinity/observations.json` exist in `src/aipass/devpulse/`. If they don't, run `bash setup.sh` again to re-bootstrap the identity files.

### `drone @git system-pr` fails with a lock error

```bash
drone @git lock           # check the lock state
drone @git fix            # attempt to fix broken git state
```

Do NOT use raw `git reset --hard` — merge conflicts are easier to resolve than lost work.

### Branch mail not arriving

```bash
drone @ai_mail inbox      # check your inbox
drone @prax watch         # watch the monitoring dashboard
```

A known issue at the end of S90 affected wake delivery; see the wake investigation in DPLAN-0125 Track E if you're running a recent build.

### Tests fail on a fresh clone

```bash
cd ~/Projects/AIPass
source .venv/bin/activate
python -m pytest src/aipass/<branch>/tests/
```

If tests fail because `AIPASS_HOME` leaks the real registry into test results, that's a known pattern — the tests need `monkeypatch.delenv("AIPASS_HOME")`. See S90 notes for the fixture pattern.

### `.claude/settings.json` has hardcoded absolute paths

You pulled an old clone. The hardcoded paths were removed in commit `867dad0` (April 5, 2026). Pull the latest main and re-run `setup.sh`, which generates the settings dynamically from your local repo root.

---

## Environment variables

| Variable | Purpose | Set where |
|---|---|---|
| `AIPASS_HOME` | Lets external projects find the AIPass registry | `~/.bashrc` + `~/.claude/settings.json` env block |
| `AIPASS_CALLER_BRANCH` | Auto-set by dispatch; identifies the sending branch for feedback/mail | Runtime only, do not set manually |
| `AIPASS_CALLER_CWD` | Auto-set by dispatch; identifies the caller's project directory | Runtime only, do not set manually |

Sensitive values (API keys, tokens, recovery codes) belong in `~/.secrets/aipass/.env`, not in shell rc or repo files.

---

## Reporting bugs

File issues at https://github.com/AIOSAI/AIPass/issues.

Helpful info to include:
- OS and version
- Python version (`python3 --version`)
- Claude Code version (`claude --version`)
- The exact command you ran and the full error output
- Whether you cloned recently or have been on the same checkout for a while (clone age helps us distinguish current bugs from fixed-but-stale-clone issues)

The first external bug report was [#261 by Gavin Rooney](https://github.com/AIOSAI/AIPass/issues/261) — that template is a good example of a useful report.

---

## See also

- [DevPulse README](README.md) — the lean entry point
- [AIPass root README](../../../README.md) — the whole framework
- [STATUS.local.md](STATUS.local.md) — current work and loose ends
- [issue #261](https://github.com/AIOSAI/AIPass/issues/261) — Windows compat tracking
