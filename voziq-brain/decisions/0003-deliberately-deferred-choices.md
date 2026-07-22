---
type: decision
title: Choices we have deliberately deferred
timestamp: 2026-07-22
author: suresh
tags: [meta, orchestration, mlops, architecture]
status: accepted
---

# 0003: Choices we have deliberately deferred

## Context

Several infrastructure choices keep resurfacing in design conversations. Recording the deferrals so they stop being re-litigated by accident, and so designs don't quietly assume tools we haven't adopted.

## Decision

Three things are parked, on purpose. Orchestration stays on Jenkins; the Prefect versus Dagster evaluation is deferred, so don't design around either. MLflow and model tracking are removed from the current architecture; don't reintroduce tracking dependencies. Multi-tenant architecture is off the table; we are single-tenant per client and designs must not hedge toward shared infrastructure.

## Alternatives we rejected

Deciding now. Each of these is a real future conversation, but adopting any of them mid-restructure would couple two migrations together. The GitLab restructure and the AI tooling rollout take priority.

## Consequences

Anyone proposing a design that assumes Prefect, Dagster, MLflow, or shared tenancy should link to this note and make the case for un-deferring first, as its own decision, rather than smuggling the assumption into a feature design. When one of these gets un-deferred, supersede this note.
