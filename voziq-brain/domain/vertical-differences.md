---
type: domain
title: What actually differs between our three verticals
timestamp: 2026-07-22
author: suresh
tags: [verticals, clients, home-security, pest-control, healthcare]
status: current
---

# What actually differs between our three verticals

## The fact

Three verticals, three different retention shapes. Home security is contract-based with equipment leases and monitoring fees. Pest control is service-based with strong seasonal patterns and route optimization concerns. Healthcare is patient retention under HIPAA.

## Why it matters

Features and models that transfer cleanly between verticals are the exception, not the rule. Tenure means something different under a contract than under a seasonal service relationship; churn signals differ accordingly. And healthcare work carries HIPAA obligations on top of our normal data posture, so anything touching a healthcare client gets the stricter reading of every rule.

## Detail

This is also why the Data Gateway does schema mapping per client in YAML: the verticals don't share database shapes, and the platform absorbs that at ingestion rather than letting it leak downstream.
