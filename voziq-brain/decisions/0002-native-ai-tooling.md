---
type: decision
title: Standardize on native AI tooling, not agent frameworks
timestamp: 2026-07-22
author: suresh
tags: [meta, ai-tooling, claude-code, copilot, codex]
status: accepted
---

# 0002: Standardize on native AI tooling, not agent frameworks

## Context

We're rolling out AI coding agents across the team while restructuring GitLab. The team is mixed-tool: Claude Code, Copilot, Codex, GLM through compatible CLIs, and some people using no agent at all. We evaluated AIPass, an open-source multi-agent framework offering persistent agent memory, identity, inter-agent mail, and standards auditing, as a possible scaffold. We handle subscriber data for clients in regulated verticals, so any tooling that moves data through third parties is suspect by default, and engineers run on existing subscriptions, so API-key-based frameworks change the cost model.

## Decision

No third-party agent framework. Each seat uses its own tool's native capabilities (memory, instruction files, commands). Shared knowledge lives in this brain repo. Instructions are AGENTS.md-first with a CLAUDE.md shim. Hard enforcement (secret scan, hardcoded-client check, lint) runs server-side in GitLab CI on every merge request, so the safety model does not depend on which tool a seat runs.

## Alternatives we rejected

- AIPass: well-engineered, but native Claude Code had absorbed 80 to 90 percent of what it offered by mid-2026, it's a solo-maintainer beta, and it only helps Claude seats. We kept its useful patterns (standards-as-gate, session capture) and dropped the dependency.
- Ruflo (claude-flow): an independent audit found most of its tools were stubs returning fabricated metrics, plus a supply-chain incident. Disqualified outright.
- Letta: serious memory architecture, but it's a replacement CLI on API-key economics, not an overlay on the tools people already run.
- Mem0 and Zep: default pipelines send memory content to OpenAI. Non-starter for our data posture.

## Consequences

Zero new runtime dependencies and no framework to maintain or fork. Per-seat memory quality is whatever each vendor ships, which we accept; if recall depth becomes a real problem on Claude seats, claude-mem (local SQLite, subscription-powered) is the sanctioned escalation, evaluated on one seat first. Team-level knowledge compounds only through this repo, which makes the memo ritual load-bearing: if capture stops, we lose the layer no vendor provides. Revisit this decision if a framework ever offers something the native stack plus this brain demonstrably cannot.
