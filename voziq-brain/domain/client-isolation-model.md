---
type: domain
title: Every client runs a fully isolated stack in their own cloud
timestamp: 2026-07-22
author: suresh
tags: [deployment, clients, architecture, compliance]
status: current
---

# Every client runs a fully isolated stack in their own cloud

## The fact

Each client gets a complete, separate deployment (Data Gateway, Feature Bank, ML models, dashboards) inside the client's own cloud environment. Zero infrastructure is shared between clients. We are deliberately single-tenant, and staying that way.

## Why it matters

Two consequences shape almost every design conversation. First, nothing can assume cross-client access, shared services, or centralized data; designs that need those are dead on arrival. Second, onboarding a new client must require zero code changes, only new YAML (schema mapping plus config extending the common base). If a feature needs client-specific code, the design is wrong.

## Detail

Data leaves the client environment never. The Data Gateway has read-only access to the client's SQL Server and extracts to Parquet staging inside their cloud. This isolation is also our strongest compliance story, which is why "no external SaaS dependencies, no code paths that transmit data externally" is a hard rule, not a preference.
