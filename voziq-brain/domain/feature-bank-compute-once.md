---
type: domain
title: Feature Bank exists to compute every metric exactly once
timestamp: 2026-07-22
author: suresh
tags: [feature-bank, dbt, architecture]
status: current
---

# Feature Bank exists to compute every metric exactly once

## The fact

Before the Feature Bank, the same metric (MRR being the worst offender) was computed differently in SQL Server stored procedures, ML pipelines, and dashboards, and the numbers disagreed. The Feature Bank computes each feature once; everything else reads that value.

## Why it matters

Any new pipeline, model, or dashboard that computes its own version of an existing metric reintroduces the disease this system was built to cure. If a feature you need doesn't exist, add it to the Feature Bank; never compute it locally.

## Detail

dbt-core over DuckDB with a Parquet lakehouse. Model layers: `staging/` is 1:1 with source tables and light cleaning, `intermediate/` holds business logic and joins, `features/` is final vectors for ML, `marts/` is aggregates for BI. Put logic at the right layer. Two invariants: features are immutable snapshots (computed for a date, stored permanently, with metadata), and no feature ever depends on ML output.
