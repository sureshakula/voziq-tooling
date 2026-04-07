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
- [The 15 Agents](#the-15-agents)
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

**Start with one agent that remembers:**

Your AI reads `.trinity/` on startup and writes back what it learned before the session ends. That's the whole memory model — JSON files your AI can read and write. Next session, it picks up where it left off. No database, no API, no setup beyond one command.

```bash
aipass init ~/Projects/my-saas-app   # coming soon — currently requires dev setup
```

Your project gets its own registry, its own identity, and persistent memory. Each project is isolated — its own agents, its own rules. No cross-contamination between projects.

**Add teammates when you need them:**

When one agent isn't enough, use `spawn` to create specialists with the same infrastructure AIPass runs on — communication, monitoring, standards, the whole scaffold.

| Start here | What to use | What you get |
|------------|-------------|-------------|
| One persistent agent | `aipass init` | Registry, passport, memory files, local prompt |
| A lightweight specialist | `spawn passport` | Identity + rich memory (no apps scaffold) |
| A full specialist | `spawn create` | All of the above + apps scaffold, mail, dashboard, tests |

**How AIPass itself is built:**

AIPass ships with 15 specialist agents that maintain and develop the framework. It looks like a lot — but every agent follows one pattern and needs one command:

```bash
drone @branch command [args]    # Every agent, every task. Drone handles routing.
```

Drone resolves who you're talking to, routes the work, and handles errors. You never need to know where anything lives. Each agent has the same directory layout — learn the pattern once and you know every agent.

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

These 15 agents work on the **same filesystem, same project, same time**. No sandboxes. No worktrees. No isolation. They see each other's work, coordinate through mail, and share a planning system that prevents conflicts.

**How they stay out of each other's way:**

- **Agent locks** — an agent can't run twice simultaneously. Dispatch checks for active locks before waking anyone.
- **PR locks** — only one agent creates a PR at a time. No merge conflicts from parallel commits.
- **File isolation** — branches don't touch each other's files. Hard rule, enforced every session.
- **Standards baked in** — quality checks are embedded in every workflow template. Agents follow them without being told.
- **Self-healing** — the monitoring system detects errors and can dispatch the offending agent to fix itself.

This is the pattern your projects inherit.

**What makes this different:**

- **Agents are persistent.** They have memories and expertise that develop over time. They're not disposable workers — they're specialists who remember.
- **Everything is local.** Your data stays on your machine. Memory is JSON files. Communication is local mailbox files. No cloud dependencies, no external APIs for core operations.
- **Projects are isolated by design.** Each project gets its own registry. Agents communicate within their project, not across projects. No external agent can accidentally break your system.
- **Standards are baked into the workflow.** Quality isn't an afterthought — workflow templates inject standards directly into every plan, ensuring agents follow best practices automatically.

**Say "hi" tomorrow and pick up exactly where you left off.** One agent or fifteen — the memory persists.

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
claude                # devpulse reads its memory, knows who it is, picks up where it left off
```

Say "hi." devpulse reads its identity and memory files, tells you what's been happening, and is ready to dispatch work. Come back tomorrow — it remembers.

```bash
# See the system in action:
drone @seedgo audit aipass              # Run 33 quality checks across all agents
drone @flow create . "Add user auth"    # Create a work plan
drone systems                           # List every agent and what it does
```

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
- **Dispatch work, don't do it yourself.** Send a task to the right agent — it investigates, builds, tests, and reports back. You keep working on something else.
- **Or work with an agent directly.** `cd src/aipass/memory && claude` — sit down with a specialist one-on-one for complex problems. Direct access is a first-class workflow, not a fallback. The agent has its own memory, its own expertise, and picks up where you left off.
- **Agents work as a team.** Agents within a project share one filesystem, communicate through mail, and coordinate through plans. No sandboxes isolating them.
- **Enforce quality automatically.** Standards are embedded in every workflow template. Agents follow them without being told. Code stays consistent at scale.
- **Use any AI CLI.** Tested with Claude Code, Codex, and Gemini. Same hooks, same identity, same commands.
- **Scale your way.** One agent with memory, or fifty agents with full infrastructure. The framework grows with your project.

<p align="right"><a href="#contents">Back to contents</a></p>

---

## How It Works

**One agent:** Your AI reads `.trinity/` on startup and writes back what it learned. That's the whole memory model — JSON files on disk. Next session, it picks up where it left off.

**A team:** When one agent isn't enough, every agent shares the same structure:

```
src/aipass/<agent>/
├── .trinity/           # Identity + memory (persists across sessions)
├── .ai_mail.local/     # Mailbox (receives tasks, sends results)
├── apps/               # Entry point → modules → handlers
└── README.md           # Domain knowledge (the agent reads this on startup)
```

Identical layout everywhere. If you know one agent, you know all of them. Communication happens through mail, coordination through plans, and routing through one command:

```bash
drone @seedgo audit aipass                    # Run quality checks on everything
drone @flow create . "Refactor auth module"   # Create a work plan
drone @ai_mail dispatch @memory "Archive old sessions" "Find sessions older than 30 days"
```

**Two ways to work:**

- **Team mode (most of the time):** Talk to `devpulse`, dispatch work across the team. Agents work in parallel and report back.
- **Direct mode (for deeper work):** `cd src/aipass/memory && claude` — work one-on-one with a specialist when the problem needs focused domain expertise.

<p align="right"><a href="#contents">Back to contents</a></p>

---

## The 15 Agents

You don't need to memorize this list. Start with `devpulse`, use `drone` to reach any agent, and learn the rest as your workflow expands.

**You interact with one:** [**devpulse**](src/aipass/devpulse/README.md) — the orchestrator. You talk to it, it coordinates everyone else.

**Core infrastructure** — how agents connect:

| Agent | Role |
|-------|------|
| [**drone**](src/aipass/drone/README.md) | Routes `drone @branch command` to the right agent |
| [**ai_mail**](src/aipass/ai_mail/README.md) | Agent-to-agent messaging and task dispatch |
| [**memory**](src/aipass/memory/README.md) | Long-term vector search across all agent knowledge |
| [**spawn**](src/aipass/spawn/README.md) | Creates new agents from templates |

**Quality and operations** — how the system stays healthy:

| Agent | Role |
|-------|------|
| [**seedgo**](src/aipass/seedgo/README.md) | 33 automated quality standards, enforced across all agents |
| [**prax**](src/aipass/prax/README.md) | Real-time monitoring, logs, dashboards |
| [**flow**](src/aipass/flow/README.md) | Work plans, phased coordination |
| [**trigger**](src/aipass/trigger/README.md) | Event-driven automation + self-healing |

**Support** — everything else:

| Agent | Role |
|-------|------|
| [**cli**](src/aipass/cli/README.md) | Terminal formatting and rich output |
| [**daemon**](src/aipass/daemon/README.md) | Background scheduler with cron jobs |
| [**backup**](src/aipass/backup/README.md) | Snapshots, versioned backups, Google Drive sync |
| [**api**](src/aipass/api/README.md) | LLM access via OpenRouter (optional) |
| [**commons**](src/commons/README.md) | Community space for agent updates and discussion |
| [**skills**](src/skills/README.md) | Reusable capabilities agents can invoke |

---

## CLI Support

AIPass works with three AI coding CLIs. Claude Code is the most tested.

| CLI | Autonomous Mode | Status |
|-----|----------------|--------|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | `claude -p "prompt" --permission-mode bypassPermissions` | Fully tested |
| [Codex](https://github.com/openai/codex) | `codex exec "prompt" --dangerously-bypass-approvals-and-sandbox` | Integrated, less tested |
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

**Beta.** Actively developed by a solo developer working with the AI agents themselves — every PR, every test, every fix is human-AI collaboration.

| Metric | Value |
|--------|-------|
| Agents | 15 |
| Quality standards | 33 automated checks |
| Tests | 4,900+ (across all agents) |
| PRs merged | 192+ (created by agents, reviewed by human) |
| Development sessions | 78 |

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
