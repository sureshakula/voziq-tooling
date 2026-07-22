---
type: domain
title: MRR calculation is YAML config, not code
timestamp: 2026-07-22
author: suresh
tags: [feature-bank, mrr, config, revenue]
status: current
---

# MRR calculation is YAML config, not code

## The fact

MRR rules are defined per client in YAML (base column, adjustments like promo discounts, segment filters), interpreted by one shared implementation. This replaced per-client stored procedures.

## Why it matters

When a client's MRR is wrong or needs a new adjustment, the fix is a config change, not a code change. Anyone reaching for Python or SQL to handle a client's revenue quirk is solving it in the wrong layer.

## Detail

The config shape, roughly:

```yaml
mrr:
  base_column: monthly_charge
  adjustments:
    - type: discount
      column: promo_discount
      operation: subtract
  segments:
    - name: residential
      filter: "customer_type = 'residential'"
```

Client configs extend a common base, so shared rules live once and clients override only what differs.
