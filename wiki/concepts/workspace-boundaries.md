---
title: Workspace Boundaries
created: 2026-06-09
updated: 2026-06-09
type: concept
tags: [workspace, workflow, evidence, reporting, tooling]
sources: [AGENTS.md, OSS_ANALYSIS_WORKFLOW.md]
confidence: high
---

# Workspace Boundaries

This page defines what belongs in each top-level directory of `/Users/kkh/Desktop/oss-analysis`.

## Canonical directories

| Directory | Role | Write policy |
|---|---|---|
| `repos/<repo>/` | Local git checkout; primary source evidence | Clone/update repos here. Do not use analyzer output as source truth. |
| `artifacts/<repo>/` | Raw analyzer and external-baseline output | Store DeepWiki, graphify, Understand-Anything, static analysis, metadata. |
| `reports/<repo>/` | Human-facing analysis documents | Write readable overview, architecture, code map, risk, dependency, test/CI reports. |
| `wiki/` | LLM-managed durable synthesis | Store reusable project summaries, concepts, comparisons, and durable queries. |

## Evidence boundary

[[evidence-backed-analysis]] depends on this separation:

- `repos/` answers “what does the code actually do?”
- `artifacts/` answers “what did tools or external baselines claim?”
- `reports/` answers “what did we conclude for a human reader?”
- `wiki/` answers “what durable knowledge should future analysis reuse?”

## Wiki boundary

[[llm-wiki-operating-model]] should not copy entire repos or analyzer outputs into the wiki. Instead, wiki pages cite paths in `repos/`, `artifacts/`, and `reports/`, then synthesize only the reusable knowledge.
