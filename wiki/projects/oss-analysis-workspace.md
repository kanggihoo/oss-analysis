---
title: oss-analysis Workspace
created: 2026-06-09
updated: 2026-06-09
type: project
tags: [workspace, open-source, project, workflow, llm-wiki, evidence]
sources: [AGENTS.md, OSS_ANALYSIS_WORKFLOW.md]
confidence: high
---

# oss-analysis Workspace

`/Users/kkh/Desktop/oss-analysis` is the working directory for the Hermes `oss-analyst` profile. Its purpose is to analyze open-source repositories through a repeatable evidence-backed workflow and preserve durable knowledge in the LLM Wiki.

## Current active layout

Verified on 2026-06-09:

```text
oss-analysis/
├── AGENTS.md
├── OSS_ANALYSIS_WORKFLOW.md
├── scripts/
├── artifacts/
├── reports/
├── repos/
└── wiki/
```

## Directory roles

- `repos/`: local repository checkouts and primary source evidence.
- `artifacts/`: raw outputs from DeepWiki, graphify, Understand-Anything, static analysis, and other analyzers.
- `reports/`: human-facing per-repo analysis reports. It is currently empty, so future analyses should write new reports here.
- `wiki/`: this LLM-managed knowledge base for durable synthesis.

See [[workspace-boundaries]] for the detailed boundary rules.

## Analysis flow

The workspace workflow remains:

```text
repo clone/update
→ local/external analyzer capture
→ source verification
→ reports writing
→ wiki update
→ reuse in later analysis/comparison
```

The quality gate is [[evidence-backed-analysis]]: claims from DeepWiki, graphify, and Understand-Anything are hypotheses until verified against source files in `repos/<repo>/`.

## Wiki relationship

[[llm-wiki-operating-model]] describes how this wiki is maintained. The wiki should store durable project summaries, reusable concepts, comparisons, and high-value query answers; it should not store temporary progress logs or large duplicated analyzer dumps.
