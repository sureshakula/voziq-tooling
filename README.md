[![Status](https://img.shields.io/badge/status-beta-yellow)](HERALD.md)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CLIs](https://img.shields.io/badge/CLIs-Claude%20%7C%20Codex%20%7C%20Gemini-purple)](#cli-support)
[![Give Feedback](https://img.shields.io/badge/Give-Feedback-brightgreen)](https://github.com/AIOSAI/AIPass/issues/new?template=feedback.yml)

<!-- TODO: Terminal GIF here — show a dispatch + mail + memory session -->


# AIPass

**Your AI agents remember yesterday.**

A local multi-agent framework where your AI assistants keep their memory between sessions, work together on the same codebase, and never ask you to re-explain context.

---

## Contents

- [The Problem](#the-problem)
- [What AIPass Does](#what-aipass-does)
- [Quick Start](#quick-start)
- [What You Can Do](#what-you-can-do)
- [How It Works](#how-it-works)
- [The 15 Branches](#the-15-branches)
- [CLI Support](#cli-support)
- [Platform Support](#platform-support)
- [Project Status](#project-status)
- [Requirements](#requirements)
- [Subscriptions & Compliance](#subscriptions--compliance)

---

## The Problem

Your AI has memory now. It remembers your name, your preferences, your last conversation. That used to be the hard part. It isn't anymore.

The hard part is everything that comes after. You're still one person talking to one agent in one conversation doing one thing at a time. When the task gets complex, *you* become the coordinator — copying context between tools, dispatching work manually, keeping track of who's doing what. You are the glue holding your AI workflow together, and you shouldn't have to be.

Multi-agent frameworks tried to solve this. They run agents in parallel, spin up specialists, orchestrate pipelines. But they isolate every agent in its own sandbox. Separate filesystems. Separate worktrees. Separate context. One agent can't see what another just built. Nobody picks up where a teammate left off. Nobody works on the same project at the same time. The agents don't know each other exist.

That's not a team. That's a room full of people wearing headphones.

What's missing isn't more agents — it's *presence*. Agents that have identity, memory, and expertise. Agents that share a workspace, communicate through their own channels, and collaborate on the same files without stepping on each other. Not isolated workers running in parallel. A persistent society with operational rules — where the system gets smarter over time because every agent remembers, every interaction builds on the last, and nobody starts from zero.

## What AIPass Does

AIPass is a local CLI framework that gives your AI agents **identity, memory, and teamwork**. Tested with Claude Code, Codex, and Gemini — built to work with any AI that can read a file and follow a prompt.

**Start a project in one command:**

```bash
aipass init ~/Projects/my-saas-app   # coming soon — currently requires dev setup
```

Your project gets its own registry, its own identity, and persistent memory. Your AI reads its context on startup, remembers across sessions, and saves what it learns. Each project is isolated — its own agents, its own mail, its own rules. No cross-contamination between projects.

**Need more than memory? Build a team:**

Use `spawn` to create full agents with the same infrastructure AIPass itself runs on — communication, monitoring, standards, the whole scaffold. Or keep it lightweight with just memory and identity. Your choice:

| What you need | What to use | What you get |
|---------------|-------------|-------------|
| Memory + identity | `aipass init` | Registry, passport, memory files, local prompt |
| A full agent | `spawn create` | All of the above + apps scaffold, mail, dashboard, tests |
| A lightweight agent | `spawn passport` | Identity + rich memory (no apps scaffold) |

**How AIPass itself is built:**

AIPass ships with 15 specialist agents that maintain and develop the framework. They're the reference implementation — proof that the architecture works at scale:

```
devpulse (orchestrator)
   ├── drone    — command routing + @agent resolution
   ├── seedgo   — 33 automated quality standards
   ├── prax     — real-time monitoring across all agents
   ├── ai_mail  — agent-to-agent communication + task dispatch
   ├── flow     — plans, workflows, phased coordination
   ├── spawn    — creates new agents anywhere on your filesystem
   ├── memory   — vector search across archived context
   ├── backup   — versioned backups + Google Drive sync
   └── ...and 6 more specialists
```

These 15 agents work on the **same filesystem, same project, same time**. No sandboxes. No worktrees. No isolation. They see each other's work, coordinate through mail, and share a planning system that prevents conflicts. This is the pattern your projects inherit.

**What makes this different:**

- **Agents are persistent.** They have passports, memories, and expertise that develop over time. They're not disposable workers — they're specialists who remember.
- **Everything is local.** Your data stays on your machine. Memory is JSON files. Communication is local mailbox files. No cloud dependencies, no external APIs for core operations.
- **Projects are isolated by design.** Each project gets its own registry. Agents communicate within their project, not across projects. No external agent can accidentally break your system.
- **You build within the framework, and the framework gives you everything.** Follow the structure and you get memory, monitoring, communication, quality enforcement, backup, and dispatch for free.

**Say "hi" tomorrow and pick up exactly where you left off.**

<p align="right"><a href="#contents">Back to contents</a></p>

---

## Quick Start

```bash
git clone https://github.com/AIOSAI/AIPass.git
cd AIPass
./setup.sh        # Creates venv, installs, bootstraps 15 agents
drone systems     # See all agents
```

Then start working:

```bash
cd src/aipass/devpulse
claude
```

Talk to devpulse. Ask what's happening. Dispatch work. Come back later.

<details>
<summary>Linux (fully tested)</summary>

Works out of the box. This is the primary development platform.

```bash
./setup.sh
```

</details>

<details>
<summary>macOS (untested, should work)</summary>

setup.sh should work on macOS. Known issue: Apple Silicon Macs may need Homebrew path adjustment for symlinks.

```bash
brew install python@3.10
./setup.sh
```

</details>

<details>
<summary>Windows</summary>

**WSL2 (recommended):** setup.sh runs with zero changes inside WSL2.

**Native Windows:** Has been tested on Windows 10 with most functionality working. No setup.ps1 yet — manual setup required.

</details>

<details>
<summary>Docker</summary>

```bash
docker build -t aipass .
docker run -d -p 8080:8080 aipass
```

Opens a code-server IDE with Python, Node.js, and Claude Code pre-installed.

</details>

---

## What You Can Do

- **Start any project with memory.** `aipass init` gives your AI persistent context — it picks up where you left off, every session, no re-explaining.
- **Build your own agents.** Use `spawn` to create agents with the same infrastructure AIPass runs on. Full scaffold or lightweight — your call.
- **Agents work as a team.** Agents within a project share one filesystem, communicate through mail, and coordinate through plans. No sandboxes isolating them.
- **Dispatch work, don't do it yourself.** Send a task to the right agent — it investigates, builds, tests, and reports back. You keep working on something else.
- **Enforce quality automatically.** Define standards, run audits across every agent. Code stays consistent at scale.
- **Use any AI CLI.** Tested with Claude Code, Codex, and Gemini. Same hooks, same identity, same commands. The framework is model-agnostic.
- **Projects stay isolated.** Each project gets its own registry. Your agents talk to each other, not to other projects' agents. No cross-contamination.
- **Scale your way.** One agent with memory, or fifty agents with full infrastructure. The framework grows with your project.

<p align="right"><a href="#contents">Back to contents</a></p>

---

## How It Works

Every agent has three things: an **identity** (who it is), **memory** (what it knows), and a **mailbox** (how it communicates).

```
src/aipass/<agent>/
├── .trinity/           # Identity + memory (persists across sessions)
├── .ai_mail.local/     # Mailbox (receives tasks, sends results)
├── apps/               # What this agent can do
└── README.md
```

You talk to **devpulse** (the orchestrator). It knows every agent's specialty and dispatches work:

```bash
drone @ai_mail dispatch @memory "Archive old sessions" "Find sessions older than 30 days and archive them"
drone @seedgo audit aipass                    # Run quality checks on everything
drone @flow create . "Refactor auth module"   # Create a work plan
```

Pattern: `drone @branch command [args]` — one line, non-interactive.

<p align="right"><a href="#contents">Back to contents</a></p>

---

## The 15 Agents

| Branch | What It Does |
|--------|-------------|
| [**devpulse**](src/aipass/devpulse/README.md) | Orchestrator — you talk to this one. It coordinates everyone else. |
| [**drone**](src/aipass/drone/README.md) | Routes commands to the right branch. The postal service. |
| [**memory**](src/aipass/memory/README.md) | Long-term storage. Vector search over everything branches have learned. |
| [**ai_mail**](src/aipass/ai_mail/README.md) | Messaging between branches. Dispatch tasks, get replies. |
| [**flow**](src/aipass/flow/README.md) | Work plans — tracks what's being built and what's being designed. |
| [**seedgo**](src/aipass/seedgo/README.md) | Quality enforcement — 33 automated checks across all branches. |
| [**prax**](src/aipass/prax/README.md) | Monitoring — logs, dashboards, real-time session tracking. |
| [**trigger**](src/aipass/trigger/README.md) | Event system — things that happen automatically when conditions are met. |
| [**spawn**](src/aipass/spawn/README.md) | Creates new branches from templates. |
| [**cli**](src/aipass/cli/README.md) | Terminal formatting and rich output. |
| [**daemon**](src/aipass/daemon/README.md) | Background scheduler with cron jobs. |
| [**backup**](src/aipass/backup/README.md) | Snapshots, versioned backups, Google Drive sync. |
| [**api**](src/aipass/api/README.md) | LLM access via OpenRouter (optional). |
| [**commons**](src/commons/README.md) | Community space where branches share updates and discuss. |
| [**skills**](src/skills/README.md) | Reusable capabilities that branches can invoke. |

---

## CLI Support

AIPass works with three AI coding CLIs. Claude Code is the most tested.

| CLI | Autonomous Mode | Status |
|-----|----------------|--------|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | `claude -p "prompt" --permission-mode bypassPermissions` | Fully tested |
| [Codex](https://github.com/openai/codex) | `codex exec "prompt" --approval-mode never` | Integrated, less tested |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | `gemini -p "prompt" --approval-mode=yolo` | Integrated, less tested |

setup.sh auto-detects which CLIs are installed and configures hooks for each.

<p align="right"><a href="#contents">Back to contents</a></p>

---

## Platform Support

| Platform | Status |
|----------|--------|
| Linux | Fully tested |
| Windows (WSL2) | Expected to work, zero changes needed |
| Windows (native) | Partial testing on Windows 10 |
| macOS | Untested, should work |

---

## Project Status

**Beta.** Actively developed by a solo developer + AI team.

| Metric | Value |
|--------|-------|
| Agents | 15 |
| Quality standards | 33 |
| Tests | 4,900+ |
| PRs merged | 192+ |
| Development sessions | 76 |

For detailed session history, see [HERALD.md](HERALD.md).

<p align="right"><a href="#contents">Back to contents</a></p>

---

## Requirements

- Python 3.10+
- Linux recommended (macOS should work; Windows via WSL2)
- At least one AI CLI: [Claude Code](https://docs.anthropic.com/en/docs/claude-code) (recommended), [Codex](https://github.com/openai/codex), or [Gemini CLI](https://github.com/google-gemini/gemini-cli)
- `sudo` access (for global CLI symlinks)
- API keys optional (only for the `api` branch — OpenRouter/OpenAI)

<p align="right"><a href="#contents">Back to contents</a></p>

---

<details>
<summary>Subscriptions & Compliance</summary>

### Use your existing subscription

AIPass runs on your **existing CLI subscription** — Claude Pro/Max, Codex, or Gemini. No API keys required for core functionality. No extra costs. Your subscription covers everything.

This works because AIPass runs each CLI as an **official subprocess** — the same binary you'd run yourself in a terminal. It doesn't extract credentials, proxy API calls, or intercept tokens. Your subscription stays within the provider's infrastructure at all times.

This is different from tools like OpenClaw that were [restricted by Anthropic](https://venturebeat.com/technology/anthropic-cracks-down-on-unauthorized-claude-usage-by-third-party-harnesses) for extracting subscription OAuth tokens and routing workloads outside the official CLI. AIPass doesn't do that — it enhances the CLI through officially supported extension points (hooks, CLAUDE.md, AGENTS.md, GEMINI.md).

### What AIPass does NOT do

- Extract or redirect subscription OAuth tokens
- Intercept CLI-to-provider communication
- Bypass rate limits or prompt caching
- Impersonate official CLI clients

Claude Code is proprietary but officially supports hooks and subprocess usage. Codex and Gemini CLI are open source (Apache 2.0). No provider forbids this usage pattern.

> API keys are only needed for the optional `api` agent (OpenRouter/OpenAI). For server/automated deployments, API key authentication is recommended per [Anthropic's guidance](https://code.claude.com/docs/en/legal-and-compliance).

</details>

---

<p align="center"><a href="#aipass">Back to top</a></p>
