---
type: domain
title: Data Gateway is read-only extraction to a fixed Parquet staging layout
timestamp: 2026-07-22
author: suresh
tags: [data-gateway, ingestion, parquet, staging]
status: current
---

# Data Gateway is read-only extraction to a fixed Parquet staging layout

## The fact

The Data Gateway bridges the client's SQL Server to the Feature Bank, running entirely inside the client's cloud. Access to the source is read-only. Extraction (incremental plus full refresh) lands Parquet files in a fixed staging layout:

```
data/staging/{client}/{table}/{date}/part-0001.parquet
```

## Why it matters

Read-only is a hard boundary: nothing we run may write to a client's source database, ever. The staging path convention is load-bearing; tooling, backfills, and the Feature Bank all assume it, so don't invent variant layouts. Schema differences across verticals (security, pest control, healthcare) are absorbed by per-client YAML schema mapping in the gateway, not by downstream code.

## Related

See "Feature Bank exists to compute every metric exactly once" for what consumes staging, and "Every client runs a fully isolated stack in their own cloud" for why staging never leaves the client environment.
