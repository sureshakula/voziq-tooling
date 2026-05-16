[![Status](https://img.shields.io/badge/status-beta-yellow)](#project-status)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/aipass)](https://pypi.org/project/aipass/)
[![CLI](https://img.shields.io/badge/CLI-Claude%20Code-purple)](#cli-support)
[![Give Feedback](https://img.shields.io/badge/Give-Feedback-brightgreen)](https://github.com/AIOSAI/AIPass/issues/new?template=feedback.yml)
[![codecov](https://codecov.io/gh/AIOSAI/AIPass/graph/badge.svg)](https://codecov.io/gh/AIOSAI/AIPass)
[![OSS Health](https://oss-health-monitor.vercel.app/api/badge/AIOSAI/AIPass)](https://github.com/volotat/OSS-Health-Monitor)

# AIPass

**Your AI agents remember yesterday.**

A local multi-agent framework where your AI assistants keep their memory between sessions, work together on the same codebase, and never ask you to re-explain context.

---

## Contents

- [The Problem](#the-problem)
- [What AIPass Does](#what-aipass-does)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [The 12 Agents](#the-12-agents)
- [CLI Support](#cli-support)
- [Project Status](#project-status)
- [Requirements](#requirements)
- [Roadmap](#roadmap)

---

## The Problem

Your AI has memory now. It remembers your name, your preferences, your last conversation. That used to be the hard part. It isn't anymore.

The hard part is everything that comes after. You're still one person talking to one agent in one conversation doing one thing at a time. When the task gets complex, *you* become the coordinator — copying context between tools, dispatching work manually, keeping track of who's doing what. You are the glue holding your AI workflow together, and you shouldn't have to be.

Multi-agent frameworks tried to solve this. They run agents in parallel, spin up specialists, orchestrate pipelines. But they isolate every agent in its own sandbox. Separate filesystems. Separate worktrees. Separate context. One agent can't see what another just built. Nobody picks up where a teammate left off. Nobody works on the same project at the same time. The agents don't know each other exist.

That's not a team. That's a room full of people wearing headphones.

> *"Where else would AI presence exist except in memory? Code doesn't make AI aware — memory makes it possible."* — AIPass

What's missing isn't more agents — it's *presence*. Agents that have identity, memory, and expertise. Agents that share a workspace, communicate through their own channels, and collaborate on the same files without stepping on each other. Not isolated workers running in parallel. A persistent society with operational rules — where the system gets smarter over time because every agent remembers, every interaction builds on the last, and nobody starts from zero.

## What AIPass Does

AIPass is a local CLI framework that gives your AI agents **identity, memory, and teamwork**. Built and tested with Claude Code on Linux/WSL. Designed for terminal-native coding agents that support instruction files, hooks, and subprocess invocation.

**Start with one agent that remembers:**

Your AI reads `.trinity/` on startup and writes back what it learned before the session ends. That's the whole memory model — JSON files your AI can read and write. Next session, it picks up where it left off. No database, no API, no setup beyond one command.

```bash
mkdir my-project && cd my-project
aipass init run
```

A 12-step guided setup walks you through everything: system detection, health check, profile, CLI choice, agent creation, and handoff. At the end, a new terminal window opens with your first AI agent ready to talk. The whole thing takes about 5 minutes.

Your project gets its own registry, its own identity, and persistent memory. Each project is isolated — its own agents, its own rules. No cross-contamination between projects.

**Add agents when you need them:**

```bash
aipass init agent my-agent            # Full agent: apps, mail, memory, identity
```

| What you need | Command | What you get |
|---------------|---------|-------------|
| A new project | `aipass init` | Project scaffold (registry, prompts, hooks, docs) |
| Guided setup | `aipass init run` | 12-step interactive onboarding — creates project + first agent + handoff |
| Another agent | `aipass init agent <name>` | Apps scaffold, mailbox, memory, identity — registered in project |
| A lightweight agent | `drone @spawn create <name> --template birthright` | Identity + memory only (no apps scaffold) |

**What makes this different:**

- **Agents are persistent.** They have memories and expertise that develop over time. They're not disposable workers — they're specialists who remember.
- **Everything is local.** Your data stays on your machine. Memory is JSON files. Communication is local mailbox files. No cloud dependencies, no external APIs for core operations.
- **One pattern for everything.** Every agent follows the same structure. One command (`drone @branch command`) reaches any agent. Learn it once, use it everywhere.
- **Projects are isolated by design.** Each project gets its own registry. Agents communicate within their project, not across projects.
- **The system protects itself.** Agent locks prevent double-dispatch. Git access is tier-controlled through drone. Branches don't touch each other's files. Quality standards are embedded in every workflow. Errors trigger self-healing.

**Say "hi" tomorrow and pick up exactly where you left off.** One agent or fifteen — the memory persists.

---

## Quick Start

### Start your own project

```bash
pip install aipass

mkdir my-project && cd my-project
aipass init run                       # 12-step guided setup — creates project, first agent, opens terminal
```

That's it. The setup creates your project, runs a health check, asks your name, creates your first AI agent, and opens a new terminal window where that agent is already running. Your agent has identity, memory, a mailbox, and knows what AIPass is. Say "hi" — it picks up where it left off. Come back tomorrow, it remembers.

Want more control? Use the individual commands:

```bash
aipass init                           # Just the project scaffold (no guided setup)
aipass init agent my-agent            # Add another agent to your project
aipass doctor                         # Check system health
```

> **Need help?** [Ask in Discussions](https://github.com/AIOSAI/AIPass/discussions) or [file feedback](https://github.com/AIOSAI/AIPass/issues/new?template=feedback.yml) — both take 30 seconds.

Your project automatically gets access to every AIPass service — dispatch work to specialists, create plans, run quality audits, monitor agents in real-time. Agents within your project can email each other. All through `drone @branch command`.

### Explore the full framework

Clone the repo to see all 12 agents working together — the reference implementation:

```bash
git clone https://github.com/AIOSAI/AIPass.git
cd AIPass
./setup.sh                            # Creates venv, installs, bootstraps 12 agents
drone systems                         # See all agents

cd src/aipass/devpulse
claude                                # Talk to the orchestrator
```

```bash
# Things you can do:
aipass doctor                            # Check system health (15+ checks)
drone @seedgo audit aipass               # Run 34 quality checks across all agents
drone @flow create . "Add user auth"     # Create a work plan
drone @ai_mail dispatch @agent "Subject" "Body"  # Send task + wake an agent
drone @prax monitor run                  # Watch all agent activity in real-time
drone systems                            # List every agent and what it does
```

---

## How It Works

**One agent:** Run `aipass init run` and in 5 minutes you have a project with an agent that reads `.trinity/` on startup and picks up where it left off. Memory files have limits — when they fill up, the memory agent automatically archives older entries into a searchable vector database (ChromaDB). Nothing is lost — it just moves from active memory to long-term recall.

**A team:** When one agent isn't enough, every agent shares the same structure:

```
src/aipass/<agent>/
├── .trinity/           # Identity + memory (persists across sessions)
├── .ai_mail.local/     # Mailbox (receives tasks, sends results)
├── apps/               # Entry point → modules → handlers
└── README.md           # Domain knowledge (the agent reads this on startup)
```

Identical layout everywhere. If you know one agent, you know all of them. One command reaches anyone:

```bash
drone @branch command [args]    # Every agent, every task. Drone handles routing.
```

```bash
drone @seedgo audit aipass                    # Run quality checks on everything
drone @flow create . "Refactor auth module"   # Create a work plan
drone @ai_mail dispatch @memory "Archive old sessions" "Find sessions older than 30 days"
```

**Two ways to use AIPass:**

- **Your own project:** `aipass init run` sets up a new project with your first agent. Add more agents as you need them. Your first agent is the orchestrator — it coordinates the others.
- **The full framework:** Clone the repo to work with all 12 core agents. Talk to `devpulse` (the orchestrator), dispatch work across specialists. Agents work in parallel and report back.

**AIPass ships with 12 core agents** that maintain and develop the framework — the reference implementation proving the architecture works at scale:

```
devpulse (orchestrator)
   ├── aipass   — concierge + onboarding (aipass init, doctor, profile)
   ├── drone    — command routing + @agent resolution
   ├── seedgo   — 34 automated quality standards
   ├── prax     — real-time monitoring across all agents
   ├── ai_mail  — agent-to-agent communication + task dispatch
   ├── flow     — plan lifecycle, templates, auto-archival
   ├── spawn    — creates new agents anywhere on your filesystem
   ├── memory   — automatic archival, ChromaDB, semantic search
   ├── api      — LLM access layer (OpenRouter, multi-provider)
   ├── trigger  — event-driven automation + self-healing
   └── cli      — terminal formatting and rich output
```

These agents work on the **same filesystem, same project, same time** — no sandboxes, no worktrees. This is the pattern your projects inherit.

---

## The 12 Agents

You don't need to memorize this list. Start with `devpulse`, use `drone` to reach any agent, and learn the rest as your workflow expands.

**You interact with one:** [**devpulse**](src/aipass/devpulse/README.md) — the orchestrator. You talk to it, it coordinates everyone else.

**Core infrastructure** — how agents connect:

| Agent | Role |
|-------|------|
| [**aipass**](src/aipass/aipass/README.md) | Concierge — `aipass init`, doctor, profile, onboarding |
| [**drone**](src/aipass/drone/README.md) | Routes `drone @branch command` to the right agent |
| [**ai_mail**](src/aipass/ai_mail/README.md) | Agent-to-agent messaging and task dispatch |
| [**memory**](src/aipass/memory/README.md) | Memory lifecycle — automatic archival, ChromaDB vectors, semantic search |
| [**api**](src/aipass/api/README.md) | LLM access layer — multi-provider routing (OpenRouter) |
| [**spawn**](src/aipass/spawn/README.md) | Creates new agents from templates |

**Quality and operations** — how the system stays healthy:

| Agent | Role |
|-------|------|
| [**seedgo**](src/aipass/seedgo/README.md) | 34 automated quality standards, enforced across all agents |
| [**prax**](src/aipass/prax/README.md) | Real-time monitoring, logs, dashboards |
| [**flow**](src/aipass/flow/README.md) | Plan lifecycle — 6 template types, auto-archival, vector verification |
| [**trigger**](src/aipass/trigger/README.md) | Event-driven automation + self-healing |
| [**cli**](src/aipass/cli/README.md) | Terminal formatting and rich output |

---

## CLI Support

AIPass is built and tested with **Claude Code** on Linux/WSL.

| CLI | Autonomous Mode | Status |
|-----|----------------|--------|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | `claude -p "prompt" --permission-mode bypassPermissions` | Fully tested |
| [Codex](https://github.com/openai/codex) | `codex exec "prompt" --dangerously-bypass-approvals-and-sandbox` | Experimental — see [Roadmap](#roadmap) |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | `gemini -p "prompt" --approval-mode=yolo` | Experimental — see [Roadmap](#roadmap) |

setup.sh auto-detects which CLIs are installed and configures hooks for each.

---

## Project Status

**Beta.** Actively developed by a solo developer working with the AI agents themselves — every PR, every test, every fix is human-AI collaboration.

| Metric | Value |
|--------|-------|
| Version | 2.3.0 |
| Agents | 12 core + user-created |
| Quality standards | 34 automated checks |
| Tests | 7,600+ (across all agents) |
| PRs merged | 560+ (human-AI collaboration) |

Each agent documents its own operational status in its branch README — what works, what doesn't, and why.

---

## Requirements

- Python 3.10+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- Linux, macOS, or WSL (all CI-tested)
- `sudo` access optional (for `/usr/local/bin` symlinks — falls back to `~/.local/bin` without sudo)
- API keys optional (OpenRouter/OpenAI — for optional add-on agents)

## Roadmap

These items have partial work done and are under ongoing testing:

- **macOS support** — CI green, full test suite passing ([#360](https://github.com/AIOSAI/AIPass/issues/360))
- **Windows native** — CI green, full test suite passing
- **Codex CLI** — hooks and AGENTS.md wired, needs end-to-end testing
- **Gemini CLI** — hooks and GEMINI.md wired, needs end-to-end testing
- **Fork contributor workflow** — improved error handling for fork-based PRs ([#329](https://github.com/AIOSAI/AIPass/issues/329))

---

<details>
<summary>Uninstall</summary>

### Remove AIPass from a project

AIPass stores everything locally in your project directory. To remove it:

```bash
# Remove AIPass files from your project
rm -rf .aipass/ .claude/ .ai_mail.local/ hooks/ src/
rm -f CLAUDE.md AGENTS.md GEMINI.md STATUS.local.md *_REGISTRY.json .gitignore

# If you installed via pip
pip uninstall aipass
```

No cloud accounts, no external services, no cleanup beyond your local filesystem.

### Remove a single agent

Use spawn's delete command to cleanly archive and deregister:

```bash
drone @spawn delete @agent_name
```

This archives the agent's directory and removes it from the registry.

</details>

<details>
<summary>Subscriptions & Compliance</summary>

### Use your existing subscription

AIPass runs on your **existing CLI subscription** — Claude Pro/Max, Codex, or Gemini. No API keys required for core functionality. No extra costs beyond your existing subscription.

This works because AIPass runs each CLI as an **official subprocess** — the same binary you'd run yourself in a terminal. It doesn't extract credentials, proxy API calls, or intercept tokens. Your subscription stays within the provider's infrastructure at all times.

### What AIPass does NOT do

- Extract or redirect subscription OAuth tokens
- Intercept CLI-to-provider communication
- Bypass rate limits or prompt caching
- Impersonate official CLI clients

Claude Code is proprietary but officially supports hooks and subprocess usage. Codex and Gemini CLI are open source (Apache 2.0).

> API keys are only needed for optional add-on agents (OpenRouter/OpenAI). For server/automated deployments, API key authentication is recommended per [Anthropic's guidance](https://code.claude.com/docs/en/legal-and-compliance).

</details>
