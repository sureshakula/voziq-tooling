# UX Probe -- Fresh Eyes Review

**Reviewer:** Builder agent (simulating first-time developer clone)
**Date:** 2026-04-26
**Scope:** README, setup, onboarding, CLI, drone, branch docs, .claude config, HERALD, pyproject.toml

---

## First Impressions

The README is genuinely good. The opening hook -- "Your AI agents remember yesterday" -- immediately communicates the value proposition. The "Problem" section articulates a real pain point (you are the glue holding your AI workflow together) that resonates with anyone who has tried to coordinate AI tools manually.

The Quick Start is clean: three commands to get going (`pip install aipass`, `mkdir && cd`, `aipass init`). That is a strong first impression. The table showing "what you need / command / what you get" is the single most useful element on the page for a new user.

The 311-line README manages to be comprehensive without drowning you. The collapsible sections (Uninstall, Subscriptions) are a nice touch -- they keep the page scannable while still being thorough.

One thing that jumped out immediately: the README says version 2.1.0 but pyproject.toml says 2.2.0. Small thing, but the kind of detail that makes a new developer wonder "is this maintained?" when they catch it.

---

## Onboarding Experience

### The pip install path (new project)

This is the smoother path. `pip install aipass` gives you two CLI commands: `aipass` and `drone`. The `aipass init` command creates 12 scaffold files. The output after init tells you what to do next (create an agent, start a session, read the docs). This is well-designed.

However, I had to read the init_project.py source code to understand this. The README shows `aipass init` but the actual CLI routing goes through `drone @cli aipass init` internally. If a user runs `aipass --help`, they would get... what exactly? The CLI entry point calls `cli.apps.cli:main()` which discovers modules and routes. Running `aipass` with no args gives you a "Discovered Modules" introspection that mentions `drone @cli aipass` as the way to explore. That is confusing -- you ran `aipass` and the tool tells you to use `drone @cli aipass` instead. The `aipass` command should feel self-sufficient for project bootstrapping, not redirect you to drone.

### The clone path (full framework)

`git clone && cd && ./setup.sh` is the heavier path. setup.sh is an 811-line bash script that:
- Finds Python, creates a venv, installs in editable mode
- Bootstraps identity files for all 11 agents
- Installs Claude Code hooks into `~/.claude/settings.json`
- Optionally installs Codex and Gemini hooks
- Creates global symlinks (requires sudo on Linux)
- Sets AIPASS_HOME in your shell profile

This is thorough but invasive. It writes to `~/.bashrc`, `~/.claude/settings.json`, and `/usr/local/bin/`. A developer cloning a repo to evaluate it would not expect that. There is no `--dry-run` flag and no confirmation prompt. The script just does it.

For someone who already has Claude Code configured with their own hooks, `setup.sh` will **overwrite** their entire `~/.claude/settings.json` hooks block. The Python script in setup.sh does `settings["hooks"] = { ... }` which replaces the whole hooks key. This is destructive.

### What is missing from onboarding

1. **No `--dry-run` for setup.sh.** You cannot preview what it will do before it does it.
2. **No "what just happened?" summary after pip install.** Running `pip install aipass` gives you the commands but no guidance unless you already read the README.
3. **The relationship between `aipass` and `drone` is unclear.** Both are installed. When do I use which? The README uses both interchangeably in examples. A new user would not know that `aipass init` and `drone @cli aipass init` are the same thing.
4. **No quickstart for "I just want one agent in my existing project."** The README assumes you want to create a new project. What if I have an existing codebase and just want memory persistence for my Claude Code sessions?

---

## Documentation Gaps

### Gap 1: The @ syntax is never formally defined

`drone @seedgo audit aipass` -- what does the `@` mean? The README uses it everywhere but never explains the grammar. Is it `drone @<agent> <command> [args]`? Always? What happens if I type `drone seedgo audit aipass` without the `@`? The drone README explains the routing flow (branch resolution via registry) but the actual syntax rule is implicit, not stated.

### Gap 2: How agents actually communicate is hand-waved

The README says "agents communicate within their project" and mentions ai_mail. But how? If I create two agents in my project, how does agent A send a message to agent B? The README shows `drone @ai_mail email @agent "Subject"` but this is the AIPass framework talking to itself. For a user's own project, is there a simpler way? What triggers an agent to check its mail?

### Gap 3: .trinity/ files are described philosophically but not practically

The CLAUDE.md culture doc says "Your `.trinity/local.json` is your session history." But what is the actual JSON schema? What fields can I set? What are the limits? The memory README mentions "v1: line-count" and "v2: entry-count" schemas but never shows an example of what a populated local.json looks like. setup.sh has the bootstrap template but it is buried in a heredoc in a bash script.

### Gap 4: No troubleshooting guide

What do I do if `drone @seedgo audit aipass` hangs? What if `aipass init` fails? What if hooks are not firing? There is no FAQ, no troubleshooting section, no "common problems" document.

### Gap 5: HERALD.md is internal-only useful

HERALD.md documents 86 sessions of development history. For a contributor or someone studying the architecture, this is gold. For a new user, it is overwhelming and does not help them use the tool. It is also slightly stale -- it references 230+ PRs and 3,500 tests while the README claims 470+ PRs and 6,500+ tests.

### Gap 6: The `.claude/` directory has two README paths that diverge

The `.claude/README.md` describes a manual setup process (copy global_hooks to `~/.claude/hooks/`, configure settings.json by hand). But `setup.sh` does all of this automatically. Which is the canonical path? If I run setup.sh, do I also need to follow the README steps? If I do both, will they conflict?

---

## What Confused Me

### 1. `aipass` vs `drone` -- two CLIs, unclear boundary

pyproject.toml registers two console_scripts: `aipass = aipass.cli:cli_entry` and `drone = aipass.drone.cli:main`. The README uses both. `aipass init` creates projects. `drone @branch command` does everything else. But `drone @cli aipass init` also creates projects. Why are there two entry points? Which one is "mine"?

**My best guess after reading the code:** `aipass` is the project management CLI (init, update). `drone` is the agent dispatch CLI (routing commands to agents). But this is never stated.

### 2. The "branch" terminology

Everything is called a "branch" -- drone, seedgo, memory, etc. But these are not git branches. They are Python packages under `src/aipass/`. The README says "agents live in branches." The spawn docs talk about "branch lifecycle management." The registry is called `AIPASS_REGISTRY.json` and tracks "branches." But git branches are also heavily used (citizen branches, system-pr). The overloading of "branch" to mean both "agent directory" and "git branch" is genuinely confusing.

### 3. The hooks architecture requires deep reading to understand

The `.claude/README.md` explains that project settings do not fire UserPromptSubmit hooks from subdirectories, so hooks must go in global settings. This is a Claude Code limitation, not an AIPass design choice -- but it means setup.sh modifies your global Claude Code config. A new user would not understand why this is necessary without reading DPLAN-0053.

### 4. "Citizen class" terminology

spawn has "citizen classes" (builder, birthright). The CLAUDE.md culture document talks about "citizenship." Agents have "passports." This anthropomorphic language is charming but obscures the technical reality. A "builder" citizen class means "full scaffold with apps/, tests/, etc." A "birthright" class means "just .trinity/ and a README." These are just template levels -- calling them citizen classes adds cognitive overhead for new users.

### 5. Where does my project's data live?

After `aipass init`, my project gets a registry, global prompt, CLAUDE.md, etc. After `aipass init agent my-agent`, the agent lives in `src/my-agent/`. But the README also mentions `AIPASS_HOME` as an environment variable pointing to the framework clone. So my project depends on the framework installation? The external project support section of the drone README clarifies this (dual registry lookup, module fallback) but this is a deep-in-the-docs answer to a first-five-minutes question.

---

## What Impressed Me

### 1. The architecture is genuinely consistent

Every agent follows the exact same pattern: `.trinity/`, `.ai_mail.local/`, `apps/` with modules/ and handlers/. The three-layer design (entry point, modules, handlers) is enforced everywhere. Once you understand one agent, you understand the structure of all of them. This is rare in multi-agent systems.

### 2. The branch READMEs are excellent

drone, spawn, and memory each have detailed READMEs with:
- Clear "what I do" section
- Full CLI command reference with examples
- Architecture diagram showing the file tree
- Integration points (depends on / provides to)
- Test counts and quality metrics
- Known issues -- honestly stated

These READMEs are the best documentation in the project. They are better than the top-level README for understanding what each agent actually does.

### 3. Cross-platform support is real

setup.sh handles Linux, macOS (including stock Python 3.9 with auto-install via brew or uv), and Windows (Git Bash, MSYS2, Cygwin, PowerShell wrapper for the @ symbol). The Windows drone wrapper that handles PowerShell's splatting operator is a detail that shows real user testing.

### 4. The seedgo quality system

33 automated checks enforced across all agents. Every branch README reports its seedgo compliance score. This is self-documenting quality -- you can see at a glance which agents are at 100% and which have known issues.

### 5. The memory model is simple and smart

JSON files that the AI reads on startup and writes before session end. No database required for basic use. ChromaDB for overflow archival is optional. The simplicity of "just read .trinity/ on startup" is the kind of design that scales because it is easy to understand.

### 6. Defensive coding in setup.sh

The script checks for Python version, handles venv creation edge cases on Windows, detects shadowing drone installs, creates secrets directories with proper permissions, and seeds config from .example files. It is clear this script has been battle-tested across environments.

### 7. The pyproject.toml is clean

Minimal dependencies (rich, watchdog, requests). Optional extras are clearly separated (llm, memory, dev). The build system uses hatchling. The test and coverage configuration is reasonable.

---

## Suggestions for New Users

### For the README

1. **Add a one-line definition of the @ syntax** early in the Quick Start: "The `@` prefix addresses an agent by name. `drone @seedgo audit aipass` means: drone, route the command `audit aipass` to the agent named `seedgo`."

2. **Clarify `aipass` vs `drone`** -- add a small box: "`aipass` manages your project (init, update). `drone` talks to agents (@agent command). Both are installed by pip."

3. **Fix the version number.** README says 2.1.0, pyproject.toml and __init__.py say 2.2.0.

4. **Add a "Just want memory for your existing project?" section** with a 2-command quickstart that does not require creating a new project directory.

### For setup.sh

5. **Add `--dry-run` support.** Print what the script would do without doing it.

6. **Merge hooks instead of replacing.** The Python block that writes `~/.claude/settings.json` should merge AIPass hooks with existing hooks, not overwrite the hooks key.

7. **Add a confirmation prompt** before writing to `~/.bashrc` and `~/.claude/settings.json`. Or at minimum, print a warning: "This script will modify your global Claude Code settings. Press Enter to continue or Ctrl+C to cancel."

### For documentation

8. **Create a TROUBLESHOOTING.md** or FAQ section. Common issues: hooks not firing, drone not found on PATH, agent creation failing, registry corruption.

9. **Add a `.trinity/` schema reference** -- a single page showing the JSON structure of passport.json, local.json, and observations.json with field descriptions.

10. **Reconcile the .claude/README.md with setup.sh.** State clearly: "If you ran setup.sh, hooks are already installed. The manual steps below are for users who installed via pip only."

### For terminology

11. **Consider calling agents "agents" consistently**, not "branches" and "citizens" interchangeably. The branch/citizen/agent terminology overlap adds friction for new users. Use "agent" in user-facing docs, keep "branch" and "citizen" as internal/cultural terms.

### For the CLI

12. **Make `aipass --help` useful on its own.** Currently it shows module discovery output that says "use drone @cli aipass." The help should show the init commands directly since that is the only thing the `aipass` CLI does.

---

*Review conducted by reading source code, README, setup.sh, 3 branch READMEs (drone, spawn, memory), .claude/ configuration, HERALD.md, pyproject.toml, and CLI entry points. No commands were executed -- this is a pure code-reading review.*
